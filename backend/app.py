# main_app.py

# Import necessary libraries from Flask and other packages
import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import torch
from transformers import DetrImageProcessor, DetrForObjectDetection
import requests # Used to fetch image from URL if needed, good for testing




# ----------------- INITIALIZATION -----------------
# Initialize the Flask application
app = Flask(__name__)
# Enable Cross-Origin Resource Sharing (CORS) to allow the frontend to access the API
CORS(app)
# --- Database Configuration ---
# Get the database URL from the environment variable we set in docker-compose.yml
# Use SQLite as a fallback for local development if DATABASE_URL is not set
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
# Disable a feature of SQLAlchemy that we don't need and which adds overhead
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Initialize the SQLAlchemy object with our Flask app
db = SQLAlchemy(app)

# --- Database Model Definition ---
# This class defines the structure of the 'analysis_results' table in our database.
class AnalysisResult(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Primary key for the record
    image_filename = db.Column(db.String(100), nullable=False) # Name of the uploaded file
    detected_objects_json = db.Column(db.JSON, nullable=False) # Store the detected objects as JSON
    suggestions_json = db.Column(db.JSON, nullable=False) # Store the suggestions as JSON
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # Timestamp

    def __repr__(self):
        return f'<AnalysisResult {self.id}>'


# ----------------- AI MODEL LOADING -----------------
# This part is crucial and can be slow, so it's done once when the server starts.

# Load the pre-trained object detection model and its processor from Hugging Face
# DETR (DEtection TRansformer) is a powerful model for object detection.
# We are using the 'facebook/detr-resnet-50' version.
print("Loading model...") # Log message to know when model loading starts
processor = DetrImageProcessor.from_pretrained('facebook/detr-resnet-50')
model = DetrForObjectDetection.from_pretrained('facebook/detr-resnet-50')
print("Model loaded successfully!") # Log message to confirm model is ready

# ----------------- SUGGESTION LOGIC -----------------
# This is a simple rule-based suggestion engine.
# It's a dictionary where keys are object labels and values are suggestions.
# This can be expanded significantly or replaced with a more advanced system (like an LLM).
SUGGESTION_DATABASE = {
    'person': 'Consider the lighting on the person. Is it flattering? Natural light from a window is often a great choice.',
    'car': 'To make the car look more dynamic, try taking the photo from a lower angle.',
    'chair': 'If this is for a room design, think about the chair\'s placement. Does it invite conversation or block a path?',
    'sofa': 'A few throw pillows or a cozy blanket can make a sofa look much more inviting.',
    'potted plant': 'Ensure the plant is healthy and the pot is clean. It adds a touch of nature to the scene.',
    'bed': 'A neatly made bed with layered pillows can instantly make a bedroom look more put-together.',
    'dining table': 'A simple centerpiece, like a vase of flowers or a bowl of fruit, can elevate the look of a dining table.',
    'tv': 'Is the TV the focal point? If not, consider hiding it within a gallery wall or a cabinet to make the room feel less centered around electronics.',
    'laptop': 'For a clean desk setup, consider cable management solutions to hide wires.',
    'book': 'Stacking books horizontally with a small object on top can be more visually interesting than a simple row.',
    'clock': 'An interesting clock can be a piece of art. Does this one match the room\'s style?',
    'default': 'Try to find a clear subject for your photo. What is the main story you want to tell with this image?'
}


# ----------------- API ENDPOINTS -----------------

@app.route('/api/analyze', methods=['POST'])
def analyze_image():
    """
    This function handles the image analysis API endpoint.
    It expects a multipart/form-data request with an image file.
    """
    # Check if an image file is present in the request
    if 'image' not in request.files:
        # If no image is found, return an error response
        return jsonify({'error': 'No image file provided'}), 400

    # Get the image file from the request
    file = request.files['image']
    
    # Try to open the image using Pillow to ensure it's a valid image file
    try:
        image = Image.open(file.stream).convert('RGB')
    except Exception as e:
        # If the file cannot be opened as an image, return an error
        return jsonify({'error': f'Invalid image file: {e}'}), 400

    # --- Object Detection ---
    # Process the image using the pre-loaded processor. This prepares the image for the model.
    inputs = processor(images=image, return_tensors="pt")
    # Pass the processed inputs to the model to get the predictions.
    outputs = model(**inputs)
    # The model outputs a lot of data. We need to process it to get human-readable results.
    # We set a threshold of 0.7 to keep more detections (was 0.9).
    target_sizes = torch.tensor([image.size[::-1]])
    results = processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.7)[0]

    # --- Formatting Results ---
    detected_objects = []
    # Loop through the detection results
    for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
        # Get the name of the detected object from the model's configuration
        label_name = model.config.id2label[label.item()]
        # Create a dictionary for the detected object with its details
        detected_objects.append({
            'label': label_name,
            'confidence': round(score.item(), 3), # Confidence score, rounded to 3 decimal places
            'box': [round(i, 2) for i in box.tolist()] # Bounding box coordinates
        })

    # --- Generating Suggestions ---
    suggestions = []
    # Create a set of unique labels to avoid duplicate suggestions
    unique_labels = set(d['label'] for d in detected_objects)
    # If no objects are detected, provide a default suggestion
    if not unique_labels:
        suggestions.append(SUGGESTION_DATABASE['default'])
    else:
        # For each unique object detected, find a corresponding suggestion
        for label in unique_labels:
            # If a specific suggestion exists for the label, add it.
            # Otherwise, you could add a more generic one or do nothing.
            if label in SUGGESTION_DATABASE:
                suggestions.append(SUGGESTION_DATABASE[label])
    
    # --- SAVING TO DATABASE ---
    try:
        # Create a new record using our AnalysisResult model
        new_result = AnalysisResult(
            image_filename=file.filename,
            detected_objects_json=detected_objects, # The list of dicts we created
            suggestions_json=suggestions # The list of strings we created
        )
        # Add the new record to the database session
        db.session.add(new_result)
        # Commit the session to save the changes to the database
        db.session.commit()
    except Exception as e:
        # If there's an error with the database, log it to the server console.
        # In a real production app, you'd have more robust error logging.
        print(f"Error saving to database: {e}")
        # We don't want a DB error to stop the user from getting their results,
        # so we don't return an error here, we just log it.
    
    # --- Final Response ---
    # Combine the detected objects and suggestions into a single JSON response
    return jsonify({
        'detected_objects': detected_objects,
        'suggestions': suggestions
    })
# --- A NEW ENDPOINT TO VIEW DATABASE CONTENT (for verification) ---
@app.route('/api/history', methods=['GET'])
def get_history():
    """
    Retrieves all analysis results from the database.
    """
    try:
        # Query the database for all records in the AnalysisResult table, ordered by most recent first.
        all_results = AnalysisResult.query.order_by(AnalysisResult.created_at.desc()).all()
        # Format the results into a list of dictionaries.
        results_list = [
            {
                'id': result.id,
                'filename': result.image_filename,
                'detected_objects': result.detected_objects_json,
                'suggestions': result.suggestions_json,
                'timestamp': result.created_at.isoformat()
            }
            for result in all_results
        ]
        return jsonify(results_list)
    except Exception as e:
        print(f"Error fetching history: {e}")
        return jsonify({'error': 'Could not fetch history from database'}), 500

# This block ensures that the Flask server runs only when the script is executed directly
# (and not when imported as a module).

# --- Global error handler to always return JSON ---
@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    return jsonify({'error': f'Internal server error: {str(e)}', 'trace': traceback.format_exc()}), 500

if __name__ == '__main__':
    # Run the app on host 0.0.0.0 to make it accessible from outside the container
    # The port is set to 5001 to avoid conflicts with other common ports.
    # debug=True will auto-reload the server on code changes, but should be False in production.
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5001, debug=True)

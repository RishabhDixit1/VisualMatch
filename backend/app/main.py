from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.preprocessing import image as keras_image
from tensorflow.keras.models import Model
import faiss
import os
import shutil
import uuid
from typing import List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS (Cross-Origin Resource Sharing)
origins = [
    "http://localhost:3000", # Frontend
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Variables & Configuration ---
IMAGE_DIR = "static/images"
FAISS_INDEX_PATH = "/app/faiss_index_storage/image_features.index" # Path inside Docker volume
IMAGE_LIST_PATH = "/app/faiss_index_storage/image_list.txt" # Path inside Docker volume

# Ensure directories exist
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)

# Load pre-trained ResNet50 model + higher level layers
logger.info("Loading ResNet50 model...")
try:
    base_model = ResNet50(weights='imagenet', include_top=False, pooling='avg')
    # If you want to use a specific layer output, you can define the model like this:
    # base_model = ResNet50(weights='imagenet', include_top=False)
    # model = Model(inputs=base_model.input, outputs=base_model.get_layer('conv5_block3_out').output)
    # For simplicity, using average pooling output which is a 1D vector (2048,)
    model = base_model
    FEATURE_DIMENSION = model.output_shape[1]
    logger.info(f"ResNet50 model loaded. Feature dimension: {FEATURE_DIMENSION}")
except Exception as e:
    logger.error(f"Error loading ResNet50 model: {e}")
    model = None # Handle gracefully if model loading fails

# FAISS Index
faiss_index = None
image_path_list = []

def load_faiss_index_and_list():
    global faiss_index, image_path_list
    if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(IMAGE_LIST_PATH):
        logger.info(f"Loading FAISS index from {FAISS_INDEX_PATH}")
        faiss_index = faiss.read_index(FAISS_INDEX_PATH)
        logger.info(f"FAISS index loaded. Total vectors: {faiss_index.ntotal}")
        with open(IMAGE_LIST_PATH, "r") as f:
            image_path_list = [line.strip() for line in f.readlines()]
        logger.info(f"Image list loaded. Total paths: {len(image_path_list)}")
    else:
        logger.info("FAISS index or image list not found. Initializing new index.")
        faiss_index = faiss.IndexFlatL2(FEATURE_DIMENSION) # L2 distance
        image_path_list = []
        # Optionally, scan IMAGE_DIR and add existing images
        rebuild_index_from_disk()

def save_faiss_index_and_list():
    if faiss_index is not None:
        logger.info(f"Saving FAISS index to {FAISS_INDEX_PATH}")
        faiss.write_index(faiss_index, FAISS_INDEX_PATH)
        with open(IMAGE_LIST_PATH, "w") as f:
            for path in image_path_list:
                f.write(f"{path}\n")
        logger.info("FAISS index and image list saved.")

def rebuild_index_from_disk():
    """Rebuilds index if it's empty or not found, from images on disk."""
    global faiss_index, image_path_list
    logger.info(f"Rebuilding index from images in {IMAGE_DIR}...")
    current_images_on_disk = [os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR)
                              if os.path.isfile(os.path.join(IMAGE_DIR, f)) and f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not current_images_on_disk and faiss_index.ntotal == 0:
        logger.info("No images on disk to rebuild index from.")
        return

    # Reset index and list before rebuilding
    faiss_index = faiss.IndexFlatL2(FEATURE_DIMENSION)
    image_path_list = []
    
    features_to_add = []
    for img_path_on_disk in current_images_on_disk:
        try:
            logger.info(f"Processing {img_path_on_disk} for index rebuild.")
            # Use relative path for web serving
            relative_img_path = os.path.join("static/images", os.path.basename(img_path_on_disk))
            
            img = keras_image.load_img(img_path_on_disk, target_size=(224, 224))
            img_array = keras_image.img_to_array(img)
            expanded_img_array = np.expand_dims(img_array, axis=0)
            preprocessed_img = preprocess_input(expanded_img_array)
            features = model.predict(preprocessed_img, verbose=0).flatten()
            
            features_to_add.append(features)
            image_path_list.append(relative_img_path)
        except Exception as e:
            logger.error(f"Error processing image {img_path_on_disk} for rebuild: {e}")

    if features_to_add:
        faiss_index.add(np.array(features_to_add, dtype=np.float32))
        logger.info(f"Rebuilt index with {faiss_index.ntotal} images.")
    save_faiss_index_and_list()


# --- Application Startup ---
@app.on_event("startup")
async def startup_event():
    if model is None:
        logger.error("Model not loaded. Backend might not function correctly.")
        # You might want to raise an exception here or prevent startup
    load_faiss_index_and_list()
    if faiss_index.ntotal == 0: # If index is still empty after loading (e.g. first run)
        rebuild_index_from_disk()

# --- Helper Functions ---
def extract_features(image_bytes: bytes) -> np.ndarray:
    if model is None:
        raise HTTPException(status_code=500, detail="Image processing model not available.")
    try:
        img = Image.open(image_bytes).convert("RGB")
        img = img.resize((224, 224))
        img_array = keras_image.img_to_array(img)
        expanded_img_array = np.expand_dims(img_array, axis=0)
        preprocessed_img = preprocess_input(expanded_img_array)
        features = model.predict(preprocessed_img, verbose=0) # verbose=0 to suppress progress bar
        return features.flatten() # Flatten to 1D array
    except Exception as e:
        logger.error(f"Error during feature extraction: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing image for feature extraction: {e}")


# --- API Endpoints ---
@app.post("/api/upload")
async def upload_image_to_db(file: UploadFile = File(...)):
    global faiss_index, image_path_list
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")

    try:
        contents = await file.read()
        
        # Save image
        filename = f"{uuid.uuid4()}_{file.filename}"
        image_save_path = os.path.join(IMAGE_DIR, filename)
        with open(image_save_path, "wb") as f:
            f.write(contents)
        
        # Extract features
        features = extract_features(image_bytes=contents) # Pass bytes directly
        
        # Add to FAISS index and list
        faiss_index.add(np.array([features], dtype=np.float32))
        relative_image_path = os.path.join("static/images", filename) # Path for web serving
        image_path_list.append(relative_image_path)
        
        save_faiss_index_and_list()
        
        logger.info(f"Uploaded {filename}. Index size: {faiss_index.ntotal}")
        return {"message": "Image uploaded and processed successfully", "filename": filename, "path": relative_image_path, "features_shape": features.shape}
    except HTTPException as e: # Re-raise HTTPExceptions
        raise e
    except Exception as e:
        logger.error(f"Error in /api/upload: {e}")
        # Clean up partially saved file if error occurs after saving
        if 'image_save_path' in locals() and os.path.exists(image_save_path):
            os.remove(image_save_path)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/api/find_similar")
async def find_similar_images(file: UploadFile = File(...), k: int = 5):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Query file is not an image.")
    if faiss_index is None or faiss_index.ntotal == 0:
        raise HTTPException(status_code_404, detail="Image database is empty. Please upload images first.")

    try:
        contents = await file.read()
        query_features = extract_features(image_bytes=contents)
        
        # Ensure k is not greater than the number of items in the index
        num_items_in_index = faiss_index.ntotal
        actual_k = min(k, num_items_in_index)
        
        if actual_k == 0: # Should not happen if check above is done, but good for safety
             return {"message": "No images in the database to search.", "results": []}

        distances, indices = faiss_index.search(np.array([query_features], dtype=np.float32), actual_k)
        
        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if 0 <= idx < len(image_path_list): # Boundary check
                results.append({
                    "path": image_path_list[idx],
                    "distance": float(distances[0][i]) # L2 distance, lower is better
                })
            else:
                logger.warning(f"FAISS returned an out-of-bounds index: {idx}")
        
        logger.info(f"Found {len(results)} similar images for query.")
        return {"message": "Search complete", "results": results}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in /api/find_similar: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred during similarity search: {str(e)}")

# Mount static files (for serving uploaded images)
# The path "/static/images" in the URL will map to the "static/images" directory in the backend app.
app.mount("/static/images", StaticFiles(directory=IMAGE_DIR), name="static_images")

if __name__ == "__main__":
    import uvicorn
    # This part is for local dev without Docker, Docker CMD will override this.
    uvicorn.run(app, host="0.0.0.0", port=8000)
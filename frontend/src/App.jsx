// App.jsx

// Import React hooks for state management (useState) and other necessary tools.
import React, { useState } from 'react';
// Import Axios for making HTTP requests to our backend API.
import axios from 'axios';
// Import the stylesheet for this component.
import './App.css';

function App() {
  // --- STATE MANAGEMENT ---
  // `useState` is a React Hook that lets you add state to function components.

  // `imageFile`: Stores the actual image file selected by the user. Initial value is null.
  const [imageFile, setImageFile] = useState(null);
  // `previewUrl`: Stores a URL for the selected image to display it in the browser. Initial value is null.
  const [previewUrl, setPreviewUrl] = useState(null);
  // `analysisResult`: Stores the data received from the backend (detected objects, suggestions). Initial value is null.
  const [analysisResult, setAnalysisResult] = useState(null);
  // `isLoading`: A boolean to track whether an API call is in progress. Used to show a loading message.
  const [isLoading, setIsLoading] = useState(false);
  // `error`: Stores any error message that occurs during the process.
  const [error, setError] = useState('');

  // --- EVENT HANDLERS ---

  /**
   * Handles the file input change event.
   * This function is called when the user selects a file.
   * @param {Event} e - The event object from the file input.
   */
  const handleFileChange = (e) => {
    // Get the first file from the list of selected files.
    const file = e.target.files[0];
    if (file) {
      // If a file was selected, update the state.
      setImageFile(file);
      // Create a temporary URL for the image file to show a preview.
      setPreviewUrl(URL.createObjectURL(file));
      // Reset previous results and errors.
      setAnalysisResult(null);
      setError('');
    }
  };

  /**
   * Handles the form submission.
   * This function is called when the "Analyze Image" button is clicked.
   */
  const handleSubmit = async () => {
    // Check if an image has been selected.
    if (!imageFile) {
      setError('Please select an image file first.');
      return;
    }

    // Prepare for the API call.
    setIsLoading(true); // Show loading indicator
    setError(''); // Clear previous errors
    setAnalysisResult(null); // Clear previous results

    // `FormData` is a web API to construct a set of key/value pairs representing form fields.
    // This is how we send a file to the backend.
    const formData = new FormData();
    // Append the image file to the form data with the key 'image'. The backend expects this key.
    formData.append('image', imageFile);

    try {
      // --- API CALL ---
      // Send a POST request to the backend's /api/analyze endpoint.
      // The URL points to the backend service. When running with Docker Compose,
      // we'll proxy this through Nginx. For local dev, it's http://localhost:5001.
      const response = await axios.post('/api/analyze', formData, {...AppdefaultProps, headers: { 'Content-Type': 'multipart/form-data' }});

      // If the request is successful, update the state with the received data.
      setAnalysisResult(response.data);

    } catch (err) {
      // If an error occurs during the API call...
      // Set an appropriate error message to display to the user.
      setError(err.response?.data?.error || 'An unexpected error occurred.');
    } finally {
      // This block will run whether the request succeeded or failed.
      setIsLoading(false); // Hide loading indicator
    }
  };

  // --- JSX RENDER ---
  // This is the HTML-like structure of our component.
  return (
    <div className="container">
      <header className="header">
        <h1>VisualMatch - Image Recognition & Suggestion System</h1>
      </header>
      
      <main className="main-content">
        <section className="upload-section">
          <h2>1. Upload an Image</h2>
          {/* File input for image selection */}
          <input type="file" onChange={handleFileChange} accept="image/*" />
          {/* Button to trigger the analysis */}
          <button onClick={handleSubmit} disabled={isLoading || !imageFile}>
            {isLoading ? 'Analyzing...' : 'Analyze Image'}
          </button>
          
          {/* Display the selected image preview if a URL is available */}
          {previewUrl && <img src={previewUrl} alt="Selected Preview" className="image-preview" />}
        </section>

        <section className="results-section">
          <h2>2. Analysis & Suggestions</h2>
          {/* Show a loading message while waiting for the API response */}
          {isLoading && <p className="loading-indicator">Analyzing image, please wait... (This can take a moment)</p>}
          
          {/* Display any error messages */}
          {error && <p className="error-message">{error}</p>}
          
          {/* Display the results if they are available */}
          {analysisResult && (
            <div>
              <h3>Detected Objects:</h3>
              {/* Check if any objects were detected */}
              {analysisResult.detected_objects.length > 0 ? (
                <ul className="results-list">
                  {/* Map over the array of detected objects and create a list item for each */}
                  {analysisResult.detected_objects.map((obj, index) => (
                    <li key={index}>
                      <strong>{obj.label}</strong> (Confidence: {obj.confidence * 100}%)
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No objects detected with high confidence.</p>
              )}

              <h3>Suggestions for Improvement:</h3>
              <ul className="suggestions-list">
                {/* Map over the array of suggestions and create a list item for each */}
                {analysisResult.suggestions.map((sugg, index) => (
                  <li key={index}>{sugg}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

function App() {
  const [dbImageFile, setDbImageFile] = useState(null);
  const [queryImageFile, setQueryImageFile] = useState(null);
  const [queryPreview, setQueryPreview] = useState(null);
  const [similarImages, setSimilarImages] = useState([]);
  const [message, setMessage] = useState({ text: '', type: '' }); // type: 'success' or 'error'
  const [isLoadingDbUpload, setIsLoadingDbUpload] = useState(false);
  const [isLoadingQuery, setIsLoadingQuery] = useState(false);

  const handleDbImageChange = (event) => {
    setDbImageFile(event.target.files[0]);
  };

  const handleQueryImageChange = (event) => {
    const file = event.target.files[0];
    setQueryImageFile(file);
    if (file) {
      setQueryPreview(URL.createObjectURL(file));
    } else {
      setQueryPreview(null);
    }
  };

  const showMessage = (text, type, duration = 3000) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: '', type: '' }), duration);
  };

  const handleDbUpload = async () => {
    if (!dbImageFile) {
      showMessage('Please select an image to upload to the database.', 'error');
      return;
    }
    setIsLoadingDbUpload(true);
    const formData = new FormData();
    formData.append('file', dbImageFile);

    try {
      const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      showMessage(`Database: ${response.data.message}`, 'success');
      setDbImageFile(null); // Clear file input
      document.getElementById('db-file-input').value = ''; // Reset file input visually
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Error uploading image to database.';
      showMessage(`Database Error: ${errorMsg}`, 'error');
      console.error('Error uploading DB image:', error);
    } finally {
      setIsLoadingDbUpload(false);
    }
  };

  const handleFindSimilar = async () => {
    if (!queryImageFile) {
      showMessage('Please select a query image.', 'error');
      return;
    }
    setIsLoadingQuery(true);
    setSimilarImages([]); // Clear previous results
    const formData = new FormData();
    formData.append('file', queryImageFile);
    // formData.append('k', 5); // Optional: number of results, backend defaults to 5

    try {
      const response = await axios.post(`${API_BASE_URL}/find_similar`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setSimilarImages(response.data.results || []);
      if (response.data.results && response.data.results.length > 0) {
        showMessage(`Found ${response.data.results.length} similar images.`, 'success');
      } else {
        showMessage('No similar images found, or database might be empty.', 'success');
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Error finding similar images.';
      showMessage(`Query Error: ${errorMsg}`, 'error');
      console.error('Error finding similar images:', error);
    } finally {
      setIsLoadingQuery(false);
    }
  };

  // Cleanup object URL
  useEffect(() => {
    return () => {
      if (queryPreview) {
        URL.revokeObjectURL(queryPreview);
      }
    };
  }, [queryPreview]);

  return (
    <div className="container">
      <h1>VisualMatch - Similar Image Finder</h1>

      {message.text && (
        <div className={`message ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="upload-section">
        <h2>Upload Image to Database</h2>
        <input type="file" id="db-file-input" accept="image/*" onChange={handleDbImageChange} />
        <button onClick={handleDbUpload} disabled={isLoadingDbUpload}>
          {isLoadingDbUpload ? 'Uploading...' : 'Upload to DB'}
        </button>
      </div>

      <div className="query-section">
        <h2>Find Similar Images</h2>
        <input type="file" accept="image/*" onChange={handleQueryImageChange} />
        {queryPreview && (
          <div>
            <p>Query Preview:</p>
            <img src={queryPreview} alt="Query Preview" className="preview-image" />
          </div>
        )}
        <button onClick={handleFindSimilar} disabled={isLoadingQuery || !queryImageFile}>
          {isLoadingQuery ? 'Searching...' : 'Find Similar'}
        </button>
      </div>

      {similarImages.length > 0 && (
        <div>
          <h2>Results:</h2>
          <div className="results-grid">
            {similarImages.map((img, index) => (
              <div key={index} className="result-item">
                <img
                  src={`${API_BASE_URL.replace('/api', '')}/${img.path}`} // Construct full URL
                  alt={`Similar ${index}`}
                  className="result-image"
                />
                <p>Distance: {img.distance.toFixed(4)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
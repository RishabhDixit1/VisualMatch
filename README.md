# VisualMatch - Similar Image Finder

Finds visually similar images using a pre-trained ResNet50 model for feature extraction and FAISS for similarity search.

## Project Structure

-   `backend/`: FastAPI application for image processing, feature extraction, and similarity search.
-   `frontend/`: React application for the user interface.
-   `docker-compose.yml`: Defines services for frontend and backend.

## Prerequisites

-   Docker
-   Docker Compose

## Setup & Run

1.  Clone the repository.
2.  Navigate to the `visualmatch` directory.
3.  Build and run the containers:
    ```bash
    docker-compose up --build
    ```
4.  Open your browser:
    -   Frontend: `http://localhost:3000`
    -   Backend API (docs): `http://localhost:8000/docs`

## How it Works

1.  **Upload to Database:** Upload images via the "Upload Image to Database" section.
    -   The backend saves the image.
    -   Extracts features using ResNet50.
    -   Adds the feature vector to a FAISS index.
    -   The FAISS index and a list of image paths are persisted.
2.  **Find Similar Images:** Upload a query image.
    -   The backend extracts features from the query image.
    -   Searches the FAISS index for the most similar image vectors.
    -   Returns the paths to the similar images.

## Notes

-   The FAISS index and uploaded images are persisted in Docker volumes (`faiss_index_data` and `image_data` respectively).
-   The first time the backend starts and no FAISS index is found, it will try to build one from any images already present in `backend/app/static/images/`.
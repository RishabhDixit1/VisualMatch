FROM python:3.9-slim

WORKDIR /app

# Install system dependencies that might be needed by Pillow or other libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories if they don't exist and set permissions
RUN mkdir -p /app/static/images /app/faiss_index_storage
RUN chmod -R 777 /app/static/images /app/faiss_index_storage

COPY ./app /app

# Ensure TensorFlow doesn't try to write to a non-existent home dir during model download
ENV TF_KERAS_CACHE_DIR=/tmp/.keras

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# Use an official Python runtime as a parent image.
# Using 'slim' version for a smaller image size.
FROM python:3.9-slim

# Set the working directory inside the container.
# All subsequent commands will be run from this directory.
WORKDIR /app

# Copy the file that lists the dependencies.
COPY requirements.txt .

# Install any needed packages specified in requirements.txt.
# Increase pip timeout and use a fast mirror for large packages like torch.
ENV PIP_DEFAULT_TIMEOUT=1000
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# Copy the rest of the application's code into the container's /app directory.
COPY . .

# Make port 5001 available to services outside this container.
# Flask will run on this port.
EXPOSE 5001

# Define the command to run the application.
# This is executed when the container starts.
CMD ["python", "app.py"]

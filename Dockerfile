# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install system dependencies for Tesseract and OpenCV
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy your local project files into the container
COPY . /app

# Install the Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 10000

# Command to run the application using Gunicorn (production server)
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
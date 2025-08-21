# Use an official Python runtime as a parent image
# Using a slim version to keep the image size down
FROM python:3.12-slim

# Set environment variables to improve Python's performance in a container
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to leverage Docker's layer caching
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Run the web service on container startup using gunicorn.
# Cloud Run automatically sets the PORT environment variable.
# Using 'exec' ensures that gunicorn runs as PID 1 and receives signals correctly.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
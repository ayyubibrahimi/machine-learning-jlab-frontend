# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Install poppler-utils and other dependencies
RUN apt-get update && apt-get install -y poppler-utils

# Set the working directory
WORKDIR /workspace

# Copy the requirements file first and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Command to run the function
CMD ["functions-framework", "--target=uploadFunction"]

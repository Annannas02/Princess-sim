# Use an official Python runtime as a base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port on which the app will run
EXPOSE 5050

# Define environment variable
ENV FLASK_APP=auth_service.py

# Command to run the app
CMD ["flask", "run", "--host=0.0.0.0", "--port=5050"]
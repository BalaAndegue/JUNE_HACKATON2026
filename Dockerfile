FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn for production
RUN pip install --no-cache-dir gunicorn

# Copy project files
COPY . /app/

# Create directory for uploads and SQLite database
RUN mkdir -p /app/instance /app/uploads

# Expose backend port
EXPOSE 5000

# Start Flask app using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "run:app"]

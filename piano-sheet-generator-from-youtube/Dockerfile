# Use a lightweight Python base image
FROM python:3.9-slim

# Install system dependencies (FFmpeg, yt-dlp requires it)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    yt-dlp \
    bc \
    && rm -rf /var/lib/apt/lists/*

# Install img2pdf
RUN pip install --no-cache-dir img2pdf flask

# Set working directory
WORKDIR /app

# Copy application files
COPY web_app.py .
COPY templates/ templates/

# Expose port (Render/Railway use this)
EXPOSE 5000

# Start the Flask app
CMD ["python", "web_app.py"]

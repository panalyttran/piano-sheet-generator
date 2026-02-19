# Use a modern Python base image (3.11 for yt-dlp compatibility)
FROM python:3.11-slim

# Install system dependencies (FFmpeg, JS runtime for yt-dlp)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    bc \
    nodejs \
    npm \
    && ln -s /usr/bin/nodejs /usr/bin/node \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages (yt-dlp via pip is more up-to-date)
RUN pip install --no-cache-dir img2pdf flask yt-dlp -U

# Set working directory
WORKDIR /app

# Copy application files
COPY web_app.py .
COPY templates/ templates/

# Expose port (Render/Railway use this)
EXPOSE 5000

# Start the Flask app
CMD ["python", "web_app.py"]

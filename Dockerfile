# Use a full Python image for better tool support (including JS runtimes)
FROM python:3.11

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    bc \
    nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages (yt-dlp latest is critical)
RUN pip install --no-cache-dir img2pdf flask yt-dlp -U

# Set working directory
WORKDIR /app

# Copy application files (Copy root files directly)
COPY . .

# Expose port
EXPOSE 5000

# Start the Flask app
CMD ["python", "web_app.py"]

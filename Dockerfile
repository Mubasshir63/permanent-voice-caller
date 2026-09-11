FROM python:3.11-slim

# Install system dependencies needed for audio/network streaming
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 7860 (Hugging Face's default web port)
EXPOSE 7860

# Run the script
CMD ["python", "main.py"]

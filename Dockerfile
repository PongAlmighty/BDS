# Use a lightweight Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY index.html .
COPY Windchimes.mp3 .

# Expose ports: 8080 for Web, 8765 for WebSocket
EXPOSE 8080
EXPOSE 8765

# Run the server
CMD ["python", "server.py"]

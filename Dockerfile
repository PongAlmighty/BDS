# Use a lightweight Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Ensure Python output is sent straight to terminal (e.g. your container log)
# without being first buffered and that you can see the output of your application (e.g. django logs) in real time.
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY index.html .
COPY Windchimes.mp3 .
COPY nut.obj .

# Expose ports: 18080 for Web, 18765 for WebSocket
EXPOSE 18080
EXPOSE 18765

# Run the server
CMD ["python", "server.py"]

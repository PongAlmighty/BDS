---
description: Build and push the BDS container to Docker Hub
---

# Push to Docker Hub

This workflow will help you build, tag, and push your image to Docker Hub.

1.  **Login to Docker Hub** (if not already logged in):
    ```bash
    docker login
    ```
    *(Enter your username and password/token when prompted)*

2.  **Build and Tag the Image**:
    Replace `your-username` with your actual Docker Hub username in the commands below.
    
    **Option A: Multi-Arch Build (Recommended)**
    *Allows running on both Mac (arm64) and standard servers (amd64)*
    ```bash
    docker buildx build --platform linux/amd64,linux/arm64 -t <your-username>/bds:latest --push .
    ```
    
    **Option B: Standard Build**
    *Just builds for your current machine's architecture*
    ```bash
    docker build -t <your-username>/bds:latest .
    docker push <your-username>/bds:latest
    ```

3.  **Run on Pi using the Hub Image**:
    Update your `docker-compose.yml` on the Pi:
    ```yaml
    services:
      bds:
        image: <your-username>/bds:latest
        # build: .  <-- Comment this out
        # ... rest of config
    ```

# Raspberry Pi Setup Guide for BDS

This guide will help you run the Bean Delivery System on a Raspberry Pi (or any other headless Linux environment).

## 1. Prepare the Code
1. Clone this repository onto your Raspberry Pi.
2. **Create a Virtual Environment** (Required for newer Raspberry Pi OS versions):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. **Audio File**: Ensure `Windchimes.mp3` is present in the project directory for sound effects.

## 2. Authentication (One-Time Setup)
Twitch authentication requires opening a browser. On a headless Pi, authenticate on your PC first:

1. **Run `server.py` on your PC/Mac first.**
   - Configure `.env` with `TWITCH_APP_ID`, `TWITCH_APP_SECRET`, etc.
   - Run `python server.py`.
   - Complete the browser login flow.
   - A `tokens.json` file will be created.
   - Stop the server.

2. **Transfer `tokens.json` and `.env` to the Pi.**
   - Copy both files to the BDS folder on your Raspberry Pi.

## 3. Run on Pi
### Option A: Standard Python (Good for development)
1. Run the server:
   ```bash
   source venv/bin/activate
   python server.py
   ```
   - It should listen on **0.0.0.0:18765** (WebSocket) and **0.0.0.0:18080** (Web Server).
   - The WebSocket port comes from `LOCAL_WS_PORT` in `.env` and **must be `18765`** -- the overlay hardcodes it. If the startup log says `port 8765`, your `.env` was not picked up.

### Option B: Docker (Recommended for stability)
1. Ensure Docker and Docker Compose are installed on your Pi.
2. Build and run the container:
   ```bash
   docker compose up -d --build
   ```
   - This keeps the app running in the background.
   - It persists your `tokens.json` and `.env` config.
   - To stop: `docker compose down`

### Option C: Docker Hub (For easy updates)
1. Build and push the image from your PC (see `.agent/workflows/push_to_dockerhub.md`).
2. Update `docker-compose.yml` on the Pi to use your image:
   ```yaml
   services:
     bds:
       image: <your-username>/bds:latest
       # build: .
   ```
3. Pull and restart:
   ```bash
   docker compose pull && docker compose up -d
   ```

## 4. Configure OBS (on your Streaming PC)
Since the Pi now hosts the overlay directly, setup is simple:

1. In OBS, add a **Browser Source**.
2. **URL**: `http://<PI_IP_ADDRESS>:18080`
   - Example: `http://192.168.1.50:18080`
   - *Note*: You no longer need to add `?ws=...` if using this hosted URL.
3. **Width/Height**: 1920x1080.
4. Check **Refresh browser when scene becomes active**.
5. **Audio**: Control audio via OBS Monitor settings if needed (ensure "Control Audio via OBS" is checked if you want to route it through OBS).

## 5. Testing & Controls
The server includes built-in test endpoints. Open these URLs in a browser on your PC/Phone (replace `<PI_IP>` with the Pi's IP, or `localhost` if testing locally):

- **Test Cheer (Bits)**: 
  `http://<PI_IP>:18080/test/cheer?bits=100&user=TestUser`
  - *Logic*: < 100 bits = Silent, >= 100 bits = "GOLDEN BEANS" text + Sound.
  
- **Test Redemption**:
  `http://<PI_IP>:18080/test/redeem?reward=FULL%20BEANS&user=TestUser`
  - *Logic*: Standard pinto beans + "FULL BEANS" text.

## Troubleshooting
- **No Sound**: 
  - Ensure `Windchimes.mp3` is in the folder.
  - Browser autoplay policy might block sound. Interactions (clicking the overlay) usually unlock it. In OBS, checking "Control Audio via OBS" usually bypasses this.
- **Connection Refused**: Check your Pi's firewall (allow ports 18765 and 18080).

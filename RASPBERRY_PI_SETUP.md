# Raspberry Pi Setup Guide for BDS

This guide will help you run the Bean Delivery System on a Raspberry Pi (or any other headless Linux environment).

## 1. Prepare the Code
1. Clone this repository onto your Raspberry Pi.
2. **Create a Virtual Environment** (Required for newer Raspberry Pi OS versions like Trixie):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 2. Authentication (One-Time Setup)
Twitch authentication requires opening a browser, which isn't easy on a headless Pi.
We will authenticate on your PC first and transfer the token.

1. **Run `server.py` on your PC/Mac first.**
   - Make sure your `.env` has the correct `TWITCH_APP_ID`, `TWITCH_APP_SECRET`, etc.
   - Run `python server.py`.
   - It will open a browser to authenticate.
   - Once connected, it will create a `tokens.json` file in the same folder.
   - Stop the server (Ctrl+C).

2. **Transfer `tokens.json` and `.env` to the Pi.**
   - Copy the `.env` file and the newly created `tokens.json` to the BDS folder on your Raspberry Pi.

## 3. Run on Pi
1. On the Pi, navigate to the folder.
2. Run the server:
   ```bash
   source venv/bin/activate
   python server.py
   ```
   - It should say: `Using saved authentication tokens.`
   - It will listen on `0.0.0.0:8765` so it's accessible from your network.

## 4. Configure OBS (on your Streaming PC)
1. In OBS, add a **Browser Source**.
2. **URL**: Point to the `index.html` file on your Streaming PC (e.g., `file:///path/to/BDS/index.html` or hosted on a local web server).
   - **Crucial**: You must tell the overlay where the Pi is. Add `?ws=<PI_IP_ADDRESS>:8765` to the end of the URL.
   - Example (Local file): 
     `file:///Users/Me/BDS/index.html?ws=192.168.1.50:8765`
   - Example (Hosted):
     `http://localhost:8000/index.html?ws=192.168.1.50:8765`
3. **Width/Height**: 1920x1080 (or your overlay resolution).
4. check **Shutdown source when not visible** (optional, saves resources).
5. check **Refresh browser when scene becomes active** (optional).

## Troubleshooting
- **Connection Refused**: Ensure the Pi's firewall isn't blocking port 8765. Checks the IP address.
- **Token Expired**: If the token expires and can't refresh, `server.py` will try to open a browser (and fail on headless). simple re-run step 2 (generate new `tokens.json` on PC and copy it over).

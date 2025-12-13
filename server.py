import os

from dotenv import load_dotenv

import certifi

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.getenv('BDS_ENV_FILE') or os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path=DOTENV_PATH, override=False)

if not os.getenv('SSL_CERT_FILE'):
    os.environ['SSL_CERT_FILE'] = certifi.where()

BDS_DEBUG = os.getenv('BDS_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}

APP_ID = os.getenv('TWITCH_APP_ID', '')
APP_SECRET = os.getenv('TWITCH_APP_SECRET', '')
TARGET_CHANNEL = os.getenv('TWITCH_TARGET_CHANNEL', '')
LOCAL_WS_PORT = int(os.getenv('LOCAL_WS_PORT', '8765'))
BDS_RELAY_ONLY = os.getenv('BDS_RELAY_ONLY', '').strip().lower() in {'1', 'true', 'yes', 'on'}

if BDS_DEBUG:
    print(f"Config file: {DOTENV_PATH}")
    print(f"TWITCH_APP_ID set: {bool(APP_ID)}")
    print(f"TWITCH_APP_SECRET set: {bool(APP_SECRET)}")
    print(f"TWITCH_TARGET_CHANNEL set: {bool(TARGET_CHANNEL)}")
    print(f"LOCAL_WS_PORT: {LOCAL_WS_PORT}")
    print(f"BDS_RELAY_ONLY: {BDS_RELAY_ONLY}")

import asyncio
import json
import websockets
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope
from twitchAPI.eventsub.websocket import EventSubWebsocket
from aiohttp import web

# =====================================================
# CONFIGURATION
# Get these from https://dev.twitch.tv/console
# =====================================================

# =====================================================

TOKEN_FILE = os.path.join(BASE_DIR, 'tokens.json')

def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        return None, None
    try:
        with open(TOKEN_FILE, 'r') as f:
            data = json.load(f)
        return data.get('token'), data.get('refresh_token')
    except Exception:
        return None, None

def save_tokens(token, refresh_token):
    with open(TOKEN_FILE, 'w') as f:
        json.dump({'token': token, 'refresh_token': refresh_token}, f)

connected_clients = set()

async def ws_handler(websocket):
    """Handles new connections from the HTML overlay"""
    connected_clients.add(websocket)
    print(f"Overlay connected! (Total: {len(connected_clients)})")
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print(f"Overlay disconnected. (Total: {len(connected_clients)})")

async def http_handler(request):
    """Serves the index.html file"""
    return web.FileResponse(os.path.join(BASE_DIR, 'index.html'))

async def on_redemption(data):
    """Callback for when a redemption happens on Twitch"""
    reward_title = data.event.reward.title
    user_name = data.event.user_name
    print(f"Redemption received: {reward_title} by {user_name}")
    
    if connected_clients:
        payload = json.dumps({
            "reward": reward_title,
            "user": user_name
        })
        # Broadcast to all connected overlays
        tasks = [asyncio.create_task(client.send(payload)) for client in connected_clients]
        if tasks:
            await asyncio.wait(tasks)

async def main():
    # 1. Setup Local WebSocket Server (8765) & HTTP Server (8080)
    print(f"Starting local relay server on port {LOCAL_WS_PORT}...")
    # Bind to 0.0.0.0 so the Pi is accessible from your PC/OBS
    ws_server = await websockets.serve(ws_handler, "0.0.0.0", LOCAL_WS_PORT)

    # Setup HTTP Server for index.html
    app = web.Application()
    app.add_routes([web.get('/', http_handler)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print(f"Serving Overlay on http://0.0.0.0:8080")

    if BDS_RELAY_ONLY:
        print("Relay-only mode enabled; not connecting to Twitch.")
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            print("Stopping...")
        finally:
            ws_server.close()
        return

    # 2. Setup Twitch API
    print("Connecting to Twitch...")
    if not APP_ID or not APP_SECRET or not TARGET_CHANNEL:
        raise RuntimeError('Missing Twitch configuration. Set TWITCH_APP_ID, TWITCH_APP_SECRET, and TWITCH_TARGET_CHANNEL (or run with BDS_RELAY_ONLY=1). You can place these in a .env file next to server.py or point BDS_ENV_FILE to an external .env file.')
    twitch = await Twitch(APP_ID, APP_SECRET)
    
    # 3. Authenticate (will open browser if needed)
    # 3. Authenticate
    # Try to load existing tokens to avoid opening a browser on the Pi
    target_scopes = [AuthScope.CHANNEL_READ_REDEMPTIONS, AuthScope.BITS_READ]
    token, refresh_token = load_tokens()
    
    if token and refresh_token:
        try:
            await twitch.set_user_authentication(token, target_scopes, refresh_token)
            print("Using saved authentication tokens.")
        except Exception as e:
            print(f"Saved tokens failed ({e}), re-authenticating...")
            token = None

    if not token:
        print("Opening browser for Twitch authentication...")
        auth = UserAuthenticator(twitch, target_scopes)
        token, refresh_token = await auth.authenticate()
        await twitch.set_user_authentication(token, target_scopes, refresh_token)
        save_tokens(token, refresh_token)
        print("Authentication successful and tokens saved.")

    # 4. Get User ID
    user_id = None
    async for u in twitch.get_users(logins=[TARGET_CHANNEL]):
        user_id = u.id
        break
    if not user_id:
        raise RuntimeError(f'Could not find Twitch user for login: {TARGET_CHANNEL}')
    print(f"Listening for events on channel: {TARGET_CHANNEL} (ID: {user_id})")

    # 5. Start EventSub (WebSocket)
    eventsub = EventSubWebsocket(twitch)
    eventsub.start()
    
    # 6. Subscribe to Channel Points and Cheers
    await eventsub.listen_channel_points_custom_reward_redemption_add(user_id, on_redemption)
    await eventsub.listen_channel_cheer(user_id, on_cheer)
    print("EventSub connected! Waiting for beans (Points & Bits)...")

    # Keep the script running
    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        print("Stopping...")
    finally:
        await eventsub.stop()
        ws_server.close()
        await runner.cleanup()
        await twitch.close()

async def on_cheer(data):
    """Callback for when bits are cheered"""
    bits = data.event.bits
    user_name = data.event.user_name or "Anonymous"
    print(f"Cheer received: {bits} bits by {user_name}")
    
    beans_count = bits * 2
    show_text = bits >= 100
    
    if connected_clients:
        payload = json.dumps({
            "type": "cheer",
            "user": user_name,
            "beans": beans_count,
            "showText": show_text
        })
        tasks = [asyncio.create_task(client.send(payload)) for client in connected_clients]
        if tasks:
            await asyncio.wait(tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

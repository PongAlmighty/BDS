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
# 18765 is not really optional -- index.html hardcodes it when building the
# WebSocket URL and docker-compose maps 18765:18765. Defaulting to anything else
# means a missing .env yields an overlay that renders but never receives a drop.
LOCAL_WS_PORT = int(os.getenv('LOCAL_WS_PORT', '18765'))
BDS_RELAY_ONLY = os.getenv('BDS_RELAY_ONLY', '').strip().lower() in {'1', 'true', 'yes', 'on'}

# StrangerTV kiosk corner watcher. The kiosk drops beans when its DVD nut lands in a
# corner, but it cannot reach this machine -- that direction of the network is blocked
# -- so we poll it instead. Empty URL disables the watcher entirely.
KIOSK_STATUS_URL = os.getenv('KIOSK_STATUS_URL', '').strip()
KIOSK_POLL_INTERVAL = float(os.getenv('KIOSK_POLL_INTERVAL', '2'))
CORNER_NUTS = int(os.getenv('CORNER_NUTS', os.getenv('CORNER_BEANS', '120')))
CORNER_USER = os.getenv('CORNER_USER', 'CORNER')
CORNER_TEXT = os.getenv('CORNER_TEXT', 'CORNER INCOMING!')
# The kiosk warns us a few seconds before the nut lands in a corner, so the drop is
# the heads-up to go and watch it happen. Dropping on the hit itself is the old
# behaviour and is off by default -- with the warning on, it would double-drop.
CORNER_DROP_ON_HIT = os.getenv('CORNER_DROP_ON_HIT', '').strip().lower() in {'1', 'true', 'yes', 'on'}
# The warning is a single oversized nut rather than a shower of small ones -- it reads
# as "look up now" at a glance, which a hundred little ones do not.
CORNER_WARN_NUTS = int(os.getenv('CORNER_WARN_NUTS', '1'))
CORNER_WARN_SCALE = float(os.getenv('CORNER_WARN_SCALE', '10'))

if BDS_DEBUG:
    print(f"Config file: {DOTENV_PATH}")
    print(f"TWITCH_APP_ID set: {bool(APP_ID)}")
    print(f"TWITCH_APP_SECRET set: {bool(APP_SECRET)}")
    print(f"TWITCH_TARGET_CHANNEL set: {bool(TARGET_CHANNEL)}")
    print(f"LOCAL_WS_PORT: {LOCAL_WS_PORT}")
    print(f"BDS_RELAY_ONLY: {BDS_RELAY_ONLY}")

import asyncio
import json
import aiohttp
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
    # No caching: OBS browser sources hold onto a cached page across restarts, so
    # a rebuilt overlay keeps running the old JS until someone clears the cache by
    # hand. Costs nothing here -- it is one small file over localhost.
    return web.FileResponse(os.path.join(BASE_DIR, 'index.html'), headers={
        'Cache-Control': 'no-store, no-cache, must-revalidate',
    })

async def broadcast(message):
    if connected_clients:
        payload = json.dumps(message)
        tasks = [asyncio.create_task(client.send(payload)) for client in connected_clients]
        if tasks:
            await asyncio.wait(tasks)

async def test_cheer_handler(request):
    bits = int(request.query.get('bits', '100'))
    user_name = request.query.get('user', 'TestUser')
    
    beans_count = bits * 2
    show_text = bits >= 100
    
    await broadcast({
        "type": "cheer",
        "user": user_name,
        "beans": beans_count,
        "showText": show_text
    })
    return web.Response(text=f"Simulated cheer: {bits} bits from {user_name}")

async def test_redemption_handler(request):
    reward = request.query.get('reward', 'FULL BEANS')
    user_name = request.query.get('user', 'TestUser')
    
    await broadcast({
        "reward": reward,
        "user": user_name
    })
    return web.Response(text=f"Simulated redemption: {reward} from {user_name}")

async def test_nut_handler(request):
    count = int(request.query.get('count', CORNER_NUTS))
    scale = float(request.query.get('scale', '1'))
    await broadcast({
        "type": "nut",
        "user": request.query.get('user', CORNER_USER),
        "count": count,
        "scale": scale,
        "showText": request.query.get('text', '1') not in {'0', 'false', 'no'},
        "text": request.query.get('text') if request.query.get('text') not in
                {None, '1', '0', 'false', 'no'} else CORNER_TEXT,
    })
    return web.Response(text=f"Dropped {count} nuts at {scale}x")


async def test_warn_handler(request):
    """Fire exactly what a real corner warning fires, for checking the look of it."""
    await broadcast({
        "type": "nut",
        "user": CORNER_USER,
        "count": CORNER_WARN_NUTS,
        "scale": CORNER_WARN_SCALE,
        "showText": True,
        "text": CORNER_TEXT,
    })
    return web.Response(text=f"Simulated corner warning: {CORNER_WARN_NUTS} nut(s) at {CORNER_WARN_SCALE}x")

async def on_redemption(data):
    """Callback for when a redemption happens on Twitch"""
    reward_title = data.event.reward.title
    user_name = data.event.user_name
    print(f"Redemption received: {reward_title} by {user_name}")
    
    await broadcast({
        "reward": reward_title,
        "user": user_name
    })

async def audio_handler(request):
    return web.FileResponse(os.path.join(BASE_DIR, 'Windchimes.mp3'))

async def nut_handler(request):
    # Only the nut-aware overlay asks for this, so the log line doubles as proof
    # that a browser source is running current JS rather than a cached old page.
    print("nut.obj requested -- overlay is running the current page")
    return web.FileResponse(os.path.join(BASE_DIR, 'nut.obj'))

async def watch_kiosk_corners():
    """Drop nuts just before the StrangerTV kiosk lands its DVD nut in a corner.

    The kiosk publishes both an advance warning and the hit itself on its own /status
    endpoint and we poll it, because the kiosk cannot open a connection to this
    machine. We adopt whatever is already published on the first successful poll, so
    restarting BDS never replays an old event; anything that happens while BDS is
    down is simply missed.

    The warning fires KIOSK_CORNER_WARN seconds ahead (5 by default). Our poll only
    lands every KIOSK_POLL_INTERVAL, so the notice we actually pass on is somewhere
    between the full lead and lead-minus-one-interval -- roughly 3-5s at the defaults,
    which is the point: enough time to look up before it happens.
    """
    seen_warn, seen_hit, have_baseline = None, None, False
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(KIOSK_STATUS_URL,
                                       timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            except Exception as e:
                print(f"Kiosk poll failed: {e}")
            else:
                warn, hit = data.get('corner_warn'), data.get('last_corner')
                if not have_baseline:
                    seen_warn, seen_hit, have_baseline = warn, hit, True
                    print(f"Kiosk corner watcher ready (baseline warn={seen_warn} hit={seen_hit})")
                else:
                    if warn is not None and warn != seen_warn:
                        seen_warn = warn
                        lead = data.get('corner_warn_lead')
                        print(f"CORNER INCOMING (kiosk lead {lead}s) -- dropping "
                              f"{CORNER_WARN_NUTS} nut(s) at {CORNER_WARN_SCALE}x")
                        await broadcast({
                            "type": "nut",
                            "user": CORNER_USER,
                            "count": CORNER_WARN_NUTS,
                            "scale": CORNER_WARN_SCALE,
                            "showText": True,
                            "text": CORNER_TEXT,
                        })
                    if hit is not None and hit != seen_hit:
                        seen_hit = hit
                        if CORNER_DROP_ON_HIT:
                            print(f"CORNER HIT at {hit} -- dropping {CORNER_NUTS} nuts")
                            await broadcast({
                                "type": "nut",
                                "user": CORNER_USER,
                                "count": CORNER_NUTS,
                                "showText": True,
                                "text": "CORNER HIT!",
                            })
                        else:
                            print(f"CORNER HIT at {hit} (already announced)")
            await asyncio.sleep(KIOSK_POLL_INTERVAL)

async def main():
    # 1. Setup Local WebSocket Server (18765) & HTTP Server (18080)
    print(f"Starting local relay server on port {LOCAL_WS_PORT}...")
    # Bind to 0.0.0.0 so the Pi is accessible from your PC/OBS
    ws_server = await websockets.serve(ws_handler, "0.0.0.0", LOCAL_WS_PORT)

    # Setup HTTP Server for index.html
    app = web.Application()
    app.add_routes([
        web.get('/', http_handler),
        web.get('/Windchimes.mp3', audio_handler),
        web.get('/nut.obj', nut_handler),
        web.get('/test/cheer', test_cheer_handler),
        web.get('/test/redeem', test_redemption_handler),
        web.get('/test/nut', test_nut_handler),
        web.get('/test/warn', test_warn_handler),
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 18080)
    await site.start()
    print(f"Serving Overlay on http://0.0.0.0:18080")

    # Runs in relay-only mode too -- it has nothing to do with Twitch.
    if KIOSK_STATUS_URL:
        asyncio.create_task(watch_kiosk_corners())
        print(f"Watching kiosk corners at {KIOSK_STATUS_URL} every {KIOSK_POLL_INTERVAL}s")

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
    
    await broadcast({
        "type": "cheer",
        "user": user_name,
        "beans": beans_count,
        "showText": show_text
    })


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

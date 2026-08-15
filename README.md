# Bean Delivery System (BDS)

A physics-based Twitch overlay that drops 3D beans on your screen when viewers Cheer or Redeem points.

## Features
- **Physics Simulation**: Hundreds of 3D beans colliding with each other (Three.js + Cannon.js).
- **Twitch Integration**: 
  - **Points**: Drops literal Pinto Beans.
  - **Bits**: Drops Golden Beans.
- **Dynamic Responses**:
  - **< 100 Bits**: Silent golden drop.
  - **>= 100 Bits**: "GOLDEN BEANS" banner + Windchime sound effect.
  - **Redemptions**: "FULL BEANS" banner.
- **Optimized Performance**: Drops start at full speed (~8 seconds for a typical drop) and a frame-rate governor stretches the spawn interval if the browser starts to slip, so a huge cheer lands slowly instead of crashing the tab.

## Known Issues

**Three.js and Cannon-es load from the unpkg CDN at runtime** ([index.html](index.html), top of the module script). All physics, lighting, and rendering happen in the browser -- the container only serves static files and relays WebSocket messages -- so the overlay needs outbound internet on every fresh load even though the server is on the LAN.

If unpkg is down, slow, or blocked, **the overlay renders as a blank page**. There is no fallback and no error banner; it fails silently, which on stream looks identical to the overlay simply not firing. The versions are also unpinned against CDN availability, so a change on unpkg's side can break a machine that worked yesterday without anything in this repo changing.

The fix, if this ever bites: vendor both libraries into the repo, `COPY` them in the Dockerfile alongside `nut.obj`, add routes for them in `server.py`, and change the imports to local paths. That makes the overlay fully self-contained and removes the internet dependency entirely.

## Setup
See [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md) for installation and running instructions. 

**Docker support is available** for easier deployment:
`docker compose up -d`

## Quick Start (Local)
1. Install dependencies: `pip install -r requirements.txt`
2. Create `.env` with your Twitch App credentials.
3. Run `python server.py`.
4. Open `http://localhost:8080` in OBS or your browser.
5. Test using `http://localhost:8080/test/cheer?bits=100`.

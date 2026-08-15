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
- **StrangerTV Corner Hits (predicted)**: Polls the kiosk's status endpoint and drops 3D hex nuts (not beans) *a few seconds before* its bouncing DVD nut lands in a corner, so the drop is the cue to look up and watch it happen rather than an announcement that you missed it. The kiosk's bounce is deterministic, so it tabulates its own hit times exactly and publishes a `corner_warn` ahead of each one -- this is a lookup, not a guess. Polling rather than push because the kiosk cannot reach this machine. Set `KIOSK_STATUS_URL` to enable, blank to disable.
  - Advance notice is `KIOSK_CORNER_WARN` seconds on the kiosk (default 5). BDS only sees it on its next poll, so the notice actually delivered is between the full lead and lead-minus-`KIOSK_POLL_INTERVAL` -- roughly **3-5 seconds** at the defaults.
  - Set `CORNER_DROP_ON_HIT=1` to also drop on the hit itself (the old behaviour). Off by default, since with the warning enabled it would double-drop.
  - The warning drops **one nut at `CORNER_WARN_SCALE`x** (default 10) rather than a shower of small ones, so it reads as "look up now" at a glance. The drop point is clamped so an oversized nut cannot spawn overlapping the side walls; past about 15x it is taller than the frustum. Preview it with `/test/warn`.
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
4. Open `http://localhost:18080` in OBS or your browser.
5. Test using `http://localhost:18080/test/cheer?bits=100`.

### Test Endpoints
All served from port `18080`:

| Endpoint | Effect |
|---|---|
| `/test/cheer?bits=100&user=Name` | Golden beans, `bits * 2` of them. `>= 100` bits also shows the banner and plays the windchime. |
| `/test/redeem?reward=FULL%20BEANS&user=Name` | Pinto beans, fixed at `beansPerRedeem` (100), plus the banner. |
| `/test/nut?count=120&scale=1&text=CORNER%20HIT!` | Hex nuts, arbitrary count. `scale` multiplies nut size. `text=0` suppresses the banner. |
| `/test/warn` | Fires exactly what a real corner warning fires -- one nut at `CORNER_WARN_SCALE`. |

`/test/cheer` is the only way to request an arbitrary *bean* count -- `/test/redeem` takes no count parameter.

### Debug Overlay
Load the overlay with `?debug` (e.g. `http://localhost:18080/?debug`) for a live `fps · on screen · queued` readout, plus keyboard and click triggers: **B** or a click anywhere drops 100 beans.

### Ports
| Port | Purpose | Configurable |
|---|---|---|
| `18080` | HTTP -- overlay page, assets, test endpoints | No, hardcoded in `server.py` |
| `18765` | WebSocket relay the overlay connects to | `LOCAL_WS_PORT`, but see below |

**`LOCAL_WS_PORT` must be `18765`.** The overlay hardcodes that port when building its WebSocket URL, and `docker-compose.yml` maps `18765:18765`. The `?ws=` query parameter overrides only the *host*, not the port, so pointing `LOCAL_WS_PORT` anywhere else leaves the overlay connecting to a port nothing is listening on -- it renders but never receives a drop. The fallback in `server.py` is also `18765`, so a missing or unreadable `.env` still comes up working.

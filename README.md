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
- **Optimized Performance**: Dynamic spawn rates ensure even massive drops (1000+ beans) remain smooth and finish within ~8 seconds.

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

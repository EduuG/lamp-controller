# Smart Lamp Controller

Simple desktop app to control Tuya RGBWW lamps locally using `tinytuya`. Built it because opening the phone app every time was annoying.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Config

Put your device credentials in `config.json` at the project root:

```json
{
    "device_id": "your_device_id",
    "ip": "192.168.x.x",
    "local_key": "your_local_key",
    "protocol_version": 3.5
}
```

You can also set environment variables instead: `LAMP_DEVICE_ID`, `LAMP_IP`, `LAMP_KEY` (and optionally `LAMP_PROTOCOL`).

To find your device's ID and key, run `tinytuya scan`:

```bash
python -m tinytuya scan
```

## Run

```bash
source .venv/bin/activate
python -m src.main
```

## What it does

- **Power** toggle
- **White mode** — brightness + color temperature sliders
- **Color mode** — hue/saturation sliders + 9 color presets
- **Scenes** — Reading, Work, Relax, Night, Party, Romantic
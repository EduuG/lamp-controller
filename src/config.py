"""Device credentials and configuration loader."""

import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "device_id": "",
    "ip": "",
    "local_key": "",
    "protocol_version": 3.5,
}


def load_config(config_path: str | None = None) -> dict:
    """Load device config from JSON file or environment variables.

    Priority:
    1. Config file at config_path (default: config.json next to this module)
    2. Environment variables: LAMP_DEVICE_ID, LAMP_IP, LAMP_KEY
    3. Defaults (empty strings — will fail at runtime)
    """
    # Try config file first
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.json"

    config_path = Path(config_path)
    if config_path.is_file():
        with open(config_path) as f:
            file_cfg = json.load(f)
        return {
            "device_id": file_cfg.get("device_id", ""),
            "ip": file_cfg.get("ip", ""),
            "local_key": file_cfg.get("local_key", ""),
            "protocol_version": float(file_cfg.get("protocol_version", 3.5)),
        }

    # Fallback to environment variables
    return {
        "device_id": os.environ.get("LAMP_DEVICE_ID", ""),
        "ip": os.environ.get("LAMP_IP", ""),
        "local_key": os.environ.get("LAMP_KEY", ""),
        "protocol_version": float(os.environ.get("LAMP_PROTOCOL", 3.5)),
    }

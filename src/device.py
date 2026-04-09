"""TinyTuya device wrapper with value conversion helpers."""

import tinytuya

# Type B bulb ranges (most common for RGBWW bulbs)
BRIGHT_MIN, BRIGHT_MAX = 10, 1000
TEMP_MIN, TEMP_MAX = 0, 1000


class LampDevice:
    """High-level wrapper around tinytuya.BulbDevice."""

    def __init__(self, device_id: str, ip: str, local_key: str, version: float = 3.5):
        self._dev = tinytuya.BulbDevice(device_id, ip, local_key)
        self._dev.set_version(version)
        self._connected = True

    @property
    def connected(self) -> bool:
        return self._connected

    # --- State ---
    def get_state(self) -> dict | None:
        """Return current device state, or None on error."""
        try:
            return self._dev.state()
        except Exception:
            return None

    # --- Power ---
    def turn_on(self) -> bool:
        try:
            self._dev.turn_on()
            return True
        except Exception:
            return False

    def turn_off(self) -> bool:
        try:
            self._dev.turn_off()
            return True
        except Exception:
            return False

    # --- White mode ---
    def set_white(self, brightness_pct: int, colortemp_pct: int) -> bool:
        """Set white mode with brightness and color temp (0–100 each)."""
        try:
            self._dev.set_white_percentage(brightness_pct, colortemp_pct)
            return True
        except Exception:
            return False

    # --- Color mode ---
    def set_color(self, hue: int, saturation_pct: int, brightness_pct: int) -> bool:
        """Set RGB color via HSV.

        Args:
            hue: 0–360
            saturation_pct: 0–100
            brightness_pct: 0–100
        """
        try:
            self._dev.set_hsv(
                hue / 360.0,
                saturation_pct / 100.0,
                brightness_pct / 100.0,
            )
            return True
        except Exception:
            return False

    # --- Conversion helpers ---
    @staticmethod
    def raw_to_slider_brightness(raw: int) -> int:
        if raw < BRIGHT_MIN:
            return 0
        return max(0, int(((raw - BRIGHT_MIN) / (BRIGHT_MAX - BRIGHT_MIN)) * 100))

    @staticmethod
    def raw_to_slider_colortemp(raw: int) -> int:
        if raw < TEMP_MIN:
            return 0
        return int((raw / TEMP_MAX) * 100)

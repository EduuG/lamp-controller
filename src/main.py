"""Smart Lamp Controller — PyQt6 GUI."""

import sys
import os
import colorsys

os.environ["QT_PLUGIN_PATH"] = "/usr/lib/qt6/plugins"
os.environ["QT_QPA_PLATFORMTHEME"] = "qt6ct"

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QGridLayout,
    QComboBox,
    QFrame,
    QGroupBox,
    QMenuBar,
    QStatusBar,
    QDialog,
    QCheckBox,
    QDialogButtonBox,
    QFormLayout,
)
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QStyle

from src.config import load_config
from src.device import LampDevice


ORG_NAME = "SmartLamp"
APP_NAME = "Controller"


class SettingsDialog(QDialog):
    def __init__(self, realtime: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(280, 130)
        layout = QFormLayout(self)
        self.realtime_cb = QCheckBox("Real-time preview")
        self.realtime_cb.setChecked(realtime)
        layout.addRow(self.realtime_cb)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class SmartLampController(QMainWindow):
    def __init__(self, device: LampDevice):
        super().__init__()
        self.device = device
        self._settings = QSettings(ORG_NAME, APP_NAME)
        self.realtime = self._settings.value("realtime", True, type=bool)

        self.ui_brightness = 50
        self.ui_colortemp = 50
        self.ui_hue = 0
        self.ui_saturation = 100
        self.ui_mode = "white"
        self.dev_mode = "white"
        self.ui_power = False

        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._flush_pending)
        self._pending = None

        self._icons = self._load_icons()
        self.init_ui()
        self._sync_from_device()

    # --- Icons ---
    @staticmethod
    def _load_icons() -> dict[str, QIcon]:
        """Load standard Qt icons that get themed by the system style."""
        si = QApplication.style().standardIcon
        return {
            "power_on": si(QStyle.StandardPixmap.SP_MediaPlay),
            "power_off": si(QStyle.StandardPixmap.SP_MediaStop),
            "apply": si(QStyle.StandardPixmap.SP_DialogApplyButton),
            "settings": si(QStyle.StandardPixmap.SP_FileDialogDetailedView),
            "exit": si(QStyle.StandardPixmap.SP_DialogCloseButton),
            "bulb": si(QStyle.StandardPixmap.SP_TitleBarMenuButton),
        }

    # --- UI ---
    def init_ui(self):
        self.setWindowTitle("Smart Lamp Controller")
        self.setWindowIcon(self._icons["bulb"])
        self.setFixedSize(440, 480)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction(self._icons["settings"], "Settings...", self._open_settings)
        file_menu.addSeparator()
        file_menu.addAction(self._icons["exit"], "Exit", self.close)

        wrapper = QWidget()
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        # Power button with icon
        pwr_row = QHBoxLayout()
        self.pwr_btn = QPushButton()
        self.pwr_btn.setMinimumHeight(36)
        self._update_power_btn()
        self.pwr_btn.clicked.connect(self._toggle_power)
        pwr_row.addWidget(self.pwr_btn)
        pwr_row.addStretch()
        lay.addLayout(pwr_row)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        lay.addWidget(sep1)

        # Mode selector with icons
        mr = QHBoxLayout()
        mr.addWidget(QLabel("Mode:"))
        mr.addStretch()
        self.mode_cb = QComboBox()
        self.mode_cb.addItems(["White", "Color", "Scenes"])
        self.mode_cb.currentIndexChanged.connect(self._on_mode)
        mr.addWidget(self.mode_cb)
        lay.addLayout(mr)

        # Sliders
        lay.addWidget(self._slider_group("Brightness", "sl_bright", 0, 100, 50, self._on_bright))
        self.temp_group = self._slider_group("Temperature", "sl_temp", 0, 100, 50, self._on_temp)
        lay.addWidget(self.temp_group)

        # Panels
        lay.addWidget(self._color_panel())
        lay.addWidget(self._scene_panel())

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        lay.addWidget(sep2)

        # Apply button
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setIcon(self._icons["apply"])
        self.apply_btn.clicked.connect(self._apply_now)
        lay.addWidget(self.apply_btn)

        self.setCentralWidget(wrapper)

        # Status bar
        self.sts_bar = QStatusBar()
        self.setStatusBar(self.sts_bar)
        self.live_label = QLabel("● Real-time")
        self.sts_bar.addPermanentWidget(self.live_label)
        self._update_live_label()
        self._update_status()

        # self._poll = QTimer()
        # self._poll.timeout.connect(self._sync_from_device)
        # self._poll.start(3000)

    def _slider_group(self, title, name, lo, hi, default, callback):
        g = QGroupBox(title)
        f = QVBoxLayout(g)
        f.setContentsMargins(6, 10, 6, 4)
        f.setSpacing(0)
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(default)
        s.setObjectName(name)
        s.valueChanged.connect(callback)
        f.addWidget(s)
        return g

    def _color_panel(self):
        self.cf = QFrame()
        self.cf.setFrameShape(QFrame.Shape.Box)
        clf = QVBoxLayout(self.cf)
        clf.setContentsMargins(4, 4, 4, 4)
        clf.setSpacing(3)

        clf.addWidget(QLabel("Color"), alignment=Qt.AlignmentFlag.AlignCenter)

        for label_text, slider_attr, range_, label in [
            ("H:", "hue_sl", (0, 360), self._on_hue),
            ("S:", "sat_sl", (0, 100), self._on_sat),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text, minimumWidth=15))
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(*range_)
            if slider_attr == "sat_sl":
                sl.setValue(100)
            sl.valueChanged.connect(label)
            row.addWidget(sl)
            setattr(self, slider_attr, sl)
            clf.addLayout(row)

        self.cprev = QFrame()
        self.cprev.setFrameShape(QFrame.Shape.Box)
        self.cprev.setFixedHeight(20)
        clf.addWidget(self.cprev)
        self._update_color_preview()

        pg = QGridLayout()
        pg.setSpacing(2)
        for i, (h, hx) in enumerate([
            (0, "#ff0000"), (120, "#00ff00"), (240, "#0000ff"),
            (60, "#ffff00"), (180, "#00ffff"), (300, "#ff00ff"),
            (30, "#ff8800"), (330, "#ff66aa"), (270, "#8800ff"),
        ]):
            b = QPushButton()
            b.setFixedHeight(22)
            b.setToolTip(self._hue_name(h))
            b.setStyleSheet(f"background-color:{hx}; border:1px solid palette(mid);")
            b.clicked.connect(lambda _, h=h: self._set_hue_preset(h))
            pg.addWidget(b, i // 3, i % 3)
        clf.addLayout(pg)

        self.cf.setVisible(False)
        return self.cf

    def _scene_panel(self):
        self.snf = QFrame()
        self.snf.setFrameShape(QFrame.Shape.Box)
        sf = QVBoxLayout(self.snf)
        sf.setContentsMargins(4, 4, 4, 4)
        sf.setSpacing(3)
        sg = QGridLayout()
        sg.setSpacing(2)
        for i, (name, sid) in enumerate([
            ("Reading", "reading"), ("Work", "work"),
            ("Relax", "relax"), ("Night", "night"),
            ("Party", "party"), ("Romantic", "romantic"),
        ]):
            b = QPushButton(name)
            b.clicked.connect(lambda _, s=sid: self._apply_scene(s))
            sg.addWidget(b, i // 3, i % 3)
        sf.addLayout(sg)
        self.snf.setVisible(False)
        return self.snf

    @staticmethod
    def _hue_name(h: int) -> str:
        names = {
            0: "Red", 30: "Orange", 60: "Yellow",
            120: "Green", 180: "Cyan", 240: "Blue",
            270: "Purple", 300: "Magenta", 330: "Pink",
        }
        return names.get(h, "")

    # --- Settings ---
    def _open_settings(self):
        dlg = SettingsDialog(self.realtime, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.realtime = dlg.realtime_cb.isChecked()
            self._settings.setValue("realtime", self.realtime)
            self._update_live_label()

    def _update_live_label(self):
        if self.realtime:
            self.live_label.setText("● Real-time")
            self.live_label.setVisible(True)
            self.apply_btn.setText("Apply")
            self.apply_btn.setIcon(self._icons["apply"])
        else:
            self.live_label.setVisible(False)
            self.apply_btn.setText("Apply now")

    def _update_power_btn(self):
        if self.ui_power:
            self.pwr_btn.setText("  Turn Off")
            self.pwr_btn.setIcon(self._icons["power_off"])
        else:
            self.pwr_btn.setText("  Turn On")
            self.pwr_btn.setIcon(self._icons["power_on"])

    # --- Debounced send ---
    def _queue(self, fn):
        if not self.realtime:
            return
        self._pending = fn
        self._debounce.start(150)

    def _flush_pending(self):
        fn = self._pending
        self._pending = None
        if fn:
            fn()
            self._update_status()

    # --- Device commands ---
    def _send_white(self):
        self.device.set_white(self.ui_brightness, self.ui_colortemp)

    def _send_color(self):
        self.device.set_color(self.ui_hue, self.ui_saturation, self.ui_brightness)

    def _apply_now(self):
        if self.ui_mode == "white":
            self._send_white()
        elif self.ui_mode == "color":
            self._send_color()
        self._update_status()

    # --- Event handlers ---
    def _toggle_power(self):
        self.ui_power = not self.ui_power
        ok = self.device.turn_on() if self.ui_power else self.device.turn_off()
        if ok:
            self._update_power_btn()
        else:
            self.ui_power = not self.ui_power
        self._update_status()

    def _on_mode(self):
        m = self.mode_cb.currentText()
        if m == "White":
            self.temp_group.setVisible(True)
            self.cf.setVisible(False)
            self.snf.setVisible(False)
            self.ui_mode = "white"
            self.dev_mode = "white"
        elif m == "Color":
            self.temp_group.setVisible(False)
            self.cf.setVisible(True)
            self.snf.setVisible(False)
            self.ui_mode = "color"
            self.dev_mode = "color"
        else:
            self.temp_group.setVisible(False)
            self.cf.setVisible(False)
            self.snf.setVisible(True)
            self.ui_mode = "scene"
            self.dev_mode = "scene"

    def _on_bright(self, v):
        self.ui_brightness = v
        cmd = self._send_white if self.ui_mode == "white" else self._send_color
        self._queue(cmd)

    def _on_temp(self, v):
        self.ui_colortemp = v
        if self.ui_mode == "white":
            self._queue(self._send_white)

    def _on_hue(self, v):
        self.ui_hue = v
        self._update_color_preview()
        if self.ui_mode == "color":
            self._queue(self._send_color)

    def _on_sat(self, v):
        self.ui_saturation = v
        self._update_color_preview()
        if self.ui_mode == "color":
            self._queue(self._send_color)

    def _set_hue_preset(self, h):
        self.hue_sl.setValue(h)

    def _apply_scene(self, sid):
        scenes = {
            "reading": (80, 70), "work": (100, 80),
            "relax": (40, 20), "night": (10, 0),
            "party": (100, 50), "romantic": (30, 10),
        }
        b, t = scenes.get(sid, (50, 50))
        self.ui_brightness, self.ui_colortemp = b, t
        for name, val in [("sl_bright", b), ("sl_temp", t)]:
            sl = self.findChild(QSlider, name)
            if sl:
                sl.blockSignals(True)
                sl.setValue(val)
                sl.blockSignals(False)
        self._send_white()
        self._update_status()

    # --- Sync from device ---
    def _sync_from_device(self):
        state = self.device.get_state()
        if not state:
            return

        dev_on = state.get("is_on", state.get("switch", None))
        if dev_on is not None and bool(dev_on) != self.ui_power:
            self.ui_power = bool(dev_on)
            self._update_power_btn()

        raw_mode = state.get("mode", "white")
        if raw_mode == "colour":
            self.dev_mode = "color"
        else:
            self.dev_mode = raw_mode

        rb = state.get("brightness")
        rt = state.get("colourtemp")
        if rb is not None:
            sb = LampDevice.raw_to_slider_brightness(rb)
            if abs(sb - self.ui_brightness) > 3:
                self.ui_brightness = sb
                sl = self.findChild(QSlider, "sl_bright")
                if sl:
                    sl.blockSignals(True)
                    sl.setValue(sb)
                    sl.blockSignals(False)
        if rt is not None:
            st = LampDevice.raw_to_slider_colortemp(rt)
            if abs(st - self.ui_colortemp) > 3:
                self.ui_colortemp = st
                sl = self.findChild(QSlider, "sl_temp")
                if sl:
                    sl.blockSignals(True)
                    sl.setValue(st)
                    sl.blockSignals(False)

        if raw_mode == "colour":
            colour_hex = state.get("colour", "")
            if colour_hex and len(colour_hex) >= 12:
                try:
                    hue_raw = int(colour_hex[0:4], 16)
                    sat_raw = int(colour_hex[4:8], 16)
                    self.ui_hue = int(hue_raw / 360.0 * 360)
                    self.ui_saturation = int(sat_raw / 1000.0 * 100)
                    self._update_color_preview()
                except (ValueError, IndexError):
                    pass

        self._update_status()

    # --- Helpers ---
    def _update_color_preview(self):
        r, g, b = colorsys.hsv_to_rgb(
            self.ui_hue / 360, self.ui_saturation / 100, 1.0
        )
        hx = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        self.cprev.setStyleSheet(f"background-color:{hx};")

    def _update_status(self):
        p = "On" if self.ui_power else "Off"
        mode_names = {"white": "White", "color": "Color", "scene": "Scenes"}
        m = mode_names.get(self.dev_mode, self.dev_mode)
        self.sts_bar.showMessage(
            f"Status: {p} | Mode: {m} | Brightness: {self.ui_brightness}%"
        )


def main():
    app = QApplication(sys.argv)

    cfg = load_config()
    if not cfg["device_id"] or not cfg["ip"] or not cfg["local_key"]:
        print("Error: missing device credentials.")
        print("Create config.json or set LAMP_DEVICE_ID, LAMP_IP, LAMP_KEY env vars.")
        sys.exit(1)

    try:
        device = LampDevice(
            cfg["device_id"],
            cfg["ip"],
            cfg["local_key"],
            cfg["protocol_version"],
        )
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    w = SmartLampController(device)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

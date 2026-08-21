"""
Systray battery indicator for the SteelSeries Arctis Nova 7.

Shows the battery percentage as two digits in the tray icon:
green while charging, red while discharging, gray when offline.
"""

import threading
import time

import hid
import pystray
from PIL import Image, ImageDraw, ImageFont

VID = 0x1038
PID = 0x22A1
POLL_INTERVAL_SEC = 30
DISCONNECTED_POLL_INTERVAL_SEC = 120

GREEN = (46, 204, 113, 255)
RED = (231, 76, 60, 255)
GRAY = (130, 130, 130, 255)

ICON_SIZE = 128
FONT_CANDIDATES = ["arialbd.ttf", "seguisb.ttf", "arial.ttf"]


def load_font(size):
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def find_interface_path():
    for d in hid.enumerate(VID, PID):
        if d.get("interface_number") == 3 and d.get("usage_page") == 0xFFC0:
            return d["path"]
    return None


def read_battery(dev):
    """Returns (level_percent, charging) or None if offline/unreadable."""
    req = bytes([0x00, 0xB0]) + bytes(62)
    dev.write(req)
    resp = dev.read(128, timeout_ms=2000)
    if not resp or len(resp) < 4:
        return None
    if resp[3] == 0x00:
        return None  # headset offline / not connected
    charging = resp[3] in (0x01, 0x02)
    level = min(resp[2], 100)
    return level, charging


def make_icon_image(level, charging):
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if level is None:
        text, color = "--", GRAY
    else:
        text, color = f"{level:02d}" if level < 100 else "99", (GREEN if charging else RED)

    # Start big and shrink only if the text would overflow the icon.
    font_size = 132
    margin = 4
    while font_size > 20:
        font = load_font(font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w <= ICON_SIZE - margin and h <= ICON_SIZE - margin:
            break
        font_size -= 4

    pos = ((ICON_SIZE - w) / 2 - bbox[0], (ICON_SIZE - h) / 2 - bbox[1])
    draw.text(pos, text, font=font, fill=color)
    return img


class ArctisTray:
    def __init__(self):
        self.path = find_interface_path()
        self.dev = None
        self.wake = threading.Event()
        self.running = True
        self.icon = pystray.Icon(
            "arctis_battery",
            make_icon_image(None, False),
            "Arctis Nova 7: checking...",
            menu=pystray.Menu(
                pystray.MenuItem("Refresh now", self._refresh_now),
                pystray.MenuItem("Quit", self._quit),
            ),
        )

    def _ensure_connected(self):
        if self.dev is not None:
            return True
        if self.path is None:
            self.path = find_interface_path()
        if self.path is None:
            return False
        try:
            dev = hid.device()
            dev.open_path(self.path)
            dev.set_nonblocking(False)
            self.dev = dev
            return True
        except OSError:
            self.dev = None
            return False

    def _poll_once(self):
        """Returns True if the headset battery was actually readable."""
        level = charging = None
        try:
            if self._ensure_connected():
                result = read_battery(self.dev)
                if result is not None:
                    level, charging = result
        except OSError:
            # dongle unplugged / handle went stale, force reconnect next time
            self.dev = None
            self.path = None

        self.icon.icon = make_icon_image(level, charging)
        if level is None:
            self.icon.title = "Arctis Nova 7: offline"
        else:
            state = "Charging" if charging else "Discharging"
            self.icon.title = f"Arctis Nova 7: {level}% ({state})"

        return level is not None

    def _poll_loop(self):
        while self.running:
            connected = self._poll_once()
            interval = POLL_INTERVAL_SEC if connected else DISCONNECTED_POLL_INTERVAL_SEC
            self.wake.wait(interval)
            self.wake.clear()

    def _refresh_now(self, icon, item):
        self.wake.set()

    def _quit(self, icon, item):
        self.running = False
        self.wake.set()
        icon.stop()

    def run(self):
        threading.Thread(target=self._poll_loop, daemon=True).start()
        self.icon.run()


if __name__ == "__main__":
    ArctisTray().run()

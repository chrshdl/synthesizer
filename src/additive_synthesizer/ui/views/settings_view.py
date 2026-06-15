import subprocess
import threading

import pygame
from pygame.sprite import LayeredDirty

from ...config import ConfigManager
from ...logger import Logger
from ...ui.utils.font import FontFamily, load_font
from ..widgets.button_widget import ButtonWidget


class SettingsView:
    def __init__(self, on_back):
        self.on_back = on_back
        self.logger = Logger(__class__.__name__).get()
        self.width = ConfigManager.get_config().width
        self.height = ConfigManager.get_config().height

        self.ui_layer = LayeredDirty()
        self.bg_color = (12, 14, 18)
        self.panel_color = (22, 26, 32)
        self.panel_accent = (40, 46, 56)
        self.white = (240, 242, 245)
        self.font_large = load_font(size=32, family=FontFamily.D_DIN_EXP_BOLD)
        self.font_med = load_font(size=22, family=FontFamily.D_DIN_EXP_BOLD)

        self.devices = []  # list of dicts: {'mac': str, 'name': str}
        self.is_scanning = False
        self.status_message = ""
        self.scan_thread = None

        self._init_ui()
        self.refresh_devices_sync()  # load already known devices

    def _init_ui(self):
        btn_w, btn_h = 140, 60
        self.btn_back = ButtonWidget(
            (16, 16, btn_w, btn_h),
            "BACK",
            self.on_back,
            self.font_med,
            self.panel_accent,
            self.white,
        )
        self.btn_scan = ButtonWidget(
            (16 + btn_w + 16, 16, btn_w, btn_h),
            "SCAN BT",
            self.start_scan,
            self.font_med,
            self.panel_accent,
            self.white,
        )
        self.ui_layer.add(self.btn_back)
        self.ui_layer.add(self.btn_scan)

        self.device_buttons = []

    def start_scan(self):
        if self.is_scanning:
            return
        self.is_scanning = True
        self.status_message = "Scanning for 5 seconds..."
        self.scan_thread = threading.Thread(target=self._scan_thread_func, daemon=True)
        self.scan_thread.start()

    def _scan_thread_func(self):
        try:
            # ensure powered on
            subprocess.run(["bluetoothctl", "power", "on"], capture_output=True)
            # scan
            subprocess.run(["bluetoothctl", "--timeout", "5", "scan", "on"], capture_output=True)
        except Exception as e:
            self.logger.error(f"Scan error: {e}")

        self.refresh_devices_sync()
        self.is_scanning = False
        self.status_message = "Scan complete."

    def refresh_devices_sync(self):
        try:
            res = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True)
            lines = res.stdout.strip().split('\n')
            new_devices = []
            for line in lines:
                if line.startswith("Device "):
                    parts = line.split(" ", 2)
                    if len(parts) >= 3:
                        new_devices.append({"mac": parts[1], "name": parts[2]})
            self.devices = new_devices
        except Exception as e:
            self.logger.error(f"Get devices error: {e}")
            self.devices = []
        self._rebuild_device_buttons()

    def connect_device(self, mac):
        self.status_message = f"Connecting to {mac}..."
        threading.Thread(target=self._connect_thread_func, args=(mac,), daemon=True).start()

    def _connect_thread_func(self, mac):
        try:
            # Pair, trust, connect
            subprocess.run(["bluetoothctl", "pair", mac], capture_output=True)
            subprocess.run(["bluetoothctl", "trust", mac], capture_output=True)
            res = subprocess.run(["bluetoothctl", "connect", mac], capture_output=True, text=True)
            if "Connection successful" in res.stdout:
                self.status_message = f"Connected to {mac}"
            else:
                self.status_message = f"Failed to connect {mac}"
        except Exception as e:
            self.status_message = f"Error: {e}"

    def _rebuild_device_buttons(self):
        for b in self.device_buttons:
            self.ui_layer.remove(b)
        self.device_buttons.clear()

        start_y = 100
        btn_w, btn_h = 600, 50
        for i, dev in enumerate(self.devices):
            y = start_y + i * (btn_h + 10)
            if y > self.height - btn_h:
                break

            # capture dev['mac'] in closure
            def make_action(mac):
                return lambda: self.connect_device(mac)

            label = f"{dev['name'][:30]} ({dev['mac']})"
            btn = ButtonWidget(
                (16, y, btn_w, btn_h),
                label,
                make_action(dev['mac']),
                self.font_med,
                self.panel_accent,
                self.white,
            )
            self.device_buttons.append(btn)
            self.ui_layer.add(btn)

    def draw(self, surface, background):
        surface.fill(self.bg_color)

        # draw title/status
        title = self.font_large.render("Bluetooth Settings", True, self.white)
        surface.blit(title, (16 + 140 * 2 + 32, 16))

        status = self.font_med.render(self.status_message, True, (200, 200, 100))
        surface.blit(status, (16 + 140 * 2 + 32, 56))

        for sprite in self.ui_layer.sprites():
            sprite.dirty = 1
        self.ui_layer.draw(surface)
        return [surface.get_rect()]

    def full_paint(self, surface, background):
        for sprite in self.ui_layer.sprites():
            sprite.dirty = 1
        if background:
            surface.blit(background, (0, 0))
        self.draw(surface, background)

    def update(self, dt: float):
        self.ui_layer.update(dt=dt)

    def handle_event(self, ev):
        for b in self.ui_layer.sprites():
            if hasattr(b, 'handle_event') and b.handle_event(ev):
                return True
        return False
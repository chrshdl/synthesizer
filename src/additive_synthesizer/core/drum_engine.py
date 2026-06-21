import os
from pathlib import Path

import pygame

from ..logger import Logger

_logger = Logger("DrumEngine").get()

class DrumEngine:
    def __init__(self):
        self.sounds = {}
        self.reload_sounds()

    def reload_sounds(self):
        base_dir = Path(__file__).resolve().parent.parent
        assets_dir = base_dir / "assets"

        if not assets_dir.is_dir():
            _logger.error(
                f"Assets directory not found: {assets_dir}. No drum sounds loaded."
            )
            return

        new_sounds = {}
        for filename in os.listdir(assets_dir):
            if filename.endswith(".wav"):
                path = str(assets_dir / filename)
                try:
                    new_sounds[filename] = pygame.mixer.Sound(path)
                except pygame.error as exc:
                    _logger.warning(f"Could not load drum sample '{filename}': {exc}")

        self.sounds = new_sounds
        _logger.debug(f"Loaded {len(self.sounds)} drum sample(s) from {assets_dir}")

    def play_sound(self, filename):
        if filename in self.sounds:
            self.sounds[filename].play()

    def get_available_sounds(self):
        return sorted(list(self.sounds.keys()))

    def set_master_volume(self, vol: float):
        for sound in self.sounds.values():
            sound.set_volume(vol)

    def handle_event(self, event):
        pass

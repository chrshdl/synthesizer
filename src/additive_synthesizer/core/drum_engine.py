import os
from pathlib import Path
import pygame

class DrumEngine:
    def __init__(self):
        self.sounds = {}
        self.reload_sounds()

    def reload_sounds(self):
        base_dir = Path(__file__).resolve().parent.parent
        assets_dir = base_dir / "assets"

        for filename in os.listdir(assets_dir):
            if filename.endswith(".wav"):
                path = str(assets_dir / filename)
                self.sounds[filename] = pygame.mixer.Sound(path)

    def play_sound(self, filename):
        if filename in self.sounds:
            self.sounds[filename].play()

    def get_available_sounds(self):
        return sorted(list(self.sounds.keys()))

    def handle_event(self, event):
        pass

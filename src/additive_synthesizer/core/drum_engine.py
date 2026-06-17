from pathlib import Path

import pygame


class DrumEngine:
    def __init__(self):
        self.reload_sounds()

        # Temporary QWERTY mapping for testing
        self.drum_mapping = {
            pygame.K_1: self.play_kick,
            pygame.K_2: self.play_snare,
            pygame.K_3: self.play_hat,
        }

    def reload_sounds(self):
        base_dir = Path(__file__).resolve().parent.parent
        assets_dir = base_dir / "assets"

        # load .wav files (ensure 16-bit, 44.1kHz to match the mixer)
        self.kick = pygame.mixer.Sound(str(assets_dir / "kick.wav"))
        self.snare = pygame.mixer.Sound(str(assets_dir / "snare.wav"))
        self.hat = pygame.mixer.Sound(str(assets_dir / "hihat.wav"))

    def play_kick(self):
        self.kick.play()

    def play_snare(self):
        self.snare.play()

    def play_hat(self):
        self.hat.play()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in self.drum_mapping:
            self.drum_mapping[event.key]()

import pygame


class DrumEngine:
    def __init__(self):
        # channels specifically for drums
        self.kick_channel = pygame.mixer.Channel(13)
        self.snare_channel = pygame.mixer.Channel(14)
        self.hat_channel = pygame.mixer.Channel(15)

        # load .wav files (ensure 16-bit, 44.1kHz to match the mixer)
        self.kick = pygame.mixer.Sound("assets/kick.wav")
        self.snare = pygame.mixer.Sound("assets/snare.wav")
        self.hat = pygame.mixer.Sound("assets/hihat.wav")

        # Temporary QWERTY mapping for testing
        self.drum_mapping = {
            pygame.K_1: self.play_kick,
            pygame.K_2: self.play_snare,
            pygame.K_3: self.play_hat,
        }

    def play_kick(self):
        self.kick_channel.play(self.kick)

    def play_snare(self):
        self.snare_channel.play(self.snare)

    def play_hat(self):
        self.hat_channel.play(self.hat)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in self.drum_mapping:
            self.drum_mapping[event.key]()

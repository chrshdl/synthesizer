import pygame
import numpy as np

class AudioEngine:
    def __init__(self, frequency=44100, size=-16, channels=1, buffer=512, num_partials=8):
        pygame.mixer.pre_init(frequency=frequency, size=size, channels=channels, buffer=buffer)
        pygame.init()
        
        self.num_partials = num_partials
        self.freq = 220.5  # Exactly 200 samples per period at 44.1kHz
        self.sr = frequency
        self.length = 4000  # 20 periods
        
        t = np.linspace(0, self.length / self.sr, self.length, endpoint=False)
        self.synth_sound = pygame.mixer.Sound(np.zeros(self.length, dtype=np.int16))
        self.synth_channel = self.synth_sound.play(loops=-1)
        self.synth_arr = pygame.sndarray.samples(self.synth_sound)
        
        self.partials_waves = np.array([np.sin(2 * np.pi * self.freq * (i + 1) * t) for i in range(self.num_partials)], dtype=np.float32)
        
        self.master_volume = 1.0
        self.current_amps = [0.0] * self.num_partials
        self.last_waveform = np.zeros(self.length, dtype=np.float32)

    def set_master_volume(self, vol: float):
        self.master_volume = vol
        self.update_amplitudes(self.current_amps)

    def get_current_waveform(self):
        return self.last_waveform

    def update_amplitudes(self, amps: list[float]):
        if len(amps) != self.num_partials:
            return
        self.current_amps = amps
        amps_arr = np.array(amps, dtype=np.float32).reshape(self.num_partials, 1)
        # Base waveform without master volume for the UI scope
        waveform = (np.sum(amps_arr * self.partials_waves, axis=0) / self.num_partials)
        self.last_waveform = waveform
        
        # Apply master volume for the actual audio output
        int_waveform = (waveform * self.master_volume * 32767).astype(np.int16)
        if self.synth_arr.ndim == 2 and self.synth_arr.shape[1] == 2:
            # Re-shape for stereo: the original length was used to create the Sound,
            # so if pygame forced stereo, length is halved in frames.
            frames = self.synth_arr.shape[0]
            self.synth_arr[:, 0] = int_waveform[:frames]
            self.synth_arr[:, 1] = int_waveform[:frames]
        else:
            self.synth_arr[:] = int_waveform

import pygame
import numpy as np

class AudioEngine:
    def __init__(self, frequency=44100, size=-16, channels=1, buffer=512, num_partials=16):
        pygame.mixer.pre_init(frequency=frequency, size=size, channels=channels, buffer=buffer)
        pygame.init()
        
        actual_freq, actual_format, actual_channels = pygame.mixer.get_init()
        
        self.num_partials = num_partials
        self.sr = actual_freq
        # Use exactly 1 second buffer so any integer frequency loops perfectly
        self.length = actual_freq  
        
        # 1 Octave integer frequencies: C4 to C5 + Default 220Hz
        self.key_freqs = [262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466, 494, 523]
        self.all_freqs = [220] + self.key_freqs
        
        t = np.linspace(0, 1.0, self.length, endpoint=False)
        
        # Precompute the wavetables for all keys to ensure 0ms latency switching
        self.freq_waves = {}
        for f in self.all_freqs:
            self.freq_waves[f] = np.array([np.sin(2 * np.pi * f * (i + 1) * t) for i in range(self.num_partials)], dtype=np.float32)
            
        self.freq = 220
        self.partials_waves = self.freq_waves[self.freq]
        
        if actual_channels == 2:
            buffer_shape = (self.length, 2)
        else:
            buffer_shape = (self.length,)
            
        self.synth_sound = pygame.mixer.Sound(np.zeros(buffer_shape, dtype=np.int16))
        self.synth_channel = self.synth_sound.play(loops=-1)
        self.synth_arr = pygame.sndarray.samples(self.synth_sound)
        
        self.master_volume = 1.0
        self.current_amps = [0.0] * self.num_partials
        self.last_waveform = np.zeros(self.length, dtype=np.float32)
        
        self.keys_mode = False
        self.gate_active = True

    def set_master_volume(self, vol: float):
        self.master_volume = vol
        self.update_amplitudes(self.current_amps)

    def set_keys_mode(self, active: bool):
        self.keys_mode = active
        # If keys mode is ON, silence the synth until a key is pressed (gate)
        self.gate_active = not active
        if not active:
            self.set_frequency(220)
        self.update_amplitudes(self.current_amps)
        
    def set_gate(self, active: bool):
        self.gate_active = active
        self.update_amplitudes(self.current_amps)
        
    def set_frequency(self, freq: int):
        if freq in self.freq_waves:
            self.freq = freq
            self.partials_waves = self.freq_waves[freq]
            self.update_amplitudes(self.current_amps)

    def get_current_waveform(self):
        return self.last_waveform

    def update_amplitudes(self, amps: list[float]):
        if len(amps) != self.num_partials:
            return
        self.current_amps = amps
        amps_arr = np.array(amps, dtype=np.float32).reshape(self.num_partials, 1)
        
        # Calculate raw waveform shape
        waveform = (np.sum(amps_arr * self.partials_waves, axis=0) / self.num_partials)
        self.last_waveform = waveform
        
        # Apply gate and master volume for actual output buffer
        eff_vol = self.master_volume if self.gate_active else 0.0
        int_waveform = (waveform * eff_vol * 32767).astype(np.int16)
        
        if self.synth_arr.ndim == 2 and self.synth_arr.shape[1] == 2:
            frames = self.synth_arr.shape[0]
            self.synth_arr[:, 0] = int_waveform[:frames]
            self.synth_arr[:, 1] = int_waveform[:frames]
        else:
            self.synth_arr[:] = int_waveform

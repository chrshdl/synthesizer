import numpy as np
import pygame


class AudioEngine:
    def __init__(
        self, frequency=44100, size=-16, channels=1, buffer=512, num_partials=8
    ):
        # Initialize mixer with 16 dedicated channels for polyphony
        pygame.mixer.set_num_channels(16)
        actual_freq, actual_format, actual_channels = pygame.mixer.get_init()

        self.num_partials = num_partials
        self.sr = actual_freq
        self.length = actual_freq  # 1 second buffer for perfect loops

        # 1 Octave integer frequencies: C4 to C5
        self.key_freqs = [
            262,
            277,
            294,
            311,
            330,
            349,
            370,
            392,
            415,
            440,
            466,
            494,
            523,
        ]

        t = np.linspace(0, 1.0, self.length, endpoint=False)

        self.freq_partials = {}
        self.sounds = {}
        self.sound_arrays = {}
        self.active_channels = {}  # Tracks which channel is playing which freq

        # Determine shape based on stereo/mono
        self.buffer_shape = (self.length, 2) if actual_channels == 2 else (self.length,)
        self.actual_channels = actual_channels

        # Precompute the thickened wavetables for all keys
        for f in self.key_freqs:
            partials = []
            for i in range(self.num_partials):
                base_f = f * (i + 1)

                # Faster, scaled integer detuning.
                # The fundamental gets a 3Hz beat, the next gets 4Hz, then 5Hz, etc.
                # This speeds up the oscillation and mimics natural inharmonicity!
                detune_hz = 3 + i

                # Integer Detuning: Base wave + faster beating voices
                wave_center = np.sin(2 * np.pi * base_f * t)
                wave_sharp = np.sin(2 * np.pi * (base_f + detune_hz) * t) * 0.4
                wave_flat = np.sin(2 * np.pi * (base_f - detune_hz) * t) * 0.4

                # Mix them together into a single "thick" partial
                thick_wave = (wave_center + wave_sharp + wave_flat) / 1.8
                partials.append(thick_wave)

            # Store the raw float arrays
            self.freq_partials[f] = np.array(partials, dtype=np.float32)

            # Create a Pygame Sound object for this specific key
            sound = pygame.mixer.Sound(np.zeros(self.buffer_shape, dtype=np.int16))
            self.sounds[f] = sound
            self.sound_arrays[f] = pygame.sndarray.samples(sound)

        self.master_volume = 0.5
        # Start with just the fundamental frequency at max volume
        self.current_amps = [1.0] + [0.0] * (self.num_partials - 1)

        # Initialize the buffers with the default amplitude
        self.update_amplitudes(self.current_amps)

    def set_master_volume(self, vol: float):
        self.master_volume = vol
        self.update_amplitudes(self.current_amps)

    def update_amplitudes(self, amps: list[float]):
        if len(amps) != self.num_partials:
            return
        self.current_amps = amps
        amps_arr = np.array(amps, dtype=np.float32).reshape(self.num_partials, 1)

        # Instantly update the wavetables for ALL keys simultaneously
        for f in self.key_freqs:
            waveform = (
                np.sum(amps_arr * self.freq_partials[f], axis=0) / self.num_partials
            )
            int_waveform = (waveform * self.master_volume * 32767).astype(np.int16)

            if self.actual_channels == 2:
                frames = self.sound_arrays[f].shape[0]
                self.sound_arrays[f][:, 0] = int_waveform[:frames]
                self.sound_arrays[f][:, 1] = int_waveform[:frames]
            else:
                self.sound_arrays[f][:] = int_waveform

    def note_on(self, freq: int):
        if freq in self.sounds and freq not in self.active_channels:
            # Find an available channel and play the specific sound for this frequency
            channel = pygame.mixer.find_channel()
            if channel:
                # 20ms fade in prevents popping on attack
                channel.play(self.sounds[freq], loops=-1, fade_ms=20)
                self.active_channels[freq] = channel

    def note_off(self, freq: int):
        if freq in self.active_channels:
            # 200ms fade out simulates natural decay and prevents clicking
            self.active_channels[freq].fadeout(200)
            del self.active_channels[freq]

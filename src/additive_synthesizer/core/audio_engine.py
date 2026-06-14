import numpy as np
import pygame


class AudioEngine:
    def __init__(self, num_partials=8):
        # we need at least 13 channels for our 13 keys (C4 to C5)
        pygame.mixer.set_num_channels(16)
        actual_freq, actual_format, actual_channels = pygame.mixer.get_init()

        self.num_partials = num_partials
        self.sr = actual_freq
        self.length = actual_freq  # 1 second buffer for perfect loops

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

        # hardware voice architecture
        self.freq_channels = {}
        self.active_notes = set()

        self.buffer_shape = (self.length, 2) if actual_channels == 2 else (self.length,)
        self.actual_channels = actual_channels

        # precompute the thickened wavetables for all keys
        for i, f in enumerate(self.key_freqs):
            partials = []
            for p_idx in range(self.num_partials):
                base_f = f * (p_idx + 1)

                detune_hz = 3 + p_idx
                wave_center = np.sin(2 * np.pi * base_f * t)
                wave_sharp = np.sin(2 * np.pi * (base_f + detune_hz) * t) * 0.4
                wave_flat = np.sin(2 * np.pi * (base_f - detune_hz) * t) * 0.4
                thick_wave = (wave_center + wave_sharp + wave_flat) / 1.8
                partials.append(thick_wave)

            self.freq_partials[f] = np.array(partials, dtype=np.float32)

            sound = pygame.mixer.Sound(np.zeros(self.buffer_shape, dtype=np.int16))
            self.sounds[f] = sound
            self.sound_arrays[f] = pygame.sndarray.samples(sound)

            # permanently assign a dedicated pygame channel (0 - 12)
            self.freq_channels[f] = pygame.mixer.Channel(i)

        self.master_volume = 0.5
        self.current_amps = [1.0] + [0.0] * (self.num_partials - 1)
        self.update_amplitudes(self.current_amps)

    def set_master_volume(self, vol: float):
        self.master_volume = vol
        self.update_amplitudes(self.current_amps)

    def update_amplitudes(self, amps: list[float]):
        if len(amps) != self.num_partials:
            return
        self.current_amps = amps
        amps_arr = np.array(amps, dtype=np.float32).reshape(self.num_partials, 1)

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
        if freq in self.sounds and freq not in self.active_notes:
            self.active_notes.add(freq)
            # call the dedicated channel directly
            channel = self.freq_channels[freq]
            channel.set_volume(1.0)  # ensure volume is maxed
            channel.play(
                self.sounds[freq], loops=-1
            )  # no fade_ms prevents collision bugs

    def note_off(self, freq: int):
        if freq in self.active_notes:
            self.active_notes.remove(freq)
            # 200ms fadeout stops pops on release
            self.freq_channels[freq].fadeout(200)

    def all_notes_off(self):
        """Nuclear panic function. Instantly kills all dedicated channels."""
        for channel in self.freq_channels.values():
            channel.stop()  # hard stop bypassing fadeouts
        self.active_notes.clear()

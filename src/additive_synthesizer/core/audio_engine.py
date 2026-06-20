"""
AudioEngine — smart dispatcher

Tries to load the native C++ engine (libsynthengine.so) first for minimum
latency.  If the shared library is not available (e.g. during host-side
development without an ALSA device) it falls back to the pure-Python
implementation that streams raw PCM to aplay.

Typical latency comparison
──────────────────────────
                        native C++      Python/aplay
  chunk generation       ~1.5 ms         ~11 ms
  kernel pipe            0 ms            ~46 ms
  ALSA hw buffer         ~11 ms          ~23 ms
  ─────────────────────────────────────────────
  total engine           ~13 ms          ~80 ms

Usage (unchanged from before — main.py needs zero edits):
    from additive_synthesizer.core.audio_engine import AudioEngine
    engine = AudioEngine(num_partials=8)
    engine.note_on(440)
    engine.update_amplitudes([1.0, 0.5, 0.25, ...])
"""

from .audio_engine_native import NativeAudioEngine, is_available as _native_available


if _native_available:
    class AudioEngine(NativeAudioEngine):
        """
        AudioEngine backed by the C++ ALSA engine (libsynthengine.so).
        Lowest possible latency — writes directly to ALSA from a native thread.
        """
        pass

else:
    # ------------------------------------------------------------------ #
    # Pure-Python fallback (original aplay-based implementation)         #
    # ------------------------------------------------------------------ #
    import numpy as np
    import threading
    import subprocess

    class AudioEngine:  # type: ignore[no-redef]
        """
        AudioEngine — Native Python Gapless Audio Streamer via aplay

        Bypasses Pygame's mixer entirely for the synthesizer, as Pygame's
        queue() has a known bug causing stuttering for chunks < 0.1s.  We
        stream raw 16-bit PCM directly to the native ALSA 'aplay' utility via
        a blocking subprocess pipe.  This guarantees perfect, kernel-level
        gapless audio scheduling while preserving our mathematical envelope
        smoothing.

        NOTE: this path is only used when libsynthengine.so is not found.
              Build the synthesizer-audio-engine Buildroot package to get the
              low-latency C++ engine.
        """

        def __init__(self, num_partials=8):
            self.num_partials = num_partials
            self.key_freqs = [
                262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466, 494, 523,
            ]

            self.master_volume = 0.5
            self.target_amps = np.array(
                [1.0] + [0.0] * (self.num_partials - 1), dtype=np.float32
            )
            self.current_amps = self.target_amps.copy()

            self.active_notes = set()
            self.note_envs = {}
            self.note_states = {}
            self.lock = threading.Lock()

            # Generate in small 64-sample chunks (1.45ms) for fast UI responsiveness
            self.chunk_size = 64
            self.t_idx = 0
            self.sr = 44100
            self.length = self.sr

            self._precompute_sounds()

            self.running = True
            self.aplay_process = None
            self.thread = threading.Thread(target=self._audio_thread, daemon=True)
            self.thread.start()

        def _precompute_sounds(self):
            t = np.linspace(0, 1.0, self.length, endpoint=False)
            self.freq_partials = {}

            for f in self.key_freqs:
                partials = []
                for p_idx in range(self.num_partials):
                    base_f = f * (p_idx + 1)
                    detune_hz = 3 + p_idx

                    # Randomize starting phases to prevent the 'Crest Factor' problem
                    p_c = np.random.uniform(0, 2 * np.pi)
                    p_s = np.random.uniform(0, 2 * np.pi)
                    p_f = np.random.uniform(0, 2 * np.pi)

                    wave_center = np.sin(2 * np.pi * base_f * t + p_c)
                    wave_sharp = np.sin(2 * np.pi * (base_f + detune_hz) * t + p_s) * 0.4
                    wave_flat = np.sin(2 * np.pi * (base_f - detune_hz) * t + p_f) * 0.4

                    thick_wave = (wave_center + wave_sharp + wave_flat) / 1.8
                    partials.append(thick_wave)

                self.freq_partials[f] = np.array(partials, dtype=np.float32)

        def _audio_thread(self):
            # Start aplay subprocess for stereo 44.1kHz 16-bit PCM.
            # We use --period-size=128 / --buffer-size=512.
            # Anything smaller causes ALSA to starve and throw constant XRUN
            # crackles because Python's GIL cannot feed it fast enough!
            self.aplay_process = subprocess.Popen(
                [
                    "aplay", "-q",
                    "-f", "S16_LE",
                    "-c", "2",
                    "-r", "44100",
                    "--period-size=128",
                    "--buffer-size=512",
                ],
                stdin=subprocess.PIPE,
            )
            try:
                import fcntl
                # F_SETPIPE_SZ = 1031. Shrink pipe to 4096 bytes (~23ms latency)
                fcntl.fcntl(self.aplay_process.stdin.fileno(), 1031, 4096)
            except Exception as e:
                print("Could not resize pipe:", e)

            # 25ms linear attack and release to eliminate clicking
            env_step = 1.0 / (44100 * 0.025)

            while self.running:
                chunk = np.zeros(self.chunk_size, dtype=np.float32)

                with self.lock:
                    active_list = list(self.active_notes)
                    states = self.note_states.copy()
                    target = self.target_amps.copy()

                if np.array_equal(target, self.current_amps):
                    amp_envelope = self.current_amps[:, None]
                else:
                    amp_step = (target - self.current_amps) / self.chunk_size
                    steps = np.arange(self.chunk_size, dtype=np.float32)
                    amp_envelope = self.current_amps[:, None] + amp_step[:, None] * steps
                    self.current_amps = target

                if active_list:
                    start_idx = self.t_idx % self.length
                    end_idx = start_idx + self.chunk_size

                    for f in active_list:
                        state = states.get(f, "off")
                        start_env = self.note_envs.get(f, 0.0)

                        target_env = 1.0 if state == "on" else 0.0

                        if start_env == target_env:
                            end_env = start_env
                            note_ramp = start_env
                        else:
                            max_change = env_step * self.chunk_size
                            if target_env > start_env:
                                end_env = min(target_env, start_env + max_change)
                            else:
                                end_env = max(target_env, start_env - max_change)

                            note_ramp = np.linspace(
                                start_env, end_env, self.chunk_size, dtype=np.float32
                            )

                        self.note_envs[f] = end_env

                        if end_idx <= self.length:
                            waves = self.freq_partials[f][:, start_idx:end_idx]
                        else:
                            waves = np.concatenate(
                                (
                                    self.freq_partials[f][:, start_idx : self.length],
                                    self.freq_partials[f][:, 0 : end_idx - self.length],
                                ),
                                axis=1,
                            )

                        note_audio = np.sum(waves * amp_envelope, axis=0)
                        if type(note_ramp) is float and note_ramp == 1.0:
                            chunk += note_audio
                        else:
                            chunk += note_audio * note_ramp

                        if end_env == 0.0 and state == "off":
                            with self.lock:
                                if (
                                    f in self.active_notes
                                    and self.note_states.get(f) == "off"
                                ):
                                    self.active_notes.remove(f)

                    chunk = chunk * (self.master_volume / (self.num_partials * 2.5))

                # DSP Soft Limiter
                chunk = np.tanh(chunk)
                int_chunk = (chunk * 32767).astype(np.int16)

                # Stereo interleave to double byte-rate and halve pipe latency
                stereo_chunk = np.empty(self.chunk_size * 2, dtype=np.int16)
                stereo_chunk[0::2] = int_chunk
                stereo_chunk[1::2] = int_chunk

                try:
                    self.aplay_process.stdin.write(stereo_chunk.tobytes())
                    self.aplay_process.stdin.flush()

                    if np.max(np.abs(int_chunk)) > 100:
                        import time
                        from additive_synthesizer.config import ConfigManager
                        conf = ConfigManager.get_config()
                        if hasattr(conf, "latency_t0") and conf.latency_t0 is not None:
                            t1 = time.time()
                            print(
                                f"===========================================================",
                                flush=True,
                            )
                            print(
                                f">>> SOFTWARE LATENCY: {(t1 - conf.latency_t0)*1000:.2f} ms <<<",
                                flush=True,
                            )
                            print(
                                f"===========================================================",
                                flush=True,
                            )
                            conf.latency_t0 = None

                except (BrokenPipeError, OSError):
                    break

                self.t_idx += self.chunk_size

            if self.aplay_process:
                self.aplay_process.terminate()

        def update_amplitudes(self, amps: list[float]):
            if len(amps) != self.num_partials:
                return
            with self.lock:
                self.target_amps = np.array(amps, dtype=np.float32)

        def set_master_volume(self, vol: float):
            self.master_volume = vol

        def note_on(self, freq: int):
            with self.lock:
                self.active_notes.add(freq)
                if freq not in self.note_envs:
                    self.note_envs[freq] = 0.0
                self.note_states[freq] = "on"

        def note_off(self, freq: int):
            with self.lock:
                self.note_states[freq] = "off"

        def all_notes_off(self):
            with self.lock:
                for freq in self.active_notes:
                    self.note_states[freq] = "off"

        def switch_to_bluetooth(self):
            pass

        def tick(self):
            pass

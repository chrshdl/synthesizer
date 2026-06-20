"""
audio_engine_native.py — ctypes bindings for libsynthengine.so (v4)

Architecture:
  - C++ library is a self-contained ALSA audio engine.
  - It owns its own high-priority audio thread and writes directly to ALSA
    (which routes to PipeWire).
  - There is no aplay subprocess, no Python streaming loop, and no pipe buffer.
  - Python calls are simple lock-free atomic writes (microsecond overhead).

Library search order:
  1. $SYNTH_ENGINE_LIB
  2. /usr/lib/libsynthengine.so
  3. <this file's parent>/libsynthengine.so
"""

import ctypes
import os
import pathlib

# ---------------------------------------------------------------------------
# Library loading
# ---------------------------------------------------------------------------

def _find_lib() -> str | None:
    candidates = [
        os.environ.get("SYNTH_ENGINE_LIB"),
        "/usr/lib/libsynthengine.so",
        str(pathlib.Path(__file__).parent / "libsynthengine.so"),
    ]
    for p in candidates:
        if p and pathlib.Path(p).exists():
            return p
    return None

def _load_lib():
    path = _find_lib()
    if path is None:
        return None
    try:
        lib = ctypes.CDLL(path)
    except OSError as e:
        print(f"[synthengine] Could not load {path}: {e}")
        return None

    lib.se_create.restype  = ctypes.c_void_p
    lib.se_create.argtypes = [ctypes.c_int]

    lib.se_destroy.restype  = None
    lib.se_destroy.argtypes = [ctypes.c_void_p]

    lib.se_note_on.restype  = None
    lib.se_note_on.argtypes = [ctypes.c_void_p, ctypes.c_int]

    lib.se_note_off.restype  = None
    lib.se_note_off.argtypes = [ctypes.c_void_p, ctypes.c_int]

    lib.se_all_notes_off.restype  = None
    lib.se_all_notes_off.argtypes = [ctypes.c_void_p]

    lib.se_update_amplitudes.restype  = None
    lib.se_update_amplitudes.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_int,
    ]

    lib.se_set_master_volume.restype  = None
    lib.se_set_master_volume.argtypes = [ctypes.c_void_p, ctypes.c_float]

    lib.se_trigger_latency_measurement.restype = None
    lib.se_trigger_latency_measurement.argtypes = [ctypes.c_void_p, ctypes.c_double]

    return lib

_lib = _load_lib()
is_available = _lib is not None

# ---------------------------------------------------------------------------
# NativeAudioEngine
# ---------------------------------------------------------------------------

class NativeAudioEngine:
    """
    Drop-in replacement for the pure-Python AudioEngine.

    The C++ engine owns the audio thread and directly writes to ALSA.
    Python methods are just thin wrappers around non-blocking C functions.
    """

    def __init__(self, num_partials: int = 8):
        if not is_available:
            raise RuntimeError(
                "libsynthengine.so not found. "
                "Set SYNTH_ENGINE_LIB or build the synthesizer-audio-engine package."
            )
        self._num_partials = num_partials
        self._handle = _lib.se_create(ctypes.c_int(num_partials))
        if not self._handle:
            raise RuntimeError("se_create() returned NULL")

        print(f"[synthengine] Native C++ engine wrapper started ({num_partials} partials)")

    # ------------------------------------------------------------------ #
    # Public API                                                          #
    # ------------------------------------------------------------------ #

    def note_on(self, freq: int) -> None:
        try:
            from additive_synthesizer.config import ConfigManager
            conf = ConfigManager.get_config()
            if hasattr(conf, "latency_t0") and conf.latency_t0 is not None:
                _lib.se_trigger_latency_measurement(self._handle, ctypes.c_double(conf.latency_t0))
                conf.latency_t0 = None
        except Exception:
            pass

        _lib.se_note_on(self._handle, ctypes.c_int(freq))

    def note_off(self, freq: int) -> None:
        _lib.se_note_off(self._handle, ctypes.c_int(freq))

    def all_notes_off(self) -> None:
        _lib.se_all_notes_off(self._handle)

    def update_amplitudes(self, amps: list[float]) -> None:
        if len(amps) != self._num_partials:
            return
        arr = (ctypes.c_float * len(amps))(*amps)
        _lib.se_update_amplitudes(self._handle, arr, ctypes.c_int(len(amps)))

    def set_master_volume(self, vol: float) -> None:
        _lib.se_set_master_volume(self._handle, ctypes.c_float(vol))

    def switch_to_bluetooth(self) -> None:
        pass

    def tick(self) -> None:
        pass

    # ------------------------------------------------------------------ #
    # Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    def shutdown(self) -> None:
        if self._handle:
            _lib.se_destroy(self._handle)
            self._handle = None

    def __del__(self) -> None:
        self.shutdown()

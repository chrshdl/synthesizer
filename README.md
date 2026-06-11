# Additive Synthesizer

A child-friendly, wavetable-based additive synthesizer designed specifically for the Raspberry Pi 4 and the Raspberry Pi Touch Display 2.

## Overview

This project was built to provide an interactive experience for learning about sound synthesis. Interact in real-time with 8 colorful "bubbles" representing distinct harmonic partials and shape waveforms by tapping and dragging.

Features:
- **Zero-Latency Audio:** Uses a high-performance `numpy` wavetable engine that writes directly to a looping Pygame buffer, entirely bypassing Python-side queuing overhead.
- **Hardware Optimized:** Targets 60 FPS on the Raspberry Pi 4 without stuttering or audio dropouts.
- **Child-Robust UI:** Forgiving hitboxes, locked horizontal drag mechanics, and tap-to-set functionalities to accommodate inexact inputs.
- **Master Controls:** Includes Mute All, Randomize, Reset, and a Master Volume slider.

## Architecture

The project has been carefully refactored to separate rendering, state management, and core audio logic, taking heavy architectural cues from modern embedded dashboard applications.

```
src/synthesizer/
├── core/
│   └── audio_engine.py      # Numpy wavetable generation and buffer management
├── states/
│   ├── state_manager.py     # Hierarchical state machine
│   ├── state.py             # Base State
│   └── synthesizer_state.py # Dashboard state for the synth UI
├── ui/
│   ├── views/
│   │   └── synthesizer_view.py # Pure layout and rendering logic
│   └── widgets/
│       ├── button_widget.py    # Reusable UI button component
│       └── slider_widget.py    # Master volume slider component
├── main.py                  # Entry point
└── pyproject.toml           # Packaging and dependencies
```

## Running Locally

To run the application locally on your host machine:

1. Ensure you have Python 3.13+ installed.
2. We recommend using `uv` to manage the environment:
   ```bash
   uv sync
   uv run synthesizer
   ```
   *(Alternatively, run `python3 main.py` directly after installing `pygame` and `numpy`)*

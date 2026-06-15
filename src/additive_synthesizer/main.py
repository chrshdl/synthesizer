import os
import signal
import sys

os.environ["SDL_AUDIODRIVER"] = "alsa"
import pygame

from .config import Config, ConfigManager
from .core.audio_engine import AudioEngine
from .core.drum_engine import DrumEngine
from .core.system_health_monitor import SystemHealthMonitor
from .logger import Logger
from .states.state_manager import StateManager
from .states.synthesizer_state import SynthesizerState

logger = Logger("SynthesizerOS").get()


def is_raspberry_pi_4() -> bool:
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read()
            return "Raspberry Pi 4" in model
    except (FileNotFoundError, OSError):
        return False


def run(conf: Config) -> None:

    def handle_exit(sig, frame):
        """Signal handler for graceful shutdown (SIGTERM/SIGINT)"""
        logger.info("Exit signal received. Closing dashboard ...")
        state_manager.is_running = False

    # register OS signals for systemd compatibility
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # pre-init mixer with a very low buffer size (128 or 256) to ensure low latency
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=256)
    pygame.mixer.init(
        frequency=44100,
        size=-16,
        channels=2,
        buffer=256,
        allowedchanges=0,
    )
    pygame.init()
    pygame.mouse.set_visible(False)

    use_hardware_renderer = is_raspberry_pi_4()
    gpu_renderer = None
    main_surface = None

    try:
        if use_hardware_renderer:
            from .core.hardware_renderer import HardwareRenderer

            gpu_renderer = HardwareRenderer(
                physical_size=(conf.height, conf.width),
                logical_size=(conf.width, conf.height),
                rotation_angle=270,
            )
            main_surface = pygame.Surface((conf.width, conf.height))
        else:
            main_surface = pygame.display.set_mode((conf.width, conf.height))

        state_manager = StateManager(main_surface)

        # Initialize system health monitor
        health = SystemHealthMonitor()

        n_partials = 8
        audio_engine = AudioEngine(num_partials=n_partials)
        drum_engine = DrumEngine()

        initial_state = SynthesizerState(
            state_manager=state_manager,
            audio_engine=audio_engine,
            drum_engine=drum_engine,
            n_partials=n_partials,
        )

        state_manager.push_state(initial_state)

        # notify systemd that initialization is complete
        health.notify_ready()

        clock = pygame.time.Clock()

        # --- QWERTY Polyphony Mapping ---
        # A S D F G H J K L ; ' = C4 to C5 white keys
        # W E T Y U O P = Black keys
        qwerty_mapping = {
            pygame.K_a: 0,
            pygame.K_w: 1,
            pygame.K_s: 2,
            pygame.K_e: 3,
            pygame.K_d: 4,
            pygame.K_f: 5,
            pygame.K_t: 6,
            pygame.K_g: 7,
            pygame.K_y: 8,
            pygame.K_h: 9,
            pygame.K_u: 10,
            pygame.K_j: 11,
            pygame.K_k: 12,
        }

        while state_manager.is_running:
            # calculate delta time (targeting 60 fps)
            dt = clock.tick(60) / 1000.0

            # update system health (watchdog tick)
            health.update(dt)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    state_manager.is_running = False

                # Let the UI handle standard events first (like mouse clicks)
                state_manager.handle_event(event)
                drum_engine.handle_event(event)

                # --- Handle QWERTY Intercepts ---
                if event.type == pygame.KEYDOWN and event.key in qwerty_mapping:
                    idx = qwerty_mapping[event.key]
                    # Add to the visual set
                    initial_state.view.keyboard.active_indices.add(idx)
                    initial_state.view.keyboard._rebuild_image()
                    # Trigger audio
                    initial_state.view.on_note_on(idx)

                elif event.type == pygame.KEYUP and event.key in qwerty_mapping:
                    idx = qwerty_mapping[event.key]
                    # Remove from the visual set
                    initial_state.view.keyboard.active_indices.discard(idx)
                    initial_state.view.keyboard._rebuild_image()
                    # Stop audio
                    initial_state.view.on_note_off(idx)

            state_manager.update(dt)
            dirty_rects = state_manager.draw(main_surface)

            if dirty_rects:
                if use_hardware_renderer and gpu_renderer:
                    gpu_renderer.render(main_surface)
                else:
                    # standard software blit
                    pygame.display.update(dirty_rects)
    except Exception as e:
        logger.error(f"Critical system error: {e}", exc_info=True)

    finally:
        logger.info("Cleaning up resources...")
        pygame.quit()


def main() -> None:
    """Entry point for the application."""
    try:
        run(ConfigManager.get_config())
    except Exception as e:
        logger.critical(f"Application failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

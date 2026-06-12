import signal
import sys

import pygame

from .config import Config, ConfigManager
from .core.audio_engine import AudioEngine
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
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=256)
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

        n_partials = 8
        audio_engine = AudioEngine(num_partials=n_partials)

        initial_state = SynthesizerState(
            state_manager=state_manager,
            audio_engine=audio_engine,
            n_partials=n_partials,
        )

        state_manager.push_state(initial_state)

        clock = pygame.time.Clock()

        while state_manager.is_running:
            # calculate delta time (targeting 60 fps)
            dt = clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    state_manager.is_running = False
                state_manager.handle_event(event)

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

import sys

import pygame

from core.audio_engine import AudioEngine
from states.state_manager import StateManager
from states.synthesizer_state import SynthesizerState


def main():
    pygame.init()
    audio_engine = AudioEngine()

    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Additive Synthesizer")

    state_manager = StateManager(screen)
    initial_state = SynthesizerState(state_manager, audio_engine)
    state_manager.push_state(initial_state)

    clock = pygame.time.Clock()

    while state_manager.is_running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                state_manager.is_running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state_manager.is_running = False
            state_manager.handle_event(event)

        state_manager.update(dt)
        dirty_rects = state_manager.draw(screen)

        if dirty_rects:
            pygame.display.update(dirty_rects)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()

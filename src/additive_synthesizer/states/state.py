from abc import ABC
from typing import Optional

import pygame

from .state_types import SupportsStateChange


class State(ABC):
    def __init__(self, state_manager: Optional[SupportsStateChange] = None):
        self.state_manager = state_manager
        self.screen: pygame.Surface | None = None
        self.background: pygame.Surface | None = None
        self.view = None
        self._pending_transition = None

    def draw(self, surface: pygame.Surface):
        if self.view:
            return self.view.draw(surface, self.background)
        return []

    def full_paint(self, surface: pygame.Surface):
        if self.background is not None:
            surface.blit(self.background, (0, 0))
        if self.view:
            self.view.full_paint(surface, self.background)

    def handle_event(self, event) -> bool:
        if self.view and self.view.handle_event(event):
            return True
        return False

    def enter(self, screen: pygame.Surface):
        self.screen = screen
        self.background = pygame.Surface(screen.get_size()).convert()
        self.background.fill(self.background_color())
        self.draw_static_background(self.background)
        screen.blit(self.background, (0, 0))
        return [screen.get_rect()]

    def exit(self):
        pass

    def update(self, dt: float):
        self.process_delayed_transition(self.state_manager)
        if self.view:
            self.view.update(dt)

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    def background_color(self):
        return (0, 0, 0)

    def draw_static_background(self, bg: pygame.Surface):
        pass

    def request_delayed_transition(self, next_state, delay_seconds):
        trigger_time = pygame.time.get_ticks() / 1000.0 + delay_seconds
        self._pending_transition = (next_state, trigger_time)

    def process_delayed_transition(self, state_manager: SupportsStateChange):
        if self._pending_transition:
            _, trigger_time = self._pending_transition
            now = pygame.time.get_ticks() / 1000.0
            if now >= trigger_time:
                next_state, _ = self._pending_transition
                self._pending_transition = None
                state_manager.change_state(next_state)
                return True
        return False

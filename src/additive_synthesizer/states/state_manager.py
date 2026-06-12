from typing import List, Optional

import pygame

from .state import State
from .state_types import SupportsStateChange


class StateManager(SupportsStateChange):
    def __init__(self, screen: pygame.Surface, initial_state: Optional[State] = None):
        self.is_running = True
        self._screen = screen
        self._stack: List[State] = []
        self._pending_rects: list[pygame.Rect] = []

        if initial_state is not None:
            self.push_state(initial_state)

    @property
    def current_state(self) -> Optional[State]:
        return self._stack[-1] if self._stack else None

    def handle_event(self, event: pygame.event.Event) -> bool:
        for state in reversed(self._stack):
            try:
                if bool(state.handle_event(event)):
                    return True
            except Exception as e:
                print(e)
        return False

    def update(self, dt: float):
        try:
            if self.current_state:
                self.current_state.update(dt)
        except Exception:
            pass

    def draw(self, surface: pygame.Surface):
        s = self.current_state
        if not s:
            return []

        if getattr(self, "_pending_rects", None):
            try:
                s.full_paint(surface)
            except Exception as e:
                print("full_paint error:", e)
            rects = self._pending_rects
            self._pending_rects = []
            return rects

        rects: list[pygame.Rect] = []
        r = s.draw(surface)
        if r:
            rects.extend(r)
        return rects

    def change_state(self, new_state: State):
        if self._stack:
            top = self._stack.pop()
            try:
                top.exit()
            except Exception:
                pass
        self.push_state(new_state)

    def push_state(self, state: State):
        top = self.current_state
        if top is not None:
            try:
                top.on_pause()
            except Exception as e:
                print(e)
        state.state_manager = self
        self._stack.append(state)
        try:
            rects = state.enter(self._screen) or [self._screen.get_rect()]
            self._pending_rects = list(rects)
        except Exception as e:
            print(e)

    def pop_state(self):
        if not self._stack:
            return
        top = self._stack.pop()
        try:
            top.exit()
        except Exception:
            pass
        if self._stack:
            state = self._stack[-1]
            try:
                state.on_resume()
            finally:
                self._pending_rects = [self._screen.get_rect()]

from dataclasses import dataclass

import pygame
from pygame.sprite import DirtySprite
from ..utils.input import get_event_pos, is_primary_click
from ...config import ConfigManager


@dataclass
class DrumPad:
    """Layout and runtime state for one drum surface."""
    name: str
    nx: float        # normalised x position (0–1)
    ny: float        # normalised y position (0–1)
    nw: float        # normalised width
    nh: float        # normalised height
    active_frames: int   # frames remaining in the hit-flash animation
    default_wav: str     # fallback sample filename


class DrumKitWidget(DirtySprite):
    def __init__(self, rect, drum_engine, on_long_press=None):
        super().__init__()
        self.rect = pygame.Rect(rect)
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.drum_engine = drum_engine
        self.on_long_press = on_long_press
        self.is_locked = True

        config = ConfigManager.get_config()
        self.mapping = config.drum_mapping

        # Normalised layout: positions and sizes are fractions of the widget
        # rect so the drum kit scales correctly at any resolution.
        self.drums: list[DrumPad] = [
            DrumPad("cymbal1", 0.10, 0.15, 0.20, 0.12, 0, "cymbal1.wav"),
            DrumPad("hihat",   0.15, 0.40, 0.20, 0.12, 0, "hihat.wav"),
            DrumPad("cymbal2", 0.70, 0.15, 0.25, 0.15, 0, "cymbal2.wav"),
            DrumPad("tom1",    0.35, 0.25, 0.15, 0.20, 0, "tom1.wav"),
            DrumPad("tom2",    0.50, 0.25, 0.15, 0.20, 0, "tom2.wav"),
            DrumPad("snare",   0.20, 0.65, 0.22, 0.25, 0, "snare.wav"),
            DrumPad("tom3",    0.60, 0.65, 0.22, 0.25, 0, "tom3.wav"),
            DrumPad("kick",    0.38, 0.55, 0.24, 0.40, 0, "kick.wav"),
        ]

        for d in self.drums:
            if d.name not in self.mapping:
                self.mapping[d.name] = d.default_wav

        # Track touch down times for long press detection
        self.active_touches: dict = {}  # pointer_id → (drum_index, down_time_ms)
        self.long_press_threshold_ms = 600

        self._rebuild_image()

    def update(self, dt):
        dirty = False
        for d in self.drums:
            if d.active_frames > 0:
                d.active_frames -= 1
                dirty = True

        # Check long presses
        current_time = pygame.time.get_ticks()
        to_remove = []
        for touch_id, (d_idx, down_time) in self.active_touches.items():
            if not self.is_locked and current_time - down_time >= self.long_press_threshold_ms:
                if self.on_long_press:
                    self.on_long_press(self.drums[d_idx].name)
                to_remove.append(touch_id)

        for t in to_remove:
            del self.active_touches[t]

        if dirty:
            self._rebuild_image()

    def _rebuild_image(self):
        self.image.fill((0, 0, 0, 0))
        w, h = self.rect.width, self.rect.height

        for d in self.drums:
            rx = int(d.nx * w)
            ry = int(d.ny * h)
            rw = int(d.nw * w)
            rh = int(d.nh * h)
            kr = pygame.Rect(rx, ry, rw, rh)
            color = (255, 255, 255) if d.active_frames > 0 else (120, 120, 120)
            line_width = 4 if d.active_frames > 0 else 2
            pygame.draw.ellipse(self.image, color, kr, line_width)

            inner_kr = pygame.Rect(rx + 10, ry + 10, rw - 20, rh - 20)
            if inner_kr.width > 0 and inner_kr.height > 0:
                pygame.draw.ellipse(self.image, color, inner_kr, 1)

        self.dirty = 1

    def handle_event(self, ev):
        pos = get_event_pos(ev)
        if pos is None:
            return False

        pointer_id = getattr(ev, "finger_id", "mouse")

        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN) and is_primary_click(ev):
            if self.rect.collidepoint(pos):
                rel_x = pos[0] - self.rect.x
                rel_y = pos[1] - self.rect.y
                w, h = self.rect.width, self.rect.height

                for i in reversed(range(len(self.drums))):
                    d = self.drums[i]
                    rx = int(d.nx * w)
                    ry = int(d.ny * h)
                    rw = int(d.nw * w)
                    rh = int(d.nh * h)
                    dr = pygame.Rect(rx, ry, rw, rh)

                    if dr.collidepoint((rel_x, rel_y)):
                        self.drum_engine.play_sound(self.mapping[d.name])
                        d.active_frames = 5
                        self.active_touches[pointer_id] = (i, pygame.time.get_ticks())
                        self._rebuild_image()
                        return True

        elif ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            if pointer_id in self.active_touches:
                del self.active_touches[pointer_id]
                return True

        return False

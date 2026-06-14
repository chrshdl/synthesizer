import pygame
from pygame.sprite import DirtySprite

from ..utils.input import get_event_pos, is_primary_click

class KeyboardWidget(DirtySprite):
    def __init__(self, rect, action_note_on, action_note_off):
        super().__init__()
        self.rect = pygame.Rect(rect)
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.action_note_on = action_note_on
        self.action_note_off = action_note_off

        # Track multiple visual keys for polyphony
        self.active_indices = set()
        # Track active pointers (mouse/fingers) to note indices
        self.active_pointers = {} # pointer_id -> note_idx

        self.white_indices = [0, 2, 4, 5, 7, 9, 11, 12]
        self.black_indices = [1, 3, None, 6, 8, 10, None]

        self.white_keys = []
        self.black_keys = []

        ww = self.rect.width / 8
        wh = self.rect.height
        bw = ww * 0.6
        bh = wh * 0.6

        for i, note_idx in enumerate(self.white_indices):
            kr = pygame.Rect(i * ww, 0, ww, wh)
            global_kr = pygame.Rect(self.rect.x + i * ww, self.rect.y, ww, wh)
            self.white_keys.append((kr, global_kr, note_idx))

        for i, note_idx in enumerate(self.black_indices):
            if note_idx is not None:
                kr = pygame.Rect((i + 1) * ww - bw / 2, 0, bw, bh)
                global_kr = pygame.Rect(
                    self.rect.x + (i + 1) * ww - bw / 2, self.rect.y, bw, bh
                )
                self.black_keys.append((kr, global_kr, note_idx))

        self._rebuild_image()

    def _rebuild_image(self):
        self.image.fill((0, 0, 0, 0))
        # Draw white keys
        for kr, _, idx in self.white_keys:
            # Check the set for polyphony visuals
            color = (200, 200, 200) if idx in self.active_indices else (250, 250, 250)
            pygame.draw.rect(self.image, color, kr, border_radius=4)
            pygame.draw.rect(self.image, (30, 30, 30), kr, 2, border_radius=4)

        # Draw black keys
        for kr, _, idx in self.black_keys:
            # Check the set for polyphony visuals
            color = (80, 80, 80) if idx in self.active_indices else (20, 20, 20)
            pygame.draw.rect(self.image, color, kr, border_radius=4)
            pygame.draw.rect(self.image, (0, 0, 0), kr, 2, border_radius=4)

        self.dirty = 1

    def get_note_at(self, pos):
        for _, global_kr, idx in self.black_keys:
            if global_kr.collidepoint(pos):
                return idx
        for _, global_kr, idx in self.white_keys:
            if global_kr.collidepoint(pos):
                return idx
        return None

    def handle_event(self, ev):
        pos = get_event_pos(ev)
        if pos is None:
            return False

        pointer_id = getattr(ev, "finger_id", 0) if ev.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION) else 0

        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            if is_primary_click(ev):
                if self.rect.collidepoint(pos):
                    note = self.get_note_at(pos)
                    if note is not None:
                        self.active_pointers[pointer_id] = note
                        self.active_indices.add(note)
                        self._rebuild_image()
                        self.action_note_on(note)
                        return True

        elif ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            if pointer_id in self.active_pointers:
                released_idx = self.active_pointers.pop(pointer_id)
                # Only discard from active_indices if no other pointer is pressing this note
                if released_idx not in self.active_pointers.values():
                    self.active_indices.discard(released_idx)
                self._rebuild_image()
                self.action_note_off(released_idx)
                return True

        elif ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
            if pointer_id in self.active_pointers:
                note = self.get_note_at(pos)
                if note != self.active_pointers[pointer_id]:
                    # Release the old note
                    released_idx = self.active_pointers[pointer_id]
                    
                    if note is None:
                        del self.active_pointers[pointer_id]
                    else:
                        # Press the new note
                        self.active_pointers[pointer_id] = note
                        self.active_indices.add(note)
                        self.action_note_on(note)
                    
                    # Clean up visual state for released_idx
                    if released_idx not in self.active_pointers.values():
                        self.active_indices.discard(released_idx)
                    
                    self.action_note_off(released_idx)
                    self._rebuild_image()
                return True
        return False

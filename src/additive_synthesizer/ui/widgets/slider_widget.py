import pygame
from pygame.sprite import DirtySprite

from ..utils.input import get_event_pos, is_primary_click


class SliderWidget(DirtySprite):
    def __init__(
        self, rect, initial_value, action, bg_color, fill_color, release_action=None
    ):
        super().__init__()
        self.rect = pygame.Rect(rect)

        # Create the surface exactly the size of the passed rect.
        # The knob will fit perfectly inside this bounding box without clipping.
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)

        self.value = initial_value
        self.action = action
        self.release_action = release_action
        self.bg_color = bg_color
        self.fill_color = fill_color

        self.active_pointer = None
        self.dragging = False

        # Pre-calculate geometric bounds
        self.knob_radius = self.rect.height // 2

        # The track is thinner than the total widget height to create the "large knob" effect
        self.track_h = max(4, self.rect.height - 8)
        self.track_r = self.track_h // 2

        # The draggable width is constrained so the knob never leaves the left/right surface bounds
        self.track_w = self.rect.width - (self.knob_radius * 2)

        self._rebuild_image()

    def _rebuild_image(self):
        self.image.fill((0, 0, 0, 0))
        local_rect = self.image.get_rect()

        track_y = local_rect.centery - self.track_r

        bg_rect = pygame.Rect(
            self.knob_radius - self.track_r,
            track_y,
            self.track_w + (self.track_r * 2),
            self.track_h,
        )
        pygame.draw.rect(self.image, self.bg_color, bg_rect, border_radius=self.track_r)

        if self.value > 0:
            pygame.draw.circle(
                self.image,
                self.fill_color,
                (self.knob_radius, local_rect.centery),
                self.track_r,
            )

            fill_body_w = int(self.value * self.track_w)
            if fill_body_w > 0:
                fill_rect = pygame.Rect(
                    self.knob_radius, track_y, fill_body_w, self.track_h
                )
                pygame.draw.rect(self.image, self.fill_color, fill_rect)

        knob_x = self.knob_radius + int(self.value * self.track_w)
        pygame.draw.circle(
            self.image, (255, 255, 255), (knob_x, local_rect.centery), self.knob_radius
        )
        self.dirty = 1

    def handle_event(self, ev):
        pos = get_event_pos(ev)
        if pos is None:
            return False

        pointer_id = (
            getattr(ev, "finger_id", 0)
            if ev.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION)
            else 0
        )

        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            if is_primary_click(ev):
                # Extend hitbox slightly for the knob
                hitbox = self.rect.inflate(self.rect.height + 8, self.rect.height + 8)
                if hitbox.collidepoint(pos):
                    self.dragging = True
                    self.active_pointer = pointer_id
                    self._update_value(pos[0])
                    return True
        elif ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            if self.dragging and self.active_pointer == pointer_id:
                self.dragging = False
                self.active_pointer = None
                if self.release_action:
                    self.release_action()
                return True
        elif ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
            if self.dragging:
                if ev.type == pygame.MOUSEMOTION or self.active_pointer == pointer_id:
                    self._update_value(pos[0])
                    return True
        return False

    def _update_value(self, mouse_x):
        if self.track_w <= 0:
            return

        rel_x = mouse_x - (self.rect.x + self.knob_radius)
        raw_val = rel_x / self.track_w
        self.value = max(0.0, min(1.0, raw_val))

        self._rebuild_image()
        self.action(self.value)

    def update(self, *args, **kwargs):
        pass

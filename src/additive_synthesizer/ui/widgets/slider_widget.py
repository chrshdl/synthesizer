import pygame
from pygame.sprite import DirtySprite

class SliderWidget(DirtySprite):
    def __init__(self, rect, initial_value, action, bg_color, fill_color, release_action=None):
        super().__init__()
        self.rect = pygame.Rect(rect)
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.value = initial_value
        self.action = action
        self.release_action = release_action
        self.bg_color = bg_color
        self.fill_color = fill_color
        self.dragging = False
        self._rebuild_image()

    def _rebuild_image(self):
        self.image.fill((0, 0, 0, 0))
        local_rect = self.image.get_rect()
        
        # Background
        pygame.draw.rect(
            self.image, self.bg_color, local_rect, border_radius=local_rect.height // 2
        )

        # Fill
        fill_w = int(self.value * local_rect.width)
        if fill_w > 0:
            fill_rect = pygame.Rect(local_rect.x, local_rect.y, fill_w, local_rect.height)
            pygame.draw.rect(
                self.image, self.fill_color, fill_rect, border_radius=local_rect.height // 2
            )

        # Knob
        knob_x = local_rect.x + fill_w
        # Keep knob within bounds
        knob_x = max(local_rect.x, min(local_rect.x + local_rect.width, knob_x))
        knob_y = local_rect.centery
        pygame.draw.circle(
            self.image, (255, 255, 255), (knob_x, knob_y), local_rect.height // 2 + 4
        )
        self.dirty = 1

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 0):
            # Extend hitbox slightly for the knob
            hitbox = self.rect.inflate(self.rect.height + 8, self.rect.height + 8)
            if hitbox.collidepoint(ev.pos):
                self.dragging = True
                self._update_value(ev.pos[0])
                return True
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button in (1, 0):
            if self.dragging:
                self.dragging = False
                if self.release_action:
                    self.release_action()
                return True
        elif ev.type == pygame.MOUSEMOTION:
            if self.dragging:
                self._update_value(ev.pos[0])
                return True
        return False

    def _update_value(self, mouse_x):
        rel_x = mouse_x - self.rect.x
        raw_val = rel_x / self.rect.width
        self.value = max(0.0, min(1.0, raw_val))
        self._rebuild_image()
        self.action(self.value)
        
    def update(self, *args, **kwargs):
        pass

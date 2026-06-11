import pygame


class SliderWidget:
    def __init__(self, rect, initial_value, action, bg_color, fill_color):
        self.rect = pygame.Rect(rect)
        self.value = initial_value
        self.action = action
        self.bg_color = bg_color
        self.fill_color = fill_color
        self.dragging = False

    def draw(self, surf):
        # Background
        pygame.draw.rect(
            surf, self.bg_color, self.rect, border_radius=self.rect.height // 2
        )

        # Fill
        fill_w = int(self.value * self.rect.width)
        if fill_w > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height)
            pygame.draw.rect(
                surf, self.fill_color, fill_rect, border_radius=self.rect.height // 2
            )

        # Knob
        knob_x = self.rect.x + fill_w
        # Keep knob within bounds
        knob_x = max(self.rect.x, min(self.rect.x + self.rect.width, knob_x))
        knob_y = self.rect.centery
        pygame.draw.circle(
            surf, (255, 255, 255), (knob_x, knob_y), self.rect.height // 2 + 4
        )

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
        self.action(self.value)

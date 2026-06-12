import pygame
from pygame.sprite import DirtySprite

class ButtonWidget(DirtySprite):
    def __init__(self, rect, label, action, font, panel_accent, white, long_press_action=None):
        super().__init__()
        self.rect = pygame.Rect(rect)
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.label = label
        self.action = action
        self.long_press_action = long_press_action
        self.font = font
        self.panel_accent = panel_accent
        self.white = white
        
        self.is_pressed = False
        self.press_time = 0
        self.long_press_threshold = 600 # ms
        self.long_press_triggered = False
        self._rebuild_image()

    def _rebuild_image(self):
        self.image.fill((0, 0, 0, 0))
        color = self.panel_accent
        if self.is_pressed:
            # Highlight if pressed
            color = (min(255, color[0] + 20), min(255, color[1] + 20), min(255, color[2] + 20))
        
        pygame.draw.rect(self.image, color, self.image.get_rect(), border_radius=14)
        txt = self.font.render(self.label, True, self.white)
        self.image.blit(txt, txt.get_rect(center=self.image.get_rect().center))
        self.dirty = 1

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 0):
            if self.rect.collidepoint(ev.pos):
                self.is_pressed = True
                self.press_time = pygame.time.get_ticks()
                self.long_press_triggered = False
                self._rebuild_image()
                return True
        
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button in (1, 0):
            if self.is_pressed:
                self.is_pressed = False
                self._rebuild_image()
                if self.rect.collidepoint(ev.pos) and not self.long_press_triggered:
                    self.action()
                return True
                
        return False

    def update(self, *args, **kwargs):
        if self.is_pressed and self.long_press_action and not self.long_press_triggered:
            if pygame.time.get_ticks() - self.press_time > self.long_press_threshold:
                self.long_press_action()
                self.long_press_triggered = True

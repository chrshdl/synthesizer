import pygame

class ButtonWidget:
    def __init__(self, rect, label, action, font, panel_accent, white, long_press_action=None):
        self.rect = pygame.Rect(rect)
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

    def draw(self, surf):
        color = self.panel_accent
        if self.is_pressed:
            # Highlight if pressed
            color = (min(255, color[0] + 20), min(255, color[1] + 20), min(255, color[2] + 20))
        
        pygame.draw.rect(surf, color, self.rect, border_radius=14)
        txt = self.font.render(self.label, True, self.white)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 0):
            if self.rect.collidepoint(ev.pos):
                self.is_pressed = True
                self.press_time = pygame.time.get_ticks()
                self.long_press_triggered = False
                return True
        
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button in (1, 0):
            if self.is_pressed:
                self.is_pressed = False
                if self.rect.collidepoint(ev.pos) and not self.long_press_triggered:
                    self.action()
                return True
                
        return False

    def update(self, dt):
        if self.is_pressed and self.long_press_action and not self.long_press_triggered:
            if pygame.time.get_ticks() - self.press_time > self.long_press_threshold:
                self.long_press_action()
                self.long_press_triggered = True

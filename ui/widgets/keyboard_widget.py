import pygame

class KeyboardWidget:
    def __init__(self, rect, action_note_on, action_note_off):
        self.rect = pygame.Rect(rect)
        self.action_note_on = action_note_on
        self.action_note_off = action_note_off
        self.active_idx = None
        
        self.white_indices = [0, 2, 4, 5, 7, 9, 11, 12]
        self.black_indices = [1, 3, None, 6, 8, 10, None]
        
        self.white_keys = []
        self.black_keys = []
        
        ww = self.rect.width / 8
        wh = self.rect.height
        bw = ww * 0.6
        bh = wh * 0.6
        
        for i, note_idx in enumerate(self.white_indices):
            kr = pygame.Rect(self.rect.x + i * ww, self.rect.y, ww, wh)
            self.white_keys.append((kr, note_idx))
            
        for i, note_idx in enumerate(self.black_indices):
            if note_idx is not None:
                kr = pygame.Rect(self.rect.x + (i + 1) * ww - bw/2, self.rect.y, bw, bh)
                self.black_keys.append((kr, note_idx))
                
    def draw(self, surf):
        # Draw white keys
        for kr, idx in self.white_keys:
            color = (200, 200, 200) if idx == self.active_idx else (250, 250, 250)
            pygame.draw.rect(surf, color, kr, border_radius=4)
            pygame.draw.rect(surf, (30, 30, 30), kr, 2, border_radius=4)
            
        # Draw black keys
        for kr, idx in self.black_keys:
            color = (80, 80, 80) if idx == self.active_idx else (20, 20, 20)
            pygame.draw.rect(surf, color, kr, border_radius=4)
            pygame.draw.rect(surf, (0, 0, 0), kr, 2, border_radius=4)

    def get_note_at(self, pos):
        # Hit test black keys first as they sit on top
        for kr, idx in self.black_keys:
            if kr.collidepoint(pos):
                return idx
        for kr, idx in self.white_keys:
            if kr.collidepoint(pos):
                return idx
        return None

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 0):
            if self.rect.collidepoint(ev.pos):
                note = self.get_note_at(ev.pos)
                if note is not None:
                    self.active_idx = note
                    self.action_note_on(note)
                    return True
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button in (1, 0):
            if self.active_idx is not None:
                self.active_idx = None
                self.action_note_off()
                return True
        elif ev.type == pygame.MOUSEMOTION:
            if self.active_idx is not None:
                note = self.get_note_at(ev.pos)
                if note != self.active_idx:
                    if note is None:
                        self.active_idx = None
                        self.action_note_off()
                    else:
                        self.active_idx = note
                        self.action_note_on(note)
                return True
        return False

import pygame
from pygame.sprite import DirtySprite
from ..utils.input import get_event_pos, is_primary_click
from ...config import ConfigManager

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
        
        # Coordinates and sizes relative to 1.0 (width and height)
        # We will scale these to the actual rect size.
        self.drums = [
            # [name, norm_x, norm_y, norm_w, norm_h, active_frames, default_wav]
            ["cymbal1", 0.10, 0.15, 0.20, 0.12, 0, "cymbal1.wav"],
            ["hihat", 0.15, 0.40, 0.20, 0.12, 0, "hihat.wav"],
            ["cymbal2", 0.70, 0.15, 0.25, 0.15, 0, "cymbal2.wav"],
            ["tom1", 0.35, 0.25, 0.15, 0.20, 0, "tom1.wav"],
            ["tom2", 0.50, 0.25, 0.15, 0.20, 0, "tom2.wav"],
            ["snare", 0.20, 0.65, 0.22, 0.25, 0, "snare.wav"],
            ["tom3", 0.60, 0.65, 0.22, 0.25, 0, "tom3.wav"],
            ["kick", 0.38, 0.55, 0.24, 0.40, 0, "kick.wav"],
        ]
        
        for d in self.drums:
            if d[0] not in self.mapping:
                self.mapping[d[0]] = d[6]

        # Track touch down times for long press detection
        self.active_touches = {} # pointer_id/mouse_btn -> (drum_index, down_time_ms)
        self.long_press_threshold_ms = 600

        self._rebuild_image()

    def update(self, dt):
        dirty = False
        for d in self.drums:
            if d[5] > 0:
                d[5] -= 1
                dirty = True
                
        # Check long presses
        current_time = pygame.time.get_ticks()
        to_remove = []
        for touch_id, (d_idx, down_time) in self.active_touches.items():
            if not self.is_locked and current_time - down_time >= self.long_press_threshold_ms:
                if self.on_long_press:
                    self.on_long_press(self.drums[d_idx][0])
                to_remove.append(touch_id)
                
        for t in to_remove:
            del self.active_touches[t]
                
        if dirty:
            self._rebuild_image()

    def _rebuild_image(self):
        self.image.fill((0, 0, 0, 0))
        w, h = self.rect.width, self.rect.height
        
        for name, nx, ny, nw, nh, frames, def_wav in self.drums:
            rx, ry, rw, rh = int(nx * w), int(ny * h), int(nw * w), int(nh * h)
            kr = pygame.Rect(rx, ry, rw, rh)
            color = (255, 255, 255) if frames > 0 else (120, 120, 120)
            line_width = 4 if frames > 0 else 2
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
                rel_x, rel_y = pos[0] - self.rect.x, pos[1] - self.rect.y
                w, h = self.rect.width, self.rect.height
                
                for i in reversed(range(len(self.drums))):
                    d = self.drums[i]
                    rx, ry, rw, rh = int(d[1] * w), int(d[2] * h), int(d[3] * w), int(d[4] * h)
                    dr = pygame.Rect(rx, ry, rw, rh)
                    
                    if dr.collidepoint((rel_x, rel_y)):
                        self.drum_engine.play_sound(self.mapping[d[0]])
                        d[5] = 5 # active frames
                        self.active_touches[pointer_id] = (i, pygame.time.get_ticks())
                        self._rebuild_image()
                        return True
                        
        elif ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            if pointer_id in self.active_touches:
                del self.active_touches[pointer_id]
                return True
                
        return False

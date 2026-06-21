import threading
import time

import pygame

from additive_synthesizer.config import ConfigManager

# Protects conf.latency_t0, which is written here (main thread on FINGERDOWN)
# and read by the fallback Python audio thread.
_latency_lock = threading.Lock()

def get_event_pos(ev, width=None, height=None):
    """
    Unified coordinate extraction for mouse and finger events.
    Adapts touch mappings based on display type.
    """
    if ev.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
        conf = ConfigManager.get_config()
        if ev.type == pygame.FINGERDOWN:
            with _latency_lock:
                conf.latency_t0 = time.time()
            
        w = width if width is not None else conf.width
        h = height if height is not None else conf.height
        
        if conf.display_type == "waveshare":
            # 180-degree rotation mapping
            return (int((1.0 - ev.x) * w), int((1.0 - ev.y) * h))
        else:
            # RPi Display 2 (or unknown): 270-degree rotation mapping
            return (int((1.0 - ev.x) * w), int(ev.y * h))
    elif hasattr(ev, "pos"):
        return ev.pos
    return None


def is_touch_event(ev):
    return ev.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION)


def is_mouse_event(ev):
    return ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)


def is_primary_click(ev):
    if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        return ev.button in (1, 0)
    return True

import pygame


def get_event_pos(ev, width=1280, height=720):
    """
    Unified coordinate extraction for mouse and finger events.
    Supports the 270-degree rotation mapping for RPi Display 2.
    """
    if ev.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
        # Mapping: (1.0 - event.x) * width, event.y * height
        return (int((1.0 - ev.x) * width), int(ev.y * height))
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

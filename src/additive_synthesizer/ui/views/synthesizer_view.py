import random

import numpy as np
import pygame
from pygame.sprite import LayeredDirty

from ...config import ConfigManager
from ...core.partial import Partial
from ...logger import Logger
from ...ui.utils.font import FontFamily, load_font
from ..utils.input import get_event_pos, is_primary_click, is_touch_event
from ..widgets.button_widget import ButtonWidget
from ..widgets.keyboard_widget import KeyboardWidget
from ..widgets.slider_widget import SliderWidget


class SynthesizerView:
    def __init__(self, audio_engine, n_partials=8):
        self.audio_engine = audio_engine
        self.ui_layer = LayeredDirty()
        self.widget_layer = LayeredDirty()

        self.width = ConfigManager.get_config().width
        self.height = ConfigManager.get_config().height
        self.n_partials = n_partials

        self.logger = Logger(__class__.__name__).get()

        self.margin_x = 30
        self.bottom_gutter = 350
        self.top_bar_h = 80
        self.bar_eq_h = 56
        self.long_press_ms = 600
        self.long_press_move_tol = 14
        self.dot_radius = 9

        self.bg_color = (12, 14, 18)
        self.panel_color = (22, 26, 32)
        self.panel_accent = (40, 46, 56)
        self.white = (240, 242, 245)
        self.muted = (120, 130, 140)
        self.inactive = (80, 85, 92)

        self.palette = [
            (255, 99, 132),
            (255, 159, 64),
            (255, 205, 86),
            (75, 192, 192),
            (54, 162, 235),
            (153, 102, 255),
            (201, 203, 207),
            (255, 111, 181),
        ]

        self.font_med = load_font(size=22, family=FontFamily.D_DIN_EXP_BOLD)

        base_min_r = 32
        base_max_r = 56

        self.bubble_margin_x = base_max_r + 16

        usable_w = self.width - 2 * self.bubble_margin_x

        self.step = (
            usable_w / (self.n_partials - 1) if self.n_partials > 1 else usable_w
        )
        self.base_y = self.height - self.bottom_gutter
        self.drag_strip_w = int(max(32, self.step * 0.7))

        scale_factor = min(1.0, (self.step * 0.8) / (base_max_r * 2))

        self.partials = [
            Partial(
                i,
                int(self.bubble_margin_x + i * self.step),  # Use bubble margin here
                self.base_y,
                self.palette[i % len(self.palette)],
                self.top_bar_h,
                self.bottom_gutter,
                self.bar_eq_h,
                self.height,
            )
            for i in range(self.n_partials)
        ]

        for p in self.partials:
            p.bubble_min_r = int(base_min_r * scale_factor)
            p.bubble_max_r = int(base_max_r * scale_factor)

        config = self._load_settings()
        self.presets = config.presets
        self.master_volume = config.master_volume
        self.show_waveform = config.show_waveform
        self.show_keys = config.show_keys

        self.key_freqs = [
            262,
            277,
            294,
            311,
            330,
            349,
            370,
            392,
            415,
            440,
            466,
            494,
            523,
        ]

        # self.default_drone_freqs = [self.key_freqs[0], self.key_freqs[4]]
        self.default_drone_freqs = [self.key_freqs[0]]

        self._init_ui_elements()
        self._init_widgets()

        self.active_idx = None
        self.phase_offset = 0.0
        self.audio_engine.set_master_volume(self.master_volume)
        self._notify_audio()

        if not self.show_keys:
            for f in self.default_drone_freqs:
                self.audio_engine.note_on(f)

    def _init_ui_elements(self):
        btn_w, btn_h, pad = 140, 60, 12

        btn_y = (self.top_bar_h - btn_h) // 2

        self.buttons = [
            ButtonWidget(
                (16, btn_y, btn_w, btn_h),
                "MUTE ALL",
                self.mute_all,
                self.font_med,
                self.panel_accent,
                self.white,
            ),
            ButtonWidget(
                (16 + (btn_w + pad), btn_y, btn_w, btn_h),
                "RANDOM",
                self.randomize,
                self.font_med,
                self.panel_accent,
                self.white,
            ),
            ButtonWidget(
                (16 + 2 * (btn_w + pad), btn_y, btn_w, btn_h),
                "SAW",
                lambda: self.load_preset(1),
                self.font_med,
                self.panel_accent,
                self.white,
            ),
            ButtonWidget(
                (16 + 3 * (btn_w + pad), btn_y, btn_w, btn_h),
                "SQUARE",
                lambda: self.load_preset(2),
                self.font_med,
                self.panel_accent,
                self.white,
            ),
            ButtonWidget(
                (16 + 4 * (btn_w + pad), btn_y, btn_w, btn_h),
                "PRESET 1",
                lambda: self.load_preset(3),
                self.font_med,
                self.panel_accent,
                self.white,
                long_press_action=lambda: self.save_preset(3),
            ),
            ButtonWidget(
                (16 + 5 * (btn_w + pad), btn_y, btn_w, btn_h),
                "KEYS",
                self.toggle_keys,
                self.font_med,
                self.panel_accent,
                self.white,
            ),
        ]

        slider_w = 200
        slider_h = 36
        slider_x = self.width - slider_w - 32
        slider_y = (self.top_bar_h - slider_h) // 2
        self.vol_slider = SliderWidget(
            (slider_x, slider_y, slider_w, slider_h),
            initial_value=self.master_volume,
            action=self.set_master_volume,
            bg_color=self.bg_color,
            fill_color=(75, 192, 192),
            release_action=self._save_settings,
        )

        self.ui_layer.add(*self.buttons)
        self.ui_layer.add(self.vol_slider)

    def _init_widgets(self):
        self.keyboard = KeyboardWidget(
            (self.margin_x, self.height - 300, self.width - 2 * self.margin_x, 280),
            self.on_note_on,
            self.on_note_off,
        )
        self.keyboard.visible = 1 if self.show_keys else 0
        self.widget_layer.add(self.keyboard)

    def _load_settings(self):
        config = ConfigManager.get_config()
        sawtooth = [
            ((self.n_partials - i) / self.n_partials, True)
            for i in range(self.n_partials)
        ]
        square = [
            ((self.n_partials - i) / self.n_partials if i % 2 == 0 else 0.0, True)
            for i in range(self.n_partials)
        ]

        needs_save = False
        if not config.presets:
            config.presets = {"1": sawtooth, "2": square, "3": None}
            needs_save = True
        else:
            if (
                config.presets.get("1") is None
                or len(config.presets["1"]) != self.n_partials
            ):
                config.presets["1"] = sawtooth
                needs_save = True
            if (
                config.presets.get("2") is None
                or len(config.presets["2"]) != self.n_partials
            ):
                config.presets["2"] = square
                needs_save = True
            if "3" not in config.presets:
                config.presets["3"] = None
                needs_save = True

        if needs_save:
            config.write_to_file(ConfigManager.path)
        return config

    def _save_settings(self):
        config = ConfigManager.get_config()
        config.presets = self.presets
        config.master_volume = self.master_volume
        config.show_waveform = self.show_waveform
        config.show_keys = self.show_keys
        config.write_to_file(ConfigManager.path)

    def save_preset(self, slot):
        slot_str = str(slot)
        self.presets[slot_str] = [(p.amp, p.active) for p in self.partials]
        self._save_settings()
        self.logger.info(
            f"Saved configuration ({len(self.partials)} partials) to Preset {slot}"
        )

    def load_preset(self, slot):
        slot_str = str(slot)
        config = self.presets.get(slot_str)
        if config:
            for i, p in enumerate(self.partials):
                if i < len(config):
                    p.amp, p.active = config[i]
                else:
                    p.amp = 0.0
                    p.active = False
            self._notify_audio()
            self.logger.info(f"Loaded Preset {slot}")

    def toggle_waveform(self):
        self.show_waveform = not self.show_waveform
        self._save_settings()

    def toggle_keys(self):
        self.show_keys = not self.show_keys
        self.keyboard.visible = 1 if self.show_keys else 0
        self._save_settings()

        if self.show_keys:
            for f in self.default_drone_freqs:
                self.audio_engine.note_off(f)
        else:
            for f in self.key_freqs:
                self.audio_engine.note_off(f)
            for f in self.default_drone_freqs:
                self.audio_engine.note_on(f)

    def on_note_on(self, idx):
        if not self.show_keys:
            return

        if idx < len(self.key_freqs):
            freq = self.key_freqs[idx]
            self.audio_engine.note_on(freq)

    def on_note_off(self, idx):
        if not self.show_keys:
            return

        if idx < len(self.key_freqs):
            freq = self.key_freqs[idx]
            self.audio_engine.note_off(freq)

    def set_master_volume(self, vol):
        self.master_volume = vol
        self.audio_engine.set_master_volume(vol)

    def _notify_audio(self):
        amps = [p.amp if p.active else 0.0 for p in self.partials]
        self.audio_engine.update_amplitudes(amps)

    def mute_all(self):
        for p in self.partials:
            p.amp = 0.0
        self._notify_audio()
        self.audio_engine.all_notes_off()

        if hasattr(self, "keyboard"):
            self.keyboard.active_indices.clear()
            self.keyboard.active_pointers.clear()
            self.keyboard._rebuild_image()

    def randomize(self):
        for p in self.partials:
            p.amp = random.random()
        self._notify_audio()

    def draw(self, surface, background):
        surface.fill(self.bg_color)

        if self.show_waveform:
            wf = self.audio_engine.sound_arrays.get(self.key_freqs[0])
            if wf is not None and len(wf) > 0:
                samples_to_show = 200
                offset = int(-self.phase_offset) % 200
                segment = (
                    wf[offset : offset + samples_to_show, 0]
                    if wf.ndim == 2
                    else wf[offset : offset + samples_to_show]
                )
                max_val = np.max(np.abs(segment))
                display_wf = segment / max_val if max_val > 1e-5 else segment

                points = []
                available_bottom = (
                    self.height - 310 if self.show_keys else self.height - 50
                )
                usable_height = available_bottom - self.top_bar_h
                center_y = self.top_bar_h + usable_height // 2
                scale_y = usable_height * 0.4
                step = samples_to_show / self.width

                for x in range(self.width):
                    idx = int(x * step)
                    y = center_y - int(display_wf[idx] * scale_y)
                    points.append((x, y))

                if len(points) >= 2:
                    scope_surf = pygame.Surface(
                        (self.width, self.height), pygame.SRCALPHA
                    )
                    pygame.draw.lines(scope_surf, (75, 192, 192, 128), False, points, 4)
                    surface.blit(scope_surf, (0, 0))

        pygame.draw.rect(surface, self.panel_color, (0, 0, self.width, self.top_bar_h))
        vol_label = self.font_med.render("Volume", True, self.white)
        surface.blit(
            vol_label,
            (
                self.vol_slider.rect.x - vol_label.get_width() - 16,
                self.top_bar_h // 2 - vol_label.get_height() // 2,
            ),
        )

        for p in self.partials:
            cx, cy = p.bubble_center()
            r = p.bubble_radius()
            color = p.color if p.active else self.inactive
            pygame.draw.circle(surface, (0, 0, 0), (cx + 2, cy + 4), r + 4)
            pygame.draw.circle(surface, color, (cx, cy), r)
            pygame.draw.circle(
                surface, (255, 255, 255), (cx - r // 3, cy - r // 3), max(3, r // 6)
            )

        for sprite in self.widget_layer.sprites():
            sprite.dirty = 1
        for sprite in self.ui_layer.sprites():
            sprite.dirty = 1

        self.widget_layer.draw(surface)
        self.ui_layer.draw(surface)
        return [surface.get_rect()]

    def full_paint(self, surface, background):
        for sprite in self.widget_layer.sprites():
            sprite.dirty = 1
        for sprite in self.ui_layer.sprites():
            sprite.dirty = 1

        if background:
            surface.blit(background, (0, 0))
        self.draw(surface, background)

    def update(self, dt: float):
        self.ui_layer.update(dt=dt)
        self.widget_layer.update(dt=dt)

    def nearest_partial_idx_at_x(self, x):
        # Updated to use bubble_margin_x
        i = round((x - self.bubble_margin_x) / self.step) if self.step > 0 else 0
        return max(0, min(self.n_partials - 1, i))

    def column_rect_for_idx(self, i):
        # Updated to use bubble_margin_x
        cx = int(self.bubble_margin_x + i * self.step)
        half = self.drag_strip_w // 2
        return pygame.Rect(
            cx - half, self.top_bar_h, self.drag_strip_w, self.base_y - self.top_bar_h
        )

    def handle_event(self, ev):
        if self.vol_slider.handle_event(ev):
            return True
        for b in self.buttons:
            if b.handle_event(ev):
                return True
        if self.show_keys and self.keyboard.handle_event(ev):
            return True

        pos = get_event_pos(ev, self.width, self.height)
        if pos is None:
            return False

        pointer_id = getattr(ev, "finger_id", 0) if is_touch_event(ev) else 0

        if (
            ev.type == pygame.MOUSEBUTTONDOWN and is_primary_click(ev)
        ) or ev.type == pygame.FINGERDOWN:
            px, py = pos
            y0 = self.height - self.bottom_gutter + 10
            for i, p in enumerate(self.partials):
                # Updated to use bubble_margin_x
                x = int(self.bubble_margin_x + i * self.step)
                dot_rect = pygame.Rect(
                    x - (self.dot_radius + 4),
                    y0 + self.bar_eq_h + 6,
                    (self.dot_radius + 4) * 2,
                    self.dot_radius * 2 + 4,
                )
                if dot_rect.collidepoint(pos):
                    p.active = not p.active
                    self._notify_audio()
                    return True

            idx = self.nearest_partial_idx_at_x(px)
            col_rect = self.column_rect_for_idx(idx)
            if col_rect.collidepoint(pos):
                p = self.partials[idx]
                p.dragging = True
                p.last_touch_down_t = pygame.time.get_ticks()
                p.touch_down_pos = pos
                p.active_pointer = pointer_id
                p.set_amp_from_y(py)
                self.active_idx = idx
                self._notify_audio()
                return True

            for i, p in enumerate(self.partials):
                if p.hit_test(pos, pad=16):
                    p.dragging = True
                    p.last_touch_down_t = pygame.time.get_ticks()
                    p.touch_down_pos = pos
                    p.active_pointer = pointer_id
                    self.active_idx = i
                    p.set_amp_from_y(py)
                    self._notify_audio()
                    return True
            return False

        elif (
            ev.type == pygame.MOUSEBUTTONUP and is_primary_click(ev)
        ) or ev.type == pygame.FINGERUP:
            if self.active_idx is None:
                return False
            p = self.partials[self.active_idx]

            if getattr(p, "active_pointer", 0) != pointer_id:
                return False

            dx = pos[0] - p.touch_down_pos[0]
            dy = pos[1] - p.touch_down_pos[1]
            moved = (dx * dx + dy * dy) ** 0.5 > self.long_press_move_tol
            held_ms = pygame.time.get_ticks() - p.last_touch_down_t
            if (not moved) and held_ms >= self.long_press_ms:
                p.amp = 0.0
                self._notify_audio()
            p.dragging = False
            self.active_idx = None
            return True

        elif ev.type == pygame.MOUSEMOTION or ev.type == pygame.FINGERMOTION:
            if self.active_idx is not None:
                p = self.partials[self.active_idx]
                if (
                    ev.type == pygame.FINGERMOTION
                    and getattr(p, "active_pointer", 0) != pointer_id
                ):
                    return False

                if p.dragging:
                    p.set_amp_from_y(pos[1])
                    self._notify_audio()
                return True
        return False

import random

import numpy as np
import pygame
from pygame.sprite import LayeredDirty

from ...config import ConfigManager
from ...core.partial import Partial
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
        self.margin_x = 30
        self.bottom_gutter = 250
        self.top_bar_h = 64
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

        self.font_small = pygame.font.SysFont("Inter", 18)
        self.font_med = pygame.font.SysFont("Inter", 22, bold=True)
        self.font_big = pygame.font.SysFont("Inter", 28, bold=True)

        usable_w = self.width - 2 * self.margin_x
        self.step = (
            usable_w / (self.n_partials - 1) if self.n_partials > 1 else usable_w
        )
        self.base_y = self.height - self.bottom_gutter
        self.drag_strip_w = int(max(32, self.step * 0.7))

        base_min_r = 32
        base_max_r = 56
        scale_factor = min(1.0, (self.step * 0.8) / (base_max_r * 2))

        self.partials = [
            Partial(
                i,
                int(self.margin_x + i * self.step),
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

        self._init_ui_elements()
        self._init_widgets()

        self.active_idx = None
        self.phase_offset = 0.0
        self.audio_engine.set_master_volume(self.master_volume)
        self.audio_engine.set_keys_mode(self.show_keys)
        self._notify_audio()

    def _init_ui_elements(self):
        btn_w, btn_h, pad = 140, 44, 12
        self.buttons = [
            ButtonWidget(
                (16, 10, btn_w, btn_h),
                "MUTE ALL",
                self.mute_all,
                self.font_med,
                self.panel_accent,
                self.white,
            ),
            ButtonWidget(
                (16 + (btn_w + pad), 10, btn_w, btn_h),
                "RANDOMIZE",
                self.randomize,
                self.font_med,
                self.panel_accent,
                self.white,
            ),
            ButtonWidget(
                (16 + 2 * (btn_w + pad), 10, btn_w, btn_h),
                "WAVEFORM",
                self.toggle_waveform,
                self.font_med,
                self.panel_accent,
                self.white,
            ),
            ButtonWidget(
                (16 + 3 * (btn_w + pad), 10, btn_w, btn_h),
                "SAWTOOTH",
                lambda: self.load_preset(1),
                self.font_med,
                self.panel_accent,
                self.white,
            ),
            ButtonWidget(
                (16 + 4 * (btn_w + pad), 10, btn_w, btn_h),
                "SQUARE",
                lambda: self.load_preset(2),
                self.font_med,
                self.panel_accent,
                self.white,
            ),
            ButtonWidget(
                (16 + 5 * (btn_w + pad), 10, btn_w, btn_h),
                "PRESET 1",
                lambda: self.load_preset(3),
                self.font_med,
                self.panel_accent,
                self.white,
                long_press_action=lambda: self.save_preset(3),
            ),
            ButtonWidget(
                (16 + 6 * (btn_w + pad), 10, btn_w, btn_h),
                "KEYS",
                self.toggle_keys,
                self.font_med,
                self.panel_accent,
                self.white,
            ),
        ]

        slider_w = 100
        slider_h = 8
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
            (self.margin_x, self.height - 160, self.width - 2 * self.margin_x, 150),
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
        print(f"Saved configuration ({len(self.partials)} partials) to Preset {slot}")

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
            print(
                f"Loaded Preset {slot} (mapped {min(len(config), len(self.partials))} partials)"
            )

    def toggle_waveform(self):
        self.show_waveform = not self.show_waveform
        self._save_settings()

    def toggle_keys(self):
        self.show_keys = not self.show_keys
        self.keyboard.visible = 1 if self.show_keys else 0
        self.audio_engine.set_keys_mode(self.show_keys)
        self._save_settings()

    def on_note_on(self, idx):
        if idx < len(self.key_freqs):
            freq = self.key_freqs[idx]
            self.audio_engine.set_frequency(freq)
            self.audio_engine.set_gate(True)

    def on_note_off(self):
        self.audio_engine.set_gate(False)

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

    def randomize(self):
        for p in self.partials:
            p.amp = random.random()
        self._notify_audio()

    def draw_static_elements(self, background_surface):
        pass

    def draw(self, surface, background):
        surface.fill(self.bg_color)

        if self.show_waveform:
            wf = self.audio_engine.get_current_waveform()
            if wf is not None and len(wf) > 0:
                samples_to_show = 200
                offset = int(-self.phase_offset) % 200
                segment = wf[offset : offset + samples_to_show]
                max_val = np.max(np.abs(segment))
                display_wf = segment / max_val if max_val > 1e-5 else segment

                points = []
                available_bottom = (
                    self.height - 160 if self.show_keys else self.height - 50
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
        i = round((x - self.margin_x) / self.step) if self.step > 0 else 0
        return max(0, min(self.n_partials - 1, i))

    def column_rect_for_idx(self, i):
        cx = int(self.margin_x + i * self.step)
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

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 0):
            pos = ev.pos
            px, py = pos
            y0 = self.height - self.bottom_gutter + 10
            for i, p in enumerate(self.partials):
                x = int(self.margin_x + i * self.step)
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
                p.set_amp_from_y(py)
                self.active_idx = idx
                self._notify_audio()
                return True

            for i, p in enumerate(self.partials):
                if p.hit_test(pos, pad=16):
                    p.dragging = True
                    p.last_touch_down_t = pygame.time.get_ticks()
                    p.touch_down_pos = pos
                    self.active_idx = i
                    p.set_amp_from_y(py)
                    self._notify_audio()
                    return True
            return False

        elif ev.type == pygame.MOUSEBUTTONUP and ev.button in (1, 0):
            if self.active_idx is None:
                return False
            p = self.partials[self.active_idx]
            dx = ev.pos[0] - p.touch_down_pos[0]
            dy = ev.pos[1] - p.touch_down_pos[1]
            moved = (dx * dx + dy * dy) ** 0.5 > self.long_press_move_tol
            held_ms = pygame.time.get_ticks() - p.last_touch_down_t
            if (not moved) and held_ms >= self.long_press_ms:
                p.amp = 0.0
                self._notify_audio()
            p.dragging = False
            self.active_idx = None
            return True

        elif ev.type == pygame.MOUSEMOTION:
            if self.active_idx is not None:
                p = self.partials[self.active_idx]
                if p.dragging:
                    p.set_amp_from_y(ev.pos[1])
                    self._notify_audio()
                return True
        return False

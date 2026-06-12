import json
import os
import random

import numpy as np
import pygame

from ..widgets.button_widget import ButtonWidget
from ..widgets.slider_widget import SliderWidget


class Partial:
    def __init__(
        self, idx, x, base_y, color, top_bar_h, bottom_gutter, bar_eq_h, height
    ):
        self.idx = idx
        self.x = x
        self.base_y = base_y
        self.amp = 0.0
        self.color = color
        self.active = True
        self.dragging = False
        self.last_touch_down_t = 0
        self.touch_down_pos = (0, 0)

        self.top_bar_h = top_bar_h
        self.bottom_gutter = bottom_gutter
        self.bar_eq_h = bar_eq_h
        self.height = height

        self.bubble_min_r = 32
        self.bubble_max_r = 56

    def bubble_radius(self):
        return int(
            self.bubble_min_r + (self.bubble_max_r - self.bubble_min_r) * self.amp
        )

    def bubble_center(self):
        y = int(
            self.base_y
            - self.amp
            * (self.height - self.top_bar_h - self.bottom_gutter - self.bar_eq_h - 20)
        )
        return (self.x, y)

    def hit_test(self, pos, pad=12):
        cx, cy = self.bubble_center()
        px, py = pos
        r = self.bubble_radius() + pad
        return (px - cx) ** 2 + (py - cy) ** 2 <= r * r

    def set_amp_from_y(self, y):
        max_travel = (
            self.height - self.top_bar_h - self.bottom_gutter - self.bar_eq_h - 20
        )
        raw = (self.base_y - y) / max_travel
        self.amp = max(0.0, min(1.0, raw))


class SynthesizerView:
    def __init__(self, audio_engine, n_partials=8):
        self.audio_engine = audio_engine
        self.width = 1280
        self.height = 720
        self.n_partials = n_partials
        self.margin_x = 30
        self.bottom_gutter = 95
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

        # Dynamic bubble scaling
        base_min_r = 32
        base_max_r = 56
        # Reduce size if they would overlap too much
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

        self.presets_file = "settings.json"
        # Try to use a persistent path on Buildroot if it exists
        if os.path.exists("/data/config"):
            self.presets_file = "/data/config/settings.json"

        settings = self._load_settings()
        self.presets = settings.get("presets", {"1": None, "2": None})
        self.master_volume = settings.get("master_volume", 0.5)
        self.show_waveform = settings.get("show_waveform", False)

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
                long_press_action=lambda: self.save_preset(1),
            ),
            ButtonWidget(
                (16 + 4 * (btn_w + pad), 10, btn_w, btn_h),
                "SQUARE",
                lambda: self.load_preset(2),
                self.font_med,
                self.panel_accent,
                self.white,
                long_press_action=lambda: self.save_preset(2),
            ),
        ]

        slider_w = 160
        slider_h = 6
        slider_x = self.width - slider_w - 32
        slider_y = (self.top_bar_h - slider_h) // 2
        self.vol_slider = SliderWidget(
            (slider_x, slider_y, slider_w, slider_h),
            initial_value=self.master_volume,
            action=self.set_master_volume,
            bg_color=self.bg_color,
            fill_color=(75, 192, 192),  # Teal
        )

        self.active_idx = None
        self.audio_engine.set_master_volume(self.master_volume)
        self._notify_audio()

    def _load_settings(self):
        # Generate dynamic factory defaults based on current n_partials
        # The image shows a linear decay, not 1/n.
        # e.g., for 16 partials, it goes from 1.0 down to ~0.0625 linearly
        sawtooth = [
            ((self.n_partials - i) / self.n_partials, True)
            for i in range(self.n_partials)
        ]
        square = [
            ((self.n_partials - i) / self.n_partials if i % 2 == 0 else 0.0, True)
            for i in range(self.n_partials)
        ]

        defaults = {
            "presets": {"1": sawtooth, "2": square},
            "master_volume": 0.5,
            "show_waveform": False,
        }
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, "r") as f:
                    data = json.load(f)
                    # Migrate old format or fill missing slots
                    if "presets" not in data:
                        data = {
                            "presets": {"1": sawtooth, "2": square},
                            "master_volume": 0.5,
                            "show_waveform": False,
                        }

                    # Ensure factory defaults are used if slots are empty or length changed
                    if (
                        data["presets"].get("1") is None
                        or len(data["presets"]["1"]) != self.n_partials
                    ):
                        data["presets"]["1"] = sawtooth
                    if (
                        data["presets"].get("2") is None
                        or len(data["presets"]["2"]) != self.n_partials
                    ):
                        data["presets"]["2"] = square

                    return data
            except Exception as e:
                print(f"Error loading settings: {e}")

        # If no file exists, save the factory defaults immediately
        try:
            with open(self.presets_file, "w") as f:
                json.dump(defaults, f)
        except Exception:
            pass

        return defaults

    def _save_settings(self):
        data = {
            "presets": self.presets,
            "master_volume": self.master_volume,
            "show_waveform": self.show_waveform,
        }
        try:
            with open(self.presets_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def save_preset(self, slot):
        slot_str = str(slot)
        self.presets[slot_str] = [(p.amp, p.active) for p in self.partials]
        self._save_settings()
        print(f"Saved configuration ({len(self.partials)} partials) to Preset {slot}")

    def load_preset(self, slot):
        slot_str = str(slot)
        config = self.presets.get(slot_str)
        if config:
            # Handle loading presets that might have a different number of partials
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

    def set_master_volume(self, vol):
        self.master_volume = vol
        self.audio_engine.set_master_volume(vol)
        self._save_settings()

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

    def draw(self, surface, background):
        surface.fill(self.bg_color)

        # Draw Waveform Scope (Background)
        if self.show_waveform:
            wf = self.audio_engine.get_current_waveform()
            if wf is not None and len(wf) > 0:
                samples_to_show = 200
                segment = wf[:samples_to_show]
                max_val = np.max(np.abs(segment))
                display_wf = segment / max_val if max_val > 1e-5 else segment

                points = []
                center_y = self.height // 2
                scale_y = self.height * 0.4
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

        # Draw Top Bar
        pygame.draw.rect(surface, self.panel_color, (0, 0, self.width, self.top_bar_h))
        vol_label = self.font_big.render("Volume", True, self.white)
        surface.blit(
            vol_label,
            (
                self.vol_slider.rect.x - vol_label.get_width() - 16,
                self.top_bar_h // 2 - vol_label.get_height() // 2,
            ),
        )
        self.vol_slider.draw(surface)

        for b in self.buttons:
            b.draw(surface)

        # Draw Partials
        for p in self.partials:
            cx, cy = p.bubble_center()
            r = p.bubble_radius()
            color = p.color if p.active else self.inactive
            pygame.draw.circle(surface, (0, 0, 0), (cx + 2, cy + 4), r + 4)
            pygame.draw.circle(surface, color, (cx, cy), r)
            pygame.draw.circle(
                surface, (255, 255, 255), (cx - r // 3, cy - r // 3), max(3, r // 6)
            )
        # pygame.draw.line(
        #     surface,
        #     self.panel_accent,
        #     (self.margin_x, self.base_y),
        #     (self.width - self.margin_x, self.base_y),
        #     2,
        # )

        # Draw EQ Bars
        # bar_w = max(12, int((self.width - 2 * self.margin_x) / (self.n_partials * 1.6)))
        # y0 = self.height - self.bottom_gutter + 10
        # for i, p in enumerate(self.partials):
        #     x = int(self.margin_x + i * self.step)
        #     h = int(p.amp * (self.bar_eq_h - 8))
        #     color = p.color if p.active else self.inactive
        #     pygame.draw.rect(
        #         surface,
        #         color,
        #         (x - bar_w // 2, y0 + (self.bar_eq_h - h), bar_w, h),
        #         border_radius=6,
        #     )
        # pygame.draw.circle(
        #     surface, color, (x, y0 + self.bar_eq_h + 14), self.dot_radius
        # )

        # Draw Footer Hints
        # txt1 = self.font_small.render("Tap/drag inside a column to set loudness", True, self.muted)
        # txt2 = self.font_small.render("Tap tiny dot to toggle a column ON/OFF | Long-press Presets to Save", True, self.muted)
        # surface.blit(txt1, (16, self.height - 28))
        # surface.blit(txt2, (16, self.height - 52))

        return [surface.get_rect()]

    def full_paint(self, surface, background):
        self.draw(surface, background)

    def update(self, dt: float):
        for b in self.buttons:
            b.update(dt)

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

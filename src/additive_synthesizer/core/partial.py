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
        self.active_pointer = None

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

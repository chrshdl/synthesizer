from pygame.sprite import LayeredDirty
from ...config import ConfigManager
from ...logger import Logger
from ...ui.utils.font import FontFamily, load_font
from ..widgets.button_widget import ButtonWidget

class DrumAssignView:
    def __init__(self, on_back, drum_engine, drum_name):
        self.on_back = on_back
        self.drum_engine = drum_engine
        self.drum_name = drum_name
        self.logger = Logger(__class__.__name__).get()
        self.width = ConfigManager.get_config().width
        self.height = ConfigManager.get_config().height

        self.ui_layer = LayeredDirty()
        self.bg_color = (12, 14, 18)
        self.panel_color = (22, 26, 32)
        self.panel_accent = (40, 46, 56)
        self.white = (240, 242, 245)
        self.font_large = load_font(size=32, family=FontFamily.D_DIN_EXP_BOLD)
        self.font_med = load_font(size=22, family=FontFamily.D_DIN_EXP_BOLD)

        self._init_ui()

    def _init_ui(self):
        btn_w, btn_h = 140, 60
        self.btn_back = ButtonWidget(
            (16, 16, btn_w, btn_h),
            "BACK",
            self.on_back,
            self.font_med,
            self.panel_accent,
            self.white,
        )
        self.ui_layer.add(self.btn_back)

        sounds = self.drum_engine.get_available_sounds()
        
        start_y = 120
        btn_h = 70
        total_w = 400
        
        cols = 2
        col_w = total_w + 40
        start_x = (self.width - (cols * col_w)) // 2 + 20
        
        for i, wav_file in enumerate(sounds):
            col = i % cols
            row = i // cols
            x = start_x + col * col_w
            y = start_y + row * (btn_h + 16)
            
            # Action to assign and go back
            def make_action(w):
                return lambda: self.assign_sound(w)
                
            label = wav_file.upper().replace(".WAV", "")
            btn = ButtonWidget(
                (x, y, total_w, btn_h),
                label,
                make_action(wav_file),
                self.font_med,
                self.panel_accent,
                self.white,
            )
            self.ui_layer.add(btn)
            
    def assign_sound(self, wav_file):
        config = ConfigManager.get_config()
        config.drum_mapping[self.drum_name] = wav_file
        config.write_to_file(ConfigManager.path)
        self.on_back()

    def draw(self, surface, background):
        surface.fill(self.bg_color)
        title = self.font_large.render(f"Assign Sound: {self.drum_name.upper()}", True, self.white)
        surface.blit(title, (16 + 140 + 32, 26))
        for sprite in self.ui_layer.sprites():
            sprite.dirty = 1
        self.ui_layer.draw(surface)
        return [surface.get_rect()]

    def full_paint(self, surface, background):
        for sprite in self.ui_layer.sprites():
            sprite.dirty = 1
        if background:
            surface.blit(background, (0, 0))
        self.draw(surface, background)

    def update(self, dt: float):
        self.ui_layer.update(dt=dt)

    def handle_event(self, ev):
        for b in self.ui_layer.sprites():
            if hasattr(b, "handle_event") and b.handle_event(ev):
                return True
        return False

from ..ui.views.settings_view import SettingsView
from .state import State


class SettingsState(State):
    def __init__(self, state_manager, audio_engine, drum_engine):
        super().__init__(state_manager)
        self.view = SettingsView(on_back=self.go_back, audio_engine=audio_engine, drum_engine=drum_engine)

    def go_back(self):
        self.state_manager.pop_state()

    def background_color(self):
        return (12, 14, 18)
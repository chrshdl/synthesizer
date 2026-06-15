from ..ui.views.settings_view import SettingsView
from .state import State


class SettingsState(State):
    def __init__(self, state_manager):
        super().__init__(state_manager)
        self.view = SettingsView(on_back=self.go_back)

    def go_back(self):
        self.state_manager.pop_state()

    def background_color(self):
        return (12, 14, 18)
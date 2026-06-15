from ..ui.views.synthesizer_view import SynthesizerView
from .state import State


class SynthesizerState(State):
    def __init__(self, state_manager, audio_engine, drum_engine, n_partials=8):
        super().__init__(state_manager)
        self.audio_engine = audio_engine
        self.drum_engine = drum_engine
        self.view = SynthesizerView(audio_engine, n_partials=n_partials)
        self.view.on_settings_action = self.go_to_settings

    def go_to_settings(self):
        from .settings_state import SettingsState
        self.state_manager.push_state(SettingsState(self.state_manager, self.audio_engine, self.drum_engine))

    def background_color(self):
        return (12, 14, 18)

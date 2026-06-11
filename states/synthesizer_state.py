from ui.views.synthesizer_view import SynthesizerView

from .state import State


class SynthesizerState(State):
    def __init__(self, state_manager, audio_engine):
        super().__init__(state_manager)
        self.view = SynthesizerView(audio_engine)

    def background_color(self):
        return (12, 14, 18)

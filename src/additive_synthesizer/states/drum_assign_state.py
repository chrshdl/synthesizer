from ..ui.views.drum_assign_view import DrumAssignView
from .state import State

class DrumAssignState(State):
    def __init__(self, state_manager, drum_engine, drum_name):
        super().__init__(state_manager)
        self.view = DrumAssignView(
            on_back=self.go_back, 
            drum_engine=drum_engine, 
            drum_name=drum_name
        )

    def go_back(self):
        self.state_manager.pop_state()

    def background_color(self):
        return (12, 14, 18)

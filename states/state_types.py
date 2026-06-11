from typing import Protocol


class State(Protocol):
    pass


class SupportsStateChange(Protocol):
    def change_state(self, new_state: "State") -> None:
        pass

    def push_state(self, new_state: "State") -> None:
        pass

    def pop_state(self) -> None:
        pass

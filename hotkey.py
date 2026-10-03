import threading
from pynput import keyboard


class HotkeyListener(threading.Thread):
    def __init__(self, toggle_event: threading.Event):
        super().__init__(daemon=True, name="HotkeyListener")
        self.toggle_event = toggle_event

    def run(self):
        try:
            with keyboard.GlobalHotKeys({"<cmd>+<shift>+l": self.toggle_event.set}):
                threading.Event().wait()
        except Exception:
            pass

#!/usr/bin/env python3
"""Lock-In Police — macOS menubar app."""
from __future__ import annotations

import os
import queue
import random
import subprocess
import sys
import threading
import time
from enum import Enum, auto

import rumps

import pexels_client
import sticker_client
from detector import PhoneDetector
from hotkey import HotkeyListener
from quotes import QUOTES, VOICE_LINES

APP_DIR      = os.path.dirname(os.path.abspath(__file__))
POPUP_SCRIPT = os.path.join(APP_DIR, "popup.py")
ASSETS_DIR   = os.path.join(APP_DIR, "assets")
SELFIES_DIR  = os.path.join(APP_DIR, "selfies")

WORK_SECS  = 25 * 60
BREAK_SECS =  5 * 60

# Silence OpenSSL/Tk noise in subprocesses
_POPUP_ENV = {**os.environ, "TK_SILENCE_DEPRECATION": "1"}



class Phase(Enum):
    IDLE   = auto()
    WORK   = auto()
    BREAK  = auto()
    PAUSED = auto()


class LockInPoliceApp(rumps.App):
    def __init__(self):
        super().__init__("Lock-In Police", title="🔒", quit_button=None)
        os.makedirs(SELFIES_DIR, exist_ok=True)
        os.makedirs(os.path.join(APP_DIR, "logs"), exist_ok=True)

        # Session state
        self.phase        = Phase.IDLE
        self._prev_phase  = Phase.WORK
        self.pomo_remaining = WORK_SECS
        self.pomo_count   = 0
        self.session_start: float | None = None
        self.pickups      = 0
        self.selfie_paths: list[str] = []
        self._fire_count  = 0

        # Threads / queues
        self._dq         = queue.Queue()
        self._hotkey_ev  = threading.Event()
        self._popup_proc: subprocess.Popen | None = None
        self._last_img_path: str | None = None

        # Camera permission handshake (main-thread request → _tick activates detector)
        self._pending_start = False
        self._cam_granted: bool | None = None

        self.detector = PhoneDetector(self._dq, ASSETS_DIR, SELFIES_DIR)
        self.detector.start()
        HotkeyListener(self._hotkey_ev).start()

        # Menu items
        self._mi_status = rumps.MenuItem("Ready", callback=None)
        self._mi_start  = rumps.MenuItem("▶  Start Session",  callback=self.start_session)
        self._mi_pause  = rumps.MenuItem("⏸  Pause",           callback=self.pause_session)
        self._mi_resume = rumps.MenuItem("▶  Resume",          callback=self.resume_session)
        self._mi_end    = rumps.MenuItem("⏹  End Session",     callback=self.end_session)
        self._mi_test   = rumps.MenuItem("🧪  Test Popup",     callback=self._test_popup)
        self._mi_quit   = rumps.MenuItem("Quit",               callback=self._quit)

        self.menu = [
            self._mi_status,
            None,
            self._mi_start,
            self._mi_pause,
            self._mi_resume,
            self._mi_end,
            None,
            self._mi_test,
            None,
            self._mi_quit,
        ]
        self._refresh_menu()
        rumps.Timer(self._tick, 1).start()

    # ── Tick (called every 1s on main Cocoa thread) ──────────────────────────

    def _tick(self, _):
        # Camera permission callback result (set by start_session handler)
        if self._pending_start and self._cam_granted is not None:
            self._pending_start = False
            if self._cam_granted:
                self.detector.activate()
            else:
                self.phase = Phase.IDLE
                self._update_title()
                self._refresh_menu()
                rumps.alert("Camera Access Denied",
                            "Enable camera for Python in:\n"
                            "System Settings → Privacy & Security → Camera",
                            ok="OK")
            self._cam_granted = None

        # Hotkey toggle
        if self._hotkey_ev.is_set():
            self._hotkey_ev.clear()
            self._handle_hotkey()

        # Drain detection events
        try:
            event = self._dq.get_nowait()
            if self.phase == Phase.WORK:
                self.pickups += 1
                self.selfie_paths.append(event["selfie"])
                self._on_phone_detected()
        except queue.Empty:
            pass

        # Pomodoro countdown
        if self.phase in (Phase.WORK, Phase.BREAK):
            self.pomo_remaining -= 1
            self._update_title()
            if self.pomo_remaining <= 0:
                self._pomodoro_transition()

        # Report detector errors once
        if self.detector.error:
            rumps.alert("Lock-In Police — Detector Error", self.detector.error)
            self.detector.error = None

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _update_title(self):
        m, s = divmod(max(0, self.pomo_remaining), 60)
        if self.phase == Phase.WORK:
            self.title = f"👮 {m}:{s:02d}"
        elif self.phase == Phase.BREAK:
            self.title = f"☕ {m}:{s:02d}"
        elif self.phase == Phase.PAUSED:
            self.title = "⏸"
        else:
            self.title = "🔒"

    def _refresh_menu(self):
        is_idle   = self.phase == Phase.IDLE
        is_active = self.phase in (Phase.WORK, Phase.BREAK)
        is_paused = self.phase == Phase.PAUSED

        self._mi_start.set_callback(self.start_session if is_idle else None)
        self._mi_pause.set_callback(self.pause_session if is_active else None)
        self._mi_resume.set_callback(self.resume_session if is_paused else None)
        self._mi_end.set_callback(self.end_session if not is_idle else None)

        if is_active or is_paused:
            pomo_label = f"Pomodoro #{self.pomo_count + 1}"
            self._mi_status.title = f"{pomo_label}  ·  pickups: {self.pickups}"
        else:
            self._mi_status.title = "Ready — press ⌘⇧L to start"

    def _handle_hotkey(self):
        if self.phase == Phase.IDLE:
            self.start_session()
        elif self.phase in (Phase.WORK, Phase.BREAK):
            self.pause_session()
        elif self.phase == Phase.PAUSED:
            self.resume_session()

    # ── Phone detected ────────────────────────────────────────────────────────

    def _on_phone_detected(self):
        if self._popup_proc and self._popup_proc.poll() is None:
            self._popup_proc.terminate()
            if self._last_img_path:
                try:
                    os.unlink(self._last_img_path)
                except OSError:
                    pass
                self._last_img_path = None

        voice = random.choice(["Samantha", "Alex", "Victoria"])
        voice_line = random.choice(VOICE_LINES)
        subprocess.Popen(["say", "-v", voice, voice_line])

        self._fire_count += 1
        self._refresh_menu()

        if self._fire_count % 2 == 1:
            img_path = pexels_client.fetch_image()
            if img_path:
                self._last_img_path = img_path
                self._popup_proc = subprocess.Popen(
                    [sys.executable, POPUP_SCRIPT, "--mode", "image", "--image-path", img_path],
                    env=_POPUP_ENV,
                )
                return
        self._last_img_path = None

        idx = (self._fire_count // 2) % len(QUOTES)
        headline, subtext = QUOTES[idx]
        sticker = sticker_client.fetch_sticker()
        cmd = [sys.executable, POPUP_SCRIPT, "--mode", "quote",
               "--headline", headline, "--subtext", subtext]
        if sticker:
            cmd += ["--sticker-path", sticker]
        self._popup_proc = subprocess.Popen(cmd, env=_POPUP_ENV)

    # ── Pomodoro ──────────────────────────────────────────────────────────────

    def _pomodoro_transition(self):
        if self.phase == Phase.WORK:
            self.pomo_count += 1
            self.phase = Phase.BREAK
            self.pomo_remaining = BREAK_SECS
            self.detector.deactivate()
            subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"], stderr=subprocess.DEVNULL)
            rumps.notification(
                "Lock-In Police",
                f"Pomodoro #{self.pomo_count} complete!",
                "Great work. Take a 5-minute break.",
                sound=True,
            )
        elif self.phase == Phase.BREAK:
            self.phase = Phase.WORK
            self.pomo_remaining = WORK_SECS
            self.detector.activate()
            subprocess.Popen(["afplay", "/System/Library/Sounds/Ping.aiff"], stderr=subprocess.DEVNULL)
            subprocess.Popen(
                [sys.executable, POPUP_SCRIPT, "--mode", "quote",
                 "--headline", "BREAK OVER",
                 "--subtext", f"Pomodoro #{self.pomo_count + 1}. Lock in. Go.",
                 "--no-dismiss"],
                env=_POPUP_ENV,
            )
        self._update_title()
        self._refresh_menu()

    # ── Session control ───────────────────────────────────────────────────────

    def start_session(self, _=None):
        self.phase = Phase.WORK
        self.pomo_remaining = WORK_SECS
        self.pomo_count = 0
        self.pickups = 0
        self.selfie_paths = []
        self._fire_count = 0
        self.session_start = time.time()
        self._update_title()
        self._refresh_menu()

        try:
            import AVFoundation as av
            status = int(av.AVCaptureDevice.authorizationStatusForMediaType_(av.AVMediaTypeVideo))
        except Exception:
            status = 3

        if status == 3:
            self.detector.activate()
        elif status == 2:
            self.phase = Phase.IDLE
            self._update_title()
            self._refresh_menu()
            rumps.alert("Camera Access Denied",
                        "Enable camera for Python in:\n"
                        "System Settings → Privacy & Security → Camera",
                        ok="OK")
        else:
            # Not-determined: request on main thread so dialog appears
            self._pending_start = True
            self._cam_granted = None
            def _handler(granted):
                self._cam_granted = bool(granted)
            av.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
                av.AVMediaTypeVideo, _handler
            )

    def pause_session(self, _=None):
        self._prev_phase = self.phase
        self.phase = Phase.PAUSED
        self.detector.deactivate()
        self._update_title()
        self._refresh_menu()

    def resume_session(self, _=None):
        self.phase = self._prev_phase
        if self.phase == Phase.WORK:
            self.detector.activate()
        self._update_title()
        self._refresh_menu()

    def end_session(self, _=None):
        self.detector.deactivate()
        duration = int(time.time() - self.session_start) if self.session_start else 0
        pickups   = self.pickups
        pomos     = self.pomo_count
        selfies   = list(self.selfie_paths)
        self.phase = Phase.IDLE
        self.title = "🔒"
        self.session_start = None
        self._refresh_menu()
        self._show_summary(duration, pickups, pomos, selfies)

    # ── Summary ───────────────────────────────────────────────────────────────

    def _show_summary(self, duration: int, pickups: int, pomos: int, selfies: list[str]):
        mins, secs = divmod(duration, 60)
        hrs, mins  = divmod(mins, 60)
        dur_str = f"{hrs}h {mins}m" if hrs else f"{mins}m {secs}s"

        if pickups == 0:
            rating = "BEAST MODE. Completely clean session."
        elif pickups <= 2:
            rating = "Solid. Just slipped up a couple times."
        elif pickups <= 5:
            rating = f"Decent. But you checked your phone {pickups} times."
        else:
            rating = f"Rough one. Your phone won {pickups} times today."

        msg = (
            f"Duration: {dur_str}\n"
            f"Pomodoros completed: {pomos}\n"
            f"Phone pickups: {pickups}\n\n"
            f"{rating}"
        )
        if selfies:
            msg += f"\n\n{len(selfies)} shame selfie(s) saved."

        cancel_label = "View Shame Selfies" if selfies else None
        result = rumps.alert(
            title="Session Complete",
            message=msg,
            ok="Close",
            cancel=cancel_label,
        )
        if result == 0 and selfies:
            subprocess.Popen(["open", SELFIES_DIR])

    # ── Misc ──────────────────────────────────────────────────────────────────

    def _test_popup(self, _=None):
        self._fire_count += 1
        if self._fire_count % 2 == 1:
            img_path = pexels_client.fetch_image()
            if img_path:
                subprocess.Popen(
                    [sys.executable, POPUP_SCRIPT, "--mode", "image", "--image-path", img_path],
                    env=_POPUP_ENV,
                )
                return
        idx = (self._fire_count // 2) % len(QUOTES)
        headline, subtext = QUOTES[idx]
        sticker = sticker_client.fetch_sticker()
        cmd = [sys.executable, POPUP_SCRIPT, "--mode", "quote",
               "--headline", headline, "--subtext", subtext]
        if sticker:
            cmd += ["--sticker-path", sticker]
        subprocess.Popen(cmd, env=_POPUP_ENV)

    def _quit(self, _=None):
        self.detector.stop()
        rumps.quit_application()


if __name__ == "__main__":
    LockInPoliceApp().run()

from __future__ import annotations

import os
import queue
import threading
import time
from datetime import datetime

import cv2

PHONE_CLASS_ID = 77   # COCO 1-indexed class for "cell phone"
CONFIDENCE_THRESHOLD = 0.45
FPS = 2
COOLDOWN_SECS = 30


class PhoneDetector(threading.Thread):
    def __init__(self, detection_queue: queue.Queue, assets_dir: str, selfies_dir: str):
        super().__init__(daemon=True, name="PhoneDetector")
        self.q = detection_queue
        self.assets_dir = assets_dir
        self.selfies_dir = selfies_dir
        self._active = threading.Event()
        self._stop = threading.Event()
        self._release_cam = threading.Event()
        self._last_trigger = 0.0
        self.error: str | None = None

    def activate(self):
        self._release_cam.clear()
        self._active.set()

    def deactivate(self):
        self._active.clear()
        self._release_cam.set()

    def stop(self):
        self._stop.set()

    def run(self):
        model_path = os.path.join(self.assets_dir, "frozen_inference_graph.pb")
        config_path = os.path.join(self.assets_dir, "ssd_mobilenet_v2_coco.pbtxt")

        if not os.path.exists(model_path) or not os.path.exists(config_path):
            self.error = f"Model files missing in {self.assets_dir}. Run setup.sh first."
            return

        try:
            net = cv2.dnn.readNetFromTensorflow(model_path, config_path)
        except Exception as e:
            self.error = f"Failed to load model: {e}"
            return

        cap: cv2.VideoCapture | None = None

        while not self._stop.is_set():
            # Release camera when deactivated so the indicator light goes off
            if self._release_cam.is_set():
                if cap is not None:
                    cap.release()
                    cap = None
                time.sleep(0.2)
                continue

            if not self._active.is_set():
                time.sleep(0.2)
                continue

            # Open camera on demand when activated
            if cap is None:
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    self.error = "Could not open webcam."
                    return

            ret, frame = cap.read()
            if not ret:
                time.sleep(0.5)
                continue

            blob = cv2.dnn.blobFromImage(frame, size=(300, 300), swapRB=True, crop=False)
            net.setInput(blob)
            detections = net.forward()

            phone_found = False
            for i in range(detections.shape[2]):
                conf = float(detections[0, 0, i, 2])
                if conf < CONFIDENCE_THRESHOLD:
                    break  # detections sorted by confidence descending
                cls = int(detections[0, 0, i, 1])
                if cls == PHONE_CLASS_ID:
                    phone_found = True
                    break

            if phone_found:
                now = time.time()
                if now - self._last_trigger > COOLDOWN_SECS:
                    self._last_trigger = now
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    selfie_path = os.path.join(self.selfies_dir, f"shame_{timestamp}.jpg")
                    cv2.imwrite(selfie_path, frame)
                    self.q.put({"selfie": selfie_path})

            time.sleep(1 / FPS)

        if cap is not None:
            cap.release()

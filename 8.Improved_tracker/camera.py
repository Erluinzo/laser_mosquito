"""Frame acquisition.

Live sources (CSI/USB camera) are read on a background thread that keeps only
the most recent frame, so the tracking loop never processes stale video and
never blocks on capture. Video files are read synchronously so simulation
runs stay deterministic.
"""
import threading
import time

import cv2

import config


def _open(source):
    if source == "jetson":
        cap = cv2.VideoCapture(config.JETSON_PIPELINE, cv2.CAP_GSTREAMER)
    else:
        cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError("could not open camera source: %r" % (source,))
    return cap


class FrameGrabber(object):
    def __init__(self, source):
        self._cap = _open(source)
        self._live = not isinstance(source, str) or source == "jetson"
        self._lock = threading.Lock()
        self._frame = None
        self._ok = True
        if self._live:
            thread = threading.Thread(target=self._loop)
            thread.daemon = True
            thread.start()

    def _loop(self):
        while self._ok:
            ok, frame = self._cap.read()
            if not ok:
                self._ok = False
                break
            with self._lock:
                self._frame = frame

    def read(self):
        """Return the newest frame, or None when the source is finished/broken."""
        if not self._live:
            ok, frame = self._cap.read()
            return frame if ok else None
        while self._ok:
            with self._lock:
                frame, self._frame = self._frame, None
            if frame is not None:
                return frame
            time.sleep(0.001)
        return None

    def release(self):
        self._ok = False
        self._cap.release()

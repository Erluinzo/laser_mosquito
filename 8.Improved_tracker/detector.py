"""Target detection.

Two interchangeable detectors, both returning (x, y, radius) in pixels or None:
 - MotionDetector: MOG2 background subtraction; best for small moving insects.
 - ColorDetector:  HSV threshold; best for the yellow-LED bench target.
The morphology runs on the binary mask (the original scripts eroded the BGR
frame and then discarded the result before thresholding).
"""
import cv2
import numpy as np

import config

_COLOR_LO = np.array(config.COLOR_HSV_LOWER, dtype=np.uint8)
_COLOR_HI = np.array(config.COLOR_HSV_UPPER, dtype=np.uint8)
_DOT_LO = np.array(config.DOT_HSV_LOWER, dtype=np.uint8)
_DOT_HI = np.array(config.DOT_HSV_UPPER, dtype=np.uint8)


def _largest_blob(mask):
    mask = cv2.erode(mask, None, iterations=config.MORPH_ITERATIONS)
    mask = cv2.dilate(mask, None, iterations=config.MORPH_ITERATIONS)
    cnts = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    best = None
    for c in cnts:
        (x, y), r = cv2.minEnclosingCircle(c)
        if config.MIN_RADIUS_PX <= r <= config.MAX_RADIUS_PX:
            if best is None or r > best[2]:
                best = (x, y, r)
    return best


class ColorDetector(object):
    def detect(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return _largest_blob(cv2.inRange(hsv, _COLOR_LO, _COLOR_HI))


class MotionDetector(object):
    def __init__(self):
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=config.MOG2_HISTORY,
            varThreshold=config.MOG2_THRESHOLD,
            detectShadows=False)

    def detect(self, frame):
        return _largest_blob(self._bg.apply(frame))


class DotDetector(object):
    """Finds the laser dot itself, for calibration and closed-loop control."""

    def detect(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return _largest_blob(cv2.inRange(hsv, _DOT_LO, _DOT_HI))


def make(mode):
    if mode == "color":
        return ColorDetector()
    if mode == "motion":
        return MotionDetector()
    raise ValueError("unknown detector mode: %r" % (mode,))

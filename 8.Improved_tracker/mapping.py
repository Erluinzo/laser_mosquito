"""Pixel -> DAC coordinate mapping.

Uses the homography produced by calibrate.py when available, otherwise falls
back to the original hand-fitted linear map from config.py. The homography
absorbs camera/mirror rotation, offset and perspective, which the two
independent linear equations cannot.
"""
import json
import os

import numpy as np

import config


class LinearMapper(object):
    calibrated = False

    def to_dac(self, x, y):
        ax, bx = config.LINEAR_X
        ay, by = config.LINEAR_Y
        return ax * x + bx, ay * y + by


class HomographyMapper(object):
    calibrated = True

    def __init__(self, h):
        self._h = np.asarray(h, dtype=np.float64)
        self._h_inv = np.linalg.inv(self._h)

    def to_dac(self, x, y):
        return self._apply(self._h, x, y)

    def to_pixel(self, dac_a, dac_b):
        """Inverse map, used to draw the mirror aim point on the overlay."""
        return self._apply(self._h_inv, dac_a, dac_b)

    @staticmethod
    def _apply(h, x, y):
        v = h.dot(np.array([x, y, 1.0]))
        return v[0] / v[2], v[1] / v[2]


def load(path=None):
    path = path or config.CALIBRATION_FILE
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        return HomographyMapper(data["homography"])
    return LinearMapper()

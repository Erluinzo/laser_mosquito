"""Constant-velocity Kalman filter for aiming ahead of a moving target.

A mosquito keeps moving during the capture->detect->aim latency, so pointing
at the last measured position guarantees a miss. The filter smooths the
measurements, coasts through short detection dropouts, and returns an aim
point LEAD_FRAMES ahead of the newest state estimate.
"""
import cv2
import numpy as np

import config


class TargetTracker(object):
    def __init__(self):
        self._kf = None
        self._misses = 0

    def _init_filter(self, x, y):
        kf = cv2.KalmanFilter(4, 2)  # state: x, y, vx, vy ; measured: x, y
        kf.transitionMatrix = np.array(
            [[1, 0, 1, 0],
             [0, 1, 0, 1],
             [0, 0, 1, 0],
             [0, 0, 0, 1]], dtype=np.float32)
        kf.measurementMatrix = np.array(
            [[1, 0, 0, 0],
             [0, 1, 0, 0]], dtype=np.float32)
        kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
        kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1.0
        kf.errorCovPost = np.eye(4, dtype=np.float32)
        kf.statePost = np.array([[x], [y], [0], [0]], dtype=np.float32)
        self._kf = kf

    def update(self, measurement):
        """Feed one frame's detection ((x, y) or None).

        Returns the aim point (x, y) LEAD_FRAMES ahead, or None while no
        target is being tracked.
        """
        if measurement is None:
            self._misses += 1
            if self._kf is None or self._misses > config.LOST_AFTER_FRAMES:
                self._kf = None
                return None
            self._kf.predict()  # coast on the motion model during dropouts
        else:
            x, y = float(measurement[0]), float(measurement[1])
            self._misses = 0
            if self._kf is None:
                self._init_filter(x, y)
            else:
                self._kf.predict()
                self._kf.correct(np.array([[x], [y]], dtype=np.float32))
        state = self._kf.statePost.ravel()
        lead = config.LEAD_FRAMES
        return (float(state[0] + state[2] * lead),
                float(state[1] + state[3] * lead))

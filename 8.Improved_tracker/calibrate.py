"""Automatic aim calibration.

Sweeps the mirrors through a grid of DAC values, detects the laser dot at
each position with the camera, and fits a homography mapping pixel
coordinates to DAC values. Run this on the rig with a plain surface in view
and the (<= 1 mW!) laser pointer switched on manually:

    python3 calibrate.py [--source jetson]

Writes calibration.json, which track.py then picks up automatically. Re-run
whenever the camera or the galvanometers have been moved.
"""
import argparse
import json
import sys
import time

import cv2
import numpy as np

import camera
import config
import detector
from dac_mcp4922 import Mcp4922


def sample_grid(dac, grabber, dot):
    ax0, ax1, nx = config.CAL_DAC_X
    ay0, ay1, ny = config.CAL_DAC_Y
    pixels, dacs = [], []
    for a in np.linspace(ax0, ax1, nx):
        for b in np.linspace(ay0, ay1, ny):
            dac.write_xy(a, b)
            time.sleep(config.CAL_SETTLE_S)
            grabber.read()  # skip a frame that may have been taken mid-move
            frame = grabber.read()
            if frame is None:
                raise RuntimeError("camera stopped during calibration")
            hit = dot.detect(frame)
            if hit is None:
                print("no dot found at dac=(%d, %d) - skipped" % (a, b))
                continue
            pixels.append(hit[:2])
            dacs.append((float(a), float(b)))
            print("dac=(%4d, %4d) -> pixel=(%5.1f, %5.1f)" % (a, b, hit[0], hit[1]))
    return (np.array(pixels, dtype=np.float64),
            np.array(dacs, dtype=np.float64))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=None,
                    help="jetson | webcam index | video file (default: config.py)")
    ap.add_argument("--out", default=config.CALIBRATION_FILE)
    args = ap.parse_args()

    source = args.source if args.source is not None else config.CAMERA_SOURCE
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    dac = Mcp4922()
    grabber = camera.FrameGrabber(source)
    try:
        pixels, dacs = sample_grid(dac, grabber, detector.DotDetector())
    finally:
        grabber.release()
        dac.close()

    if len(pixels) < 8:
        sys.exit("only %d grid points detected - check DOT_HSV_* in config.py, "
                 "the lighting, and that the laser is on" % len(pixels))

    h, _ = cv2.findHomography(pixels, dacs, cv2.RANSAC, 20.0)
    proj = cv2.perspectiveTransform(pixels.reshape(-1, 1, 2), h).reshape(-1, 2)
    err = float(np.sqrt(((proj - dacs) ** 2).sum(axis=1)).mean())

    with open(args.out, "w") as f:
        json.dump({"homography": h.tolist(),
                   "points": len(pixels),
                   "mean_error_dac_steps": err,
                   "created": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)
    print("saved %s (%d points, mean reprojection error %.1f DAC steps)"
          % (args.out, len(pixels), err))


if __name__ == "__main__":
    main()

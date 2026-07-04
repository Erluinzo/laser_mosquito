"""Real-time insect tracker.

Pipeline: capture (threaded, newest frame only) -> detect (motion or color)
-> Kalman prediction (aim ahead of the target) -> pixel->DAC homography ->
galvo mirrors, with optional closed-loop correction using the camera's own
view of the laser dot, and strict laser gating (see safety.py).

Examples:
  bench test on the Jetson, LED target, laser disarmed:
      python3 track.py --mode color --display
  track insects, laser armed (<= 1 mW pointer only!):
      python3 track.py --arm
  simulate on a desktop PC against a recording, no hardware needed:
      python3 track.py --sim --source flight.mp4 --save-video out.mp4
"""
import argparse
import sys
import time

import cv2

import camera
import config
import detector
import mapping
import safety
from dac_mcp4922 import Mcp4922, MockSpi
from kalman import TargetTracker


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", default=None,
                   help="jetson | webcam index | video file (default: config.py)")
    p.add_argument("--mode", default=config.DETECTOR_MODE,
                   choices=["motion", "color"])
    p.add_argument("--sim", action="store_true",
                   help="mock the SPI bus, run without any hardware")
    p.add_argument("--arm", action="store_true",
                   help="allow the laser GPIO to switch on (see safety.py)")
    p.add_argument("--closed-loop", action="store_true",
                   help="correct the aim using the detected laser dot")
    p.add_argument("--display", action="store_true",
                   help="show the annotated video (needs a desktop session)")
    p.add_argument("--save-video", default=None,
                   help="write the annotated video to this file")
    return p.parse_args()


def annotate(frame, hit, aim, aim_dac, mapper, fired):
    if hit is not None:
        cv2.circle(frame, (int(hit[0]), int(hit[1])), max(int(hit[2]), 3),
                   (0, 255, 255), 1)
    if aim is not None:
        cv2.drawMarker(frame, (int(aim[0]), int(aim[1])), (0, 255, 0),
                       cv2.MARKER_CROSS, 12, 1)
    if aim_dac is not None and mapper.calibrated:
        px = mapper.to_pixel(aim_dac[0], aim_dac[1])
        cv2.drawMarker(frame, (int(px[0]), int(px[1])), (0, 0, 255),
                       cv2.MARKER_TILTED_CROSS, 12, 1)
    cv2.putText(frame, "LASER ON" if fired else "laser off", (5, 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                (0, 0, 255) if fired else (200, 200, 200), 1)


def main():
    args = parse_args()
    if args.sim and args.arm:
        sys.exit("refusing --arm together with --sim")

    source = args.source if args.source is not None else config.CAMERA_SOURCE
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    spi = MockSpi() if args.sim else None
    dac = Mcp4922(spi)
    mapper = mapping.load()
    if not mapper.calibrated:
        print("no %s - using the fallback linear map (run calibrate.py)"
              % config.CALIBRATION_FILE)
    det = detector.make(args.mode)
    dot_det = detector.DotDetector() if args.closed_loop else None
    tracker = TargetTracker()
    gate = safety.LaserGate(args.arm)
    grabber = camera.FrameGrabber(source)
    writer = None
    offset = [0.0, 0.0]  # accumulated closed-loop correction, DAC steps
    frames = hits = 0
    t0 = time.monotonic()

    try:
        while True:
            frame = grabber.read()
            if frame is None:
                break
            frames += 1

            hit = det.detect(frame)
            if hit is not None:
                hits += 1
            aim = tracker.update(hit[:2] if hit is not None else None)

            fired = False
            aim_dac = None
            if aim is not None:
                da, db = mapper.to_dac(aim[0], aim[1])
                aim_dac = (da + offset[0], db + offset[1])
                dac.write_xy(aim_dac[0], aim_dac[1])
                fired = gate.update(hit is not None)
                if dot_det is not None and gate.is_on:
                    dot = dot_det.detect(frame)
                    if dot is not None:
                        # steer the dot toward the target in DAC space
                        ta, tb = mapper.to_dac(aim[0], aim[1])
                        pa, pb = mapper.to_dac(dot[0], dot[1])
                        lim = config.CLOSED_LOOP_MAX_OFFSET
                        gain = config.CLOSED_LOOP_GAIN
                        offset[0] = max(-lim, min(lim, offset[0] + gain * (ta - pa)))
                        offset[1] = max(-lim, min(lim, offset[1] + gain * (tb - pb)))
            else:
                gate.update(False)

            if args.display or args.save_video:
                annotate(frame, hit, aim, aim_dac, mapper, fired)
                if args.save_video and writer is None:
                    writer = cv2.VideoWriter(
                        args.save_video, cv2.VideoWriter_fourcc(*"mp4v"),
                        20.0, (frame.shape[1], frame.shape[0]))
                if writer is not None:
                    writer.write(frame)
                if args.display:
                    cv2.imshow("tracker", frame)
                    if (cv2.waitKey(1) & 0xFF) == ord("q"):
                        break
    finally:
        gate.off()
        grabber.release()
        if writer is not None:
            writer.release()
        dac.close()
        cv2.destroyAllWindows()

    dt = time.monotonic() - t0
    print("%d frames, %d detections, %.1f FPS"
          % (frames, hits, frames / dt if dt > 0 else 0.0))
    if isinstance(spi, MockSpi):
        print("sim: %d DAC writes, last SPI frame %s" % (spi.writes, spi.last))


if __name__ == "__main__":
    main()

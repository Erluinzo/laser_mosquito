# 8. Improved tracker

A modular re-implementation of the tracking pipeline in `5.My_project`, built
for moving targets. Same hardware, same wiring, same MCP4922 SPI protocol —
new software.

**Only ever use a laser pointer of 1 mW or less.** The warning at the top of
the project README applies to everything here. The laser output is disabled
unless you explicitly pass `--arm`, and even then it is gated by the rules in
`safety.py`.

## What changed vs. the original scripts

| Area | Original | Here |
|---|---|---|
| Detection | `inRange` on raw BGR (matched almost nothing) | HSV color mode, or MOG2 motion mode for insects |
| Aiming | `dac = 10*x + 246` hand-fitted lines | homography fitted by an automatic laser-dot sweep (`calibrate.py`), hand-fitted lines as fallback |
| Moving targets | aims at the last seen position | Kalman filter aims `LEAD_FRAMES` ahead, coasts through dropouts |
| Latency | serial loop with `sleep(0.5)` | threaded capture that always processes the newest frame |
| Accuracy | open loop | optional `--closed-loop`: the camera watches the laser dot and servos it onto the target |
| Laser | on whenever a blob was found | off by default; `--arm` + N-frame confirmation + on-time watchdog + forced-off at exit |
| Hardware needed to develop | Jetson + rig | `--sim` mocks the SPI bus and runs against a video file on any PC |

## Files

- `config.py` — every tunable (camera, HSV bounds, DAC ranges, safety limits)
- `track.py` — main entry point
- `calibrate.py` — automatic pixel→DAC calibration, writes `calibration.json`
- `camera.py`, `detector.py`, `kalman.py`, `mapping.py`, `dac_mcp4922.py`, `safety.py` — the pipeline stages

## Quick start

Try it on any PC, no hardware, against a recording (annotated video written
to `out.mp4`, mirror commands go to a mock SPI bus):

```bash
cd 8.Improved_tracker
python3 track.py --sim --source your_recording.mp4 --save-video out.mp4
```

On the Jetson rig:

```bash
# 1. one-time aim calibration: plain surface in view, laser pointer on
python3 calibrate.py

# 2. bench test with the yellow LED, laser stays off
python3 track.py --mode color --display

# 3. track insects (motion detection), laser armed - <= 1 mW pointer only!
python3 track.py --arm --closed-loop
```

`calibration.json` is rig-specific and git-ignored; re-run `calibrate.py`
after any mechanical change.

## Dependencies

`numpy`, `opencv-python` everywhere; `spidev` and optionally `Jetson.GPIO`
on the Jetson only (`--sim` runs without either).

# Build guide — laser insect tracker, from absolutely nothing

This document takes you from an empty desk to a working tracker: every part
to buy, every wire to connect, every command to type. It builds the
**improved tracker** (`8.Improved_tracker/`): motion detection, Kalman
prediction, automatic calibration, closed-loop aiming, safety interlocks.

Read it once fully before buying anything.

---

## 0. Safety — read this first, it is not optional

- **Only ever use a laser of 1 mW or less (class 2).** Nothing in this guide
  or this repository changes that. A stronger laser can blind a person —
  including you, including through an accidental reflection off a window,
  a glass, or the galvo mirrors themselves, and the damage is painless,
  invisible at first, and permanent.
- Buy **laser safety glasses** rated for your laser's wavelength (650 nm for
  the red module below) and wear them whenever the laser is powered — even
  a 1 mW beam is unpleasant, and you will be leaning over moving mirrors.
- Set up the rig so the beam can only hit a **matte, non-reflective
  backdrop** (white cardboard). No windows, mirrors, glossy paint, or
  doorways behind or beside the target area.
- Never run it where a person or animal can walk into the scene. The
  software has interlocks (`--arm` required, confirmation frames, on-time
  watchdog, off-at-exit), but software fails; the beam power is the only
  real safety layer.
- The mirrors move fast and the galvo drivers run on bipolar supplies
  (±15 V or more). Power everything off before touching wiring.

---

## 1. What you are building

```
                          ┌───────────────┐
   CSI camera ──────────► │  Jetson Nano  │
   (sees the scene)       │   track.py    │
                          └──┬─────────┬──┘
                       SPI   │         │  GPIO pin 12
                             ▼         ▼
                        ┌─────────┐  ┌───────────────┐
                        │ MCP4922 │  │ transistor    │
                        │ 2ch DAC │  │ laser switch  │
                        └────┬────┘  └──────┬────────┘
                     0–5 V   │              │
                             ▼              ▼
                        ┌─────────┐   ≤ 1 mW laser ──► X mirror ─► Y mirror ─► target area
                        │ op-amp  │                        ▲            ▲
                        │ stage   │ bipolar signal   ┌─────┴────────────┴─────┐
                        └────┬────┘ ───────────────► │ galvo driver boards    │
                             │                       │ + ±15 V supply (kit)   │
                             └──────────────────────►└────────────────────────┘
```

The camera watches a flat target area (a wall / cardboard sheet). The Jetson
detects a moving insect, predicts where it will be a couple of frames ahead,
converts that position to two 12-bit DAC values through a calibrated
homography, and the galvanometer mirrors steer the laser dot onto it.

---

## 2. Shopping list

Prices are rough 2026 ballparks; everything is standard hobby-electronics
stock. Total ≈ **$350–550**.

### Computing and camera
| # | Item | Notes | ~Price |
|---|------|-------|--------|
| 1 | **NVIDIA Jetson Nano Developer Kit** (4 GB, A02 or B01) | New or used. The code targets the Nano's JetPack 4.6 / `nvarguscamerasrc` stack. | $150–250 |
| 2 | **microSD card, 64 GB or larger**, U3/A2 class | The Jetson's disk. | $12 |
| 3 | **5 V 4 A power supply, 5.5×2.1 mm barrel jack** | The Nano throttles on USB power; use the barrel jack. | $15 |
| 4 | **2.54 mm jumper cap** (often included) | Bridges J48 on the Nano to enable barrel-jack power. | $1 |
| 5 | **Raspberry Pi Camera Module v2** (IMX219, CSI ribbon) | **Must be the v2/IMX219.** The v1 (OV5647) and USB webcams do not work with the Jetson's CSI pipeline. | $25 |

### Galvanometer (the moving mirrors)
| # | Item | Notes | ~Price |
|---|------|-------|--------|
| 6 | **20 kpps laser-show galvo kit** ("galvanometer scanner XY kit") | Buy a kit that includes: 2 galvos with mirrors on an XY mount, 2 driver boards, and the bipolar (±15 V) supply. Sold for DIY laser shows. | $70–130 |

### Electronics
| # | Item | Notes | ~Price |
|---|------|-------|--------|
| 7 | **MCP4922** DAC, 14-pin DIP | Dual-channel, 12-bit, SPI. Get 2, they're cheap. | $3–5 |
| 8 | **TL082 (or TL072) dual op-amp**, ×2, DIP-8 | For the 0–5 V → bipolar converter stage (one dual op-amp per axis). | $2 |
| 9 | **Resistor assortment** (needs 33 kΩ, 47–50 kΩ, 100 kΩ, 1 kΩ, 4.7–5 kΩ) + a few 100 nF ceramic capacitors | For the op-amp stage and decoupling. | $10 |
| 10 | **2N2222 NPN transistor** (or any small NPN / logic-level N-MOSFET) | Switches the laser from GPIO pin 12. | $1 |
| 11 | **Red dot laser module, ≤ 1 mW, 650 nm, 3–5 V** | Class 2 pointer module. **Nothing stronger.** | $5–10 |
| 12 | **Breadboard + male-female jumper wires** | DAC and op-amp stage live here. | $10 |

### Safety and tools
| # | Item | Notes | ~Price |
|---|------|-------|--------|
| 13 | **Laser safety glasses for 650 nm** | Wear them. | $25–40 |
| 14 | **Multimeter** | Needed for the DAC and op-amp checks. | $15 |
| 15 | **Rigid mounting board** (plywood/MDF ~40×30 cm), screws, standoffs, white matte cardboard sheet for the target backdrop | The whole rig must not flex — calibration dies otherwise. | $20 |

You'll also want: a monitor + HDMI cable, USB keyboard/mouse (first Jetson
boot only), another computer with an SD-card reader, soldering iron
(the galvo kit connectors and laser module usually need it).

---

## 3. Try the software before buying anything

The whole pipeline runs on any PC against a video file, with the SPI bus
mocked. Good way to check you like the project before spending money:

```bash
git clone https://github.com/Erluinzo/laser_mosquito.git
cd laser_mosquito/8.Improved_tracker
python3 -m pip install --user opencv-python numpy
python3 track.py --sim --source /path/to/any_video.mp4 --save-video out.mp4
```

Open `out.mp4`: yellow circle = detection, green cross = where the mirrors
would aim (ahead of the target's motion).

---

## 4. Jetson software setup (from a blank SD card)

### 4.1 Flash the OS
On your PC:
1. Download the **Jetson Nano Developer Kit SD Card Image** (JetPack 4.6.x)
   from https://developer.nvidia.com/embedded/downloads
2. Download and run **balenaEtcher** (https://etcher.balena.io), select the
   image, select the SD card, flash.

### 4.2 First boot
Insert the SD card, connect monitor + keyboard, bridge jumper **J48**, plug
in the barrel-jack supply. Accept the license, create a user (the commands
below assume you also pick hostname/user you'll remember), let it finish.
Connect it to your network (Ethernet is simplest).

From here on you can work over SSH from your PC:
```bash
ssh youruser@jetson-ip-address
```

### 4.3 System packages
```bash
sudo apt update
sudo apt install -y python3-pip git python3-opencv
python3 -m pip install --user spidev
```
(`numpy`, `Jetson.GPIO` and GStreamer-enabled OpenCV ship with JetPack.)

### 4.4 Enable SPI (off by default!)
```bash
sudo /opt/nvidia/jetson-io/jetson-io.py
```
In the menu: **Configure 40-pin expansion header** → enable **spi1** →
**Save pin changes** → **Save and reboot**.

After the reboot, verify:
```bash
ls /dev/spidev*
# expected: /dev/spidev0.0  /dev/spidev0.1
```

Let your user access SPI and GPIO without sudo:
```bash
sudo usermod -aG gpio $USER
echo 'SUBSYSTEM=="spidev", GROUP="gpio", MODE="0660"' | sudo tee /etc/udev/rules.d/99-spidev.rules
sudo reboot
```

### 4.5 Get the code
```bash
git clone https://github.com/Erluinzo/laser_mosquito.git
cd laser_mosquito/8.Improved_tracker
```

### 4.6 Test the camera (before wiring anything)
Connect the Pi Camera v2 to the Nano's CSI connector (lift the black latch,
ribbon contacts facing the heatsink, press latch down). Then:
```bash
nvgstcapture-1.0
# a live preview window appears; Ctrl+C to quit
```
If you get a preview, the camera side is done.

---

## 5. Wiring

Power everything **off** while wiring. All grounds — Jetson, DAC,
op-amp stage, galvo driver signal inputs, laser — must be connected
together (common ground).

### 5.1 MCP4922 DAC ↔ Jetson 40-pin header

The Nano's J41 header has the same layout as the Raspberry Pi header shown
in the original diagram (`2.Jetson_code/2.1_mirror_control/mcp4922.bmp`).
MCP4922 pin 1 is marked by the notch/dot; pins count counter-clockwise.

| MCP4922 pin | Name | Connect to |
|---|---|---|
| 1 | VDD | Jetson **pin 2** (5 V) |
| 2 | NC | — |
| 3 | CS | Jetson **pin 24** (SPI1 CS0) |
| 4 | SCK | Jetson **pin 23** (SPI1 SCK) |
| 5 | SDI | Jetson **pin 19** (SPI1 MOSI) |
| 6, 7 | NC | — |
| 8 | LDAC | GND — outputs update immediately |
| 9 | SHDN | VDD (5 V) |
| 10 | VOUTB | → Y-axis op-amp input |
| 11 | VREFB | VDD (5 V) |
| 12 | VSS | Jetson **pin 6** (GND) |
| 13 | VREFA | VDD (5 V) |
| 14 | VOUTA | → X-axis op-amp input |

Add a 100 nF capacitor between VDD and VSS, close to the chip.

> Note: 5 V supply with the Jetson's 3.3 V logic is what the original author
> ran (and what the `*819` voltage scaling in the old scripts assumes). It is
> marginal on paper per the datasheet; if you ever see garbled outputs, the
> clean fix is a 74HCT-family level shifter on CS/SCK/SDI.

### 5.2 Laser switch (GPIO gate — this is what `--arm` controls)

```
Jetson pin 12 ──── 1 kΩ ──── base   (2N2222)
Laser module (−) ─────────── collector
Jetson pin 6  ────────────── emitter → GND
Laser module (+) ─────────── 5 V (Jetson pin 4)
```

The laser is off whenever pin 12 is low — which is the default, at boot, on
crash, and any time the tracker isn't confirming a target.

### 5.3 DAC → op-amp stage → galvo drivers

The DAC outputs 0–5 V; galvo driver boards expect a bipolar signal centered
on 0 V. Build **two copies** (X and Y) of the op-amp stage from the original
schematic: **`2.Jetson_code/2.1_mirror_control/opy.png`** — first op-amp
inverts/scales the DAC output, the second subtracts the mid-scale offset so
2.5 V in = 0 V out. Match the output range to your driver's input rating
(check the kit's leaflet; ±5 V input is typical for laser-show kits — use
the "size"/"gain" trimmer on the driver boards for final scaling).

Then per axis: op-amp output → driver board signal input (+), signal ground
→ driver input (−/GND). The kit's ±15 V supply powers the driver boards
(and can power the op-amps too).

### 5.4 Mechanical layout

- Bolt to the board: galvo XY block, laser module, camera, target backdrop
  frame. Rigidity matters more than precision — calibration absorbs
  geometry, but nothing absorbs flex.
- Aim the laser into the **X mirror**, which reflects onto the **Y mirror**
  (the kit's XY block comes pre-aligned), which points at the target area.
- Mount the camera right next to the galvo output aperture, facing the
  target area, ~1–3 m from the backdrop. The whole target area must be
  inside the camera frame.
- The calibration maps one flat plane — the system aims correctly for
  insects on/near the backdrop plane (the closed loop compensates small
  deviations).

---

## 6. Bring-up — test each subsystem alone

Run all of this from `~/laser_mosquito/8.Improved_tracker`.

### 6.1 DAC (multimeter on VOUTA/VOUTB)
```bash
python3 -c "from dac_mcp4922 import Mcp4922; d = Mcp4922(); d.write_xy(2048, 2048)"
```
Expect **≈ 2.5 V** on MCP4922 pins 14 and 10 (against GND). Then:
```bash
python3 -c "from dac_mcp4922 import Mcp4922; d = Mcp4922(); d.write_xy(0, 4095)"
```
Expect ≈ 0 V on pin 14 and ≈ 5 V on pin 10.

### 6.2 Op-amp stage
With the DAC at 2048/2048 (mid-scale), each op-amp output should read
**≈ 0 V**. At 0 and 4095 it should swing symmetrically negative/positive.
Adjust per the schematic until it does, *before* connecting the drivers.

### 6.3 Galvos
Connect the drivers, power the kit, and re-run the three commands above:
the mirrors should snap to center / one corner / the other corner.

### 6.4 Laser gate
Glasses on, backdrop in place:
```bash
python3 - <<'EOF'
import time
import Jetson.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setup(12, GPIO.OUT, initial=GPIO.HIGH)
print("laser ON for 3 s")
time.sleep(3)
GPIO.output(12, GPIO.LOW)
GPIO.cleanup()
EOF
```
A red dot must appear somewhere on the backdrop for 3 seconds.

---

## 7. Calibrate

Point the rig at the empty backdrop (nothing moving in view), then:
```bash
python3 calibrate.py --laser
```
It sweeps the mirrors over a 6×6 grid, finds the laser dot in the camera
image at each position, fits the pixel→DAC homography, and writes
`calibration.json`. You want most of the 36 points detected and a mean
reprojection error of a few tens of DAC steps.

If it reports `no dot found` everywhere: dim the room lights, and/or widen
`DOT_HSV_LOWER`/`DOT_HSV_UPPER` in `config.py` (lower the 230 brightness
threshold first).

Re-run this after *any* mechanical change. If the dot leaves the camera
frame at the sweep edges, narrow `CAL_DAC_X`/`CAL_DAC_Y` in `config.py`.

---

## 8. Run

Bench test first — laser stays off, watch the overlay (needs the monitor
connected, or `ssh -X`):
```bash
python3 track.py --display
```
Wave a small dark object on a stick in front of the backdrop: yellow circle
on it, green cross slightly ahead of its motion, `laser off` in the corner.
Quit with `q`.

The real thing — glasses on, scene clear of people and animals:
```bash
python3 track.py --arm --closed-loop
```
The laser fires only after 3 consecutive confirmed detections, never longer
than 0.5 s at a stretch, and shuts off on target loss and at exit. All of
those numbers are in `config.py` under "Safety".

Useful variants:
```bash
python3 track.py --arm --closed-loop --save-video session.mp4   # record evidence
python3 track.py --mode color --display                         # yellow-LED bench target
```

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `could not open camera source` / no preview | Ribbon seated? Contacts facing heatsink? Camera is a v2/IMX219? Test with `nvgstcapture-1.0`. |
| `ls /dev/spidev*` shows nothing | SPI not enabled — redo §4.4, reboot. |
| `PermissionError` on `/dev/spidev0.0` | udev rule + group from §4.4, or prefix `sudo`. |
| DAC outputs stuck at 0 V | Check CS/SCK/SDI pins (19/23/24), LDAC to GND, SHDN to VDD. |
| Mirrors move on the wrong axis / mirrored | Swap the two op-amp→driver leads, or swap channels A/B at the DAC outputs; re-run `calibrate.py --laser`. |
| Calibration finds < 8 points | Room too bright, dot too dim, or sweep leaves the frame — see §7. |
| Dot lags behind the insect | Raise `LEAD_FRAMES` in `config.py` (try 3–4). |
| False detections (shadows, curtains) | Raise `MOG2_THRESHOLD`, shrink `MAX_RADIUS_PX`, keep the backdrop static. |
| Laser never fires with `--arm` | It needs `CONFIRM_FRAMES` consecutive detections; check the `--display` overlay shows steady detection first. |

Every tunable mentioned above lives in `8.Improved_tracker/config.py`,
commented. The module internals are described in
`8.Improved_tracker/README.md`.

"""Central configuration for the improved tracker.

All hardware-specific numbers live here so the code never needs editing to
re-tune the rig. Positions are pixels, mirror commands are DAC steps (0-4095).
"""

# --- Camera -------------------------------------------------------------
# "jetson" builds the CSI pipeline below, an integer opens a USB webcam,
# a file path plays a recording (useful with --sim on a desktop PC).
CAMERA_SOURCE = "jetson"

JETSON_PIPELINE = (
    "nvarguscamerasrc ! video/x-raw(memory:NVMM), width=400, height=400, "
    "format=(string)NV12, framerate=(fraction)20/1 ! nvvidconv ! "
    "video/x-raw, format=(string)BGRx ! videoconvert ! "
    "video/x-raw, format=(string)BGR ! appsink drop=true max-buffers=1"
)

# --- Detection ----------------------------------------------------------
# "motion": background subtraction, best for insects in flight.
# "color":  HSV threshold, best for the yellow-LED bench target.
DETECTOR_MODE = "motion"

# HSV bounds for color mode (default: yellow LED).
COLOR_HSV_LOWER = (20, 80, 80)
COLOR_HSV_UPPER = (35, 255, 255)

# HSV bounds for spotting the laser dot itself (calibration + closed loop):
# very bright, mostly desaturated pixels.
DOT_HSV_LOWER = (0, 0, 230)
DOT_HSV_UPPER = (180, 80, 255)

MIN_RADIUS_PX = 1.5     # ignore blobs smaller than this
MAX_RADIUS_PX = 40.0    # ignore blobs larger than this (a hand, a shadow)
MORPH_ITERATIONS = 1    # erode/dilate applied to the detection mask; more than
                        # 1 iteration erases insect-sized blobs entirely

MOG2_HISTORY = 120      # frames of background memory for motion mode
MOG2_THRESHOLD = 24     # sensitivity (lower = more sensitive)

# --- Prediction ---------------------------------------------------------
LEAD_FRAMES = 2         # aim this many frames ahead of the last measurement
LOST_AFTER_FRAMES = 15  # forget the target after this many missed frames

# --- Pixel -> DAC mapping -------------------------------------------------
CALIBRATION_FILE = "calibration.json"
# Fallback used until calibrate.py has been run: the original hand-fitted map.
LINEAR_X = (10.0, 246.0)   # dac_a = 10.0 * pixel_x + 246
LINEAR_Y = (6.0, -68.0)    # dac_b =  6.0 * pixel_y - 68

# --- Calibration sweep ----------------------------------------------------
CAL_DAC_X = (300, 3800, 6)   # min, max, steps for channel A during calibrate.py
CAL_DAC_Y = (300, 3800, 6)   # min, max, steps for channel B
CAL_SETTLE_S = 0.15          # wait for the mirrors to settle before sampling

# --- SPI / DAC ------------------------------------------------------------
SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED_HZ = 1000000

# --- Closed loop -----------------------------------------------------------
CLOSED_LOOP_GAIN = 0.4        # fraction of the dot->target error corrected per frame
CLOSED_LOOP_MAX_OFFSET = 500  # DAC steps; bounds the accumulated correction

# --- Safety ----------------------------------------------------------------
# The laser is driven through a GPIO pin and stays OFF unless the tracker is
# armed (--arm) AND a target has been continuously confirmed. See safety.py.
LASER_GPIO_PIN = 12     # board pin number for Jetson.GPIO
CONFIRM_FRAMES = 3      # consecutive detections required before switching on
MAX_ON_SECONDS = 0.5    # watchdog: never keep the laser on longer than this
COOLDOWN_SECONDS = 0.3  # forced off-time after each on-period

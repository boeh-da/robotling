# ---------------------------------------------------------------------
# hexbug_config.py
# Configuration file for HexBug robotling
#
# *** Orange HexBug ***
# ---------------------------------------------------------------------
# Allow to use robotling GUI running on a PC to use the same
# configuration file as the MicroPython code
try:
  from micropython import const
  from robotling_board import *
except ModuleNotFoundError:
  const = lambda x : x
  DIO0  = None

# ---------------------------------------------------------------------
# USER SECTION
# ==>
#
# Tilt-sensing
PIRO_MAX_ANGLE   = const(25)   # Maximal tilt (i.e. pitch/roll) allowed
                               # .. before robot responds

# Obstacle/cliff detection
#
# Scan positions as list of head turn durations in [ms] and as a list
# of approx. angular positions ([°]).
IR_SCAN_POS      = [-300, 300, 300, -300]
IR_SCAN_POS_DEG  = [-35, 0, 35, 0]
IR_SCAN_BIAS_F   = -0.0        # To account for bias in turning motor:
                               # .. pos > 0 --> pos*(1+IR_SCAN_BIAS_F)
                               # .. pos < 0 --> pos*(1-IR_SCAN_BIAS_F)
IR_SCAN_CONE_DEG = const(30)   # Angular width of scan cone (only for GUI)
IR_SCAN_SENSOR   = const(0)    # 0=GP2Y0A41SK0F (4-30 cm)
                               # 1=GP2Y0AF15X (1.5-15 cm)
AI_CH_IR_RANGING = const(0)    # Analog-In channel for IR distance sensor
DIST_OBST_CM     = const(9)    # Lower distances are considered obstacles
DIST_CLIFF_CM    = const(25)   # Farer distances are considered cliffs
DIST_SMOOTH      = const(0)

# Light intensity measurements
AI_CH_LIGHT_R    = const(3)
AI_CH_LIGHT_L    = const(2)

# Servo settings
DO_CH_DIST_SERVO = DIO0        # Digital-Out channel for distance sensor servo
MIN_DIST_SERVO   = const(45)   # Limits of servo that holds the arm with the
MAX_DIST_SERVO   = const(-45)  # .. IR distance sensor in [°]
MIN_US_SERVO     = const(1172) # Minimum timing of servo in [us]
MAX_US_SERVO     = const(2033) # Maximum timing of servo in [us]
SCAN_DIST_SERVO  = const(-25)  # Angle of IR distance sensor arm

# Period of timer that keeps sensor values updated, the NeoPixel pulsing,
# and checks for tilt (in [ms])
TM_PERIOD        = const(50)

# Default motor speeds ..
SPEED_WALK       = const(-55)  # -70 .. for walking forwards
SPEED_TURN       = const(35)   # +30 .. for turning head when changing direction
SPEED_SCAN       = const(40)   # .. for turning head when scanning
SPEED_TURN_DELAY = const(500)  # Duration for turning in new direction
SPEED_BACK_DELAY = const(600)  # Duration for backing up (cliff)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Options, depending on board and sensor complement
USE_LOAD_SENSING = const(0)    # Use AI channels #6,7 for load-sensing (> v1.1)
USE_POWER_SHD    = const(0)    # Use ENAB_5V (voltage regulator off)   (> v1.1)
SEND_TELEMETRY   = const(0)    # only w/ESP32

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# "Behaviours" and their parameters
#
# Look around
DO_LOOK_AROUND   = const(30)   # =probabilty ([‰]) to activate behaviour

# Take a nap
# If activated, the roboter falls asleep from time to time. When this happens,
# the processor and all on-board electronics go to deep sleep or are turned
# off. The roboter wakes up after a random number of seconds.
# (only with ESP32, needs `USE_POWER_SHD` enabled)
DO_TAKE_NAPS     = const(0)    # =probability, [‰]to activate behaviour
NAP_FROM_S       = const(5)    # range of random numbers to sleep ...
NAP_TO_S         = const(20)   # ... in [s]

# Find light source
# Uses a photodiode pair to home in on a light source. Give pins that connect
# to the photodiodes in `AI_CH_LIGHT_R` and `AI_CH_LIGHT_L` (above)
# (obviously, does not work together `DO_WALK_STRAIGHT`)
DO_FIND_LIGHT    = const(0)    # 1=enabled

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# "Behaviors", not yet fully implemented/tested
#
# Use the compass to walk straight ahead
DO_WALK_STRAIGHT = const(0)
HEAD_ADJUST_FACT = const(-1)   #
HEAD_ADJUST_THR  = const(5)    # [°]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Additional devices plugged into the robotling board
# Possible devices:
# - Compass modules     : "compass_cmps12", "lsm303", "lsm9ds0"
# - ToF distance sensor : "vl6180x"
# - Display             : "dotstar_feather"
# - WLAN                : "wlan"
# - Cameras             : "amg88xx"
MORE_DEVICES     = ["lsm303"]

# <==
# ----------------------------------------------------------------------------
# FROM HERE ON MAKE CHANGES ONLY IF YOU KNOW WHAT YOU'RE DOING
# (These definitions are also used by the GUI that shows MQTT telemetry)
# ==>
# ----------------------------------------------------------------------------
# Robot state-related definitions
STATE_IDLE       = const(0)
STATE_WALKING    = const(1)
STATE_LOOKING    = const(2)
STATE_ON_HOLD    = const(3)
STATE_OBSTACLE   = const(4)
STATE_CLIFF      = const(5)
STATE_WAKING_UP  = const(6)

# MQTT releated definitions
#
# Message keys
KEY_RAW          = "raw"
KEY_SENSOR       = "sensor"
KEY_COMPASS      = "compass"
KEY_HEADING      = "heading_deg"
KEY_PITCH        = "pitch_deg"
KEY_ROLL         = "roll_deg"
KEY_PHOTODIODE   = "photodiode"
KEY_INTENSITY    = "intensity"
KEY_DISTANCE     = "distance_cm"
KEY_POWER        = "power"
KEY_BATTERY      = "battery_V"
KEY_STATE        = "state"
KEY_MOTORLOAD    = "motor_load"
KEY_STATISTICS   = "stats"
KEY_TURNS        = "turns"
KEY_TIMESTAMP    = "timestamp_s"
KEY_CAM_IR       = "camera_IR"
KEY_IMAGE        = "image"
KEY_SIZE         = "size"
KEY_DEBUG        = "debug"

# Limits for telemetry data
LIPO_MAX_V       = 4.2
LIPO_MIN_V       = 3.5
V_MAX            = 5.0
LOAD_MAX         = 1500
LOAD_ARR_LEN     = 200
LOAD_ARR_BOX     = 1
LIGHTDIF_ARR_BOX = 1

# Experimental parameters
MEM_INC          = 1
MEM_DEC          = 0.25

# <==
# ---------------------------------------------------------------------

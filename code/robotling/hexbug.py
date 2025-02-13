# ----------------------------------------------------------------------------
# hexbug.py
# Definition of the class `Hexbug`, derived from `Robotling`
#
# Example code for a "hijacked" HexBug. Uses the IR distance sensor to
# avoid obstacles and cliffs simply by checking if the distance measured is
# within the range expected for the surface in front of the robot (~ 6 cms).
# If a shorter or farer distance is measured, the robot turns in a random
# direction until it detects the ground again. To cover the ground in front
# of the robot, the IR sensor is moved back and forth sideways and the
# average of the measured distances is used for making the obstacle/ground/
# cliff decision.
# In parallel, all motors are stopped and the NeoPixel turns from green to
# violet dif robot is tilted (e.g. falls on the side); for this, pitch/roll
# provided by the compass (time-filtered) are checked.
#
# The MIT License (MIT)
# Copyright (c) 2018-2019 Thomas Euler
# 2018-09-13, first release.
# 2018-10-29, use pitch/roll to check if robot is tilted.
# 2018-11-03, some cleaning up and commenting of the code
# 2018-11-28, re-organised directory structure, collecting all access to
#             hardware specifics to a set of "adapter classes" in `platform`,
# 2018-12-22, reorganised into a module with the class `Hexbug` and a simpler
#             main program file (`main.py`). All hardware-related settings
#             moved to separate file (`hexbug_config-py`)
# 2019-01-01, vl6180x time-of-flight distance sensor support added
# 2019-04-07, added new "behaviour" (take a nap)
# 2019-05-06, now uses `getHeading3D` instead of `getPitchRoll` to determine
#             if the robot is tilted; the additional compass information
#             (heading) is saved for later use.
# 2019-07-13, added new "behaviour" (find light)
#             `hexbug_config.py` reorganised and cleaned up
# 2019-07-24, added the ability to send telemetry via MQTT (ESP32 only);
#             added a bias factor (`IR_SCAN_BIAS_F`) to the configuration
#             file which allows accounting for a direction bias in the turning
#             motor and let the robot walk "more straight";
#             changed the scan scheme slightly to "left-center-right-center"
#             instead of "left-right-center"
# 2019-08-03, new type of Sharp sensor added (GP2Y0AF15X, 1.5-15 cm)
# 2019-08-19, now an array of IR distance sensors is possible; in this case,
#             the robot's head is not scanning sideways.
#
# ----------------------------------------------------------------------------
import array
import random
from micropython import const
import robotling_board as rb
import driver.drv8835 as drv8835
from robotling import Robotling
from robotling_board_version import BOARD_VER
from motors.dc_motor import DCMotor
from motors.servo import Servo
from misc.helpers import TemporalFilter
from hexbug_config import *

from platform.platform import platform
if platform.ID == platform.ENV_ESP32_UPY:
  import time
  if SEND_TELEMETRY:
    mqttd = dict()
else:
  import platform.m4ex.time as time

# ----------------------------------------------------------------------------
# NeoPixel colors (r,g,b) for the different states
STATE_COLORS     = bytearray((
                   10,10,10,   # STATE_IDLE
                   20,70,0,    # STATE_WALKING
                   40,30,0,    # STATE_LOOKING
                   20,00,50,   # STATE_ON_HOLD
                   90,30,0,    # STATE_OBSTACLE
                   90,0,30,    # STATE_CLIFF
                   10,60,60))  # STATE_WAKING_UP

# ----------------------------------------------------------------------------
class HexBug(Robotling):
  """Hijacked-HexBug class"""

  def __init__(self, devices):
    super().__init__(devices)

    # Check if VL6180X time-of-flight ranging sensor is present, if not, add
    # analog IR ranging sensor (expected to be connected to A/D channel #0)
    self.RangingSensor = []
    try:
      self.RangingSensor.append(self._VL6180X)
      if not self.RangingSensor[0].isReady:
        raise AttributeError
    except AttributeError:
      if IR_SCAN_SENSOR == 1:
        # New, smaller sensor GP2Y0AF15X (1.5-15 cm)
        from sensors.sharp_ir_ranging import GP2Y0AF15X as GP2Y
      else:
        # Default to GP2Y0A41SK0F (4-30 cm)
        from sensors.sharp_ir_ranging import GP2Y0A41SK0F as GP2Y

      # For compatibility: if `AI_CH_IR_RANGING` is a constant then a
      # single IR sensor is defined, meaning that the robot's head scans
      # as usual. Otherwise, a list of ranging sensors is initialized.
      # In this case, it is assumed that an array of IR sensors is attached
      # and scanning is not needed (new).
      self.RangingSensor = []
      isList = type(AI_CH_IR_RANGING) is list
      AInCh = AI_CH_IR_RANGING if isList else [AI_CH_IR_RANGING]
      for pin in AInCh:
        self.RangingSensor.append(GP2Y(self._MCP3208, pin))
        self._MCP3208.channelMask |= 0x01 << pin
      self.nRangingSensor = len(self.RangingSensor)
    print("Using {0}x {1} as ranging sensor(s)"
          .format(self.nRangingSensor, self.RangingSensor[0].name))

    # Define scan positions to cover the ground before the robot. Currently,
    # the time the motor is running (in [s]) is used to define angular
    # position
    self._scanPos  = IR_SCAN_POS
    self._iScanPos = [0] *len(IR_SCAN_POS)
    self.onTrouble = False

    # Apply bias to scan position (times) to account for a directon bias
    # in the turning motor
    for iPos, pos in enumerate(IR_SCAN_POS):
      f = (1. +IR_SCAN_BIAS_F) if pos > 0 else (1. -IR_SCAN_BIAS_F)
      self._scanPos[iPos] *= f

    # Determine the number of different scan positions to dimension
    # the distance data array
    l = []
    for iPos, pos in enumerate(IR_SCAN_POS_DEG):
      if iPos == 0 or not pos in l:
        l.append(pos)
        self._iScanPos[iPos] = iPos
      else:
        for j in range(len(l)):
          if l[j] == pos:
            self._iScanPos[iPos] = j
            break
    # Generate array for distance data and filters for smoothing distance
    # readings, if requested
    self._distData = array.array("i", [0] *len(l))
    if DIST_SMOOTH >= 2:
      self._distDataFilters = []
      for iPos in range(len(l)):
        self._distDataFilters.append(TemporalFilter(DIST_SMOOTH))

    # Add the servo that moves the ranging sensor up and down
    self.ServoRangingSensor = Servo(DO_CH_DIST_SERVO,
                                    us_range=[MIN_US_SERVO, MAX_US_SERVO],
                                    ang_range=[MIN_DIST_SERVO, MAX_DIST_SERVO])

    # Add motors
    self.MotorWalk = DCMotor(self._motorDriver, drv8835.MOTOR_A)
    self.MotorTurn = DCMotor(self._motorDriver, drv8835.MOTOR_B)
    self._turnBias = 0
    self.turnStats = 0

    # If load sensing is enabled and supported by the board, create filters
    # to smooth the load readings from the motors and change analog sensor
    # update mask accordingly
    if BOARD_VER >= 120 and USE_LOAD_SENSING:
      self.walkLoadFilter = TemporalFilter(5)
      self.turnLoadFilter = TemporalFilter(5)
      self._loadData      = array.array("i", [0]*2)
      self._MCP3208.channelMask |= 0xC0

    # If to use compass, initialize target heading
    if DO_WALK_STRAIGHT and not DO_FIND_LIGHT:
      self.cpsTargetHead = self.Compass.getHeading()

    # If "find light" behaviour is activated, activate the AI channels to which
    # the photodiodes are connected and create a filter to smooth difference
    # in light intensity readings (`lightDiff`)
    self.lightDiff = 0
    if DO_FIND_LIGHT:
      self._MCP3208.channelMask |= 1 << AI_CH_LIGHT_R | 1 << AI_CH_LIGHT_L
      self.LightDiffFilter = TemporalFilter(5, "i")

    # Flag that indicates when the robot should stop moving
    self.onHold = False

    if SEND_TELEMETRY and platform.ID == platform.ENV_ESP32_UPY:
      from remote.telemetry import Telemetry
      self.onboardLED.on()
      self._t = Telemetry(self.ID)
      self._t.connect()
      self.onboardLED.off()

    # Create filters for smoothing the pitch and roll readings
    self.PitchFilter = TemporalFilter(8)
    self.RollFilter  = TemporalFilter(8)

    self.tTemp = time.ticks_us()
    self.debug = []

    # Starting state
    self.state = STATE_IDLE

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def housekeeper(self, info=None):
    """ Does the hexbug-related housekeeping:
        - Stop motors if robot is tilted (e.g. falls on the side) by checking
          pitch/roll provided by the compass
        - Changes also color of NeoPixel depending on the robot's state
    """
    aid = self._MCP3208.data

    # Check if robot is tilted ...
    ehpr = self.Compass.getHeading3D()
    pAv  = self.PitchFilter.mean(ehpr[2])
    rAv  = self.RollFilter.mean(ehpr[3])
    self.onHold = (abs(pAv) > PIRO_MAX_ANGLE) or (abs(rAv) > PIRO_MAX_ANGLE)
    if self.onHold:
      # Stop motors
      self.MotorTurn.speed = 0
      self.MotorWalk.speed = 0
      self.ServoRangingSensor.off()
      self.state = STATE_ON_HOLD

    # Save heading
    self.currHead = ehpr[1]

    if USE_LOAD_SENSING:
      self._loadData[0] = int(self.walkLoadFilter.mean(self._MCP3208.data[6]))
      self._loadData[1] = int(self.turnLoadFilter.mean(self._MCP3208.data[7]))

    if DO_FIND_LIGHT:
      dL = aid[AI_CH_LIGHT_R] -aid[AI_CH_LIGHT_L]
      self.lightDiff = int(self.LightDiffFilter.mean(dL))

    if SEND_TELEMETRY and self._t._isReady:
      # Collect the data ...
      mqttd[KEY_STATE] = self.state
      mqttd[KEY_TIMESTAMP] = time.ticks_ms() /1000.
      mqttd[KEY_POWER] = {KEY_BATTERY: self.Battery_V}
      if USE_LOAD_SENSING:
        mqttd[KEY_POWER].update({KEY_MOTORLOAD: list(self._loadData)})
      mqttd[KEY_SENSOR] = {KEY_DISTANCE: list(self._distData)}
      _temp = {KEY_HEADING: ehpr[1], KEY_PITCH: ehpr[2], KEY_ROLL: ehpr[3]}
      mqttd[KEY_SENSOR].update({KEY_COMPASS: _temp})
      if DO_FIND_LIGHT:
        _temp = {KEY_INTENSITY: [aid[AI_CH_LIGHT_L], aid[AI_CH_LIGHT_R]]}
        mqttd[KEY_SENSOR].update({KEY_PHOTODIODE: _temp})
      if self._AMG88XX:
        mqttd[KEY_CAM_IR] = {KEY_SIZE: (8,8)}
        mqttd[KEY_CAM_IR].update({KEY_IMAGE: list(self._AMG88XX.pixels_64x1)})
      if len(self.debug) > 0:
        mqttd[KEY_DEBUG] = self.debug
        self.debug = []
      # ... and publish
      self._t.publishDict(KEY_RAW, mqttd)

    # Change NeoPixel according to state
    i = self.state *3
    self.startPulseNeoPixel(STATE_COLORS[i:i+3])

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def onLoopStart(self):
    """ To measure the performance of the loops, call this function once at
        the beginning of the main loop
    """
    pass

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def _nextTurnDir(self, lastTurnDir):
    if not lastTurnDir == 0:
      # Just turned but not sucessful, therefore remember that
      # direction
      self.turnStats += MEM_INC if lastTurnDir > 0 else -MEM_INC
    if self.turnStats == 0:
      return [-1,1][random.randint(0,1)]
    else:
      return 1 if self.turnStats > 0 else -1

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def scanForObstacleOrCliff(self):
    """ Acquires distance data at the scan positions, currently given in motor
        run time (in [s]). Returns -1=obstacle, 1=cliff, and 0=none.
    """
    bias = 0
    if DO_FIND_LIGHT:
      bias = -self.lightDiff

    elif DO_WALK_STRAIGHT:
      # Using the compass, determine current offset from target heading and
      # set a new bias (in [ms]) by which the head position is corrected. This
      # is done by biasing the head direction after scanning for obstacles
      dh = self.currHead -self.cpsTargetHead
      tb = dh *HEAD_ADJUST_FACT if abs(dh) > HEAD_ADJUST_THR else 0

    o = False
    c = False
    l = len(self._scanPos) -1
    if self.nRangingSensor == 1:
      # Only one ranging sensor, therefore scan the head back and forth
      # (as determined in `hexbug_config.py`) to cover the ground in front
      # of the robot
      for iPos, Pos in enumerate(self._scanPos):
        # Turn head into scan position; in the first turn account for a
        # turning bias resulting from the find light behaviour
        b = 0 if iPos < l else bias
        self.MotorTurn.speed = SPEED_SCAN *(-1,1)[Pos < 0]
        self.spin_ms(abs(Pos) +b)
        self.MotorTurn.speed = 0
        # Measure distance for this position ...
        d = int(self.RangingSensor[0].range_cm)
        self._distData[self._iScanPos[iPos]] = d
        # ... check if distance within the danger-free range
        o = o or (d < DIST_OBST_CM)
        c = c or (d > DIST_CLIFF_CM)
    else:
      # Several ranging sensors installed in an array, therefore head scans
      # are not needed
      for iPos in range(self.nRangingSensor):
        # Read distance from this ranging sensor ...
        d = int(self.RangingSensor[iPos].range_cm)
        if DIST_SMOOTH >= 2:
          d = int(self._distDataFilters[iPos].mean(d))
        self._distData[iPos] = d
        # ... check if distance within the danger-free range
        o = o or (d < DIST_OBST_CM)
        c = c or (d > DIST_CLIFF_CM)

      # Turn the head slighly to acount for (1) any bias that keeps the
      # robot from walking straight and (2) any turning bias resulting from
      # the find light behaviour
      self.MotorTurn.speed = SPEED_SCAN *(-1,1)[IR_SCAN_BIAS_F < 0]
      td = abs(IR_SCAN_BIAS_F *200) +bias
      self.spin_ms(td)
      self.MotorTurn.speed = 0
      # Make sure that the robot waits a minimum duration before returning
      # to the main loop
      sd = SPEED_BACK_DELAY//3 -td
      if sd > 0:
        self.spin_ms(sd)

    # Remember turning bias and return result
    self._turnBias = bias
    return 1 if c else -1 if o else 0

  def lookAround(self):
    """ Make an appearance of "looking around"
    """
    # Stop all motors and change state
    self.MotorWalk.speed = 0
    self.MotorTurn.speed = 0
    prevState = self.state
    self.state = STATE_LOOKING
    maxPit = max(MAX_DIST_SERVO, MIN_DIST_SERVO)

    # Move head and IR distance sensor at random, as if looking around
    nSacc = random.randint(4, 10)
    yaw = 0
    pit = SCAN_DIST_SERVO
    try:
      for i in range(nSacc):
        if self.onHold:
          break
        dYaw = random.randint(-800, 800)
        yaw += dYaw
        dir  = -1 if dYaw < 0 else 1
        pit += random.randint(-10,15)
        pit  = min(max(0, pit), maxPit)
        self.ServoRangingSensor.angle = pit
        self.MotorTurn.speed = SPEED_TURN *dir
        self.spin_ms(abs(dYaw))
        self.MotorTurn.speed = 0
        self.spin_ms(random.randint(0, 500))
    finally:
      # Stop head movement, if any, move the IR sensor back into scan
      # position and change back state
      self.MotorTurn.speed = 0
      self.ServoRangingSensor.angle = SCAN_DIST_SERVO
      self.state = prevState

      # If compass is used, set new target heading
      if DO_WALK_STRAIGHT and not DO_FIND_LIGHT:
        self._targetHead = self.Compass.getHeading()

  def nap(self):
    """ Take a nap
    """
    # Remember state, switch off motors and move sensor arm into neutral
    prevState = self.state
    self.state = STATE_WAKING_UP
    self.housekeeper()
    self.MotorWalk.speed = 0
    self.MotorTurn.speed = 0
    self.ServoRangingSensor.angle = 0

    # Dim the NeoPixel
    for i in range(10, -1, -1):
      self.dimNeoPixel(i/10.0)
      self.spin_ms(250)

    # "Drop" sensor arm
    for p in range(0, SCAN_DIST_SERVO, -1):
      self.ServoRangingSensor.angle = p
      self.spin_ms(10)

    # Flash NeoPixel ...
    self.dimNeoPixel(1.0)
    self.spin_ms(100)
    self.dimNeoPixel(0.0)

    # ... and enter sleep mode for a random number of seconds
    self.sleepLightly(random.randint(NAP_FROM_S, NAP_TO_S))

    # Wake up, resume previous state and move sensor arm into scan position
    self.state = prevState
    self.ServoRangingSensor.angle = SCAN_DIST_SERVO
    self.housekeeper()

    # Bring up NeoPixel again
    for i in range(0, 11):
      self.dimNeoPixel(i/10.0)
      self.spin_ms(250)

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def getDist(self, angle=0, trials=1, channel=0):
    """ Test function to determine the relevant IR distances.
        Moves IR ranging sensor to "angle" and measures/prints distance
        "trial" times.
    """
    self.ServoRangingSensor.angle = angle
    self.spin_ms(200)
    for i in range(trials):
      self.update()
      s = ""
      for ir in self.RangingSensor:
        s += "{0} ".format(ir.range_cm)
      print(s)
      self.spin_ms(0 if trials <= 1 else 250)

# ----------------------------------------------------------------------------

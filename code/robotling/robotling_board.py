# ----------------------------------------------------------------------------
# robotling_board.py
# Global definitions for robotling board.
#
# The MIT License (MIT)
# Copyright (c) 2018 Thomas Euler
# 2018-09-13, v1
# 2018-12-22, v1.1 - pins for M4 feather express added
# ----------------------------------------------------------------------------
from micropython import const
from robotling_board_version import BOARD_VER
from platform.platform import platform

__version__ = "0.1.1.0"

SPI_FRQ   = const(4000000)
I2C_FRQ   = const(400000)

# I2C devices, maximal clock frequencies:
# AMG88XX (Infrared Array Sensor “Grid-EYE”)  <= 400 KHz
# VL6180X (Time of Flight distance sensor)    <= 400 KHz
# CMPS12  (Compass)                           <= 400 KHz
# LSM303  (Compass)                           100, 400 KHz
# LSM9DS0 (Compass)                           100, 400 KHz

# ----------------------------------------------------------------------------
# Robotling board connections/pins
#
if platform.ID == platform.ENV_ESP32_UPY:
  import platform.huzzah32.board as board

  SCK     = board.SCK
  MOSI    = board.MOSI
  MISO    = board.MISO
  CS_ADC  = board.D4

  SCL     = board.SCL
  SDA     = board.SDA

  A_ENAB  = board.D26
  A_PHASE = board.D14
  B_ENAB  = board.D21
  B_PHASE = board.D25

  ENAB_5V = board.D16
  RED_LED = board.LED

  ADC_BAT = board.BAT

  if BOARD_VER == 100:
    NEOPIX  = board.D15      # Connect Neopixel to DIO #0
    DIO0    = board.D27
    DIO1    = board.LED
    DIO2    = board.D33
    DIO3    = board.D15

  elif BOARD_VER >= 110:
    NEOPIX  = board.D15      # -> Neopixel connector
    DIO0    = board.D27
    DIO1    = board.LED
    DIO2    = board.D33
    DIO3    = board.D32


elif platform.ID == platform.ENV_CPY_SAM51:
  import board

  SCK     = board.SCK
  MOSI    = board.MOSI
  MISO    = board.MISO
  CS_ADC  = board.A5

  SCL     = board.SCL
  SDA     = board.SDA

  A_ENAB  = board.A3
  # The M4 express feather does not allow PWM with pin A0, therefore to use
  # robotling boards <= v1.2 requires to solder a bridge between the pins A0
  # and A3.
  A_PHASE = board.D5
  B_ENAB  = board.D4
  B_PHASE = board.A1

  ENAB_5V = board.RX
  RED_LED = board.D13

  ADC_BAT = board.VOLTAGE_MONITOR

  if BOARD_VER == 100:
    '''
    NEOPIX  = board.D9  #D15 # Connect Neopixel to DIO #0
    '''
    NEOPIX  = board.NEOPIXEL
    DIO0    = board.D11
    DIO1    = board.D13
    DIO2    = board.D10
    DIO3    = board.D9

  elif BOARD_VER >= 110:
    '''
    NEOPIX  = board.D9  #D15 # -> Neopixel connector
    '''
    NEOPIX  = board.NEOPIXEL
    DIO0    = board.D11
    DIO1    = board.D13
    DIO2    = board.D10
    DIO3    = board.D6

# ----------------------------------------------------------------------------
# The battery is connected to the pin via a voltage divider (1/2), and thus
# an effective voltage range of up to 7.8V (ATTN_11DB, 3.9V); the resolution
# is 12 bit (WITDH_12BIT, 4096):
# V = adc /4096 *2 *3.9 *0.901919 = 0.001717522
# (x2 because of voltage divider, x3.9 for selected range (ADC.ATTN_11DB)
#  and x0.901919 as measured correction factor)
BAT_N_PER_V   = 0.001717522

# ----------------------------------------------------------------------------
# Error codes
#
RBL_OK                      = const(0)
RBL_ERR_DEVICE_NOT_READY    = const(-1)
RBL_ERR_SPI                 = const(-2)
# ...

# ----------------------------------------------------------------------------

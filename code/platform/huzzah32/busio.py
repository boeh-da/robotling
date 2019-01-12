# ----------------------------------------------------------------------------
# busio.py
#
# Basic bus support
# (for standard micropython, ESP32, as HUZZAH32 feather)
#
# The MIT License (MIT)
# Copyright (c) 2018 Thomas Euler
# 2018-09-21, v1
# ----------------------------------------------------------------------------
from micropython import const
from machine import SPI, Pin, I2C

__version__ = "0.1.0.0"

# ----------------------------------------------------------------------------
class SPIBus(object):
  """SPI bus access."""

  def __init__(self, freq, sc, mo, mi=None, spidev=2):
    self._spi = SPI(spidev)
    if mi == None:
      self._spi.init(baudrate=freq, sck=Pin(sc), mosi=Pin(mo))
    else:
      self._spi.init(baudrate=freq, sck=Pin(sc), mosi=Pin(mo), miso=Pin(mi))

  def deinit(self):
    self._spi.deinit()

  @property
  def bus(self):
    return self._spi

  def write_readinto(self, wbuf, rbuf):
    self._spi.write_readinto(wbuf, rbuf)

  def write(self, wbuf):
    self._spi.write(wbuf)

# ----------------------------------------------------------------------------
class I2CBus(object):
  """I2C bus access."""

  def __init__(self, _freq, scl, sda):
    self._i2cDevList = []
    self._i2c = I2C(scl=Pin(scl), sda=Pin(sda), freq=_freq)
    self._i2cDevList = self._i2c.scan()

  def deinit(self):
    self._i2c = None

  @property
  def bus(self):
    return self._i2c

  @property
  def deviceAddrList(self):
    return self._i2cDevList

  def write(self, buf):
    self._i2c.write(buf)

  def writeto(self, addr, buf, stop_=True):
    self._i2c.writeto(addr, buf, stop_)

  def readinto(self, buf):
    self._i2c.readinto(buf)

  def readfrom_into(self, addr, buf):
    self._i2c.readfrom_into(addr, buf)

# ----------------------------------------------------------------------------

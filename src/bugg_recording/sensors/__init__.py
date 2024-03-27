# Import individual sensor class files into the sensor module namespace
# This does need to be edited as classes are added
from .sensorbase import SensorBase
from .i2smic import I2SMic
from .externalmic import ExternalMic
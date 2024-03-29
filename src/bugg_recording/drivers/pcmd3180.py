import logging
from smbus2 import SMBus
import time
import RPi.GPIO as GPIO

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SHDNZ = 0

I2C_ADDRESS = 0x4c

class PCMD3180:
    def __init__(self):
        self.address = I2C_ADDRESS
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(SHDNZ, GPIO.OUT)
        self.power_off()

    def power_on(self):
        GPIO.output(SHDNZ, GPIO.HIGH)
        time.sleep(0.5)

    def power_off(self):
        GPIO.output(SHDNZ, GPIO.LOW)
        time.sleep(0.1)

    def reset(self):
        self.power_off()
        self.power_on()

    def write_register(self, reg, data):
        i2c = SMBus(1)
        try:
            i2c.write_byte_data(self.address, reg, data)
        except Exception as e:
            logger.error("Failed to write to register %s: %s", reg, e)
        i2c.close()

    def read_register(self, reg):
        i2c = SMBus(1)
        try:
            data = i2c.read_byte_data(self.address, reg)
        except Exception as e:
            logger.error("Failed to read from register %s: %s", reg, e)
            data = None
        i2c.close()
        return data 

    def send_configuration(self):
        logger.info("Sending configuration to PCMD3180")
        config_data = {
            0x02: 0x81,
            0x3C: 0x40,
            0x41: 0x40,
            0x46: 0x40,
            0x4b: 0x40,
            0x22: 0x41,
            0x23: 0x41,
            0x24: 0x41,
            0x25: 0x41,
            0x2B: 0x45,
            0x2C: 0x67,
            0x73: 0xFF,
            0x74: 0xFF,
            0x75: 0x60,
            0x3e: 0xff, # Max volume (27dB)
            0x07: 0x80, # LJ format, 16 bit
        }
        for reg, data in config_data.items():
            self.write_register(reg, data)
        logger.info("Configuration sent.")


import RPi.GPIO as GPIO
import spidev

EXT_MIC_EN = 12

class Soundcard:
    """ Provides controls for the soundcard """
    PHANTOM_OFF = 0
    PHANTOM_PIP = 1
    PHANTOM_3V3 = 2
    PHANTOM_P48 = 4

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(EXT_MIC_EN, GPIO.OUT)
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.gain = 0
        self.gain_mode = 0
        self.gpo_mode = 0
        self.phantom_mode = self.PHANTOM_OFF

    def enable(self):
        """ Turn on the soundcard power rails"""
        GPIO.output(EXT_MIC_EN, 1)

    def disable(self):
        """ Turn off the soundcard power rails"""
        GPIO.output(EXT_MIC_EN, 0)

    def write_state(self):
        """ Write the current state to the soundcard """
        tx = [0, 0]
        tx[0] |= self.gain
        tx[1] |= self.gpo_mode << 5
        tx[1] |= self.gain_mode << 4
        tx[1] |= self.phantom_mode

        self.spi.xfer(tx)

    def set_gain(self, gain):
        """ Set the gain of the soundcard """
        if gain < 0 or gain > 31:
            raise ValueError("Gain must be between 0 and 31")

        self.gain = gain
        self.write_state()
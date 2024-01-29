import RPi.GPIO as GPIO

EXT_MIC_EN = 12

class Soundcard:
    """ Provides controls for the soundcard """

    def __init__(self, name):
        self.name = name
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(EXT_MIC_EN, GPIO.OUT)

    def enable(self):
        """ Turn on the soundcard power rails"""
        GPIO.output(EXT_MIC_EN, 1)

    def disable(self):
        """ Turn off the soundcard power rails"""
        GPIO.output(EXT_MIC_EN, 0)
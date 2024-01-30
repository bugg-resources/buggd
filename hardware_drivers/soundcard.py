import RPi.GPIO as GPIO
import spidev

EXT_MIC_EN = 12

class Soundcard:
    """ Provides controls for the soundcard """

    # Phantom power modes
    NONE = "NONE"
    PIP = "PIP"     # Plug In Power
    P3V3 = "P3V3"   # 3.3V on M12 pin 4
    P48 = "P48"     # 48V

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False) # Squash warning if the pin is already in use
        GPIO.setup(EXT_MIC_EN, GPIO.OUT)
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.gain = 0
        self.zc_gain = 1    # Enable zero-crossing gain control by default
        self.zc_gpo = 1     # Enable zero-crossing phantom switching by default
        self.phantom_mode = 0

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
        tx[1] |= self.zc_gpo << 5
        tx[1] |= self.zc_gain << 4
        tx[1] |= self.phantom_mode

        self.spi.xfer(tx)

    def set_gain(self, gain):
        """ Set the gain of the soundcard """
        if gain < 0 or gain > 20:
            raise ValueError("Gain must be between 0 and 20")

        self.gain = gain
        self.write_state()

    def set_phantom(self, mode):
        """ Set the phantom power mode """
        match mode:
            case self.NONE:
                self.phantom_mode = 0
            case self.PIP:
                self.phantom_mode = 1
            case self.P3V3:
                self.phantom_mode = 2
            case self.P48:
                self.phantom_mode = 4
            case _:
                raise ValueError("Invalid phantom mode")
        self.write_state()
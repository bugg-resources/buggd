""" Provides power, phantom power, and gain controls for the soundcard """

import RPi.GPIO as GPIO
import spidev
import logging
from .lock import Lock
import os
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

EXT_MIC_EN = 12

LOCK_FILE = "/tmp/soundcard.lock"
STATE_FILE = "/tmp/soundcard_state.json"

class Soundcard:
    """ Provides controls for the soundcard """

    # Phantom power modes
    NONE = "NONE"
    PIP = "PIP"     # Plug In Power
    P3V3 = "P3V3"   # 3.3V on M12 pin 4
    P48 = "P48"     # 48V

    def __init__(self, lock_file_path=LOCK_FILE):
        """ Attempt to acquire the lock and initialise the GPIO """
        try:
            self.lock = Lock(lock_file_path)
        except RuntimeError as e:
            logger.critical(e)
            self.result = False
            raise

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False) # Squash warning if the pin is already in use
        GPIO.setup(EXT_MIC_EN, GPIO.OUT)
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 5_000_000

        self.gain = 0
        self.zc_gain = 1    # Enable zero-crossing gain control by default
        self.zc_gpo = 1     # Enable zero-crossing phantom switching by default
        self.phantom_mode = 0

        self.load_state()

    def __del__(self):
        """ Release the lock file when the object is deleted"""
        self.lock.release_lock()

    def store_state(self):
        """ Write the hardware state to the temporary file. """
        with open(STATE_FILE, 'w', encoding="utf-8") as file:
            json.dump(self.state, file)
        logger.debug("Soundcard state saved %s", self.state)

    def load_state(self):
        """ Load the hardware state from the temporary file. """
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r', encoding="utf-8") as file:
                try:
                    self.state = json.load(file)
                except json.JSONDecodeError:
                    logger.warning("Failed to load soundcard state.")

                logger.debug("Soundcard state loaded %s", self.state)
                self.gain = self.state['gain']
                self.phantom_mode = self.state['phantom']
        else:
            self.gain = 0
            self.phantom_mode = 0
            self.store_state()

    def enable(self):
        """ Turn on the soundcard power rails, set gain to 0, and disable phantom power """
        GPIO.output(EXT_MIC_EN, 1)
        self.set_gain(0)
        self.set_phantom(self.NONE)
        self.write_state()

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
        self.state = {'gain':self.gain, 'phantom':self.phantom_mode}
        self.store_state()

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
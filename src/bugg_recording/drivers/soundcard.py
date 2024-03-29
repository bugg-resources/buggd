""" Provides power, phantom power, and gain controls for the soundcard """

import RPi.GPIO as GPIO
import spidev
import logging
import os
import json
import subprocess
from .lock import Lock
from .pcmd3180 import PCMD3180

logger = logging.getLogger(__name__)
#logger.setLevel(logging.INFO)

EXT_MIC_EN = 12

LOCK_FILE = "/tmp/soundcard.lock"
STATE_FILE = "/tmp/soundcard_state.json"

class Soundcard:
    """ 
    This class provides power, phantom power, and gain controls for the soundcard.
    
    It maintains the state of the SPI PGA chip (gain and phantom power settings) 
    in a temporary file. This allows us to change gain or phantom power settings
    independenty, since the chip only has a single register for both settings.

    It manages both internal and external channels.

    There is also a method to measure the variance of the audio signal, which is used to
    determine whether the soundcard is functioning correctly.
    
    """

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

        self.pcmd3180 = PCMD3180()
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False) # Squash warning if the pin is already in use
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 5_000_000

        self.gain = 0
        self.zc_gain = 1    # Enable zero-crossing gain control by default
        self.zc_gpo = 1     # Enable zero-crossing phantom switching by default
        self.phantom_mode = 0

        self.state={'gain':0, 'phantom':0}
        self.load_state()

    def close(self):
        """ Release the lock file """
        logger.debug("Closing soundcard")
        self.disable_external_channel()
        self.disable_internal_channel()
        GPIO.cleanup()
        self.spi.close()
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

    def enable_external_channel(self):
        """ Turn on the soundcard power rails, set gain to 0, and disable phantom power """
        logger.debug("Enabling external channel")

        GPIO.setup(EXT_MIC_EN, GPIO.OUT)
        GPIO.output(EXT_MIC_EN, 1)
        self.set_gain(0)
        self.set_phantom(self.NONE)
        self.write_state()

    def disable_external_channel(self):
        """ Turn off the soundcard power rails"""
        logger.debug("Disabling external channel")

        GPIO.setup(EXT_MIC_EN, GPIO.OUT)
        GPIO.output(EXT_MIC_EN, 0)

    def enable_internal_channel(self):
        """ Turn on I2S bridge, initialise it """
        logger.debug("Enabling internal channel")
        self.pcmd3180.power_on() 
        self.pcmd3180.reset()
        self.pcmd3180.send_configuration()

    def disable_internal_channel(self):
        """ Turn off I2S bridge """
        logger.debug("Disabling internal channel")

        self.pcmd3180.power_off()

    def write_state(self):
        """ Write the current state to the soundcard """
        tx = [0, 0]
        tx[0] |= self.gain
        tx[1] |= self.zc_gpo << 5
        tx[1] |= self.zc_gain << 4
        tx[1] |= self.phantom_mode

        logger.debug("Writing state: gain %d, phantom %d", self.gain, self.phantom_mode)
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

        
    def measure_variance(self):
        """
        Record a second of audio from both channels and compute the variance.
        This is used to determine whether the soundcard is functioning correctly.

        Returns a dict with the variance of each channel.
        """

        fn = '/tmp/soundcard_test.raw'
        fn_internal = fn + '.0'
        fn_external = fn + '.1'

        try:
            subprocess.run(['arecord', '--separate-channels', '--device', 'plughw:0,0', '--channels=2', '--format=S16_LE', '--rate=48000', '--duration=1', '--file-type=raw', fn], check=True)

            samples_internal = read_16bit_signed_pcm(fn_internal)
            samples_external = read_16bit_signed_pcm(fn_external)

            variance_internal = calculate_variance(samples_internal, calculate_mean(samples_internal))
            variance_external = calculate_variance(samples_external, calculate_mean(samples_external))
            
            return {'internal': variance_internal, 'external': variance_external}
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error("Failed to record audio: %s", e)
            return None


def read_16bit_signed_pcm(file_path):
    """ Read a raw 16-bit signed PCM file and return the samples as a list. """
    with open(file_path, 'rb') as file:
        content = file.read()
        samples = [int.from_bytes(content[i:i+2], 'little', signed=True) for i in range(0, len(content), 2)]
    return samples


def calculate_mean(data):
    """ Calculate the mean of a list of numbers. Avoids dependency on numpy. """
    return sum(data) / len(data)


def calculate_variance(data, mean):
    """ Calculate the variance of a list of numbers. Avoids dependency on numpy."""
    return sum((x - mean) ** 2 for x in data) / len(data)


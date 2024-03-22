""" Provides power control and status information for the RC7620 modem """
import logging
import RPi.GPIO as GPIO
import time
from enum import Enum, auto
import usb.core
import usb.util
from lock import Lock

logging.getLogger().setLevel(logging.INFO)

P3V7_EN = 7
POWER_ON_N = 5
RESET_IN_N = 6

LOCK_FILE = '/tmp/modem.lock'

VENDOR_ID = 0x1199
PRODUCT_ID = 0x68c0

class ModemState(Enum):
    """ Represents the state of the modem hardware """
    UNKNOWN = auto() # When driver initialises, the modem may already be powered on in an unknown state
    RAIL_OFF = auto() # When driver initialises, we don't even know whether we're asserting P3V7_EN
    OFF = auto()
    NO_SIM = auto() # The modem is powered on but there is no SIM card
    READY = auto() # The modem is powered on and ready to use

class Modem:
    """
    Provides power control and status information for the RC7620 GSM modem
    We use the FileLock library to ensure that only one instance of the driver is running at a time.

    """

    def __init__(self, lock_file_path=LOCK_FILE):
        """ Attempt to acquire the lock and initialise the GPIO """
        try:
            self.lock = Lock(lock_file_path)
        except RuntimeError as e:
            logging.critical(e)
            self.result = False
            raise
        self.state = ModemState.UNKNOWN

        GPIO.setmode(GPIO.BCM)

        if self.is_enumerated():
            self.configure_gpio()   # GPIO pins must be HIGH-Z until modem is booted

        GPIO.setup(P3V7_EN, GPIO.OUT)
        GPIO.setup(POWER_ON_N, GPIO.OUT, initial=GPIO.LOW)

        logging.info("Modem driver initialized successfully.")

    def configure_gpio(self):
        """
        Configure the GPIO pins
        It's important to only take the pins out of HIGH-Z when the modem is fully booted.
        """
        GPIO.setup(RESET_IN_N, GPIO.OUT, initial=GPIO.LOW)   

    def release_gpio(self):
        """ Set GPIO pins HIGH-Z """
        GPIO.setup(RESET_IN_N, GPIO.IN)

    def turn_on_rail(self):
        """ Turn on the 3.7V rail """
        GPIO.output(P3V7_EN, GPIO.HIGH)
    
    def turn_off_rail(self):
        """ Turn off the 3.7V rail """
        GPIO.output(P3V7_EN, GPIO.LOW)

    def rail_is_on(self):
        """
        Check if the 3.7V rail is on.
        This is true if P3V7_EN is an output and is HIGH.
        Calling GPIO.input on an output pin will return the output state.
        """
        if GPIO.gpio_function(P3V7_EN) == GPIO.OUT and GPIO.input(P3V7_EN) == GPIO.HIGH:
            return True

    def get_state(self):
        """ Get the state of the modem """
        return self.state

    def power_on(self):
        """ Turn on the rail, assert POWER_ON_N, and wait for the modem to enumerate """
        self.turn_on_rail()
        time.sleep(0.5)

        GPIO.output(POWER_ON_N, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(POWER_ON_N, GPIO.LOW)

        logging.info("POWER_ON_N asserted, waiting for modem to boot up...")
        # Wait for the modem to boot up
        time.sleep(2)
        max_tries = 10
        while(max_tries > 0):
            logging.info("Checking if modem is enumerated...")
            if self.is_enumerated():
                return True
            time.sleep(2)
            max_tries -= 1
        
        logging.error("Timed out waiting for modem to boot up.")
        return False

    def power_off(self):
        """ Command modem to power down safely from software then remove power """
        # TODO: Implement software shutdown
        self.release_gpio()
        self.turn_off_rail()

    def is_enumerated(self):
        """ Check if the modem is enumerated on the USB bus """
        return usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID) is not None

    
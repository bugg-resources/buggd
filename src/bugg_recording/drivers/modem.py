""" Provides power control and status information for the RC7620 modem """
import logging
import time
from enum import Enum, auto
import usb.core
import usb.util
import serial
import RPi.GPIO as GPIO
from .lock import Lock

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

P3V7_EN = 7
POWER_ON_N = 5
RESET_IN_N = 6

LOCK_FILE = "/tmp/modem.lock"

CONTROL_INTERFACE = "/dev/tty_modem_command_interface"
CONTROL_INTERFACE_BAUD = 115200
CONTROL_INTERFACE_TIMEOUT = 1

VENDOR_ID = 0x1199
PRODUCT_ID = 0x68c0

class ModemTimeoutException(Exception):
    """Exception raised when a timeout occurs while waiting for a response from the modem."""

class ModemNoSimException(Exception):
    """Exception raised when no SIM card is detected in the modem."""

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
            logger.critical(e)
            self.result = False
            raise
        self.port = None

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False) # Squash warning if the pin is already in use

        if self.is_enumerated():
            self.configure_gpio()   # GPIO pins must be HIGH-Z until modem is booted

        GPIO.setup(P3V7_EN, GPIO.OUT)
        GPIO.setup(POWER_ON_N, GPIO.OUT, initial=GPIO.LOW)

        logger.info("Modem driver initialized successfully.")

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
        return GPIO.gpio_function(P3V7_EN) == GPIO.OUT and GPIO.input(P3V7_EN) == GPIO.HIGH

    def power_on(self):
        """ Turn on the rail, assert POWER_ON_N, and wait for the modem to enumerate """
        self.turn_on_rail()
        time.sleep(0.5)

        # Strobe the POWER_ON_N pin to boot the modem
        GPIO.output(POWER_ON_N, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(POWER_ON_N, GPIO.LOW)

        logger.info("POWER_ON_N asserted, waiting for modem to boot up...")
        # Wait for the modem to boot up
        time.sleep(2)
        max_tries = 10
        while(max_tries > 0):
            logger.info("Checking if modem is enumerated...")
            if self.is_enumerated():
                return True
            time.sleep(2)
            max_tries -= 1
        
        logger.error("Timed out waiting for modem to boot up.")
        return False

    def power_off(self):
        """ Command modem to power down safely from software then remove power """
        # TODO: Implement software shutdown
        self.close_control_interface()
        self.release_gpio()
        self.turn_off_rail()

    def is_enumerated(self):
        """ Check if the modem is enumerated on the USB bus """
        return usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID) is not None

    def open_control_interface(self):
        """ Open the control interface for sending AT commands to the modem. """
        if self.port is None:
            try:
                self.port = serial.Serial(CONTROL_INTERFACE, CONTROL_INTERFACE_BAUD, timeout=CONTROL_INTERFACE_TIMEOUT)
            except serial.SerialException as e:
                logger.error("Failed to open control interface: %s", e)
                return False
        return True

    def close_control_interface(self):
        """ Close the control interface """
        if self.port is not None:
            self.port.close()
            self.port = None
    
    def send_at_command(self, command):
        """
        If the control interface is not open, open it.
        Send an AT command to the modem and returns the response string.
        
        Args:
        - command: The AT command to send to the modem. 
        
        Returns:
        - The response string from the modem.
        
        Raises:
        - ModemTimeoutException: If a timeout occurs waiting for a response.
        """
        if (self.port is None):
            self.open_control_interface()

        # Clear the input buffer
        # self.port.reset_input_buffer()  # Sometimes the modem sends status strings unprompted
        # Send the AT command
        self.port.write((command + '\r\n').encode())
        # Read the response
        response = self.port.read_until().decode('utf-8').strip()
        
        # Check if a timeout occurred
        if not response:
            raise ModemTimeoutException("Timeout occurred waiting for a response from the modem.")
        
        return response
    
    def is_responding(self):
        """
        Check if the modem is responding to AT commands.
        
        Returns:
        - True if the modem is responding, False otherwise.
        """
        try:
            response = self.send_at_command("AT")
            return "OK" in response
        except ModemTimeoutException:
            return False

    def get_sim_ccid(self):
        """
        Get the SIM card's ICCID.
        
        Returns:
        - The ICCID string.
        """
        response = self.send_at_command("AT+CCID?")
        if "ERROR" in response:
            raise ModemNoSimException("No SIM card detected.")
        return response.split(": ")[1]

    def sim_present(self):
        """
        Check if a SIM card is present in the modem.
        
        Returns:
        - True if a SIM card is present, False otherwise.
        """
        try:
            self.get_sim_ccid()
            return True
        except ModemNoSimException:
            return False 
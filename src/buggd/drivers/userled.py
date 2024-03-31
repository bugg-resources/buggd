""" Tiny driver for the user LED on the main PCB """
import RPi.GPIO as GPIO

USER_LED_PIN = 13

class UserLED():
    """
    Class to control the user LED on the main PCB
    or, if a pin is provided, any other LED connected to a GPIO pin
    """
    def __init__(self, pin=USER_LED_PIN):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.HIGH)

    def __del__(self):
        self.close()

    def on(self):
        """ Turn the LED on """
        GPIO.output(self.pin, GPIO.LOW)

    def off(self):
        """ Turn the LED off """
        GPIO.output(self.pin, GPIO.HIGH)

    def close(self):
        """ Clean up the GPIO """
        GPIO.cleanup()
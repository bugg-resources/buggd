import RPi.GPIO as GPIO
import time 

en_pin=7
power_on_n_pin = 5

GPIO.setmode(GPIO.BCM)

GPIO.setup(en_pin, GPIO.OUT)
GPIO.setup(power_on_n_pin, GPIO.OUT)

GPIO.output(en_pin,1)
time.sleep(1)
GPIO.output(power_on_n_pin,1)
time.sleep(1)
GPIO.output(power_on_n_pin,0)

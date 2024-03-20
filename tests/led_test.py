PWR_LED_ON = (0, 0)
from pcf8574 import PCF8574
from time import sleep

PCF8574_I2C_ADD = 0x23
PCF8574_I2C_BUS = 1

led_driver = PCF8574(PCF8574_I2C_BUS, PCF8574_I2C_ADD)

def all_off():
    for ch in range(8):
        led_driver.port[ch] = 1

def all_on(): 
    for ch in range(8):
        led_driver.port[ch] = 0

def one_by_one():
    for led in range(8):
        all_off()
 
        led_driver.port[led] = 0
        sleep(1)

def main():
    all_off()
    sleep(1) 
    
    one_by_one()
    
    all_on() 
    sleep(1)
    all_off()

if __name__ == "__main__":
    main()

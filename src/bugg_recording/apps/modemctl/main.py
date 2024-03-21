""" 
Standalone utility to control the modem's power state and check status
This allows the user to turn on the modem without running the recording application.
It's mainly intended for use during debugging.  
"""

import logging
from bugg_recording.drivers.modem import Modem
# en_pin=7
# power_on_n_pin = 5

# GPIO.setmode(GPIO.BCM)

# GPIO.setup(en_pin, GPIO.OUT)
# GPIO.setup(power_on_n_pin, GPIO.OUT)

# GPIO.output(en_pin,1)
# time.sleep(1)
# GPIO.output(power_on_n_pin,1)
# time.sleep(1)
# GPIO.output(power_on_n_pin,0)

def main():
    """ 
    Standalone utility to control the modem's power state and check status
    This allows the user to turn on the modem without running the recording application.
    It's mainly intended for use during debugging.  
    """
    # Create a StreamHandler for stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stdout_handler.setFormatter(formatter)

    # Configure the root logger to use the stdout handler
    logging.basicConfig(level=logging.INFO, handlers=[stdout_handler])
    logger = logging.getLogger(__name__)
    logger.info("Starting modem configuration utility.")
    

    modem = Modem()

if __name__ == "__main__":
    main()
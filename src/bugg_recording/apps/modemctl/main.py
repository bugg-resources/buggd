""" 
Standalone utility to control the modem's power state and check status
This allows the user to turn on the modem without running the recording application.
It's mainly intended for use during debugging.  
"""

import logging
import sys
import argparse
from ...drivers.modem import Modem
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

def handle_power_command(modem, args):
    """ Turn the modem on / off """
    if args.parameter == 'on':
        modem.power_on()
    elif args.parameter == 'off':
        modem.power_off()


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
    
    # Define the functions for the command line arguments
    parser = argparse.ArgumentParser(description='Control the modem.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Power command
    power_parser = subparsers.add_parser('power', help='Control power state')
    power_parser.add_argument('parameter', choices=['on', 'off'], help='Power on or off')
    power_parser.set_defaults(func=handle_power_command)

    # Check SIM card status
    get_sim_state_parser = subparsers.add_parser('get_sim_state', help='Get SIM card state')
    get_sim_state_parser.set_defaults(func=handle_sim_state)

    args = parser.parse_args()

    # Execute the function associated with the chosen command
    if hasattr(args, 'func'):
        modem = Modem()
        args.func(modem, args)
    else:
        parser.print_help()
if __name__ == "__main__":
    main()
""" 
Standalone utility to control the modem's power state and check status
This allows the user to turn on the modem without running the recording application.
It's mainly intended for use during debugging.  
"""

import logging
import sys
import argparse
from ...drivers.modem import Modem

def handle_power_command(logger, modem, args):
    """ Turn the modem on / off """
    if args.parameter == 'on':
        modem.power_on()
    elif args.parameter == 'off':
        modem.power_off()

def handle_sim_state(logger, modem, args):
    """ Get the SIM card state """
    ccid = modem.get_sim_ccid()
    if ccid:
        logger.info(f"SIM card present. CCID: {ccid}")
    else:
        logger.info("No SIM card present.")

def handle_check_responding(logger, modem, args):
    """ Check if the modem is responding """
    if modem.is_responding():
        logger.info("Modem is responding.")
    else:
        logger.info("Modem is not responding.")

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

    # Check SIM card status command
    get_sim_state_parser = subparsers.add_parser('get_sim_state', help='Get SIM card state')
    get_sim_state_parser.set_defaults(func=handle_sim_state)

    # Check if modem is responding command
    check_responding_parser = subparsers.add_parser('check_responding', help='Check if modem is responding')
    check_responding_parser.set_defaults(func=handle_check_responding)

    args = parser.parse_args()

    # Execute the function associated with the chosen command
    if hasattr(args, 'func'):
        modem = Modem()
        args.func(logger, modem, args)
    else:
        parser.print_help()
if __name__ == "__main__":
    main()
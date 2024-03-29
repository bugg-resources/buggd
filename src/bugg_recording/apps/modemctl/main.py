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

def handle_check_enumerated(logger, modem, args):
    """ Check if the modem is enumerated """
    if modem.is_enumerated():
        logger.info("Modem is enumerated.")
    else:
        logger.info("Modem is not enumerated. It's probably not powered on.")

def handle_check_responding(logger, modem, args):
    """ Check if the modem is responding """
    if modem.is_responding():
        logger.info("Modem is responding to AT commands.")
    else:
        logger.info("Modem is not responding.")

def handle_get_signal_strength(logger, modem, args):
    """ Get the signal strength """
    signal_strength = modem.get_rssi()
    if signal_strength:
        logger.info(f"Signal strength: {signal_strength}")
    else:
        logger.info("Failed to get signal strength.")

def handle_get_signal_strength_dbm(logger, modem, args):
    """ Get the signal strength in dBm """
    signal_strength_dbm = modem.get_rssi_dbm()
    if signal_strength_dbm:
        logger.info(f"Signal strength (dBm): {signal_strength_dbm}")
    else:
        logger.info("Failed to get signal strength in dBm.")
        
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

    # Check the modem is enumerated
    get_sim_ccid_parser = subparsers.add_parser('check_enumerated', help='Check if modem is enumerated')
    get_sim_ccid_parser.set_defaults(func=handle_check_enumerated)

    # Check if modem is responding command
    check_responding_parser = subparsers.add_parser('check_responding', help='Check if modem is responding')
    check_responding_parser.set_defaults(func=handle_check_responding)

    # Check SIM card status command
    get_sim_state_parser = subparsers.add_parser('get_sim_state', help='Get SIM card state')
    get_sim_state_parser.set_defaults(func=handle_sim_state)

    # Get signal strength command
    get_signal_strength_parser = subparsers.add_parser('get_signal_strength', help='Get signal strength')
    get_signal_strength_parser.set_defaults(func=handle_get_signal_strength)

    # Get signal strength in dBm command
    get_signal_strength_dbm_parser = subparsers.add_parser('get_signal_strength_dbm', help='Get signal strength in dBm')
    get_signal_strength_dbm_parser.set_defaults(func=handle_get_signal_strength_dbm)
    

    args = parser.parse_args()

    # Execute the function associated with the chosen command
    if hasattr(args, 'func'):
        modem = Modem()
        args.func(logger, modem, args)
    else:
        parser.print_help()
if __name__ == "__main__":
    main()
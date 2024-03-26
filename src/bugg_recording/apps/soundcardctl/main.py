import argparse
import logging
import sys
from ...drivers.soundcard import Soundcard

sc = Soundcard()

def handle_power_command(logger, args):
    """ Turn the soundcard on / off """
    logger.info(f"Turning soundcard {args.parameter}")
    if args.parameter == 'on':
        sc.enable()
    elif args.parameter == 'off':
        sc.disable()

def handle_gain_command(logger, args):
    """ Set gain """
    logger.info(f"Setting gain to {args.gain}")
    sc.set_gain(args.gain)


def handle_phantom_command(logger, args):
    """ Set phantom power """
    logger.info(f"Setting phantom power to {args.phantom}")
    match args.phantom:
        case 'none':
            sc.set_phantom(sc.NONE)
        case 'PIP':
            sc.set_phantom(sc.PIP)
        case '3V3':
            sc.set_phantom(sc.P3V3)
        case 'P48':
            sc.set_phantom(sc.P48)

def main():
    """ Tool to set power, gain and phantom power of the soundcard."""
    # Create a StreamHandler for stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stdout_handler.setFormatter(formatter)

    # Configure the root logger to use the stdout handler
    logging.basicConfig(level=logging.INFO, handlers=[stdout_handler])
    logger = logging.getLogger(__name__)
    logger.info("Starting soundcard configuration utility.")
    
    parser = argparse.ArgumentParser(description='Test sound commands.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Power command
    power_parser = subparsers.add_parser('power', help='Control power state')
    power_parser.add_argument('parameter', choices=['on', 'off'], help='Power on or off')
    power_parser.set_defaults(func=handle_power_command)

    # Gain command
    set_parser = subparsers.add_parser('gain', help='Set gain')
    set_parser.add_argument('parameter', type=int, choices=range(0, 21), metavar='[0-20]', help='Set gain: 3dB steps, 0-60dB')
    set_parser.set_defaults(func=handle_gain_command)

    # Phantom command
    set_parser = subparsers.add_parser('phantom', help='Set phantom')
    set_parser.add_argument('parameter', choices=['none','P48', 'PIP', '3V3'], help='set power mode')
    set_parser.set_defaults(func=handle_phantom_command)

    args = parser.parse_args()

    # Execute the function associated with the chosen command
    if hasattr(args, 'func'):
        args.func(logger, args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

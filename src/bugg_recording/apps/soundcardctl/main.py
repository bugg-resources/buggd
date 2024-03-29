import argparse
import logging
import sys
from ...drivers.soundcard import Soundcard


def handle_power_commandMeh(logger, soundcard, args):
    """ Turn the soundcard on / off """
    logger.info(f"Turning soundcard {args.parameter}")
    if args.parameter == 'on':
        soundcard.enable()
    elif args.parameter == 'off':
        soundcard.disable()

def handle_power_command(logger, soundcard, args):
    if args.object == 'internal':
        if args.state == 'on':
            print("Turning internal soundcard on")
        else:
            print("Turning internal soundcard off")
    elif args.object == 'external':
        if args.state == 'on':
            soundcard.enable()
        else:
            soundcard.disable()
    else:
        logger.error("Invalid object type specified.")


def handle_gain_command(logger, soundcard, args):
    """ Set gain """
    logger.info(f"Setting gain to {args.parameter}")
    soundcard.set_gain(args.parameter)


def handle_phantom_command(logger, soundcard, args):
    """ Set phantom power """
    logger.info(f"Setting phantom power to {args.parameter}")
    match args.parameter:
        case 'none':
            soundcard.set_phantom(soundcard.NONE)
        case 'PIP':
            soundcard.set_phantom(soundcard.PIP)
        case '3V3':
            soundcard.set_phantom(soundcard.P3V3)
        case 'P48':
            soundcard.set_phantom(soundcard.P48)

def main():
    """ Tool to set power, gain and phantom power of the soundcard."""
    # Create a StreamHandler for stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stdout_handler.setFormatter(formatter)

    # Configure the root logger to use the stdout handler
    logging.basicConfig(level=logging.WARNING, handlers=[stdout_handler])
    logger = logging.getLogger(__name__)
    logger.info("Starting soundcard configuration utility.")
    
    parser = argparse.ArgumentParser(description='Test sound commands.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    soundcard = Soundcard()

    # Power command
    power_parser = subparsers.add_parser('power', help='Control power state')
    power_subparsers = power_parser.add_subparsers(dest='object', help='Specify channel to control') 
   
    # Internal power command
    internal_power_parser = power_subparsers.add_parser('internal', help='Control power state for internal object')
    internal_power_parser.add_argument('state', choices=['on', 'off'], help='Power state for internal object')

    # External power command
    external_power_parser = power_subparsers.add_parser('external', help='Control power state for external object')
    external_power_parser.add_argument('state', choices=['on', 'off'], help='Power state for external object')

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
        args.func(logger, soundcard, args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

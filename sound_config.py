import argparse
import hardware_drivers.soundcard as soundcard

sc = soundcard.Soundcard()

def handle_power_command(args):
    """ Turn the soundcard on / off """
    if args.parameter == 'on':
        sc.enable()
    elif args.parameter == 'off':
        sc.disable()

def handle_set_command(args):
    """ Set gain and phantom power """
    sc.set_gain(args.gain)

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
    parser = argparse.ArgumentParser(description='Test sound commands.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Power command
    power_parser = subparsers.add_parser('power', help='Control power state')
    power_parser.add_argument('parameter', choices=['on', 'off'], help='Power on or off')
    power_parser.set_defaults(func=handle_power_command)

    # Set command
    set_parser = subparsers.add_parser('set', help='Control gain and phantom power')
    # set_parser.add_argument('--gain', '-g', required=True, type=int, choices=range(0, 21), metavar='[0-21]', help='Set gain: 3dB steps, 0-60dB')
    set_parser.add_argument('--gain', '-g', required=True, type=int, choices=range(0, 21), help='Set gain: 3dB steps, 0-60dB')
    set_parser.add_argument('--phantom', '-p', required=True, choices=['none','P48', 'PIP', '3V3'], help='set power mode')
    set_parser.set_defaults(func=handle_set_command)

    args = parser.parse_args()

    # Execute the function associated with the chosen command
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

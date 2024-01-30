import argparse
import hardware_drivers.soundcard as soundcard

sc = soundcard.Soundcard()

def handle_power_command(args):
    if args.parameter == 'on':
        sc.enable()
    elif args.parameter == 'off':
        sc.disable()

def handle_set_command(args):
    pass

def main():
    parser = argparse.ArgumentParser(description='Test sound commands.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Power command
    power_parser = subparsers.add_parser('power', help='Control power state')
    power_parser.add_argument('parameter', choices=['on', 'off'], help='Power on or off')
    power_parser.set_defaults(func=handle_power_command)

    # Set command
    set_parser = subparsers.add_parser('set', help='Control gain and phantom power')
    set_parser.add_argument('-g', '--gain', required=True, type=int, choices=range(0, 61), metavar='[0-60]', help='Set gain: 0-60dB in 3dB steps')
    set_parser.add_argument('-p', '--phantom', required=True, choices=['NONE','P48', 'PIP', '3V3'], help='set power mode')
    set_parser.set_defaults(func=handle_set_command)

    args = parser.parse_args()

    # Execute the function associated with the chosen command
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

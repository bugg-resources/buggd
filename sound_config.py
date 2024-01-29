import argparse
import hardware_drivers.soundcard as soundcard

sc = soundcard.Soundcard()

def handle_power_command(args):
    if args.parameter == 'on':
        sc.enable()
    elif args.parameter == 'off':
        sc.disable()

def handle_phantom_command(args):
    pass

def main():
    parser = argparse.ArgumentParser(description='Test sound commands.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Power command
    power_parser = subparsers.add_parser('power', help='Control power state')
    power_parser.add_argument('parameter', choices=['on', 'off'], help='Power on or off')
    power_parser.set_defaults(func=handle_power_command)

    # Phantom command
    phantom_parser = subparsers.add_parser('phantom', help='Control phantom power')
    phantom_parser.add_argument('parameter', choices=['P48', 'PIP', '3V3'], help='Phantom power mode')
    phantom_parser.set_defaults(func=handle_phantom_command)

    args = parser.parse_args()

    # Execute the function associated with the chosen command
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

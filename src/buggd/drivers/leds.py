from enum import Enum, auto
from pcf8574 import PCF8574

ADDRESS = 0x23
BUS = 1

class Colour(Enum):
    """ Possible colours for an LED """
    RED = auto()
    GREEN = auto()
    BLUE = auto()
    YELLOW = auto()
    CYAN = auto()
    MAGENTA = auto()
    WHITE = auto()
    BLACK = auto()
    OFF = BLACK

# Maps colours to RGB values
COLOUR_THEORY = {
    Colour.RED: (1, 0, 0),
    Colour.GREEN: (0, 1, 0),
    Colour.BLUE: (0, 0, 1),
    Colour.YELLOW: (1, 1, 0),
    Colour.CYAN: (0, 1, 1),
    Colour.MAGENTA: (1, 0, 1),
    Colour.WHITE: (1, 1, 1),
    Colour.BLACK: (0, 0, 0),
}

class Driver():
    """ This class is responsible for interfacing with the PCF8574 IO expander """
    def __init__(self, bus, address):
        self.bus = bus
        self.address = address
        self.io_expander = PCF8574(self.bus, self.address)

    def set(self, channel, value):
        """
        Turns on one channel of the IO expander (one LED within an RGB LED)
        Channels are active low
        """
        try:
            self.io_expander.port[channel] = not value
        except AssertionError:
            pass


class LED:
    """ This class represents an RGB LED """
    def __init__(self, driver, ch_r, ch_g, ch_b):
        self.driver = driver
        self.channels = {
            'red': ch_r,
            'green': ch_g,
            'blue': ch_b
        }
        self.stay_on_at_exit = False

    def set(self, colour: Colour):
        """
        Sets the colour of the LED
        An LED, like the Power LED, can have a colour hard-wired to a specific channel, so 
        check for that and raise an error if we try to set a colour that can't be displayed
        """
        col = COLOUR_THEORY[colour]
        r, g, b = col

        # Check if any of the channels are stuck in hardware
        for index, element in enumerate(self.channels.items()):
            if isinstance(element[1], bool):
                if not element[1] == col[index]:
                    inv_map = {v: k for k, v in COLOUR_THEORY.items()}
                    raise ValueError(f"{inv_map.get(col)} cannot be displayed on this LED because \
                                     it's colour {element[0]} is hard-wired to {element[1]}")

        self.driver.set(self.channels['red'], r)
        self.driver.set(self.channels['green'], g)
        self.driver.set(self.channels['blue'], b)

class LEDs():
    """ This class contains the three user-facing LEDs on the product """
    def __init__(self):
        self.driver = Driver(BUS, ADDRESS)

        self.top = LED(self.driver, 7, 6, 5)
        self.middle = LED(self.driver, 4, 3, 2)
        self.bottom = LED(self.driver, True, 1, 0)

        self.bottom.stay_on_at_exit = True


    def all_off(self):
        """ Turns off all LEDs """
        self.top.set(Colour.OFF)
        self.middle.set(Colour.OFF)
        self.bottom.set(Colour.RED)


    def at_exit(self):
        """
        Turns off all LEDs when the program exits,
        unless they are set to stay on, e.g. for use by the self-test or exit status
        """
        if not self.top.stay_on_at_exit:
            self.top.set(Colour.OFF)
        if not self.middle.stay_on_at_exit:
            self.middle.set(Colour.OFF)
        if not self.bottom.stay_on_at_exit:
            self.bottom.set(Colour.RED)


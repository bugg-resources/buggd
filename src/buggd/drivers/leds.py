from enum import Enum, auto
from pcf8574 import PCF8574

ADDRESS = 0x23
BUS = 1

class Colour(Enum):
    RED = auto()
    GREEN = auto()
    BLUE = auto()
    YELLOW = auto()
    CYAN = auto()
    MAGENTA = auto()
    WHITE = auto()
    BLACK = auto()
    OFF = BLACK

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
    def __init__(self, bus, address):
        self.bus = bus
        self.address = address
        self.io_expander = PCF8574(self.bus, self.address)

    def set(self, channel, value):
        try:
            self.io_expander.port[channel] = not value
        except AssertionError:
            pass

def close(self):
    self.driver.io_expander.close()

class LED:
    def __init__(self, driver, ch_r, ch_g, ch_b):
        self.driver = driver
        self.channels = {
            'red': ch_r,
            'green': ch_g,
            'blue': ch_b
        }

    def set(self, colour: Colour):
        col = COLOUR_THEORY[colour]
        r, g, b = col

        # Check if any of the channels are stuck in hardware
        for index, element in enumerate(self.channels.items()):
            if isinstance(element[1], bool):
                if not element[1] == col[index]:
                    inv_map = {v: k for k, v in COLOUR_THEORY.items()}
                    raise ValueError(f"{inv_map.get(col)} cannot be displayed on this LED because it's colour {element[0]} is hard-wired to {element[1]}")
        
        self.driver.set(self.channels['red'], r)
        self.driver.set(self.channels['green'], g)
        self.driver.set(self.channels['blue'], b)

class LEDs():
    def __init__(self):
        self.driver = Driver(BUS, ADDRESS)

        self.top = LED(self.driver, 7, 6, 5)
        self.middle = LED(self.driver, 4, 3, 2)
        self.bottom = LED(self.driver, True, 1, 0)
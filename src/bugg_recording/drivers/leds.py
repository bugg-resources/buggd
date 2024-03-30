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

class LED:
    def __init__(self, driver, ch_r: int, ch_g: int, ch_b: int):
        self.driver = driver
        self.channel = {
            'red': ch_r,
            'green': ch_g,
            'blue': ch_b
        }

    def set(self, colour: Colour):
        r, g, b = COLOUR_THEORY[colour]
        self.driver.set(self.channel['red'], r)
        self.driver.set(self.channel['green'], g)
        self.driver.set(self.channel['blue'], b)

class LEDs():
    def __init__(self):
        self.driver = Driver(BUS, ADDRESS)

        self.top = LED(self.driver, 0, 1, 2)
        self.middle = LED(self.driver, 3, 4, 5)
        self.bottom = LED(self.driver, None, 6, 7)
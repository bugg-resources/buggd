''' This class is used to test the hardware in the factory. It is instantiated and 
run if the trigger file is present. '''

import logging
import subprocess
import os
import time
from smbus2 import SMBus
from bugg_recording.drivers.modem import Modem
from bugg_recording.drivers.soundcard import Soundcard
from bugg_recording.drivers.pcmd3180 import PCMD3180
from bugg_recording.drivers.leds import LEDs, Colour
from bugg_recording.drivers.userled import UserLED

from .utils import discover_serial

class FactoryTest:
    """ 
    This class runs a series of tests on the hardware in the factory.
    Usually, it is triggered by the presence of a magic file on the SD card.
    
    Individual tests return succsss if they *complete* successfully, but the actual
    results of the tests are stored in the results dictionary.
    
    The results dictionary is a set of key-value pairs, where the key is the name of the test
    and the value is a boolean indicating the test's success.
    
    The results dictionary can be accessed using the get_results() method.
    
    The results can be printed as a formatted string using the get_results_string() method.
    
    This formatted string is intended to be printed to the console or logged.
    There is also a mechanism to write the results string to /etc/issue to be displayed 
    on the console before login.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.results_file = "/home/bugg/factory_test_results.txt"
        
        self.all_passed = False
        self.results = {
            "modem_enumerates": False,
            "modem_responsive": False,
            "modem_sim_readable": False,
            "modem_towers_found": False,
            "i2s_bridge_responding": False,
            "rtc_responding": False,
            "led_controller_responding": False,
            "internal_microphone_recording": False,
            "external_microphone_recording": False,
        }

    def run(self):
        """
        Run the full self-test procedure.
        
        Print the results to the log.
        Write the results to disk, and symlink to /etc/issue.d for display on the console before login.

        Returns:
            bool: True if all tests ran successfully, False otherwise.

            Note: A true result only means that the test ran, not that the hardware is functioning correctly.
            Check the results dictionary for the actual results. 

        """

        self.logger.info("Full factory test running.")

        # Run the tests
        completed = [] 
        completed.append(self.test_modem())
        completed.append(self.test_i2c_devices())
        completed.append(self.test_recording())

        if all(completed):
            self.logger.info("All tests completed.")
            ret = True
        else:
            self.logger.warning("Some tests did not complete successfully. Check the results.")
            ret = False

        # Check if all tests passed - this indicates that all the hardware is functioning correctly 
        self.all_passed = all(self.results.values())

        leds = LEDs()
        self.display_results_on_leds(leds)

        self.logger.info("\n%s", self.get_results_string())
        self.write_results_to_disk()

        return ret


    def run_bare_board(self):
        """
        Run the bare-board test. This just turns on the power rails, modem, soundcard, etc.
        so the assembly technician can measure voltages on the test points. 
        """

        self.logger.info("Running factory bare-board test.")

        modem = Modem()
        modem.turn_on_rail()

        soundcard = Soundcard()
        soundcard.enable_external_channel()
        soundcard.set_phantom(soundcard.P48)

        led = UserLED()
        while True:
            led.on()
            time.sleep(0.5)
            led.off()
            time.sleep(0.5)
            # This runs forever until the factory technician turns off the power


    def test_modem(self):
        """
        Run a series of tests on the modem.
        
        Returns:
            bool: True if all tests ran successfully, False otherwise.
            NOTE: A true result does not necessarily mean the modem is functioning correctly
            check the results dictionary for more information.
        """
        self.logger.info("Testing modem.")

        try:

            # Stop ModemManager to prevent it from interfering with the modem
            try:
                subprocess.run(["sudo", "systemctl", "stop", "ModemManager"], check=True)
            except subprocess.CalledProcessError as e:
                self.logger.warning("Failed to stop ModemManager: %s", e)
                return False

            modem = Modem()

            # Run the tests
            self.results["modem_enumerates"] = modem.power_off() and modem.power_on() and modem.is_enumerated()
            self.results["modem_responsive"] = modem.is_responding()
            self.results["modem_sim_readable"] = modem.sim_present()
            # Sometimes the modem takes a while to get a signal
            tries = 6
            while tries > 0:
                rssi = modem.get_rssi()
                self.logger.debug("RSSI: %s", rssi)
                time.sleep(1)
                tries -= 1
                if rssi and rssi != 99:
                    break
            self.results["modem_towers_found"] = rssi is not None and rssi != 99

            modem.power_off()
            return True

        except Exception as e:
            self.logger.error("Error during modem test: %s", e)
            return False 

    def test_i2c_devices(self):
        """
        Check the I2C devices are all present
        """
        self.logger.info("Testing I2C devices.")

        try:
            pcf8574_addr = 0x23 # LED controller
            pcmd3180_addr = 0x4c # I2S bridge
            ds3231_addr = 0x68 # RTC

            # Power the PCMD3180
            pcmd = PCMD3180()
            pcmd.power_on()

            # Run the tests
            self.results["i2s_bridge_responding"] = i2c_device_present(pcmd3180_addr)
            self.results["rtc_responding"] = i2c_device_present(ds3231_addr)
            self.results["led_controller_responding"] = i2c_device_present(pcf8574_addr)

            pcmd.power_off()
            pcmd.close()

            return True

        except Exception as e:
            self.logger.error("Error during I2C device test: %s", e)
            return False

    def test_recording(self):
        """
        Check for hiss on both the internal and external microphones
        Do this by recording a second of audio and checking the variance
        """
        self.logger.info("Testing recording.")

        try:
            soundcard = Soundcard()

            soundcard.disable_internal_channel()
            soundcard.disable_external_channel()
            soundcard.enable_internal_channel()
            soundcard.enable_external_channel()

            variances = soundcard.measure_variance()

            if variances is None:
                return False
            
            self.logger.info("Signal variances: Internal = %.2f, External = %.2f", variances["internal"], variances["external"])           

            self.results["internal_microphone_recording"] = variances['internal'] > 100
            self.results["external_microphone_recording"] = variances['external'] > 100

            soundcard.close()

            return True

        except Exception as e:
            self.logger.error("Error during recording test: %s", e)
            return False

    def get_results(self):
        """ Return the test results as a dictionary """
        return self.results

    def get_results_string(self):
        """ Return a formatted string of the test results, one per line """
        s = (
            "\nFactory Self-Test Results:\n"
            + "--------------------------\n"
            + "Device Serial: " + discover_serial() + "\n"
            + "\n".join([f"{k}: {v}" for k, v in self.results.items()])
            + "\n"
            + "-----------------------\n"
            + ("Factory Self-Test PASS!" if self.test_passed() else "Factory Self-Test FAIL!")
            + "\n\n"
        )
        return s

    def test_passed(self):
        """ Return True if all harware tests passed """
        return self.all_passed
        
    def write_results_to_disk(self):
        """ Write the results string to the primary user's home directory """
        with open(self.results_file, 'w', encoding='utf-8') as f:
            f.write(self.get_results_string())

        # Set permissions to globally-readable
        os.chmod(self.results_file, 0o644)

        # Link into /etc/issue.dgg
        os.makedirs("/etc/issue.d", exist_ok=True)
        try:
            os.symlink(self.results_file, "/etc/issue.d/factory_test_results.issue")
        except FileExistsError:
            pass

    def display_results_on_leds(self, leds):
        """ Display the results of the factory test on the LEDs """

        if self.test_passed():
            leds.top.set(Colour.GREEN)
            leds.middle.set(Colour.BLACK)

        else:
            results = self.get_results()

            # Split the results into the different categories
            modem_results = {k: v for k, v in results.items() if "modem" in k} 
            i2c_results = {k: v for k, v in results.items() if "responding" in k}
            recording_results = {k: v for k, v in results.items() if "recording" in k}
            
            # Create lists of the failed tests in each category
            modem_failures = [k for k, v in modem_results.items() if not v]
            i2c_failures = [k for k, v in i2c_results.items() if not v]
            recording_failures = [k for k, v in recording_results.items() if not v]
            
            if sum(bool(failures) for failures in [modem_failures, i2c_failures, recording_failures]) > 1:
                # Failures in multiple categories
                leds.top.set(Colour.WHITE)
                leds.middle.set(Colour.BLACK)
                
            elif bool(modem_failures):
                # Modem failures, indicate which ones
                leds.top.set(Colour.YELLOW)

                # Multiple failures, indicate that
                if len(modem_failures) > 1:
                    leds.middle.set(Colour.WHITE)
                
                else:
                    match modem_failures[0]:
                        case "modem_enumerates":
                            leds.middle.set(Colour.RED)
                        case "modem_responsive":
                            leds.middle.set(Colour.MAGENTA)
                        case "modem_sim_readable":
                            leds.middle.set(Colour.BLUE)
                        case "modem_towers_found":
                            leds.middle.set(Colour.YELLOW)
                            
            elif bool(i2c_failures):
                # I2C failures, indicate which ones
                leds.top.set(Colour.RED)

                # Multiple failures, indicate that
                if len(i2c_failures) > 1:
                    leds.middle.set(Colour.WHITE)
                
                else:
                    match i2c_failures[0]:
                        case "i2s_bridge_responding":
                            leds.middle.set(Colour.RED)
                        case "rtc_responding":
                            leds.middle.set(Colour.CYAN)
                        case "led_controller_responding":
                            leds.middle.set(Colour.MAGENTA) 

            elif bool(recording_failures):
                # Recording failures, indicate which ones
                leds.top.set(Colour.BLUE)

                # Multiple failures, indicate that
                if len(recording_failures) > 1:
                    leds.middle.set(Colour.WHITE)
                
                else:
                    match recording_failures[0]:
                        case "internal_microphone_recording":
                            leds.middle.set(Colour.RED)
                        case "external_microphone_recording":
                            leds.middle.set(Colour.YELLOW)


def i2c_device_present(addr, bus_num=1, force=True):
    """
    This function probes the I2C bus to check if a device responds.
    Since I2C doesn't have a standard way to check if a device is present,
    this function attempts to read a byte from the device.
    There is no guarantee that this will not change the device's state.
    There is also no guarantee that every device will respond to this, but
    it works for the devices we currently use 
    """

    try:
        # Prepare read and write operations without changing the device state
        with SMBus(bus_num) as bus:
            # Attempt to read a byte from the device
            bus.read_byte(addr, force=force)
        return True
    except OSError as expt:
        if expt.errno == 16:
            # Device is busy but present
            return True
        # Any other OSError means the device did not respond as expected
        return False
    except Exception:
        return False

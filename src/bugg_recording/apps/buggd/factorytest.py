''' This class is used to test the hardware in the factory. It is instantiated and 
run if the trigger file is present. '''

import logging
from bugg_recording.drivers.modem import Modem
import subprocess
from smbus2 import SMBus

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
        self.all_passed = False
        self.results = {
            "modem_enumerates": False,
            "modem_responsive": False,
            "modem_sim_readable": False,
            "modem_towers_found": False,
            "i2s_bridge_responding": False,
            "rtc_responding": False,
            "led_controller_responding": False,
            "internal_microphone_signal_present": False,
            "external_microphone_signal_present": False,
        }

    def run(self):
        """ Run test, log results. """
        self.logger.info("Factory test running.")

        completed = [] 

        self.logger.info("Testing modem.")
        completed.append(self.test_modem())

        self.logger.info("Testing I2C devices.")
        completed.append(self.test_i2c_devices())

        self.logger.info("Testing recording.")
        completed.append(self.test_recording())

        if all(completed):
            self.logger.info("All tests completed.")
            ret = True
        else:
            self.logger.warning("Some tests did not complete successfully. Check the results.")
            ret = False

        self.all_passed = all(self.results.values())

        # Log the results
        self.logger.info("%s", self.get_results_string())

        return ret
        

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
            self.results["modem_towers_found"] = modem.get_rssi() is not None and modem.get_rssi() != 99

            return True

        except Exception as e:
            self.logger.error("Error during modem test: %s", e)
            return False 

    def test_i2c_devices(self):
        """
        Check the I2C devices are all present
        """
        try:
            pcf8574_addr = 0x23 # LED controller
            pcmd3180_addr = 0x4c # I2S bridge
            ds3231_addr = 0x68 # RTC

            # Run the tests
            self.results["i2s_bridge_responding"] = i2c_device_present(pcmd3180_addr)
            self.results["rtc_responding"] = i2c_device_present(ds3231_addr)
            self.results["led_controller_responding"] = i2c_device_present(pcf8574_addr)

            return True

        except Exception as e:
            self.logger.error("Error during I2C device test: %s", e)
            return False

    def test_recording(self):
        pass

    def get_results(self):
        """ Return the test results as a dictionary """
        return self.results

    def get_results_string(self):
        """ Return a formatted string of the test results, one per line """
        s = (
            "\nFactory Self-Test Results:\n"
            + "\n".join([f"{k}: {v}" for k, v in self.results.items()])
            + "\n"
            + ("Factory Self-Test PASS!" if self.all_passed else "Factory Self-Test FAIL!")
        )
        return s
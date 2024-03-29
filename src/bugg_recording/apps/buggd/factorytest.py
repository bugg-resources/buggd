''' This class is used to test the hardware in the factory. It is instantiated and 
run if the trigger file is present. '''

import logging
from bugg_recording.drivers.modem import Modem
import subprocess

class FactoryTest:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.results = {
            "modem_enumerates": False,
            "modem_responsive": False,
            "modem_sim_readable": False,
            "modem_towers_found": False,
            "i2s_bridge_responding": False,
            "rtc_responding": False,
            "led_controller responding": False,
            "internal_microphone_signal_present": False,
            "external_microphone_signal_present": False,
        }

    def run(self):
        self.logger.info("Factory test running.")
        
        self.logger.info("Testing modem.")
        self.test_modem() 
        self.logger.info("Testing I2C devices.")
        self.test_i2c_devices()
        self.logger.info("Testing recording.")
        self.test_recording()
        
        self.logger.info("Factory test completed.")
        self.logger.info("Results: %s", self.get_results_string())
        return True

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
        pass
    
    def test_recording(self):
        pass

    def get_results(self):
        return self.results
    
    def get_results_string(self):
        return "\n".join([f"{k}: {v}" for k, v in self.results.items()])
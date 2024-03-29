''' This class is used to test the hardware in the factory. It is instantiated and 
run if the trigger file is present. '''

import logging
from bugg_recording.drivers.modem import Modem
import subprocess

class FactoryTest:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.results = {
            "modem_enumerated": False,
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
        return True

    def test_modem(self):
        self.logger.info("Testing modem.")

        try:
            subprocess.run(["sudo", "systemctl", "stop", "ModemManager"], check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to stop ModemManager.")
            self.logger.error(e)
            return False

        modem = Modem()
        self.results["modem_enumerated"] = modem.power_on()
            
        
        self.results["modem_responsive"] = self.modem_is_responsive()
        self.results["modem_sim_readable"] = self.modem_is_sim_readable()
        self.results["modem_towers_found"] = self.modem_towers_found()

    def test_i2c_devices(self):
        pass
    
    def test_recording(self):
        pass
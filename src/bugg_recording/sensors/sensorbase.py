import datetime
import time
import subprocess
import os
import logging
from . import set_option

class SensorBase(object):

    def __init__(self, config=None):

        """
        A base class definition to set the methods for Sensor classes.

        Args:
            config: A dictionary loaded from a config JSON file used to update
            the default settings of the sensor.
        """

        # Initialise the sensor config, double checking the types of values. This
        # code uses the variables named and described in the config static to set
        # defaults and override with any passed in the config file.
        opts = self.options()
        opts = {var['name']: var for var in opts}

        # config options
        self.capture_delay = set_option('capture_delay', config, opts)

        # set internal variables and required class variables
        self.current_file = None
        self.working_dir = None
        self.data_dir = None
        self.server_sync_interval = self.capture_delay

    @staticmethod
    def options():
        """
        Static method defining the config options and defaults for the sensor class
        """
        return [{'name': 'capture_delay',
                 'type': int,
                 'default': 86400,
                 'prompt': 'What is the interval in seconds between data capture?'}
                ]

    def setup(self):
        """
        Method to check the sensor is ready for data capture
        """

        pass

    def capture_data(self, working_dir, data_dir):
        """
        Method to capture data.

        Args:
            working_dir: A working directory to use for file processing
            data_dir: The directory to write the final data file to
        """
        self.working_dir = working_dir
        self.data_dir = data_dir
        self.current_file = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')

    def postprocess(self):
        pass

    def cleanup(self):
        pass

    def sleep(self):
        """
        Method to pause between data capture
        """
        time.sleep(self.capture_delay)

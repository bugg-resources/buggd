"""
This module is responsible for setting up the logging for thei buggd application.

On startup, setup_logging() is called to configure the logging to both stdout and a file.
The current time and CPU serial number are used to create a unique log file name.

This means that each boot of the device will create a new log file.
"""

import logging
import os
import time
import sys
from .utils import discover_serial


# The log_dir can't be included in config because we're
# not loading config until after logging has started.
LOG_DIR = '/home/buggd/logs/'

# This establishes the lowest level of logging that will be output in each handler.
# to the console and file. This can be changed to higher levels on a per-module basis.
STDOUT_DEFAULT_LOG_LEVEL = logging.DEBUG
FILE_DEFAULT_LOG_LEVEL = logging.DEBUG


def setup_logging():
    """
    Setup logging for the application

    Called once at the start of the application to setup logging to both stdout and a file
    """
    # Get the unique CPU ID of the device
    cpu_serial = discover_serial()
    # Get the current time - this is the time buggd was started
    start_time = time.strftime('%Y%m%d_%H%M')

    # Create log directory if it doesn't exist, and create a log file name
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
    logfile_name = f'rpi_eco_{cpu_serial}_{start_time}.log'
    logfile = os.path.join(LOG_DIR, logfile_name)

    # Create a logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG) # This is the lowest level of logging that will be output

    # Create a formatter
    formatter = logging.Formatter(f'{cpu_serial} - %(message)s')

    # Handler for stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    # Handler for file
    handler_file = logging.FileHandler(filename=logfile)
    handler_file.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(stdout_handler)
    logger.addHandler(handler_file)

    print("logger name: ", logger.name)
    logger.info(f'Logging to {logfile}')

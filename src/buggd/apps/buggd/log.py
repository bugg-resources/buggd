"""
This module is responsible for setting up the logging for thei buggd application.

On startup, setup_logging() is called to configure the logging to both stdout and a file.
The current time and CPU serial number are used to create a unique log file name.

This means that each boot of the device will create a new log file.
"""

import logging
from logging.handlers import WatchedFileHandler
import os
import time
import sys
import shutil
from .utils import discover_serial


# The log_dir can't be included in config because we're
# not loading config until after logging has started.
LOG_DIR = '/home/buggd/logs/'

# This establishes the lowest level of logging that will be output in each handler.
# to the console and file. This can be changed to higher levels on a per-module basis.
STDOUT_DEFAULT_LOG_LEVEL = logging.DEBUG
FILE_DEFAULT_LOG_LEVEL = logging.DEBUG

class Log:
    """
    Setup logging for the application

    Called once at the start of the application to setup logging to both stdout and a file
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Log, cls).__new__(cls)
            cls._instance.setup_logger(LOG_DIR)
        return cls._instance

    def __init__(self):
        if not self.initialized:
            self.setup_logger(LOG_DIR)
            self.initialized = True

    @staticmethod
    def get_logger():
        """ Get the logger. It's a singleton so everyone gets the same one."""
        return Log().logger

    def setup_logger(self, log_dir):
        """ Setup the logger to log to both stdout and a file"""
        self.log_dir = log_dir
        self.current_logfile_name = ''
        self.cpu_serial = discover_serial()

        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)

        # Create a logger
        self.logger = logging.getLogger(__name__)

        # This is the lowest level of logging that will be output
        self.logger.setLevel(logging.DEBUG)

        # Create a formatter
        self.formatter = logging.Formatter(f'{self.cpu_serial} - %(message)s')

        # Handler for stdout
        self.stdout_handler = logging.StreamHandler(sys.stdout)
        self.stdout_handler.setLevel(STDOUT_DEFAULT_LOG_LEVEL)
        self.stdout_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.stdout_handler)

        # Handler for file is created in rotate_log()
        self.file_handler = None
        self.logger.info('Logging to stdout started')

    def get_current_logfile(self):
        """
        Return the full path of the current log file that is being written to
        We use this in in the uploading thread to avoid moving the open file
        """
        return self.current_logfile_name


    def generate_new_logfile_name(self):
        """ Generate a new log file name based on the current time and CPU serial number """
        # Get the current time - this is the time buggd was started
        start_time = time.strftime('%Y%m%d_%H%M')

        fn = f'rpi_eco_{self.cpu_serial}_{start_time}.log'
        return os.path.join(self.log_dir, fn)


    def rotate_log(self):
        """
        Rotate the log file by closing the current one and creating a new one
        """
        if self.file_handler:
            self.logger.removeHandler(self.file_handler)

        fn = self.generate_new_logfile_name()
        new_handler = WatchedFileHandler(filename=fn)
        new_handler.setLevel(FILE_DEFAULT_LOG_LEVEL)
        new_handler.setFormatter(self.formatter)
        self.logger.addHandler(new_handler)

        self.logger.info('Logging to file %s', fn)


    def move_archived_to_dir(self, upload_dir):
        """ Move the archived log files to the upload directory """
        try:
            upload_dir_logs = os.path.join(upload_dir, 'logs')
            if not os.path.exists(upload_dir_logs):
                os.makedirs(upload_dir_logs)

            log_dir = self.log_dir

            existing_logs = [f for f in os.listdir(log_dir)
                             if f.endswith('.log')
                                and f != os.path.basename(self.get_current_logfile())]

            for log in existing_logs:
                shutil.move(os.path.join(log_dir, log),
                        os.path.join(upload_dir_logs, log))
                self.logger.info('Moved %s to upload', log)
        except OSError:
            # not critical - can leave logs in the log_dir
            self.logger.error('Could not move existing logs to upload.')
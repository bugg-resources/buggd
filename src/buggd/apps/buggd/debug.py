import traceback
import sys

import logging

# NOTE: to enable tracebacks, set the logger level to logging.DEBUG
# and set ENABLE_TRACEBACKS to True
ENABLE_TRACEBACKS = False

class Debug:
    """ Class that demonstrates logging at different levels"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def hello_logger(self):
        """ Method that demonstrates logging at different levels"""
        self.logger.debug('logging.DEBUG from DebugClass')
        self.logger.info('logging.INFO from DebugClass')
        self.logger.warning('logging.WARNING from DebugClass')
        self.logger.error('logging.ERROR from DebugClass')
        self.logger.critical('logging.CRITICAL from DebugClass')


    def write_traceback_to_log(self):
        """
        Print detailed information about an exception, including the file, class, and line number where it occurred, 
        along with a stack trace.
        """
        if not ENABLE_TRACEBACKS:
            self.logger.debug('Tracebacks are disabled')
            return

        # Fetching the current exception information
        exc_type, exc_value, exc_traceback = sys.exc_info()

        # Extracting the stack trace
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        self.logger.debug('Detailed Exception Traceback:')
        self.logger.debug(''.join(tb_lines))

        # Extract the last traceback object which points to where the exception was raised
        while exc_traceback.tb_next:
            exc_traceback = exc_traceback.tb_next
        frame = exc_traceback.tb_frame

        # Extracting file name (module) and line number
        file_name = frame.f_code.co_filename
        line_number = exc_traceback.tb_lineno

        # Attempting to extract the class name, if any
        class_name = frame.f_locals.get('self', None).__class__.__name__ if 'self' in frame.f_locals else None

        # self.logger.debuging extracted details
        self.logger.debug('Exception occurred in file: %s', file_name)
        if class_name:
            self.logger.debug('Exception occurred in class: %s', class_name)
        self.logger.debug('Exception occurred at line: %s, ', line_number)


    def divide_by_zero(self):
        """ Function that raises a divide by zero exception """
        try:
            _ = 1/0
        except Exception:
            self.write_traceback_to_log()
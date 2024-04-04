import traceback
import sys

import logging
from .log import Log

# NOTE: to enable tracebacks, set the logger level to logging.DEBUG
# and set ENABLE_TRACEBACKS to True
ENABLE_TRACEBACKS = False


logger = Log.get_logger(__name__)
logger.setLevel(logging.DEBUG)

class Debug:
    """ Class that demonstrates logging at different levels"""

    def hello_logger(self):
        """ Method that demonstrates logging at different levels"""
        logger.debug('logging.DEBUG from DebugClass')
        logger.info('logging.INFO from DebugClass')
        logger.warning('logging.WARNING from DebugClass')
        logger.error('logging.ERROR from DebugClass')
        logger.critical('logging.CRITICAL from DebugClass')


    def write_traceback_to_log(self):
        """
        Print detailed information about an exception, including the file, class, and line number where it occurred, 
        along with a stack trace.
        """
        if not ENABLE_TRACEBACKS:
            logger.debug('Tracebacks are disabled')
            return

        # Fetching the current exception information
        exc_type, exc_value, exc_traceback = sys.exc_info()

        # Extracting the stack trace
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        logger.debug('Detailed Exception Traceback:')
        logger.debug(''.join(tb_lines))

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
        logger.debug('Exception occurred in file: %s', file_name)
        if class_name:
            logger.debug('Exception occurred in class: %s', class_name)
        logger.debug('Exception occurred at line: %s, ', line_number)


    def divide_by_zero(self):
        """ Function that raises a divide by zero exception """
        try:
            _ = 1/0
        except Exception:
            self.write_traceback_to_log()
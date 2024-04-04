import traceback
import sys

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ENABLE_TRACEBACKS = True

def write_traceback_to_log(exception):
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

    # logger.debuging extracted details
    logger.debug(f'Exception occurred in file: {file_name}')
    if class_name:
        logger.debug(f'Exception occurred in class: {class_name}')
    logger.debug(f'Exception occurred at line: {line_number}')


def divide_by_zero():
    """ Function that raises a divide by zero exception """
    try:
        _ = 1/0
    except Exception as e:
        write_traceback_to_log(e)
""" This module provides a locking mechanism to ensure that only one instance of a driver is running at a time."""

import logging
from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class Lock:
    """
    For a given lock file, this class can only be instantiated once.
    If another instance of the class is created with the same lock file, it will raise an exception. 
    This is useful for ensuring that only one instance of a driver is running at a time, both 
    within the same application and across multiple applications.
    """

    def __init__(self, lock_file):
        self.lock_path = lock_file
        self.lock = FileLock(self.lock_path)
        try:
            # Attempt to acquire the lock
            self.lock.acquire(timeout=2)
            logger.debug("Lock acquired on %s", self.lock_path)
        except Timeout as e:
            raise RuntimeError(f"Could not acquire lock on {lock_file} - Another instance is already in use.") from e

    def release_lock(self):
        """ Release the lock file """
        if self.lock.is_locked:
            self.lock.release()
            logger.debug("Released lock on %s", self.lock_path)

    def __del__(self):
        """ Release the lock file when the object is deleted"""
        self.release_lock()



""" """
import logging
from filelock import FileLock, Timeout

logging.getLogger().setLevel(logging.DEBUG)

class Lock:
    """ This class creates a lock file to prevent multiple instances of an applicatoin from accessing a resource. """
    def __init__(self, lock_path):
        self.lock_path = lock_path
        self.lock = FileLock(self.lock_path)
        try:
            # Attempt to acquire the lock
            self.lock.acquire(timeout=2)
            logging.debug("Lock acquired on %s", self.lock_path)
        except Timeout as e:
            raise RuntimeError(f"Could not acquire lock on {lock_path} - Another instance is already running.") from e

    def release_lock(self):
        """ Release the lock file """
        if self.lock.is_locked:
            self.lock.release()
            logging.debug("Released lock on %s", self.lock_path)

    def __del__(self):
        """ Release the lock file when the object is deleted"""
        self.release_lock()



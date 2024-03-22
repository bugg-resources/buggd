# singleton.py
from filelock import Timeout, FileLock

class Singleton:
    _lock_path = "/tmp/singleton_app.lock"

    def __init__(self):
        self.lock = FileLock(f"{Singleton._lock_path}")
        try:
            # Attempt to acquire the lock immediately upon instance creation.
            self.lock.acquire(timeout=1)
            print("Singleton lock acquired, instance is running.")
        except Timeout:
            raise RuntimeError("Another instance is already running.")

    def release_lock(self):
        if self.lock.is_locked:
            self.lock.release()
            print("Singleton lock released.")

    def __del__(self):
        self.release_lock()

# singleton.py
from filelock import FileLock, Timeout

class Singleton:
    _lock_path = "/tmp/singleton_app.lock"

    def __init__(self):
        try:
            self.lock = FileLock(f"{Singleton._lock_path}.lock", thread_local=False)
            with self.lock.acquire(timeout=1):
                print("Singleton instance is running.")
        except Timeout:
            raise RuntimeError("Another instance of the Singleton class is already running.")

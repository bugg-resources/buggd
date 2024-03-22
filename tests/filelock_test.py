from filelock import FileLock, Timeout
import sys

class SingletonApp:
    def __init__(self, lock_file):
        self.lock_file = lock_file
        try:
            self.lock = FileLock(f"{self.lock_file}.lock")
            # Try to acquire the lock within a timeout period.
            with self.lock.acquire(timeout=1):
                print("Lock acquired, running the application.")
                self.run()
        except Timeout:
            print("Another instance of the application is already running.")
            sys.exit(1)

    def run(self):
        print("Application is running. Press Ctrl+C to exit.")
        try:
            # Simulate application running; replace with real application logic.
            while True:
                pass
        except KeyboardInterrupt:
            print("Application is exiting.")

if __name__ == "__main__":
    app = SingletonApp("/tmp/app_lock_file")

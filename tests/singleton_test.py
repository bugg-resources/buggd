# app.py
from singleton import Singleton
import sys
import time

def main():
    try:
        singleton_instance = Singleton()
        # Simulate application work
        print("Main application is running. Press Ctrl+C to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Application is exiting.")
    except RuntimeError as e:
        print(e)
        sys.exit(1)
    finally:
        # Ensure the lock is released when the application is closing.
        singleton_instance.release_lock()

if __name__ == "__main__":
    main()

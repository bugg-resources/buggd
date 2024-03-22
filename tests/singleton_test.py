# app.py
from singleton import Singleton
import sys

def main():
    try:
        instance = Singleton()
        # Simulate some work
        print("Main application is running. Press Ctrl+C to exit.")
        while True:
            pass
    except RuntimeError as e:
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    main()

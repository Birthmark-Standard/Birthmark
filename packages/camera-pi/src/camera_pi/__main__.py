"""
Main entry point for running camera_pi as a module.

Allows running:
    python -m camera_pi capture --use-certificates --mock
"""

from .main import main

if __name__ == "__main__":
    main()

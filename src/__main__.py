"""
Allow the src module to be executed as: python -m src
This enables su_logging.py to launch the meter GUI.
"""

import sys

# Import the main function from your main.py file
from .main import main

if __name__ == "__main__":
    # Run main() and pass its return value to sys.exit()
    # This ensures your terminal knows if the app closed successfully or crashed
    sys.exit(main())

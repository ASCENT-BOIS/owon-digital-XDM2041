"""
Allow the src module to be executed as: python -m src
This enables su_logging.py to launch the meter GUI.
"""
from .meter_gui import main

if __name__ == '__main__':
    main()

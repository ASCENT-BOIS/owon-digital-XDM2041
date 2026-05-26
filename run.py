# run.py
import multiprocessing
import sys

from src.main import main

# Import the entry point for your GUI script
# (Adjust this import to match whatever function actually starts meter_gui)
from src.meter_gui import main as meter_gui_main

if __name__ == "__main__":
    # Required for PyInstaller multi-process stability
    multiprocessing.freeze_support()

    # Check if this process was spawned by your subprocess code
    if "--run-meter-gui" in sys.argv:
        meter_gui_main()
    else:
        # Otherwise, run the normal main application
        main()

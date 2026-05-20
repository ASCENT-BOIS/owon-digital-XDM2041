import pyvisa

# Function that Resets the Machine when the Application is Closed.
def shutdown(inst):
    """Send device back to local mode"""
    try:
        if inst:
            inst.write('SYST:LOCAL')
            inst.close()
    except Exception as e:
        print(f"Shutdown error: {e}")

# Function that Tests "def shutdown(inst):"
def test_shutdown():
    """Test the shutdown function"""
    print("Testing shutdown function...")
    try:
        rm = pyvisa.ResourceManager('@py')
        inst = rm.open_resource('ASRL/dev/cu.usbserial-1130::INSTR')

        inst.baud_rate = 115200
        inst.data_bits = 8
        inst.stop_bits = pyvisa.constants.StopBits.one
        inst.parity = pyvisa.constants.Parity.none
        inst.timeout = 3000
        inst.read_termination = '\n'
        inst.write_termination = '\n'

        # Test device connection
        device_id = inst.query('*IDN?')
        print(f"✓ Connected: {device_id}")

        # Put device into remote mode before waiting for quit
        try:
            inst.write('SYST:REM')
            print("✓ Device set to REMOTE mode")
        except Exception as e:
            print(f"Warning: failed to set REMOTE mode: {e}")

        # Test shutdown using 'q' to quit
        while True:
            choice = input("Press 'q' then Enter to shutdown and quit: ").strip().lower()
            if choice == 'q':
                shutdown(inst)
                print("✓ Shutdown successful")
                break
            print("Please press only 'q' to quit.")

    except Exception as e:
        print(f"✗ Test failed: {e}")



import pyvisa
import time
import decimal

rm = pyvisa.ResourceManager('@py')
inst = rm.open_resource('ASRL/dev/cu.usbserial-1130::INSTR')

inst.baud_rate = 115200  # XDM2041 uses 115200, not 9600
inst.data_bits = 8
inst.stop_bits = pyvisa.constants.StopBits.one
inst.parity = pyvisa.constants.Parity.none
inst.timeout = 3000
inst.read_termination = '\n'
inst.write_termination = '\n'

print(inst.query('*IDN?'))

print(inst.query('FUNC?'))

inst.write('SYST:REM')
time.sleep(0.5)  # longer delay
inst.write('CONF:CAP')
time.sleep(0.2)

print(inst.query("FUNC?"))

while True:
    raw = inst.query('MEAS?').strip()
    value = float(raw)
    print(f"{value:.13f} μF")
    time.sleep(0.1)

def get_data(inst):
    return inst.query("MEAS?")
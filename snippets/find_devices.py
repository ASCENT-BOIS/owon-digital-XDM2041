import time

import pyvisa

rm = pyvisa.ResourceManager("@py")

inst = rm.open_resource("ASRL/dev/cu.usbserial-1130::INSTR")
inst.baud_rate = 9600
inst.data_bits = 7
inst.stop_bits = pyvisa.constants.StopBits.one
inst.parity = pyvisa.constants.Parity.even
inst.flow_control = pyvisa.constants.ControlFlow.dtr_dsr
inst.timeout = 5000
inst.read_termination = "\r\n"
inst.write_termination = "\r\n"

inst.clear()
time.sleep(0.1)

# Force the multimeter into remote mode (CRITICAL for HP 34401A over RS232)
inst.write("SYST:REM")
time.sleep(0.1)

time.sleep(0.5)
print(inst.query("*IDN?"))

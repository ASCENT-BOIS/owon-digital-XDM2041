import pyvisa
rm = pyvisa.ResourceManager('@py')
print(rm.list_resources())


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

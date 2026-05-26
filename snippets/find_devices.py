import time

import pyvisa

rm = pyvisa.ResourceManager("@py")
print(rm.list_resources())

# inst = rm.open_resource("USB0::0x0957::0x0007::INSTR")
# inst.timeout = 5000
# print(inst.query("*IDN?"))

# inst = rm.open_resource("ASRL/dev/cu.usbserial-1130::INSTR")
# inst.baud_rate = 9600
# inst.data_bits = 7
# inst.stop_bits = pyvisa.constants.StopBits.one
# inst.parity = pyvisa.constants.Parity.even
# inst.flow_control = pyvisa.constants.ControlFlow.none
# inst.timeout = 5000
# inst.read_termination = "\r\n"
# inst.write_termination = "\r"


# # Prologix-specific setup (send before any instrument commands)
# inst.write("++mode 1")  # Controller mode
# inst.write("++addr 22")  # Set GPIB address of your 34401A (check instrument menu)
# inst.write("++auto 1")  # Auto-read after query
# inst.write("++eos 2")  # Append \r\n to commands
# inst.write("++eoi 1")  # Assert EOI

# inst.write("++ver")
# time.sleep(0.3)
# print(inst.read())

# # Basic communication
# time.sleep(1)
# inst.write("*IDN?")

# time.sleep(0.5)

# print(inst.read())

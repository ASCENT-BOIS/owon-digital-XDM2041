# import usb.core

# dev = usb.core.find(idVendor=0x0957)
# print(
#     f"VID: {hex(dev.idVendor)}, PID: {hex(dev.idProduct)}, Serial: {dev.serial_number}"
# )

import pyvisa
import usb.core
import usb.util

dev = usb.core.find(idVendor=0x0957, idProduct=0x0007)

# Set active configuration before doing anything else
dev.set_configuration()

# Now check/claim the interface
try:
    if dev.is_kernel_driver_active(0):
        print("Kernel driver active, detaching...")
        dev.detach_kernel_driver(0)
    else:
        print("No kernel driver, good")
except usb.core.USBError as e:
    print(f"USBError: {e}")

# Claim the interface
usb.util.claim_interface(dev, 0)
print("Interface claimed successfully")

# Now let pyvisa take over
rm = pyvisa.ResourceManager("@py")
inst = rm.open_resource("USB0::0x0957::0x0007::0::0::INSTR")
inst.timeout = 5000
print(inst.query("*IDN?"))

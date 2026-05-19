import tkinter as tk
from tkinter import ttk
import threading


class DeviceController:
    def __init__(self, root, output_text):
        self.root = root
        self.output = output_text
        self.inst = None
        self.countdown = 0

        # Configure text tags for colors
        self.output.tag_config("connected", foreground="lime")
        self.output.tag_config("error", foreground="red")
        self.output.tag_config("disconnected", foreground="yellow")

        # Store latest device state
        self.connected = False
        self.device_message = ""
        self.error_message = ""

        # Start the check loop
        self.check_device()

    def check_device(self):
        """Check device connection every 5 seconds"""

        # Reset countdown
        self.countdown = 5

        # Run device check in thread
        threading.Thread(target=self._check_thread, daemon=True).start()

        # Start countdown loop
        self.update_countdown()

    def update_countdown(self):
        """Update the countdown display"""

        self.output.config(state="normal")
        self.output.delete("1.0", "end")

        # CONNECTED STATE
        if self.connected:

            self.output.insert("end", "CONNECTED\n\n", "connected")

            # Device info
            self.output.insert("end", f"{self.device_message}\n\n")

        # DISCONNECTED STATE
        else:

            self.output.insert("end", "DISCONNECTED\n\n", "disconnected")

            # Error message
            self.output.insert("end", f"{self.error_message}\n\n")

            # Troubleshooting
            self.output.insert("end", "Troubleshooting:\n")
            self.output.insert("end", "• Check USB cable connection\n")
            self.output.insert("end", "• Verify device is powered on\n")
            self.output.insert("end", "• Run: ls /dev/cu.* in terminal\n\n")

        # Countdown line
        self.output.insert(
            "end",
            f"Retrying in 5 Sec. [ {self.countdown} s. / 5 s. ]"
        )

        self.output.config(state="disabled")

        # Continue countdown
        if self.countdown > 0:

            self.countdown -= 1
            self.root.after(1000, self.update_countdown)

        else:

            self.check_device()

    def _check_thread(self):
        """Run device check in separate thread"""

        try:
            import pyvisa

            rm = pyvisa.ResourceManager('@py')

            self.inst = rm.open_resource(
                'ASRL/dev/cu.usbserial-1130::INSTR'
            )

            self.inst.baud_rate = 115200
            self.inst.data_bits = 8
            self.inst.stop_bits = pyvisa.constants.StopBits.one
            self.inst.parity = pyvisa.constants.Parity.none
            self.inst.timeout = 3000
            self.inst.read_termination = '\n'
            self.inst.write_termination = '\n'

            # Query device info IF DEVICE CONNECTED
            device_id = self.inst.query('*IDN?')

            # Format device info with descriptive labels
            parts = device_id.strip().split(',')

            labels = [
                "Brand",
                "Model",
                "Serial #",
                "Version"
            ]

            formatted_lines = ["Device Info:"]

            for i, part in enumerate(parts):

                if i < len(labels):

                    formatted_lines.append(
                        f"• {labels[i]}: {part}"
                    )

                else:

                    formatted_lines.append(f"• {part}")

            formatted_id = "\n".join(formatted_lines)

            # Save connected state
            self.connected = True
            self.device_message = formatted_id
            self.error_message = ""

            self.inst.close()

        except Exception as e:

            # Save disconnected state
            self.connected = False
            self.device_message = ""
            self.error_message = str(e)


def create_window():

    root = tk.Tk()

    root.title("owon XDM2041 DM Controller")

    root.geometry("1000x200")

    root.resizable(False, False)

    # Output terminal with larger text
    output_text = tk.Text(
        root,
        height=20,
        width=30,
        bg="black",
        fg="white",
        font=("Courier", 14)
    )

    output_text.pack(
        padx=10,
        pady=10,
        fill="both",
        expand=False
    )

    output_text.insert(
        "1.0",
        "Starting device check..."
    )

    return root, output_text


if __name__ == "__main__":

    root, output = create_window()

    controller = DeviceController(root, output)

    root.mainloop()
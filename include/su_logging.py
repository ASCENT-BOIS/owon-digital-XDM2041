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
        
        # Start the check loop
        self.check_device()
    
    def check_device(self):
        """Check device connection every 5 seconds"""
        threading.Thread(target=self._check_thread, daemon=True).start()

        # Start countdown
        self.countdown = 5
        self.update_countdown()
    
    def update_countdown(self):
        """Update the countdown display"""
        if self.countdown > 0:
            self.output.config(state="normal")
            
            # Get current content and check if countdown already exists
            content = self.output.get("1.0", "end-1c")
            lines = content.split('\n')
            
            # Only show countdown for disconnected state
            if "DISCONNECTED" not in content:

                # For connected state, just keep the message as is
                self.output.config(state="disabled")
                self.countdown -= 1
                self.root.after(1000, self.update_countdown)
                return
            
            # Find where the troubleshooting section starts
            error_end = 0
            for i, line in enumerate(lines):
                if line.startswith("[Errno"):
                    error_end = i
                    break
            
            # Rebuild text with colors, keeping only error message
            self.output.delete("1.0", "end")
            
            # Re-insert with color tags if disconnected
            self.output.insert("end", "DISCONNECTED\n\n", "disconnected")

            # Add only the error message (not troubleshooting)
            if error_end > 0:
                self.output.insert("end", lines[error_end] + "\n")
            self.output.insert("end", "\n")  # Add blank line after error

            # Add troubleshooting
            self.output.insert("end", "Troubleshooting:\n")
            self.output.insert("end", "• Check USB cable connection\n")
            self.output.insert("end", "• Verify device is powered on\n")
            self.output.insert("end", "• Run: ls /dev/cu.* in terminal\n\n")

            
            # Add countdown line
            self.output.insert("end", f"Retrying in 5 Sec. [ {self.countdown} s. / 5 s. ]")
            self.output.config(state="disabled")
            
            self.countdown -= 1
            self.root.after(1000, self.update_countdown)
        else:
            self.check_device()
    
    def _check_thread(self):
        """Run device check in separate thread"""
        try:
            import pyvisa
            
            rm = pyvisa.ResourceManager('@py')
            self.inst = rm.open_resource('ASRL/dev/cu.usbserial-1130::INSTR')
            
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
            labels = ["Brand", "Model", "Serial #", "Version"]
            
            formatted_lines = ["Device Info:"]
            for i, part in enumerate(parts):
                if i < len(labels):
                    formatted_lines.append(f"• {labels[i]}: {part}")
                else:
                    formatted_lines.append(f"• {part}")
            
            formatted_id = "\n".join(formatted_lines)
            
            self.output.config(state="normal")
            self.output.delete("1.0", "end")
            self.output.insert("end", f"CONNECTED\n\n", "connected")
            self.output.insert("end", f"{formatted_id}\n\n")
            self.output.insert("end", f"Retrying in 5 Sec. [ {self.countdown} s. / 5 s. ]")
            self.output.config(state="disabled")
            
            self.inst.close()
            
        except Exception as e:
            self.output.config(state="normal")
            self.output.delete("1.0", "end")
            self.output.insert("end", f"DISCONNECTED\n\n", "disconnected")
            self.output.insert("end", f"{str(e)}\n\n")
            self.output.insert("end", "Troubleshooting:\n")
            self.output.insert("end", "• Check USB cable connection\n")
            self.output.insert("end", "• Verify device is powered on\n")
            self.output.insert("end", "• Run: ls /dev/cu.* in terminal\n\n")
            self.output.config(state="disabled")

def create_window():
    root = tk.Tk()
    root.title("owon XDM2041 DM Controller")
    root.geometry("1000x200")
    
    # Output terminal with larger text
    output_text = tk.Text(root, height=20, width=30, bg="black", fg="white", font=("Courier", 14))
    output_text.pack(padx=10, pady=10, fill="both", expand=True)
    output_text.insert("1.0", "Starting device check...")
    
    return root, output_text

if __name__ == "__main__":
    root, output = create_window()
    controller = DeviceController(root, output)
    root.mainloop()


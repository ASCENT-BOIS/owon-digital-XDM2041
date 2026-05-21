import threading
import tkinter as tk
from tkinter import ttk


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

        # Track whether GUI has been launched
        self.gui_started = False
        self.gui_proc = None

        # Guard to avoid multiple countdown loops
        self.countdown_running = False

        # Start the check loop
        self.check_device()

    def check_device(self):
        """Check device connection every 5 seconds"""

        # Reset countdown
        self.countdown = 5

        # Run device check in thread
        threading.Thread(target=self._check_thread, daemon=True).start()

        # Start countdown loop if not already running
        if not self.countdown_running:
            self.update_countdown()

    def _render_display(self):
        """Render the output display based on current state and countdown."""
        try:
            self.output.config(state="normal")
            self.output.delete("1.0", "end")

            if self.connected:
                self.output.insert("end", "CONNECTED\n\n", "connected")
                self.output.insert("end", f"{self.device_message}\n\n")
            else:
                self.output.insert("end", "DISCONNECTED\n\n", "disconnected")
                self.output.insert("end", f"{self.error_message}\n\n")
                self.output.insert("end", "Troubleshooting:\n")
                self.output.insert("end", "• Check USB cable connection.\n")
                self.output.insert("end", "• Verify device is powered on.\n")
                self.output.insert("end", "• Run: ls /dev/cu.* in terminal.\n\n")

            # Countdown line
            self.output.insert(
                "end", f"Retrying in 5 Sec. [ {self.countdown} s. / 5 s. ]"
            )

            self.output.config(state="disabled")
        except Exception:
            pass

    def update_countdown(self):
        """Update the countdown display"""
        # mark running
        if not self.countdown_running:
            self.countdown_running = True

        # render display
        self._render_display()

        # Continue countdown
        if self.countdown > 0:
            self.countdown -= 1
            self.root.after(1000, self.update_countdown)
        else:
            # stop running and trigger a device check
            self.countdown_running = False
            self.check_device()

    def _check_thread(self):
        """Run device check in separate thread"""

        try:
            import pyvisa

            rm = pyvisa.ResourceManager("@py")

            self.inst = rm.open_resource("ASRL/dev/cu.usbserial-1130::INSTR")

            self.inst.baud_rate = 115200
            self.inst.data_bits = 8
            self.inst.stop_bits = pyvisa.constants.StopBits.one
            self.inst.parity = pyvisa.constants.Parity.none
            self.inst.timeout = 3000
            self.inst.read_termination = "\n"
            self.inst.write_termination = "\n"

            # Query device info IF DEVICE CONNECTED
            device_id = self.inst.query("*IDN?")

            # Format device info with descriptive labels
            parts = device_id.strip().split(",")

            labels = ["Brand", "Model", "Serial #", "Version"]

            formatted_lines = ["Device Info:"]

            for i, part in enumerate(parts):
                if i < len(labels):
                    formatted_lines.append(f"• {labels[i]}: {part}")

                else:
                    formatted_lines.append(f"• {part}")

            formatted_id = "\n".join(formatted_lines)

            # Save connected state
            self.connected = True
            self.device_message = formatted_id
            self.error_message = ""

            # reset countdown so UI shows 5/5 on connect
            self.countdown = 5

            # Immediately refresh UI to show connected state right away
            try:
                self.root.after(0, self._render_display)
            except Exception:
                pass

            # Launch or relaunch meter GUI when device is detected
            try:
                import subprocess
                import sys
                from pathlib import Path

                project_root = Path(__file__).resolve().parent.parent
                cmd = [sys.executable, "-m", "src.meter_gui"]

                def _start_proc():
                    try:
                        proc = subprocess.Popen(
                            cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True,
                            cwd=str(project_root),
                        )
                        self.gui_proc = proc
                        self.gui_started = True
                    except Exception:
                        pass

                need_start = False
                if not getattr(self, "gui_proc", None):
                    need_start = True
                else:
                    try:
                        if self.gui_proc.poll() is not None:
                            need_start = True
                    except Exception:
                        need_start = True

                if need_start:
                    try:
                        self.root.after(0, _start_proc)
                    except Exception:
                        threading.Thread(target=_start_proc, daemon=True).start()
            except Exception:
                pass

            try:
                self.inst.close()
            except Exception:
                pass

        except Exception as e:
            # Save disconnected state
            self.connected = False
            self.device_message = ""
            self.error_message = str(e)
            # If we have a running GUI subprocess, terminate it
            try:
                proc = getattr(self, "gui_proc", None)
                if proc is not None:
                    try:
                        if proc.poll() is None:
                            proc.terminate()
                            try:
                                proc.wait(timeout=2)
                            except Exception:
                                proc.kill()
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                self.gui_proc = None
                self.gui_started = False
            except Exception:
                pass


def create_window():
    root = tk.Tk()
    root.title("owon XDM2041 DM Controller")
    root.geometry("1000x200")

    root.resizable(False, False)

    # Output terminal with larger text
    output_text = tk.Text(
        root, height=20, width=30, bg="black", fg="white", font=("Courier", 14)
    )

    output_text.pack(padx=10, pady=10, fill="both", expand=False)

    output_text.insert("1.0", "Starting device check...")

    # Make the terminal non-selectable / non-focusable
    output_text.configure(exportselection=False, takefocus=0, cursor="arrow")

    def _ignore_event(event):
        return "break"

    for seq in (
        "<Button-1>",
        "<B1-Motion>",
        "<Double-Button-1>",
        "<Triple-Button-1>",
        "<ButtonRelease-1>",
        "<Control-c>",
        "<Control-C>",
    ):
        output_text.bind(seq, _ignore_event)

    return root, output_text


def start():
    root, output = create_window()
    DeviceController(root, output)
    root.mainloop()

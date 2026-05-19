import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from .pyvisa_backend import PyVISAMultimeter, SimulatorMultimeter


class MeterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Multimeter Controller')
        self.meter: Optional[PyVISAMultimeter] = None
        self._build()

    def _build(self):
        frm = ttk.Frame(self, padding=8)
        frm.grid(row=0, column=0, sticky='nsew')

        # resources
        ttk.Label(frm, text='Resource:').grid(row=0, column=0)
        self.res_cb = ttk.Combobox(frm, values=self._resources(), state='readonly', width=40)
        self.res_cb.grid(row=0, column=1, sticky='ew')
        ttk.Button(frm, text='Refresh', command=self._refresh).grid(row=0, column=2)
        ttk.Button(frm, text='Connect', command=self._connect).grid(row=0, column=3)

        # mode and range
        ttk.Label(frm, text='Mode:').grid(row=1, column=0)
        self.mode_cb = ttk.Combobox(frm, values=list(PyVISAMultimeter().DEFAULT_MODES), state='readonly')
        self.mode_cb.set('VDC')
        self.mode_cb.grid(row=1, column=1, sticky='ew')
        ttk.Label(frm, text='Range:').grid(row=1, column=2)
        self.range_ent = ttk.Entry(frm)
        self.range_ent.insert(0, 'AUTO')
        self.range_ent.grid(row=1, column=3)

        # controls
        ttk.Button(frm, text='Measure', command=self._measure).grid(row=2, column=0)
        ttk.Button(frm, text='Measure Resistance', command=self._measure_resistance).grid(row=2, column=1)
        ttk.Button(frm, text='Measure Capacitance', command=self._measure_capacitance).grid(row=2, column=2)
        self.stream_btn = ttk.Button(frm, text='Start Stream', command=self._toggle_stream)
        self.stream_btn.grid(row=2, column=3)

        # averaging and calibration
        self.avg_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text='Avg', variable=self.avg_var, command=self._toggle_avg).grid(row=3, column=0)
        self.avg_spin = tk.Spinbox(frm, from_=1, to=100, width=6)
        self.avg_spin.grid(row=3, column=1)
        ttk.Button(frm, text='Calibrate...', command=self._open_calib).grid(row=3, column=2)

        # output
        self.value_var = tk.StringVar(value='---')
        self.unit_var = tk.StringVar(value='')
        ttk.Label(frm, textvariable=self.value_var, font=('Helvetica', 36)).grid(row=4, column=0, columnspan=3)
        ttk.Label(frm, textvariable=self.unit_var, font=('Helvetica', 18)).grid(row=4, column=3)

        self.columnconfigure(0, weight=1)

        # stream state
        self._streaming = False

    def _resources(self):
        try:
            return PyVISAMultimeter.list_resources() or ['SIMULATE']
        except Exception:
            return ['SIMULATE']

    def _refresh(self):
        vals = self._resources()
        self.res_cb.config(values=vals)
        if vals:
            self.res_cb.set(vals[0])

    def _connect(self):
        sel = self.res_cb.get().strip() or 'SIMULATE'
        # create a PyVISAMultimeter instance
        backend = PyVISAMultimeter()
        try:
            backend.connect(sel, simulate=(sel.upper() == 'SIMULATE'))
        except Exception as e:
            messagebox.showerror('Connect failed', str(e))
            return
        self.meter = backend
        messagebox.showinfo('Connected', f'Connected to {sel}')

    def _measure(self):
        if not self.meter:
            messagebox.showwarning('Not connected', 'Connect first')
            return
        self.meter.set_mode(self.mode_cb.get())
        self.meter.set_range(self.range_ent.get())
        try:
            v, u = self.meter.measure()
            self.value_var.set(f"{v:.6g}")
            self.unit_var.set(u)
        except Exception as e:
            messagebox.showerror('Measure failed', str(e))

    def _measure_resistance(self):
        if not self.meter:
            messagebox.showwarning('Not connected', 'Connect first')
            return
        self.meter.set_resistance_range(self.range_ent.get())
        try:
            v, u = self.meter.measure_resistance()
            self.value_var.set(f"{v:.6g}")
            self.unit_var.set(u)
        except Exception as e:
            messagebox.showerror('Measure failed', str(e))

    def _measure_capacitance(self):
        if not self.meter:
            messagebox.showwarning('Not connected', 'Connect first')
            return
        self.meter.set_capacitance_range(self.range_ent.get())
        try:
            v, u = self.meter.measure_capacitance()
            self.value_var.set(f"{v:.6g}")
            self.unit_var.set(u)
        except Exception as e:
            messagebox.showerror('Measure failed', str(e))

    def _toggle_stream(self):
        if not self.meter:
            messagebox.showwarning('Not connected', 'Connect first')
            return
        if not self._streaming:
            self._streaming = True
            self.stream_btn.config(text='Stop Stream')
            self.meter.start_stream(self._stream_callback, interval=0.2)
        else:
            self._streaming = False
            self.stream_btn.config(text='Start Stream')
            self.meter.stop_stream()

    def _stream_callback(self, v, u):
        # called from background thread — schedule update in main thread
        self.after(0, lambda: (self.value_var.set(f"{v:.6g}"), self.unit_var.set(u)))

    def _toggle_avg(self):
        if not self.meter:
            return
        enabled = bool(self.avg_var.get())
        try:
            self.meter.enable_averaging(enabled)
            self.meter.set_averaging_count(int(self.avg_spin.get()))
        except Exception:
            pass

    def _open_calib(self):
        if not self.meter:
            messagebox.showwarning('Not connected', 'Connect first')
            return
        win = tk.Toplevel(self)
        win.title('Calibration')
        modes = self.meter.DEFAULT_MODES
        vars = {}
        for i, m in enumerate(modes):
            ttk.Label(win, text=m).grid(row=i, column=0)
            v = tk.StringVar(value=str(self.meter.get_calibration_offset(m)))
            ttk.Entry(win, textvariable=v).grid(row=i, column=1)
            vars[m] = v

        def apply_and_close():
            for k, var in vars.items():
                try:
                    self.meter.set_calibration_offset(k, float(var.get()))
                except Exception:
                    pass
            self.meter.save_config()
            win.destroy()

        ttk.Button(win, text='Save', command=apply_and_close).grid(row=len(modes), column=0, columnspan=2)


def main():
    app = MeterGUI()
    app.mainloop()


if __name__ == '__main__':
    main()

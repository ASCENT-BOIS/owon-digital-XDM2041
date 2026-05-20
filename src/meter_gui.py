import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as messagebox
import json
import csv
import os
from typing import Optional

# try:
# from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageFilter
#     PIL_AVAILABLE = True
# except Exception:
#     PIL_AVAILABLE = False


PIL_AVAILABLE = False

from .pyvisa_backend import PyVISAMultimeter, SimulatorMultimeter
from .data_logger import Logger
from tkinter import filedialog


class MeterGUI(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode('System')
        ctk.set_default_color_theme('dark-blue')
        super().__init__()
        self.title('Owon XDM2041 - Controller')
        self.geometry('820x420')

        self.meter: Optional[PyVISAMultimeter] = None

        # build UI
        self._build()

        # show splash briefly
        try:
            self._show_splash()
        except Exception:
            pass

        # internal LED image state
        self._led_img = None
        self._led_photo = None

        # logging state
        self._streaming = False
        self._logging_enabled = False
        self.logger = None
        self.log_dir = 'logs'

    def _build(self):
        frm = ctk.CTkFrame(self, corner_radius=8)
        frm.pack(fill='both', expand=True, padx=12, pady=12)

        # Top row: resources and connect
        ctk.CTkLabel(frm, text='Resource:').grid(row=0, column=0, sticky='w', padx=6, pady=6)
        self.res_cb = ctk.CTkComboBox(frm, values=self._resources(), width=420)
        self.res_cb.grid(row=0, column=1, padx=6, pady=6, sticky='w')
        ctk.CTkButton(frm, text='Refresh', command=self._refresh, width=90).grid(row=0, column=2, padx=6)
        ctk.CTkButton(frm, text='Connect', command=self._connect, width=110).grid(row=0, column=3, padx=6)

        # Mode / Range row
        ctk.CTkLabel(frm, text='Mode:').grid(row=1, column=0, sticky='w', padx=6, pady=6)
        self.mode_cb = ctk.CTkComboBox(frm, values=list(PyVISAMultimeter().DEFAULT_MODES), width=220)
        self.mode_cb.set('VDC')
        self.mode_cb.grid(row=1, column=1, sticky='w', padx=6)

        ctk.CTkLabel(frm, text='Range:').grid(row=1, column=2, sticky='w', padx=6)
        self.range_ent = ctk.CTkEntry(frm, width=140)
        self.range_ent.insert(0, 'AUTO')
        self.range_ent.grid(row=1, column=3, padx=6)

        # Controls row
        self._measure_btn = ctk.CTkButton(frm, text='Measure', width=140, command=lambda: self._animate_and_call(self._measure))
        self._measure_btn.grid(row=2, column=0, padx=6, pady=10)

        self._measure_r_btn = ctk.CTkButton(frm, text='Measure Resistance', width=220, command=lambda: self._animate_and_call(self._measure_resistance))
        self._measure_r_btn.grid(row=2, column=1, padx=6)

        self._measure_c_btn = ctk.CTkButton(frm, text='Measure Capacitance', width=220, command=lambda: self._animate_and_call(self._measure_capacitance))
        self._measure_c_btn.grid(row=2, column=2, padx=6)

        self.stream_btn = ctk.CTkButton(frm, text='Start Stream', width=140, command=lambda: self._animate_and_call(self._toggle_stream))
        self.stream_btn.grid(row=2, column=3, padx=6)

        # Averaging / Calibrate
        self.avg_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frm, text='Avg', variable=self.avg_var, command=self._toggle_avg).grid(row=3, column=0, padx=6, pady=6)
        self.avg_spin = ctk.CTkEntry(frm, width=80)
        self.avg_spin.insert(0, '1')
        self.avg_spin.grid(row=3, column=1, padx=6)
        ctk.CTkButton(frm, text='Calibrate...', command=self._open_calib, width=140).grid(row=3, column=2, padx=6)

        # Logging controls: toggle and choose directory
        self.log_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frm, text='Log', variable=self.log_var, command=self._toggle_logging).grid(row=3, column=3, padx=6)
        ctk.CTkButton(frm, text='Choose Log Dir', command=self._choose_log_dir, width=140).grid(row=3, column=4, padx=6)
        ctk.CTkButton(frm, text='Export TXT', command=self._export_txt, width=120).grid(row=3, column=5, padx=6)
        ctk.CTkButton(frm, text='Export CSV', command=self._export_csv, width=120).grid(row=3, column=6, padx=6)
        self.auto_export_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frm, text='Auto-export on stop', variable=self.auto_export_var).grid(row=3, column=7, padx=6)

        # LED display area (Pillow if available; otherwise text)
        if PIL_AVAILABLE:
            self._led_img = self._render_led('---', '', size=(540, 120))
            self._led_photo = ImageTk.PhotoImage(self._led_img)
            self._display_label = ctk.CTkLabel(frm, image=self._led_photo, text='')
        else:
            self._led_img = None
            self._led_photo = None
            self._display_label = ctk.CTkLabel(frm, text='---', font=('Helvetica', 36))
        self._display_label.grid(row=4, column=0, columnspan=3, padx=6, pady=12)
        self._unit_label = ctk.CTkLabel(frm, text='')
        self._unit_label.grid(row=4, column=3, padx=6)

        # stream indicator
        self._stream_indicator = ctk.CTkLabel(frm, text='●', text_color='#9EA0A5')
        self._stream_indicator.grid(row=0, column=4, padx=(8,0))

        # footer
        self.status_var = ctk.StringVar(value='Ready')
        ctk.CTkLabel(frm, textvariable=self.status_var).grid(row=5, column=0, columnspan=3, sticky='w', padx=6, pady=6)

        # Streaming interval control
        ctk.CTkLabel(frm, text='Interval (s):').grid(row=5, column=3, sticky='e', padx=6)
        self.interval_ent = ctk.CTkEntry(frm, width=100)
        self.interval_ent.insert(0, '0.25')
        self.interval_ent.grid(row=5, column=4, padx=6)

        # grid weights
        for i in range(8):
            frm.grid_columnconfigure(i, weight=1)

    def _resources(self):
        try:
            vals = PyVISAMultimeter.list_resources()
            return vals or ['SIMULATE']
        except Exception:
            return ['SIMULATE']

    def _refresh(self):
        vals = self._resources()
        self.res_cb.configure(values=vals)
        if vals:
            self.res_cb.set(vals[0])

    def _connect(self):
        sel = (self.res_cb.get() or 'SIMULATE').strip()
        backend = PyVISAMultimeter()
        try:
            backend.connect(sel, simulate=(sel.upper() == 'SIMULATE'))
        except Exception as e:
            messagebox.showerror('Connect failed', str(e))
            return
        self.meter = backend
        self.status_var.set(f'Connected: {sel}')

    def _measure(self):
        if not self.meter:
            messagebox.showwarning('Not connected', 'Connect first')
            return
        self.meter.set_mode(self.mode_cb.get())
        self.meter.set_range(self.range_ent.get())
        try:
            v, u = self.meter.measure()
            s = f"{v:.6g}"
            self._update_led_transition(s, u)
            # append to log if enabled
            try:
                self._append_log(v, u, mode=self.mode_cb.get())
            except Exception:
                pass
            self.status_var.set('Last read: OK')
        except Exception as e:
            messagebox.showerror('Measure failed', str(e))
            self.status_var.set('Last read: ERROR')

    def _measure_resistance(self):
        if not self.meter:
            messagebox.showwarning('Not connected', 'Connect first')
            return
        self.meter.set_resistance_range(self.range_ent.get())
        try:
            v, u = self.meter.measure_resistance()
            s = f"{v:.6g}"
            self._update_led_transition(s, u)
            try:
                self._append_log(v, u, mode='OHM')
            except Exception:
                pass
            self.status_var.set('Last read: OK')
        except Exception as e:
            messagebox.showerror('Measure failed', str(e))
            self.status_var.set('Last read: ERROR')

    def _measure_capacitance(self):
        if not self.meter:
            messagebox.showwarning('Not connected', 'Connect first')
            return
        self.meter.set_capacitance_range(self.range_ent.get())
        try:
            v, u = self.meter.measure_capacitance()
            s = f"{v:.6g}"
            self._update_led_transition(s, u)
            try:
                self._append_log(v, u, mode='CAP')
            except Exception:
                pass
            self.status_var.set('Last read: OK')
        except Exception as e:
            messagebox.showerror('Measure failed', str(e))
            self.status_var.set('Last read: ERROR')

    def _toggle_stream(self):
        if not self.meter:
            messagebox.showwarning('Not connected', 'Connect first')
            return
        if not self._streaming:
            self._streaming = True
            self.stream_btn.configure(text='Stop Stream')
            # read interval from UI
            try:
                interval = float(self.interval_ent.get())
                if interval <= 0:
                    interval = 0.25
            except Exception:
                interval = 0.25
            self.meter.start_stream(self._stream_callback, interval=interval)
            self._animate_stream_indicator(True)
            self.status_var.set('Streaming...')
        else:
            self._streaming = False
            self.stream_btn.configure(text='Start Stream')
            self.meter.stop_stream()
            self._animate_stream_indicator(False)
            self.status_var.set('Ready')
            # auto-export and show report if enabled
            try:
                if getattr(self, 'auto_export_var', None) and self.auto_export_var.get():
                    # perform export silently and show report
                    self._auto_export_and_show_report()
            except Exception:
                pass

    def _stream_callback(self, v, u):
        # update UI and write log entry
        def cb():
            self._update_led_transition(f"{v:.6g}", u)
            try:
                self._append_log(v, u, mode=self.mode_cb.get())
            except Exception:
                pass

        self.after(0, cb)

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
        # Use a simple ttk dialog for calibration
        win = tk.Toplevel(self)
        win.title('Calibration Offsets')
        modes = self.meter.DEFAULT_MODES
        entries = {}
        for i, m in enumerate(modes):
            ttk.Label(win, text=m).grid(row=i, column=0, padx=6, pady=4, sticky='w')
            v = tk.StringVar(value=str(self.meter.get_calibration_offset(m)))
            ttk.Entry(win, textvariable=v).grid(row=i, column=1, padx=6, pady=4)
            entries[m] = v

        def save_and_close():
            for k, var in entries.items():
                try:
                    self.meter.set_calibration_offset(k, float(var.get()))
                except Exception:
                    pass
            try:
                self.meter.save_config()
            except Exception:
                pass
            win.destroy()

        ttk.Button(win, text='Save', command=save_and_close).grid(row=len(modes), column=0, columnspan=2, pady=8)

    # -----------------------------
    # LED rendering / animation
    # -----------------------------
    def _render_led(self, text: str, unit: str, size=(540, 120)):
        if not PIL_AVAILABLE:
            # fallback: return None
            return None
        w, h = size
        img = Image.new('RGBA', (w, h), (12, 12, 12, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype('DejaVuSans-Bold.ttf', 56)
        except Exception:
            font = ImageFont.load_default()

        txt = f"{text} {unit}" if unit else text
        tw, th = draw.textsize(txt, font=font)
        x = 12
        y = (h - th) // 2

        # glow layers
        for blur_r, alpha in ((10, 30), (6, 90), (2, 180)):
            glow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            gdraw = ImageDraw.Draw(glow)
            gdraw.text((x, y), txt, font=font, fill=(0, 140, 255, alpha))
            glow = glow.filter(ImageFilter.GaussianBlur(radius=blur_r))
            img = Image.alpha_composite(img, glow)

        draw = ImageDraw.Draw(img)
        draw.text((x, y), txt, font=font, fill=(230, 245, 255, 255))
        return img

    def _update_led_transition(self, new_text: str, unit: str):
        try:
            new_img = self._render_led(new_text, unit, size=(540, 120))
            old_img = self._led_img or new_img
            steps = 6
            for i in range(steps):
                alpha = (i + 1) / steps
                blended = Image.blend(old_img.convert('RGBA'), new_img.convert('RGBA'), alpha)
                photo = ImageTk.PhotoImage(blended)
                self._display_label.configure(image=photo)
                self._display_label.image = photo
                self.update_idletasks()
                self.after(30)
            self._led_img = new_img
            if PIL_AVAILABLE:
                self._led_photo = ImageTk.PhotoImage(self._led_img)
                self._display_label.configure(image=self._led_photo, text='')
                self._display_label.image = self._led_photo
            else:
                self._display_label.configure(text=new_text)
            self._unit_label.configure(text=unit)
        except Exception:
            # fallback show text
            try:
                self._display_label.configure(text=new_text)
                self._unit_label.configure(text=unit)
            except Exception:
                pass

    def _animate_and_call(self, func):
        # small visual flash on button press
        try:
            func()
        except Exception:
            func()

    def _animate_stream_indicator(self, on: bool):
        if on:
            def pulse():
                if not self._streaming:
                    self._stream_indicator.configure(text_color='#9EA0A5')
                    return
                cur = getattr(self, '_stream_state', 0)
                color = '#00C851' if cur == 0 else '#9EA0A5'
                self._stream_indicator.configure(text_color=color)
                self._stream_state = 1 - cur
                self.after(400, pulse)

            pulse()
        else:
            self._stream_indicator.configure(text_color='#9EA0A5')

    # -----------------------------
    # Logging helpers
    # -----------------------------
    def _choose_log_dir(self):
        try:
            d = filedialog.askdirectory(initialdir=self.log_dir or '.')
            if d:
                self.log_dir = d
                self.status_var.set(f'Log dir: {self.log_dir}')
        except Exception:
            pass

    def _toggle_logging(self):
        enabled = bool(self.log_var.get())
        if enabled and not self.logger:
            try:
                self.logger = Logger(log_dir=self.log_dir)
                self._logging_enabled = True
                self.status_var.set(f'Logging to: {self.logger.current_path}')
            except Exception as e:
                messagebox.showerror('Logger error', str(e))
                self.log_var.set(False)
                self._logging_enabled = False
        else:
            self._logging_enabled = False
            self.log_var.set(False)
            self.status_var.set('Logging stopped')

    def _append_log(self, value, unit, mode=None, raw_response=None):
        if not self._logging_enabled or not self.logger:
            return
        try:
            rec = self.logger.make_record(value=value, unit=unit, instrument_id=(self.meter.idn if getattr(self.meter, 'idn', None) else None), mode=mode, range=self.range_ent.get(), averaging_count=(int(self.avg_spin.get()) if self.avg_var.get() else None), calibration_offsets=(getattr(self.meter, 'calibration', None) if self.meter else None), raw_response=raw_response)
            self.logger.append(rec)
        except Exception:
            pass

    def _select_source_file(self):
        # prefer active logger file, otherwise ask user
        path = None
        if self.logger and getattr(self.logger, 'current_path', None):
            path = self.logger.current_path
            if os.path.exists(path):
                return path
        # ask user to pick a JSONL file
        p = filedialog.askopenfilename(title='Select measurements JSONL file', filetypes=[('JSONL','*.jsonl'), ('All','*.*')], initialdir=(self.log_dir or '.'))
        if p:
            return p
        return None

    def _export_txt(self):
        src = self._select_source_file()
        if not src:
            return
        dest = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text','*.txt')], initialfile='res_cap_with_time.txt')
        if not dest:
            return
        try:
            with open(src, 'r', encoding='utf-8') as fh, open(dest, 'w', encoding='utf-8') as oh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    if r.get('mode') in ('OHM', 'CAP'):
                        ts = r.get('timestamp', '')
                        oh.write(f"{ts}\t{r.get('value')}\t{r.get('unit','')}\n")
            messagebox.showinfo('Export complete', f'Wrote {dest}')
        except Exception as e:
            messagebox.showerror('Export failed', str(e))

    def _export_csv(self):
        src = self._select_source_file()
        if not src:
            return
        dest = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')], initialfile='measurements_export.csv')
        if not dest:
            return
        try:
            with open(src, 'r', encoding='utf-8') as fh, open(dest, 'w', newline='', encoding='utf-8') as oh:
                writer = csv.writer(oh)
                writer.writerow(['timestamp', 'measurement_id', 'instrument_id', 'mode', 'value', 'unit'])
                for line in fh:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    writer.writerow([r.get('timestamp',''), r.get('measurement_id',''), r.get('instrument_id',''), r.get('mode',''), r.get('value',''), r.get('unit','')])
            messagebox.showinfo('Export complete', f'Wrote {dest}')
        except Exception as e:
            messagebox.showerror('Export failed', str(e))

    def _auto_export_and_show_report(self):
        # export current logger file to CSV in log_dir and show report window
        src = None
        if self.logger and getattr(self.logger, 'current_path', None):
            src = self.logger.current_path
        if not src or not os.path.exists(src):
            return
        base = os.path.splitext(os.path.basename(src))[0]
        dest = os.path.join(self.log_dir, f"{base}_auto_export.csv")
        try:
            # write CSV
            with open(src, 'r', encoding='utf-8') as fh, open(dest, 'w', newline='', encoding='utf-8') as oh:
                writer = csv.writer(oh)
                writer.writerow(['timestamp', 'measurement_id', 'instrument_id', 'mode', 'value', 'unit'])
                for line in fh:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    writer.writerow([r.get('timestamp',''), r.get('measurement_id',''), r.get('instrument_id',''), r.get('mode',''), r.get('value',''), r.get('unit','')])
            # show report window
            self._show_report_window(dest)
        except Exception:
            pass

    def _show_report_window(self, path):
        # display CSV or JSONL file contents in a table
        win = tk.Toplevel(self)
        win.title('Export Report')
        frame = ttk.Frame(win)
        frame.pack(fill='both', expand=True)
        cols = ('timestamp', 'measurement_id', 'instrument_id', 'mode', 'value', 'unit')
        tree = ttk.Treeview(frame, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120, anchor='center')
        vsb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # load rows
        try:
            if path.lower().endswith('.csv'):
                with open(path, 'r', encoding='utf-8') as fh:
                    rdr = csv.DictReader(fh)
                    for r in rdr:
                        tree.insert('', 'end', values=(r.get('timestamp',''), r.get('measurement_id',''), r.get('instrument_id',''), r.get('mode',''), r.get('value',''), r.get('unit','')))
            else:
                with open(path, 'r', encoding='utf-8') as fh:
                    for line in fh:
                        try:
                            r = json.loads(line)
                        except Exception:
                            continue
                        tree.insert('', 'end', values=(r.get('timestamp',''), r.get('measurement_id',''), r.get('instrument_id',''), r.get('mode',''), r.get('value',''), r.get('unit','')))
        except Exception:
            pass

    # -----------------------------
    # Splash and icon
    # -----------------------------
    def _generate_icon(self, w: int, h: int):
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((4, 4, w-4, h-4), fill=(31, 111, 235, 255))
        try:
            f = ImageFont.truetype('DejaVuSans-Bold.ttf', 18)
        except Exception:
            f = ImageFont.load_default()
        draw.text((w//6, h//6), 'XDM', font=f, fill=(255, 255, 255, 255))
        return img

    def _show_splash(self):
        splash = tk.Toplevel(self)
        splash.overrideredirect(True)
        splash.geometry('360x120+{}+{}'.format(self.winfo_x()+100, self.winfo_y()+100))
        splash.configure(bg='#222222')
        lbl = tk.Label(splash, text='Owon XDM2041 — Initializing', font=('Helvetica', 14), bg='#222222', fg='white')
        lbl.pack(fill='both', expand=True, padx=16, pady=16)
        self.after(900, splash.destroy)


def main():
    app = MeterGUI()
    app.mainloop()


if __name__ == '__main__':
    main()

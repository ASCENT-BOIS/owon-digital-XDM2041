import csv
import json
import os
import tkinter as tk
import tkinter.messagebox as messagebox
from tkinter import ttk
from typing import Optional

import customtkinter as ctk

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk

    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


# PIL_AVAILABLE = False

from tkinter import filedialog

from .data_logger import Logger
from .pyvisa_backend import (
    AGILENT_34401A_PROFILE,
    PyVISAMultimeter,
    SimulatorMultimeter,
)


class MeterGUI(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("dark-blue")
        super().__init__()
        self.title("Owon XDM2041 - Controller")
        self.geometry("820x420")

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
        self.log_dir = "logs"

    def _build(self):
        # two-column polished layout
        frm = ctk.CTkFrame(self, corner_radius=12)
        frm.pack(fill='both', expand=True, padx=14, pady=14)

        # left: controls
        left = ctk.CTkFrame(frm, width=360, corner_radius=12)
        left.grid(row=0, column=0, sticky='nsw', padx=(6,12), pady=6)
        # right: display
        right = ctk.CTkFrame(frm, corner_radius=12)
        right.grid(row=0, column=1, sticky='nsew', padx=(0,6), pady=6)
        frm.grid_columnconfigure(1, weight=1)

        # Controls (left)
        ctk.CTkLabel(left, text='Resource', anchor='w', font=self._font_sm).grid(row=0, column=0, sticky='w', padx=10, pady=(10,4))
        self.res_cb = ctk.CTkComboBox(left, values=self._resources(), width=300)
        self.res_cb.grid(row=1, column=0, padx=10, pady=4, sticky='w')
        ctk.CTkButton(left, text='Refresh', command=self._refresh, width=120).grid(row=1, column=1, padx=6)

        # profile selector and connect
        ctk.CTkLabel(left, text='Profile', anchor='w', font=self._font_sm).grid(row=2, column=0, sticky='w', padx=10, pady=(8,2))
        self.profile_cb = ctk.CTkComboBox(left, values=['Auto-detect', 'Agilent 34401A'], width=200)
        self.profile_cb.set('Auto-detect')
        self.profile_cb.grid(row=3, column=0, padx=10, pady=4, sticky='w')
        ctk.CTkButton(left, text='Connect', command=self._connect, width=120, fg_color=self._accent_color, hover_color='#00e066', font=self._font_sm).grid(row=3, column=1, padx=6)

        # Mode and range
        ctk.CTkLabel(left, text='Mode / Range', anchor='w', font=self._font_sm).grid(row=4, column=0, sticky='w', padx=10, pady=(10,2))
        self.mode_cb = ctk.CTkComboBox(left, values=list(PyVISAMultimeter().DEFAULT_MODES), width=140)
        self.mode_cb.set('VDC')
        self.mode_cb.grid(row=5, column=0, padx=10, pady=4, sticky='w')
        self.range_ent = ctk.CTkEntry(left, width=120)
        self.range_ent.insert(0, 'AUTO')
        self.range_ent.grid(row=5, column=1, padx=6)

        # Action buttons
        btn_frame = ctk.CTkFrame(left, fg_color='transparent')
        btn_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=(12,6), sticky='w')
        self._measure_btn = ctk.CTkButton(btn_frame, text='Measure', width=120, command=lambda: self._animate_and_call(self._measure), font=self._font_sm, fg_color='#2E8BFF', hover_color='#4EA3FF')
        self._measure_btn.grid(row=0, column=0, padx=6, pady=4)
        self._measure_r_btn = ctk.CTkButton(btn_frame, text='Measure Ω', width=140, command=lambda: self._animate_and_call(self._measure_resistance), font=self._font_sm)
        self._measure_r_btn.grid(row=0, column=1, padx=6)
        self._measure_c_btn = ctk.CTkButton(btn_frame, text='Measure F', width=140, command=lambda: self._animate_and_call(self._measure_capacitance), font=self._font_sm)
        self._measure_c_btn.grid(row=0, column=2, padx=6)
        # start with CAP disabled until profile confirms support
        try:
            self._measure_c_btn.configure(state='disabled')
        except Exception:
            pass

        # Stream and interval
        self.stream_btn = ctk.CTkButton(left, text='Start Stream', width=180, command=lambda: self._animate_and_call(self._toggle_stream), font=self._font_sm, fg_color='#FF6B00', hover_color='#FF8633')
        self.stream_btn.grid(row=7, column=0, columnspan=2, padx=10, pady=(8,6))
        ctk.CTkLabel(left, text='Interval (s):').grid(row=8, column=0, sticky='e', padx=6)
        self.interval_ent = ctk.CTkEntry(left, width=80)
        self.interval_ent.insert(0, '0.25')
        self.interval_ent.grid(row=8, column=1, sticky='w')

        # Averaging / Calibrate / Logging / Export
        ctk.CTkCheckBox(left, text='Avg', variable=self.avg_var, command=self._toggle_avg).grid(row=9, column=0, padx=10, pady=6, sticky='w')
        self.avg_spin = ctk.CTkEntry(left, width=80)
        self.avg_spin.insert(0, '1')
        self.avg_spin.grid(row=9, column=1, padx=6, sticky='w')
        ctk.CTkButton(left, text='Calibrate...', command=self._open_calib, width=120).grid(row=10, column=0, padx=10, pady=6)
        ctk.CTkCheckBox(left, text='Log', variable=self.log_var, command=self._toggle_logging).grid(row=10, column=1, padx=6, pady=6, sticky='w')
        ctk.CTkButton(left, text='Choose Log Dir', command=self._choose_log_dir, width=160).grid(row=11, column=0, padx=10, pady=6)
        exp_frame = ctk.CTkFrame(left, fg_color='transparent')
        exp_frame.grid(row=11, column=1, padx=6, pady=6)    
        ctk.CTkButton(exp_frame, text='Export TXT', command=self._export_txt, width=110).grid(row=0, column=0, padx=6)
        ctk.CTkButton(exp_frame, text='Export CSV', command=self._export_csv, width=110).grid(row=0, column=1, padx=6)
        self.auto_export_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(left, text='Auto-export on stop', variable=self.auto_export_var).grid(row=12, column=0, columnspan=2, padx=10, pady=6, sticky='w')

        # status
        self.status_var = ctk.StringVar(value='Ready')
        ctk.CTkLabel(left, textvariable=self.status_var, anchor='w').grid(row=13, column=0, columnspan=2, padx=10, pady=10, sticky='w')

        # Display (right)
        if PIL_AVAILABLE:
            self._led_img = self._render_led('---', '', size=(640, 160))
            self._led_photo = ImageTk.PhotoImage(self._led_img)
            self._display_label = ctk.CTkLabel(right, image=self._led_photo, text='')
        else:
            self._led_img = None
            self._led_photo = None
            self._display_label = ctk.CTkLabel(right, text='---', font=self._font_large, text_color='#E6F5FF')
        self._display_label.pack(fill='both', expand=False, padx=12, pady=18)
        self._unit_label = ctk.CTkLabel(right, text='', font=self._font_med, text_color='#CFEFFF')
        self._unit_label.pack(padx=12)

        # mini-plot (Matplotlib if available, otherwise fallback Canvas)
        if MATPLOTLIB_AVAILABLE:
            self._fig = Figure(figsize=(6, 1.2), dpi=100, facecolor='#0E1620')
            self._ax = self._fig.add_subplot(111)
            self._ax.set_facecolor('#0E1620')
            self._ax.tick_params(colors='#888')
            self._ax.get_xaxis().set_visible(False)
            self._ax.get_yaxis().set_visible(False)
            self._ax.set_xlim(0, self._plot_max_samples)
            self._line, = self._ax.plot([], [], color=self._accent_color, linewidth=2)
            self._canvas_fig = FigureCanvasTkAgg(self._fig, master=right)
            self._canvas_fig.get_tk_widget().pack(fill='x', padx=12, pady=(6,12))
        else:
            self._plot_canvas = tk.Canvas(right, height=80, bg='#0E1620', highlightthickness=0)
            self._plot_canvas.pack(fill='x', padx=12, pady=(6,12))

        # stream indicator and mini-stats
        bottom = ctk.CTkFrame(right, fg_color='transparent')
        bottom.pack(fill='x', padx=12, pady=6)
        self._stream_indicator = ctk.CTkLabel(bottom, text='●', text_color='#9EA0A5')
        self._stream_indicator.pack(side='left', padx=(0,8))
        self._last_read_var = ctk.StringVar(value='Last: ---')
        ctk.CTkLabel(bottom, textvariable=self._last_read_var).pack(side='left')
    def _refresh(self):
        vals = self._resources()
        self.res_cb.configure(values=vals)
        if vals:
            self.res_cb.set(vals[0])

    def _resources(self):
        """Return a list of available VISA resources, preferring SIMULATE."""
        try:
            vals = list(PyVISAMultimeter.list_resources() or [])
        except Exception:
            vals = []
        # ensure SIMULATE is always available as a first choice
        if 'SIMULATE' not in vals:
            vals.insert(0, 'SIMULATE')
        return vals

    def _connect(self):
        sel = (self.res_cb.get() or "SIMULATE").strip()
        backend = PyVISAMultimeter()
        try:
            backend.connect(sel, simulate=(sel.upper() == "SIMULATE"))
        except Exception as e:
            messagebox.showerror("Connect failed", str(e))
            return
        # apply manual profile selection if requested
        prof_choice = (self.profile_cb.get() or "Auto-detect").strip()
        try:
            if prof_choice == "Agilent 34401A":
                # attach agilent profile to backend
                try:
                    backend.instrument_profile = AGILENT_34401A_PROFILE
                    backend.profile = AGILENT_34401A_PROFILE["name"]
                except Exception:
                    pass
        except Exception:
            pass

        self.meter = backend

        # update available modes according to profile (if any)
        try:
            prof = getattr(self.meter, "instrument_profile", None)
            if prof and isinstance(prof, dict):
                modes = list(prof.get("modes", {}).keys())
                if modes:
                    self.mode_cb.configure(values=modes)
                    # ensure CAP not selected when unsupported
                    if "CAP" not in modes and self.mode_cb.get() == "CAP":
                        self.mode_cb.set(modes[0])
                    else:
                        self.mode_cb.set(modes[0])
                    # enable/disable capacitance button based on modes
                    try:
                        if 'CAP' in modes:
                            self._measure_c_btn.configure(state='normal')
                        else:
                            self._measure_c_btn.configure(state='disabled')
                    except Exception:
                        pass
            else:
                self.mode_cb.configure(values=list(PyVISAMultimeter().DEFAULT_MODES))
                try:
                    if 'CAP' in list(PyVISAMultimeter().DEFAULT_MODES):
                        self._measure_c_btn.configure(state='normal')
                    else:
                        self._measure_c_btn.configure(state='disabled')
                except Exception:
                    pass
        except Exception:
            pass

        self.status_var.set(f"Connected: {sel}")

    def _measure(self):
        if not self.meter:
            messagebox.showwarning("Not connected", "Connect first")
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
            self.status_var.set("Last read: OK")
        except Exception as e:
            messagebox.showerror("Measure failed", str(e))
            self.status_var.set("Last read: ERROR")

    def _measure_resistance(self):
        if not self.meter:
            messagebox.showwarning("Not connected", "Connect first")
            return
        self.meter.set_resistance_range(self.range_ent.get())
        try:
            v, u = self.meter.measure_resistance()
            s = f"{v:.6g}"
            self._update_led_transition(s, u)
            try:
                self._append_log(v, u, mode="OHM")
            except Exception:
                pass
            self.status_var.set("Last read: OK")
        except Exception as e:
            messagebox.showerror("Measure failed", str(e))
            self.status_var.set("Last read: ERROR")

    def _measure_capacitance(self):
        if not self.meter:
            messagebox.showwarning("Not connected", "Connect first")
            return
        self.meter.set_capacitance_range(self.range_ent.get())
        try:
            v, u = self.meter.measure_capacitance()
            s = f"{v:.6g}"
            self._update_led_transition(s, u)
            try:
                self._append_log(v, u, mode="CAP")
            except Exception:
                pass
            self.status_var.set("Last read: OK")
        except Exception as e:
            _ = messagebox.showerror("Measure failed", str(e))
            self.status_var.set("Last read: ERROR")

    def _toggle_stream(self):
        if not self.meter:
            _ = messagebox.showwarning("Not connected", "Connect first")
            return
        if not self._streaming:
            self._streaming = True
            self.stream_btn.configure(text="Stop Stream")
            # read interval from UI
            try:
                interval = float(self.interval_ent.get())
                if interval <= 0:
                    interval = 0.25
            except Exception:
                interval = 0.25
            self.meter.start_stream(self._stream_callback, interval=interval)
            self._animate_stream_indicator(True)
            self.status_var.set("Streaming...")
        else:
            self._streaming = False
            self.stream_btn.configure(text="Start Stream")
            self.meter.stop_stream()
            self._animate_stream_indicator(False)
            self.status_var.set("Ready")
            # auto-export and show report if enabled
            try:
                if (
                    getattr(self, "auto_export_var", None)
                    and self.auto_export_var.get()
                ):
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

            # update mini-plot buffer and redraw
            try:
                try:
                    fv = float(v)
                except Exception:
                    fv = None
                if fv is not None:
                    self._plot_samples.append(fv)
                    self._redraw_mini_plot()
            except Exception:
                pass

        self.after(0, cb)

    def _redraw_mini_plot(self):
        try:
            samples = list(self._plot_samples)
            if not samples:
                # clear plot
                if MATPLOTLIB_AVAILABLE and hasattr(self, '_line'):
                    self._line.set_data([], [])
                    self._canvas_fig.draw_idle()
                return

            mn = min(samples)
            mx = max(samples)
            if mx == mn:
                mx = mn + 1.0
            pad = (mx - mn) * 0.08
            mn -= pad
            mx += pad

            if MATPLOTLIB_AVAILABLE and hasattr(self, '_ax'):
                x = list(range(len(samples)))
                # update line
                self._line.set_data(x, samples)
                # clear and draw fill
                try:
                    self._ax.collections.clear()
                except Exception:
                    pass
                self._ax.fill_between(x, samples, [mn] * len(x), color='#003366', alpha=0.25)
                # update limits
                self._ax.set_xlim(0, max(self._plot_max_samples, len(samples)))
                self._ax.set_ylim(mn, mx)
                self._canvas_fig.draw_idle()
                return

            # fallback canvas drawing
            c = getattr(self, '_plot_canvas', None)
            if not c:
                return
            w = c.winfo_width() or c.winfo_reqwidth() or 400
            h = c.winfo_height() or 80
            c.delete('all')
            n = len(samples)
            if n < 2:
                return
            pts = []
            rng = mx - mn
            for i, s in enumerate(samples):
                x = int(i * (w / max(self._plot_max_samples - 1, 1)))
                y = int(h - ((s - mn) / rng) * h)
                pts.append((x, y))
            coords = []
            for (x, y) in pts:
                coords.extend([x, y])
            coords = [0, h] + coords + [w, h]
            c.create_polygon(coords, fill='#003366', outline='')
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i + 1]
                c.create_line(x1, y1, x2, y2, fill='#00C851', width=2)
            lx, ly = pts[-1]
            c.create_oval(lx - 3, ly - 3, lx + 3, ly + 3, fill='#00C851', outline='')
        except Exception:
            pass

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
            messagebox.showwarning("Not connected", "Connect first")
            return
        # Use a simple ttk dialog for calibration
        win = tk.Toplevel(self)
        win.title("Calibration Offsets")
        modes = self.meter.DEFAULT_MODES
        entries = {}
        for i, m in enumerate(modes):
            ttk.Label(win, text=m).grid(row=i, column=0, padx=6, pady=4, sticky="w")
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

        ttk.Button(win, text="Save", command=save_and_close).grid(
            row=len(modes), column=0, columnspan=2, pady=8
        )

    # -----------------------------
    # LED rendering / animation
    # -----------------------------
    def _render_led(self, text: str, unit: str, size=(540, 120)):
        if not PIL_AVAILABLE:
            # fallback: return None
            return None
        w, h = size
        img = Image.new("RGBA", (w, h), (12, 12, 12, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 56)
        except Exception:
            font = ImageFont.load_default()

        txt = f"{text} {unit}" if unit else text
        try:
            tw, th = draw.textsize(txt, font=font)
        except Exception:
            try:
                # Pillow newer versions have textbbox
                bbox = draw.textbbox((0, 0), txt, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            except Exception:
                try:
                    tw, th = font.getsize(txt)
                except Exception:
                    tw, th = (len(txt) * 10, 24)
        x = 12
        y = (h - th) // 2

        # glow layers
        for blur_r, alpha in ((10, 30), (6, 90), (2, 180)):
            glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
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
                blended = Image.blend(
                    old_img.convert("RGBA"), new_img.convert("RGBA"), alpha
                )
                photo = ImageTk.PhotoImage(blended)
                self._display_label.configure(image=photo)
                self._display_label.image = photo
                self.update_idletasks()
                self.after(30)
            self._led_img = new_img
            if PIL_AVAILABLE:
                self._led_photo = ImageTk.PhotoImage(self._led_img)
                self._display_label.configure(image=self._led_photo, text="")
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
                    self._stream_indicator.configure(text_color="#9EA0A5")
                    return
                cur = getattr(self, "_stream_state", 0)
                color = "#00C851" if cur == 0 else "#9EA0A5"
                self._stream_indicator.configure(text_color=color)
                self._stream_state = 1 - cur
                self.after(400, pulse)

            pulse()
        else:
            self._stream_indicator.configure(text_color="#9EA0A5")

    # -----------------------------
    # Logging helpers
    # -----------------------------
    def _choose_log_dir(self):
        try:
            d = filedialog.askdirectory(initialdir=self.log_dir or ".")
            if d:
                self.log_dir = d
                self.status_var.set(f"Log dir: {self.log_dir}")
        except Exception:
            pass

    def _toggle_logging(self):
        enabled = bool(self.log_var.get())
        if enabled and not self.logger:
            try:
                self.logger = Logger(log_dir=self.log_dir)
                self._logging_enabled = True
                self.status_var.set(f"Logging to: {self.logger.current_path}")
            except Exception as e:
                messagebox.showerror("Logger error", str(e))
                self.log_var.set(False)
                self._logging_enabled = False
        else:
            self._logging_enabled = False
            self.log_var.set(False)
            self.status_var.set("Logging stopped")

    def _append_log(self, value, unit, mode=None, raw_response=None):
        if not self._logging_enabled or not self.logger:
            return
        try:
            rec = self.logger.make_record(
                value=value,
                unit=unit,
                instrument_id=(
                    self.meter.idn if getattr(self.meter, "idn", None) else None
                ),
                mode=mode,
                range=self.range_ent.get(),
                averaging_count=(
                    int(self.avg_spin.get()) if self.avg_var.get() else None
                ),
                calibration_offsets=(
                    getattr(self.meter, "calibration", None) if self.meter else None
                ),
                raw_response=raw_response,
            )
            self.logger.append(rec)
        except Exception:
            pass

    def _select_source_file(self):
        # prefer active logger file, otherwise ask user
        path = None
        if self.logger and getattr(self.logger, "current_path", None):
            path = self.logger.current_path
            if os.path.exists(path):
                return path
        # ask user to pick a JSONL file
        p = filedialog.askopenfilename(
            title="Select measurements JSONL file",
            filetypes=[("JSONL", "*.jsonl"), ("All", "*.*")],
            initialdir=(self.log_dir or "."),
        )
        if p:
            return p
        return None

    def _export_txt(self):
        src = self._select_source_file()
        if not src:
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt")],
            initialfile="res_cap_with_time.txt",
        )
        if not dest:
            return
        try:
            with (
                open(src, "r", encoding="utf-8") as fh,
                open(dest, "w", encoding="utf-8") as oh,
            ):
                for line in fh:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    if r.get("mode") in ("OHM", "CAP"):
                        ts = r.get("timestamp", "")
                        oh.write(f"{ts}\t{r.get('value')}\t{r.get('unit', '')}\n")
            messagebox.showinfo("Export complete", f"Wrote {dest}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def _export_csv(self):
        src = self._select_source_file()
        if not src:
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="measurements_export.csv",
        )
        if not dest:
            return
        try:
            with (
                open(src, "r", encoding="utf-8") as fh,
                open(dest, "w", newline="", encoding="utf-8") as oh,
            ):
                writer = csv.writer(oh)
                writer.writerow(
                    [
                        "timestamp",
                        "measurement_id",
                        "instrument_id",
                        "mode",
                        "value",
                        "unit",
                    ]
                )
                for line in fh:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    writer.writerow(
                        [
                            r.get("timestamp", ""),
                            r.get("measurement_id", ""),
                            r.get("instrument_id", ""),
                            r.get("mode", ""),
                            r.get("value", ""),
                            r.get("unit", ""),
                        ]
                    )
            messagebox.showinfo("Export complete", f"Wrote {dest}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def _auto_export_and_show_report(self):
        # export current logger file to CSV in log_dir and show report window
        src = None
        if self.logger and getattr(self.logger, "current_path", None):
            src = self.logger.current_path
        if not src or not os.path.exists(src):
            return
        base = os.path.splitext(os.path.basename(src))[0]
        dest = os.path.join(self.log_dir, f"{base}_auto_export.csv")
        try:
            # write CSV
            with (
                open(src, "r", encoding="utf-8") as fh,
                open(dest, "w", newline="", encoding="utf-8") as oh,
            ):
                writer = csv.writer(oh)
                writer.writerow(
                    [
                        "timestamp",
                        "measurement_id",
                        "instrument_id",
                        "mode",
                        "value",
                        "unit",
                    ]
                )
                for line in fh:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    writer.writerow(
                        [
                            r.get("timestamp", ""),
                            r.get("measurement_id", ""),
                            r.get("instrument_id", ""),
                            r.get("mode", ""),
                            r.get("value", ""),
                            r.get("unit", ""),
                        ]
                    )
            # show report window
            self._show_report_window(dest)
        except Exception:
            pass

    def _show_report_window(self, path):
        # display CSV or JSONL file contents in a table
        win = tk.Toplevel(self)
        win.title("Export Report")
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True)
        cols = ("timestamp", "measurement_id", "instrument_id", "mode", "value", "unit")
        tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120, anchor="center")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # load rows
        try:
            if path.lower().endswith(".csv"):
                with open(path, "r", encoding="utf-8") as fh:
                    rdr = csv.DictReader(fh)
                    for r in rdr:
                        tree.insert(
                            "",
                            "end",
                            values=(
                                r.get("timestamp", ""),
                                r.get("measurement_id", ""),
                                r.get("instrument_id", ""),
                                r.get("mode", ""),
                                r.get("value", ""),
                                r.get("unit", ""),
                            ),
                        )
            else:
                with open(path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            r = json.loads(line)
                        except Exception:
                            continue
                        tree.insert(
                            "",
                            "end",
                            values=(
                                r.get("timestamp", ""),
                                r.get("measurement_id", ""),
                                r.get("instrument_id", ""),
                                r.get("mode", ""),
                                r.get("value", ""),
                                r.get("unit", ""),
                            ),
                        )
        except Exception:
            pass

    # -----------------------------
    # Splash and icon
    # -----------------------------
    def _generate_icon(self, w: int, h: int):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((4, 4, w - 4, h - 4), fill=(31, 111, 235, 255))
        try:
            f = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
        except Exception:
            f = ImageFont.load_default()
        draw.text((w // 6, h // 6), "XDM", font=f, fill=(255, 255, 255, 255))
        return img

    def _show_splash(self):
        splash = tk.Toplevel(self)
        splash.overrideredirect(True)
        splash.geometry(
            "360x120+{}+{}".format(self.winfo_x() + 100, self.winfo_y() + 100)
        )
        splash.configure(bg="#222222")
        lbl = tk.Label(
            splash,
            text="Owon XDM2041 — Initializing",
            font=("Helvetica", 14),
            bg="#222222",
            fg="white",
        )
        lbl.pack(fill="both", expand=True, padx=16, pady=16)
        self.after(900, splash.destroy)


def main():
    app = MeterGUI()
    app.mainloop()


if __name__ == "__main__":
    main()

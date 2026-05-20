import tkinter as tk
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import random

matplotlib.use('TkAgg')

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)


class ChartWindow(tk.Toplevel):
    def __init__(self, parent, x, y, titleText, **kwargs):
        super().__init__(parent, **kwargs)

        self.title(titleText)

        figure, axes = plt.subplots()
        figure_canvas = FigureCanvasTkAgg(figure, self)
        NavigationToolbar2Tk(figure_canvas, self)

        axes.plot(x, y)
        axes.set_title('Time to Random')
        axes.set_ylabel('Random Numbers')

        figure_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        tk.Label(self, text="Sampling rate: 20Hz | Rail: 3.3V").pack(pady=5)

def open_chart_window(parent, textfile):
    with open(textfile) as f:
        y = []
        for line in f:
            y.append(float(line))
        x = list(range(len(y)))

        ChartWindow(parent, x, y, titleText='Data Chart')


# --- Standalone entry point ---
if __name__ == '__main__':
    root = tk.Tk()
    root.title('Main App')

    btn = tk.Button(root, text='Open Chart', command=lambda: open_chart_window(root, "/Users/elijahflader/owon-digital-XDM2041/numbers_all.txt"))
    btn.pack(padx=20, pady=20)

    root.mainloop()
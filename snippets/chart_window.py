import random
import tkinter as tk

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Tkinter Matplotlib Demo")

        # prepare data
        x = []
        y = []
        for i in range(400):
            x.append(i)
            y.append(random.randint(90, 110))

        # create a figure
        figure, axes = plt.subplots()

        # create FigureCanvasTkAgg object
        figure_canvas = FigureCanvasTkAgg(figure, self)

        # create the toolbar
        NavigationToolbar2Tk(figure_canvas, self)

        # create axes
        axes = figure.add_subplot()

        # create the barchart
        axes.plot(x, y)
        axes.set_title("Time to Random")
        axes.set_ylabel("Random Numbers")

        figure_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)


if __name__ == "__main__":
    app = App()
    app.mainloop()

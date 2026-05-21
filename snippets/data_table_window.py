import tkinter as tk
from tkinter import ttk

class DataTableWindow(tk.Toplevel):
    def __init__(self, parent, data, dataname="Resistance (Ohms)", time=0.25, **kwargs):
        super().__init__(parent, **kwargs)
        self.title('Data Table')
        self.geometry('600x400')
        self.update_idletasks()

        columns = ["Time (s)", dataname]
        rows = []
        for i in range(len(data)):
            rows.append((round(time * i, 4), data[i]))

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', rowheight=28, borderwidth=1, font=('Courier New', 11))
        style.configure('Treeview.Heading', borderwidth=1, relief='solid', font=('Courier New', 11, 'bold'))

        scroll_y = ttk.Scrollbar(self)

        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show='headings',
            yscrollcommand=scroll_y.set,
        )

        scroll_y.config(command=self.tree.yview)

        self.tree.tag_configure('odd', background='#f0f0f0')
        self.tree.tag_configure('even', background='#ffffff')

        alignments = {"Time (s)": tk.E, dataname: tk.E}
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)

        # Insert rows once, with tags
        for i, row in enumerate(rows):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', tk.END, values=row, tags=(tag,))

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        def _on_first_resize(self, event):
            total = event.width
            self.tree.column("Time (s)", width=total // 4)
            self.tree.column(self.dataname, width=(total * 3) // 4)
            self.tree.unbind('<Configure>')  # only run once

        self.tree.bind('<Configure>', _on_first_resize)

def open_data_window(parent, textfile):
    data = []
    with open(textfile) as f:
        for line in f:
            data.append(float(line))

    if data is not None:
        DataTableWindow(parent, data)

if __name__ == '__main__':
    root = tk.Tk()
    root.title('Main App')

    btn = tk.Button(root, text='Open Chart', command=lambda: open_data_window(root, "/Users/elijahflader/owon-digital-XDM2041/numbers_all.txt"))
    btn.pack(padx=20, pady=20)

    root.mainloop()
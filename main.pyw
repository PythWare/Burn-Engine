# main.pyw

import os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import tkinter as tk
from DW2_Tools import Core_Tools

def main():
    root = tk.Tk()
    app = Core_Tools(root)
    root.mainloop()

if __name__ == "__main__":
    main()

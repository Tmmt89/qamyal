"""Красная рамка по краю экрана, пока идёт запись экрана (только Windows).

Отдельный процесс: python frame_overlay.py x y w h. Окно прозрачное, поверх всех, щелчки проходят насквозь,
в запись экрана не попадает (SetWindowDisplayAffinity: WDA_EXCLUDEFROMCAPTURE). Закрывается, когда
программа закрывает ему stdin (или вместе с ней — Job Object в sysdeps.kill_with_parent)."""
import ctypes
import sys
import threading
import tkinter as tk
from ctypes import wintypes

THICK = 4
COLOR = "#e5484d"
KEY = "#010203"                      # «прозрачный» цвет середины окна


def main():
    x, y, w, h = (int(v) for v in sys.argv[1:5])
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)        # координаты в настоящих пикселях
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    root.overrideredirect(True)
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.configure(bg=KEY)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", KEY)
    c = tk.Canvas(root, bg=KEY, highlightthickness=0, width=w, height=h)
    c.pack(fill="both", expand=True)
    c.create_rectangle(THICK // 2, THICK // 2, w - THICK // 2 - 1, h - THICK // 2 - 1, outline=COLOR, width=THICK)
    root.update_idletasks()

    u = ctypes.windll.user32
    u.GetParent.restype = wintypes.HWND
    hwnd = u.GetParent(root.winfo_id()) or root.winfo_id()
    GWL_EXSTYLE = -20
    ex = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
    # LAYERED | TRANSPARENT (щелчки насквозь) | TOOLWINDOW (нет на панели задач) | NOACTIVATE | TOPMOST
    u.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | 0x80000 | 0x20 | 0x80 | 0x08000000 | 0x8)
    u.SetWindowDisplayAffinity(hwnd, 0x11)                    # WDA_EXCLUDEFROMCAPTURE: в запись не попадает

    def keep_on_top():                   # другие «поверх всех» окна могут перекрыть — поднимаемся раз в 2 с
        u.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)    # HWND_TOPMOST, NOSIZE|NOMOVE|NOACTIVATE
        root.after(2000, keep_on_top)

    def wait_parent():
        try:
            sys.stdin.read()             # программа закрыла трубу (или упала) — уходим
        finally:
            root.after(0, root.destroy)

    threading.Thread(target=wait_parent, daemon=True).start()
    keep_on_top()
    root.mainloop()


if __name__ == "__main__":
    main()

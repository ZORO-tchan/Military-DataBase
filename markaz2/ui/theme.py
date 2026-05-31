"""
السمة (الألوان والخطوط) وإعداد ttk + دعم RTL للواجهة العربية.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk

# لوحة الألوان
PRIMARY = "#1F4E78"
PRIMARY_DARK = "#163A5A"
ACCENT = "#2E86C1"
BG = "#F4F6F9"
CARD = "#FFFFFF"
TEXT = "#1A1A1A"
MUTED = "#6B7280"

# ألوان الحالة (تلوين الصفوف)
STATUS_COLORS = {
    "present": "#FFFFFF",   # موجود - أبيض
    "leave":   "#FFF3CD",   # إجازة - أصفر فاتح
    "absent":  "#F8D7DA",   # غياب - أحمر فاتح
    "returned":"#D1E7DD",   # عاد/مرحّل - أخضر فاتح
}
STATUS_FG = {
    "present": "#1A1A1A",
    "leave":   "#856404",
    "absent":  "#842029",
    "returned":"#0F5132",
}

FONT_FAMILY = "Tahoma"   # خط يدعم العربية على ويندوز
FONT_NORMAL = (FONT_FAMILY, 11)
FONT_BOLD = (FONT_FAMILY, 11, "bold")
FONT_TITLE = (FONT_FAMILY, 16, "bold")
FONT_BIG = (FONT_FAMILY, 22, "bold")
FONT_SMALL = (FONT_FAMILY, 9)


def apply_theme(root: tk.Tk) -> None:
    """يطبّق السمة على نافذة الجذر و ttk."""
    root.configure(bg=BG)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", font=FONT_NORMAL, background=BG, foreground=TEXT)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD, relief="flat")
    style.configure("TLabel", background=BG, foreground=TEXT, font=FONT_NORMAL)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT)
    style.configure("Title.TLabel", font=FONT_TITLE, foreground=PRIMARY, background=BG)
    style.configure("Muted.TLabel", foreground=MUTED, background=CARD, font=FONT_SMALL)
    style.configure("StatBig.TLabel", font=FONT_BIG, foreground=PRIMARY, background=CARD)

    style.configure("TButton", font=FONT_BOLD, padding=(12, 7),
                    background=PRIMARY, foreground="white", borderwidth=0)
    style.map("TButton",
              background=[("active", PRIMARY_DARK), ("disabled", "#AAB7C4")])

    style.configure("Accent.TButton", background=ACCENT)
    style.map("Accent.TButton", background=[("active", PRIMARY)])

    style.configure("Danger.TButton", background="#C0392B")
    style.map("Danger.TButton", background=[("active", "#922B21")])

    style.configure("Success.TButton", background="#1E8449")
    style.map("Success.TButton", background=[("active", "#14633A")])

    style.configure("TEntry", padding=5, fieldbackground="white")
    style.configure("TCombobox", padding=5)

    # Treeview (الجداول)
    style.configure("Treeview", font=FONT_NORMAL, rowheight=28,
                    background="white", fieldbackground="white")
    style.configure("Treeview.Heading", font=FONT_BOLD,
                    background=PRIMARY, foreground="white", padding=6)
    style.map("Treeview.Heading", background=[("active", PRIMARY_DARK)])
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", font=FONT_BOLD, padding=(16, 8))
    style.map("TNotebook.Tab",
              background=[("selected", PRIMARY), ("!selected", "#D6DCE4")],
              foreground=[("selected", "white"), ("!selected", TEXT)])


def center_window(win, width: int, height: int) -> None:
    """يوسّط نافذة في الشاشة."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 3
    win.geometry(f"{width}x{height}+{x}+{y}")

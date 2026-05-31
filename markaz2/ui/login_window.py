"""نافذة تسجيل الدخول."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme
from ..core import auth


class LoginWindow:
    """
    نافذة دخول. عند النجاح تستدعي on_success(user_dict).
    """
    def __init__(self, on_success):
        self.on_success = on_success
        self.root = tk.Tk()
        self.root.title("تسجيل الدخول — المركز الثاني للمستجدين")
        theme.apply_theme(self.root)
        theme.center_window(self.root, 420, 360)
        self.root.resizable(False, False)

        # ضمان وجود مستخدم افتراضي
        created = auth.ensure_default_admin()
        self._build()
        if created:
            self.hint.config(
                text="أول تشغيل: اسم المستخدم admin وكلمة المرور admin")

    def _build(self):
        wrap = ttk.Frame(self.root, style="Card.TFrame", padding=24)
        wrap.place(relx=0.5, rely=0.5, anchor="center", width=360, height=320)

        ttk.Label(wrap, text="🛡️", style="Card.TLabel",
                  font=(theme.FONT_FAMILY, 36)).pack(pady=(0, 4))
        ttk.Label(wrap, text="نظام إدارة المركز الثاني",
                  style="Card.TLabel", font=theme.FONT_TITLE,
                  foreground=theme.PRIMARY).pack()
        ttk.Label(wrap, text="للمستجدين — V3", style="Muted.TLabel").pack(pady=(0, 14))

        ttk.Label(wrap, text="اسم المستخدم:", style="Card.TLabel").pack(anchor="e")
        self.user_var = tk.StringVar(value="admin")
        u = ttk.Entry(wrap, textvariable=self.user_var, justify="right")
        u.pack(fill="x", pady=(2, 8))

        ttk.Label(wrap, text="كلمة المرور:", style="Card.TLabel").pack(anchor="e")
        self.pass_var = tk.StringVar()
        p = ttk.Entry(wrap, textvariable=self.pass_var, show="•", justify="right")
        p.pack(fill="x", pady=(2, 12))
        p.bind("<Return>", lambda e: self._login())

        ttk.Button(wrap, text="دخول", command=self._login).pack(fill="x")
        self.hint = ttk.Label(wrap, text="", style="Muted.TLabel", wraplength=300)
        self.hint.pack(pady=(8, 0))
        p.focus_set()

    def _login(self):
        user = auth.verify_user(self.user_var.get().strip(), self.pass_var.get())
        if user:
            self.root.destroy()
            self.on_success(user)
        else:
            messagebox.showerror("خطأ", "اسم المستخدم أو كلمة المرور غير صحيحة")
            self.pass_var.set("")

    def run(self):
        self.root.mainloop()

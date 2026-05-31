"""
شاشة إدارة المستخدمين + تغيير كلمة المرور.
متاحة لمن لديه دور admin.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme
from ..core import auth


class UsersWindow(tk.Toplevel):
    def __init__(self, parent, current_user):
        super().__init__(parent)
        self.current_user = current_user
        self.title("إدارة المستخدمين")
        theme.apply_theme(self)
        self.configure(bg=theme.BG)
        theme.center_window(self, 640, 460)
        self.transient(parent)
        self.grab_set()
        self._build()
        self._refresh()

    def _build(self):
        ttk.Label(self, text="إدارة المستخدمين والصلاحيات",
                  style="Title.TLabel").pack(pady=(12, 6))

        # جدول المستخدمين
        body = ttk.Frame(self, padding=(12, 0))
        body.pack(fill="both", expand=True)
        cols = [("id", "م", 50), ("username", "اسم المستخدم", 220),
                ("role", "الصلاحية", 120), ("created", "أُنشئ في", 180)]
        self.tree = ttk.Treeview(body, columns=[c[0] for c in cols],
                                 show="headings", selectmode="browse")
        for cid, txt, w in cols:
            self.tree.heading(cid, text=txt)
            self.tree.column(cid, width=w, anchor="center")
        vs = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")

        # أزرار العمليات
        bar = ttk.Frame(self, padding=12)
        bar.pack(fill="x")
        ttk.Button(bar, text="➕ مستخدم جديد", style="Success.TButton",
                   command=self._add_user).pack(side="right", padx=4)
        ttk.Button(bar, text="🔑 تغيير كلمة المرور",
                   command=self._change_pwd).pack(side="right", padx=4)
        ttk.Button(bar, text="🛡️ تغيير الصلاحية",
                   command=self._change_role).pack(side="right", padx=4)
        ttk.Button(bar, text="🗑️ حذف", style="Danger.TButton",
                   command=self._delete_user).pack(side="right", padx=4)
        ttk.Button(bar, text="إغلاق", command=self.destroy).pack(side="left", padx=4)

    def _refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for u in auth.list_users():
            self.tree.insert("", "end", iid=u["username"],
                             values=(u["id"], u["username"], u["role"],
                                     u.get("created_at", "")))

    def _selected_username(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("تنبيه", "اختر مستخدماً أولاً", parent=self)
            return None
        return sel[0]

    def _add_user(self):
        UserFormDialog(self, on_save=self._refresh)

    def _change_pwd(self):
        username = self._selected_username()
        if not username:
            return
        PasswordDialog(self, username)

    def _change_role(self):
        username = self._selected_username()
        if not username:
            return
        win = tk.Toplevel(self)
        win.title("تغيير الصلاحية")
        theme.apply_theme(win); theme.center_window(win, 320, 180)
        win.transient(self); win.grab_set()
        f = ttk.Frame(win, padding=16); f.pack(fill="both", expand=True)
        ttk.Label(f, text=f"المستخدم: {username}").pack(pady=(0, 8))
        role = tk.StringVar(value="admin")
        ttk.Combobox(f, textvariable=role, state="readonly", justify="right",
                     values=["admin", "user"]).pack(fill="x")

        def save():
            auth.set_role(username, role.get())
            win.destroy()
            self._refresh()
        ttk.Button(f, text="حفظ", style="Success.TButton",
                   command=save).pack(pady=12)

    def _delete_user(self):
        username = self._selected_username()
        if not username:
            return
        if username == self.current_user.get("username"):
            messagebox.showerror("خطأ", "لا يمكنك حذف حسابك الحالي", parent=self)
            return
        if not messagebox.askyesno("تأكيد", f"حذف المستخدم '{username}'؟", parent=self):
            return
        try:
            auth.delete_user(username)
            self._refresh()
        except ValueError as e:
            messagebox.showerror("خطأ", str(e), parent=self)


class UserFormDialog(tk.Toplevel):
    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self.on_save = on_save
        self.title("مستخدم جديد")
        theme.apply_theme(self); theme.center_window(self, 360, 280)
        self.transient(parent); self.grab_set()
        f = ttk.Frame(self, padding=16); f.pack(fill="both", expand=True)
        f.columnconfigure(0, weight=1)
        ttk.Label(f, text="اسم المستخدم:").grid(row=0, column=1, sticky="e", pady=5)
        self.user = tk.StringVar()
        ttk.Entry(f, textvariable=self.user, justify="right").grid(
            row=0, column=0, sticky="we", pady=5)
        ttk.Label(f, text="كلمة المرور:").grid(row=1, column=1, sticky="e", pady=5)
        self.pwd = tk.StringVar()
        ttk.Entry(f, textvariable=self.pwd, show="•", justify="right").grid(
            row=1, column=0, sticky="we", pady=5)
        ttk.Label(f, text="الصلاحية:").grid(row=2, column=1, sticky="e", pady=5)
        self.role = tk.StringVar(value="user")
        ttk.Combobox(f, textvariable=self.role, state="readonly", justify="right",
                     values=["admin", "user"]).grid(row=2, column=0, sticky="we", pady=5)
        btns = ttk.Frame(f); btns.grid(row=3, column=0, columnspan=2, pady=14)
        ttk.Button(btns, text="إنشاء", style="Success.TButton",
                   command=self._save).pack(side="right", padx=6)
        ttk.Button(btns, text="إلغاء", command=self.destroy).pack(side="right", padx=6)

    def _save(self):
        u, p = self.user.get().strip(), self.pwd.get()
        if not u or not p:
            messagebox.showerror("خطأ", "أدخل اسم المستخدم وكلمة المرور", parent=self)
            return
        if auth.user_exists(u):
            messagebox.showerror("خطأ", "اسم المستخدم موجود بالفعل", parent=self)
            return
        auth.create_user(u, p, role=self.role.get())
        if self.on_save:
            self.on_save()
        self.destroy()


class PasswordDialog(tk.Toplevel):
    def __init__(self, parent, username):
        super().__init__(parent)
        self.username = username
        self.title("تغيير كلمة المرور")
        theme.apply_theme(self); theme.center_window(self, 360, 220)
        self.transient(parent); self.grab_set()
        f = ttk.Frame(self, padding=16); f.pack(fill="both", expand=True)
        f.columnconfigure(0, weight=1)
        ttk.Label(f, text=f"المستخدم: {username}").grid(
            row=0, column=0, columnspan=2, pady=(0, 8))
        ttk.Label(f, text="كلمة المرور الجديدة:").grid(row=1, column=1, sticky="e", pady=5)
        self.p1 = tk.StringVar()
        ttk.Entry(f, textvariable=self.p1, show="•", justify="right").grid(
            row=1, column=0, sticky="we", pady=5)
        ttk.Label(f, text="تأكيد كلمة المرور:").grid(row=2, column=1, sticky="e", pady=5)
        self.p2 = tk.StringVar()
        ttk.Entry(f, textvariable=self.p2, show="•", justify="right").grid(
            row=2, column=0, sticky="we", pady=5)
        btns = ttk.Frame(f); btns.grid(row=3, column=0, columnspan=2, pady=14)
        ttk.Button(btns, text="حفظ", style="Success.TButton",
                   command=self._save).pack(side="right", padx=6)
        ttk.Button(btns, text="إلغاء", command=self.destroy).pack(side="right", padx=6)

    def _save(self):
        if not self.p1.get():
            messagebox.showerror("خطأ", "أدخل كلمة المرور", parent=self)
            return
        if self.p1.get() != self.p2.get():
            messagebox.showerror("خطأ", "كلمتا المرور غير متطابقتين", parent=self)
            return
        auth.change_password(self.username, self.p1.get())
        messagebox.showinfo("تم", "تم تغيير كلمة المرور", parent=self)
        self.destroy()

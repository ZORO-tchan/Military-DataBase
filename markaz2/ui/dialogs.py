"""
حوارات الإدخال: إضافة/تعديل مجند، نزول إجازة، تغييب، ترحيل.
كلها نوافذ Toplevel مشروطة (modal).
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme
from ..core import config, services, utils


class RecruitDialog(tk.Toplevel):
    """حوار إضافة أو تعديل مجند."""
    def __init__(self, parent, intake_id, recruit=None, on_save=None):
        super().__init__(parent)
        self.intake_id = intake_id
        self.recruit = recruit            # None = إضافة
        self.on_save = on_save
        self.result = None
        is_edit = recruit is not None
        self.title("تعديل بيانات مجند" if is_edit else "إضافة مجند جديد")
        theme.apply_theme(self)
        self.configure(bg=theme.BG)
        theme.center_window(self, 520, 620)
        self.transient(parent)
        self.grab_set()
        self.vars = {}
        self._build(is_edit)

    def _row(self, parent, label, key, r, widget="entry", values=None):
        ttk.Label(parent, text=label).grid(row=r, column=1, sticky="e",
                                           padx=8, pady=5)
        var = tk.StringVar()
        if self.recruit and self.recruit.get(key) is not None:
            var.set(str(self.recruit.get(key)))
        self.vars[key] = var
        if widget == "combo":
            w = ttk.Combobox(parent, textvariable=var, values=values or [],
                             justify="right", state="normal")
        else:
            w = ttk.Entry(parent, textvariable=var, justify="right")
        w.grid(row=r, column=0, sticky="we", padx=8, pady=5)
        return var

    def _build(self, is_edit):
        canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas, padding=10)
        frame.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw", width=500)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        frame.columnconfigure(0, weight=1)

        r = 0
        self._row(frame, "رقم الشرطة *", "police_no", r); r += 1
        self._row(frame, "الاسم *", "name", r); r += 1
        self._row(frame, "المحافظة", "governorate", r, "combo",
                  config.GOVERNORATES); r += 1
        self._row(frame, "المؤهل", "qualification", r, "combo",
                  config.QUALIFICATIONS); r += 1
        self._row(frame, "الدفعة", "batch", r); r += 1
        self._row(frame, "العهدة", "custody", r, "combo",
                  config.CUSTODY_TYPES); r += 1
        self._row(frame, "الماهية (YYYY-MM-DD)", "mahia", r); r += 1
        self._row(frame, "رقم الهاتف", "phone", r); r += 1
        self._row(frame, "السرية (1-7)", "saraya", r); r += 1
        self._row(frame, "تاريخ الحضور", "attend_date", r); r += 1
        self._row(frame, "الديانة", "religion", r); r += 1
        self._row(frame, "الصنعة/المهنة", "craft", r); r += 1
        self._row(frame, "تليفون الأب", "father_phone", r); r += 1
        self._row(frame, "ملاحظات", "notes", r); r += 1

        # ملاحظة الكتيبة التلقائية
        ttk.Label(frame, text="ℹ️ الكتيبة تُحسب تلقائياً من المحافظة",
                  style="Muted.TLabel", background=theme.BG).grid(
            row=r, column=0, columnspan=2, pady=(6, 2)); r += 1

        btns = ttk.Frame(frame)
        btns.grid(row=r, column=0, columnspan=2, pady=12)
        ttk.Button(btns, text="حفظ", style="Success.TButton",
                   command=self._save).pack(side="right", padx=6)
        ttk.Button(btns, text="إلغاء",
                   command=self.destroy).pack(side="right", padx=6)

    def _collect(self):
        data = {k: v.get().strip() for k, v in self.vars.items()}
        # تحقق السرية رقم
        if data.get("saraya"):
            try:
                int(data["saraya"])
            except ValueError:
                messagebox.showerror("خطأ", "السرية يجب أن تكون رقماً", parent=self)
                return None
        if data.get("mahia") and not utils.parse_date(data["mahia"]):
            messagebox.showerror("خطأ", "صيغة الماهية غير صحيحة", parent=self)
            return None
        return data

    def _save(self):
        data = self._collect()
        if data is None:
            return
        try:
            if self.recruit:
                services.update_recruit(self.recruit["id"], data)
            else:
                services.add_recruit(self.intake_id, data)
            self.result = True
            if self.on_save:
                self.on_save()
            self.destroy()
        except services.DuplicatePoliceNo as e:
            messagebox.showerror("رقم مكرر", str(e), parent=self)
        except ValueError as e:
            messagebox.showerror("بيانات ناقصة", str(e), parent=self)


class DateRangeDialog(tk.Toplevel):
    """حوار عام لتاريخ نزول/عودة (للإجازة)."""
    def __init__(self, parent, title="نزول إجازة"):
        super().__init__(parent)
        self.result = None
        self.title(title)
        theme.apply_theme(self)
        theme.center_window(self, 380, 260)
        self.transient(parent); self.grab_set()
        f = ttk.Frame(self, padding=16); f.pack(fill="both", expand=True)
        f.columnconfigure(0, weight=1)

        ttk.Label(f, text="تاريخ النزول (YYYY-MM-DD):").grid(row=0, column=1, sticky="e")
        self.start = tk.StringVar(value=utils.fmt_date(utils.today()))
        ttk.Entry(f, textvariable=self.start, justify="right").grid(
            row=0, column=0, sticky="we", pady=5)

        ttk.Label(f, text="تاريخ العودة المتوقع:").grid(row=1, column=1, sticky="e")
        self.end = tk.StringVar()
        ttk.Entry(f, textvariable=self.end, justify="right").grid(
            row=1, column=0, sticky="we", pady=5)

        ttk.Label(f, text="طريقة عدّ العمالة:").grid(row=2, column=1, sticky="e")
        self.mode = tk.StringVar(value="continue")
        cm = ttk.Combobox(f, textvariable=self.mode, justify="right",
                          state="readonly",
                          values=["continue", "reset"])
        cm.grid(row=3, column=0, columnspan=2, sticky="we", pady=2)
        ttk.Label(f, text="continue = العدّ مستمر | reset = يعيد العدّ من العودة",
                  style="Muted.TLabel", background=theme.BG).grid(
            row=4, column=0, columnspan=2)

        btns = ttk.Frame(f); btns.grid(row=5, column=0, columnspan=2, pady=12)
        ttk.Button(btns, text="تأكيد", style="Success.TButton",
                   command=self._ok).pack(side="right", padx=6)
        ttk.Button(btns, text="إلغاء", command=self.destroy).pack(side="right", padx=6)

    def _ok(self):
        s, e = self.start.get().strip(), self.end.get().strip()
        if not utils.parse_date(s) or not utils.parse_date(e):
            messagebox.showerror("خطأ", "تواريخ غير صحيحة", parent=self)
            return
        if utils.days_between(s, e) is None or utils.days_between(s, e) < 0:
            messagebox.showerror("خطأ", "تاريخ العودة قبل النزول", parent=self)
            return
        self.result = {"start": s, "end": e, "mode": self.mode.get()}
        self.destroy()


class AbsenceDialog(tk.Toplevel):
    """حوار تغييب مباشر (تاريخ + سبب)."""
    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        self.title("تغييب مجند")
        theme.apply_theme(self)
        theme.center_window(self, 380, 230)
        self.transient(parent); self.grab_set()
        f = ttk.Frame(self, padding=16); f.pack(fill="both", expand=True)
        f.columnconfigure(0, weight=1)
        ttk.Label(f, text="تاريخ الغياب (YYYY-MM-DD):").grid(row=0, column=1, sticky="e")
        self.start = tk.StringVar(value=utils.fmt_date(utils.today()))
        ttk.Entry(f, textvariable=self.start, justify="right").grid(
            row=0, column=0, sticky="we", pady=5)
        ttk.Label(f, text="سبب التغييب:").grid(row=1, column=1, sticky="e")
        self.reason = tk.StringVar()
        ttk.Entry(f, textvariable=self.reason, justify="right").grid(
            row=1, column=0, sticky="we", pady=5)
        btns = ttk.Frame(f); btns.grid(row=2, column=0, columnspan=2, pady=14)
        ttk.Button(btns, text="تغييب", style="Danger.TButton",
                   command=self._ok).pack(side="right", padx=6)
        ttk.Button(btns, text="إلغاء", command=self.destroy).pack(side="right", padx=6)

    def _ok(self):
        if not utils.parse_date(self.start.get().strip()):
            messagebox.showerror("خطأ", "تاريخ غير صحيح", parent=self)
            return
        self.result = {"start": self.start.get().strip(),
                       "reason": self.reason.get().strip()}
        self.destroy()


class TransferDialog(tk.Toplevel):
    """حوار ترحيل (جهة + تاريخ + ملاحظات) لعدة مجندين دفعة واحدة."""
    def __init__(self, parent, count):
        super().__init__(parent)
        self.result = None
        self.title(f"ترحيل {count} مجند")
        theme.apply_theme(self)
        theme.center_window(self, 400, 270)
        self.transient(parent); self.grab_set()
        f = ttk.Frame(self, padding=16); f.pack(fill="both", expand=True)
        f.columnconfigure(0, weight=1)
        ttk.Label(f, text=f"سيتم ترحيل {count} مجند (يُحذفون من الدفعة)",
                  style="Muted.TLabel", background=theme.BG).grid(
            row=0, column=0, columnspan=2, pady=(0, 8))
        ttk.Label(f, text="جهة الترحيل:").grid(row=1, column=1, sticky="e")
        self.dest = tk.StringVar()
        ttk.Entry(f, textvariable=self.dest, justify="right").grid(
            row=1, column=0, sticky="we", pady=5)
        ttk.Label(f, text="تاريخ الترحيل:").grid(row=2, column=1, sticky="e")
        self.date = tk.StringVar(value=utils.fmt_date(utils.today()))
        ttk.Entry(f, textvariable=self.date, justify="right").grid(
            row=2, column=0, sticky="we", pady=5)
        ttk.Label(f, text="ملاحظات:").grid(row=3, column=1, sticky="e")
        self.notes = tk.StringVar()
        ttk.Entry(f, textvariable=self.notes, justify="right").grid(
            row=3, column=0, sticky="we", pady=5)
        btns = ttk.Frame(f); btns.grid(row=4, column=0, columnspan=2, pady=14)
        ttk.Button(btns, text="ترحيل", style="Accent.TButton",
                   command=self._ok).pack(side="right", padx=6)
        ttk.Button(btns, text="إلغاء", command=self.destroy).pack(side="right", padx=6)

    def _ok(self):
        if not self.dest.get().strip():
            messagebox.showerror("خطأ", "أدخل جهة الترحيل", parent=self)
            return
        if not utils.parse_date(self.date.get().strip()):
            messagebox.showerror("خطأ", "تاريخ غير صحيح", parent=self)
            return
        self.result = {"dest": self.dest.get().strip(),
                       "date": self.date.get().strip(),
                       "notes": self.notes.get().strip()}
        self.destroy()

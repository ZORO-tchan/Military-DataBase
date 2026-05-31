"""
النافذة الرئيسية: اختيار الدفعة، شريط الإحصائيات المباشر، جدول المجندين
مع تلوين الصفوف حسب الحالة، وكل أزرار العمليات + التقارير.
"""
from __future__ import annotations
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from . import theme
from .dialogs import (RecruitDialog, DateRangeDialog, AbsenceDialog,
                      TransferDialog)
from .stats_view import StatsView
from .users_window import UsersWindow, PasswordDialog
from ..core import config, services, backup, auth
from ..core.excel_io import (import_recruits_from_excel,
                             export_recruits_to_excel,
                             generate_import_template)
from ..reports import pdf_reports


class MainWindow:
    def __init__(self, user):
        self.user = user
        self.username = user.get("username", "system")
        self.root = tk.Tk()
        self.root.title(f"نظام إدارة المركز الثاني للمستجدين — V3   ({self.username})")
        theme.apply_theme(self.root)
        theme.center_window(self.root, 1180, 720)
        self.root.minsize(980, 600)

        # نسخة احتياطية يومية عند بدء التشغيل
        backup.auto_backup_daily()

        self.intake_id = None
        self.intakes = []
        self._build()
        self._load_intakes()

    # ------------------------------------------------------------------ build
    def _build(self):
        top = ttk.Frame(self.root, padding=(12, 10))
        top.pack(fill="x")
        ttk.Label(top, text="الدفعة:", style="Title.TLabel").pack(side="right")
        self.intake_var = tk.StringVar()
        self.intake_combo = ttk.Combobox(top, textvariable=self.intake_var,
                                         state="readonly", width=22, justify="right")
        self.intake_combo.pack(side="right", padx=8)
        self.intake_combo.bind("<<ComboboxSelected>>", lambda e: self._on_intake_change())
        ttk.Button(top, text="➕ دفعة جديدة", command=self._new_intake).pack(
            side="right", padx=4)

        ttk.Button(top, text="📥 استيراد Excel", style="Accent.TButton",
                   command=self._import_excel).pack(side="left", padx=4)
        ttk.Button(top, text="📤 تصدير Excel", style="Accent.TButton",
                   command=self._export_excel).pack(side="left", padx=4)
        ttk.Button(top, text="📋 قالب استيراد",
                   command=self._make_template).pack(side="left", padx=4)

        # شريط الإحصائيات
        self.stats_frame = ttk.Frame(self.root, padding=(12, 0))
        self.stats_frame.pack(fill="x")
        self.stat_cards = {}
        for key, label, color in [
            ("total", "الإجمالي", theme.PRIMARY),
            ("existing", "الموجود", "#1E8449"),
            ("on_leave", "إجازات", "#B7950B"),
            ("absent", "غياب", "#C0392B"),
            ("present", "حاضر", theme.ACCENT),
        ]:
            card = tk.Frame(self.stats_frame, bg="white", bd=0,
                            highlightbackground="#DCE3EC", highlightthickness=1)
            card.pack(side="right", expand=True, fill="x", padx=4, pady=8)
            val = tk.Label(card, text="0", bg="white", fg=color,
                           font=theme.FONT_BIG)
            val.pack(pady=(8, 0))
            tk.Label(card, text=label, bg="white", fg=theme.MUTED,
                     font=theme.FONT_SMALL).pack(pady=(0, 8))
            self.stat_cards[key] = val

        # شريط البحث والأزرار
        bar = ttk.Frame(self.root, padding=(12, 4))
        bar.pack(fill="x")
        ttk.Label(bar, text="بحث:").pack(side="right")
        self.search_var = tk.StringVar()
        se = ttk.Entry(bar, textvariable=self.search_var, justify="right", width=24)
        se.pack(side="right", padx=6)
        se.bind("<KeyRelease>", lambda e: self.refresh())

        ttk.Button(bar, text="➕ إضافة", style="Success.TButton",
                   command=self._add_recruit).pack(side="left", padx=3)
        ttk.Button(bar, text="✏️ تعديل",
                   command=self._edit_recruit).pack(side="left", padx=3)
        ttk.Button(bar, text="🗑️ حذف", style="Danger.TButton",
                   command=self._delete_recruit).pack(side="left", padx=3)
        ttk.Button(bar, text="🏖️ إجازة",
                   command=self._leave).pack(side="left", padx=3)
        ttk.Button(bar, text="🚫 تغييب", style="Danger.TButton",
                   command=self._absent).pack(side="left", padx=3)
        ttk.Button(bar, text="🚚 ترحيل", style="Accent.TButton",
                   command=self._transfer).pack(side="left", padx=3)

        # دفتر التبويبات
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(4, 6))
        self._build_recruits_tab()
        self._build_leaves_tab()
        self._build_absences_tab()
        self._build_returns_tab()
        self._build_stats_tab()
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh())

        # شريط التقارير السفلي
        rep = ttk.Frame(self.root, padding=(12, 6))
        rep.pack(fill="x")
        ttk.Label(rep, text="التقارير:", style="Title.TLabel").pack(side="right")
        ttk.Button(rep, text="🧾 صرفية PDF",
                   command=self._sarfeya_pdf).pack(side="right", padx=4)
        ttk.Button(rep, text="📄 كشف سرية",
                   command=lambda: self._roster_pdf("saraya")).pack(side="right", padx=4)
        ttk.Button(rep, text="📄 كشف كتيبة",
                   command=lambda: self._roster_pdf("battalion")).pack(side="right", padx=4)
        ttk.Button(rep, text="🪪 بطاقة فردية",
                   command=self._card_pdf).pack(side="right", padx=4)
        ttk.Button(rep, text="💾 نسخة احتياطية الآن",
                   command=self._manual_backup).pack(side="left", padx=4)
        ttk.Button(rep, text="♻️ استعادة نسخة",
                   command=self._restore_backup).pack(side="left", padx=4)
        ttk.Button(rep, text="🔑 كلمة المرور",
                   command=self._change_my_password).pack(side="left", padx=4)
        if self.user.get("role") == "admin":
            ttk.Button(rep, text="👥 المستخدمون",
                       command=self._manage_users).pack(side="left", padx=4)

    def _make_tree(self, parent, columns):
        tree = ttk.Treeview(parent, columns=[c[0] for c in columns],
                            show="headings", selectmode="extended")
        for cid, text, w in columns:
            tree.heading(cid, text=text)
            tree.column(cid, width=w, anchor="center")
        vs = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vs.set)
        tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        # تلوين الصفوف حسب الحالة
        for st, color in theme.STATUS_COLORS.items():
            tree.tag_configure(st, background=color,
                               foreground=theme.STATUS_FG.get(st, "#000"))
        return tree

    def _build_recruits_tab(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="المجندون")
        cols = [("id", "م", 45), ("police", "رقم الشرطة", 90),
                ("name", "الاسم", 200), ("gov", "المحافظة", 90),
                ("qual", "المؤهل", 80), ("custody", "العهدة", 80),
                ("mahia", "الماهية", 95), ("bat", "الكتيبة", 60),
                ("saraya", "السرية", 55), ("emp", "العمالة", 65),
                ("status", "الحالة", 75)]
        self.tree = self._make_tree(f, cols)
        self.tree.bind("<Double-1>", lambda e: self._edit_recruit())

    def _build_leaves_tab(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="الإجازات")
        bar = ttk.Frame(f); bar.pack(fill="x", pady=4)
        ttk.Button(bar, text="🟢 سجّل عودة", style="Success.TButton",
                   command=self._return_leave).pack(side="left", padx=4)
        ttk.Button(bar, text="🔴 لم يعد → غياب", style="Danger.TButton",
                   command=self._leave_to_absent).pack(side="left", padx=4)
        body = ttk.Frame(f); body.pack(fill="both", expand=True)
        cols = [("id", "م", 45), ("police", "رقم الشرطة", 90),
                ("name", "الاسم", 200), ("start", "النزول", 95),
                ("end", "العودة المتوقعة", 110), ("days", "الأيام", 60),
                ("emp", "العمالة", 65), ("result", "النتيجة", 80)]
        self.leaves_tree = self._make_tree(body, cols)

    def _build_absences_tab(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="الغياب")
        bar = ttk.Frame(f); bar.pack(fill="x", pady=4)
        ttk.Button(bar, text="🟢 سجّل عودة من الغياب", style="Success.TButton",
                   command=self._return_absence).pack(side="left", padx=4)
        body = ttk.Frame(f); body.pack(fill="both", expand=True)
        cols = [("id", "م", 45), ("police", "رقم الشرطة", 90),
                ("name", "الاسم", 200), ("start", "تاريخ الغياب", 100),
                ("ret", "تاريخ العودة", 100), ("days", "أيام الغياب", 80),
                ("source", "المصدر", 90), ("reason", "السبب", 150)]
        self.absences_tree = self._make_tree(body, cols)

    def _build_returns_tab(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="العودات")
        cols = [("id", "م", 45), ("police", "رقم الشرطة", 90),
                ("name", "الاسم", 200), ("gov", "المحافظة", 90),
                ("dest", "جهة الترحيل", 140), ("date", "تاريخ الترحيل", 110),
                ("notes", "ملاحظات", 150)]
        self.returns_tree = self._make_tree(f, cols)

    def _build_stats_tab(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="📊 البيان")
        self.stats_view = StatsView(f, lambda: self.intake_id,
                                    get_intake_name=lambda: self.intake_var.get())
        self.stats_view.pack(fill="both", expand=True)

    # ------------------------------------------------------------- intakes
    def _load_intakes(self):
        self.intakes = services.list_intakes()
        if not self.intakes:
            # دفعة افتراضية: يناير 2026
            services.get_or_create_intake(1, 2026)
            self.intakes = services.list_intakes()
        names = [it["name"] for it in self.intakes]
        self.intake_combo["values"] = names
        self.intake_var.set(names[0])
        self.intake_id = self.intakes[0]["id"]
        self.refresh()

    def _on_intake_change(self):
        name = self.intake_var.get()
        for it in self.intakes:
            if it["name"] == name:
                self.intake_id = it["id"]
                break
        self.refresh()

    def _new_intake(self):
        win = tk.Toplevel(self.root)
        win.title("دفعة جديدة")
        theme.apply_theme(win); theme.center_window(win, 320, 200)
        win.transient(self.root); win.grab_set()
        f = ttk.Frame(win, padding=16); f.pack(fill="both", expand=True)
        ttk.Label(f, text="الشهر:").grid(row=0, column=1, sticky="e", pady=5)
        month_var = tk.StringVar(value="يناير")
        ttk.Combobox(f, textvariable=month_var, state="readonly", justify="right",
                     values=list(config.INTAKE_MONTHS.values())).grid(
            row=0, column=0, sticky="we", pady=5)
        ttk.Label(f, text="السنة:").grid(row=1, column=1, sticky="e", pady=5)
        year_var = tk.StringVar(value="2026")
        ttk.Entry(f, textvariable=year_var, justify="right").grid(
            row=1, column=0, sticky="we", pady=5)

        def create():
            try:
                year = int(year_var.get())
            except ValueError:
                messagebox.showerror("خطأ", "سنة غير صحيحة", parent=win); return
            month = {v: k for k, v in config.INTAKE_MONTHS.items()}[month_var.get()]
            services.get_or_create_intake(month, year)
            win.destroy()
            self.intakes = services.list_intakes()
            self.intake_combo["values"] = [it["name"] for it in self.intakes]
            self.intake_var.set(f"{month_var.get()} {year}")
            self._on_intake_change()

        ttk.Button(f, text="إنشاء", style="Success.TButton",
                   command=create).grid(row=2, column=0, columnspan=2, pady=14)

    # ------------------------------------------------------------- refresh
    def refresh(self):
        if self.intake_id is None:
            return
        self._refresh_stats()
        self._refresh_recruits()
        self._refresh_leaves()
        self._refresh_absences()
        self._refresh_returns()
        if hasattr(self, "stats_view"):
            self.stats_view.refresh()

    def _refresh_stats(self):
        st = services.statistics(self.intake_id)
        for key, lbl in self.stat_cards.items():
            lbl.config(text=str(st.get(key, 0)))

    def _refresh_recruits(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        search = self.search_var.get().strip() or None
        for r in services.list_recruits(self.intake_id, search=search):
            self.tree.insert("", "end", iid=str(r["id"]), tags=(r["status"],),
                             values=(r["id"], r["police_no"], r["name"],
                                     r["governorate"] or "", r["qualification"] or "",
                                     r["custody"] or "", r["mahia"] or "",
                                     r["battalion"], r["saraya"] or "",
                                     r.get("employment", "") or "",
                                     theme.STATUS_FG and self._status_ar(r["status"])))

    def _status_ar(self, s):
        return {"present": "موجود", "leave": "إجازة",
                "absent": "غياب", "returned": "مُرحّل"}.get(s, s)

    def _refresh_leaves(self):
        for i in self.leaves_tree.get_children():
            self.leaves_tree.delete(i)
        for lv in services.list_leaves(self.intake_id):
            tag = {"open": "leave", "returned": "returned",
                   "absent": "absent"}.get(lv["result"], "leave")
            self.leaves_tree.insert("", "end", iid=str(lv["id"]), tags=(tag,),
                                    values=(lv["id"], lv["police_no"], lv["name"],
                                            lv["start_date"], lv["expected_return"],
                                            lv["days"], lv.get("employment_leave", ""),
                                            lv["result"]))

    def _refresh_absences(self):
        for i in self.absences_tree.get_children():
            self.absences_tree.delete(i)
        for a in services.list_absences(self.intake_id):
            tag = "returned" if a.get("return_date") else "absent"
            self.absences_tree.insert("", "end", iid=str(a["id"]), tags=(tag,),
                                      values=(a["id"], a["police_no"], a["name"],
                                              a["start_date"], a.get("return_date") or "—",
                                              a.get("current_days", ""),
                                              "من إجازة" if a["source"] == "from_leave"
                                              else "مباشر", a.get("reason") or ""))

    def _refresh_returns(self):
        for i in self.returns_tree.get_children():
            self.returns_tree.delete(i)
        for r in services.list_returns(self.intake_id):
            self.returns_tree.insert("", "end", iid=str(r["id"]), tags=("returned",),
                                     values=(r["id"], r["police_no"], r["name"],
                                             r["governorate"] or "", r["destination"] or "",
                                             r["return_date"] or "", r["notes"] or ""))

    # ------------------------------------------------------- selection helpers
    def _selected_ids(self, tree):
        return [int(i) for i in tree.selection()]

    def _need_one(self, tree, msg="اختر مجنداً أولاً"):
        ids = self._selected_ids(tree)
        if not ids:
            messagebox.showwarning("تنبيه", msg)
            return None
        return ids

    # ------------------------------------------------------------- actions
    def _add_recruit(self):
        RecruitDialog(self.root, self.intake_id, on_save=self.refresh)

    def _edit_recruit(self):
        ids = self._need_one(self.tree)
        if not ids:
            return
        rec = services.get_recruit(ids[0])
        RecruitDialog(self.root, self.intake_id, recruit=rec, on_save=self.refresh)

    def _delete_recruit(self):
        ids = self._need_one(self.tree, "اختر مجنداً (أو أكثر) للحذف")
        if not ids:
            return
        if not messagebox.askyesno("تأكيد",
                                   f"حذف {len(ids)} مجند نهائياً؟"):
            return
        for rid in ids:
            services.delete_recruit(rid, username=self.username)
        self.refresh()

    def _leave(self):
        ids = self._need_one(self.tree, "اختر مجنداً لنزول الإجازة")
        if not ids:
            return
        dlg = DateRangeDialog(self.root, "نزول إجازة")
        self.root.wait_window(dlg)
        if dlg.result:
            for rid in ids:
                services.start_leave(rid, dlg.result["start"], dlg.result["end"],
                                     count_mode=dlg.result["mode"],
                                     username=self.username)
            self.refresh()

    def _absent(self):
        ids = self._need_one(self.tree, "اختر مجنداً للتغييب")
        if not ids:
            return
        dlg = AbsenceDialog(self.root)
        self.root.wait_window(dlg)
        if dlg.result:
            for rid in ids:
                services.mark_absent_direct(rid, dlg.result["start"],
                                            dlg.result["reason"],
                                            username=self.username)
            self.refresh()

    def _transfer(self):
        ids = self._need_one(self.tree, "اختر مجنداً (أو أكثر) للترحيل")
        if not ids:
            return
        dlg = TransferDialog(self.root, len(ids))
        self.root.wait_window(dlg)
        if dlg.result:
            n = services.transfer_recruits(ids, dlg.result["dest"],
                                           dlg.result["date"], dlg.result["notes"],
                                           username=self.username)
            messagebox.showinfo("تم", f"تم ترحيل {n} مجند")
            self.refresh()

    def _return_leave(self):
        ids = self._need_one(self.leaves_tree, "اختر إجازة")
        if not ids:
            return
        for lid in ids:
            services.return_from_leave(lid, username=self.username)
        self.refresh()

    def _leave_to_absent(self):
        ids = self._need_one(self.leaves_tree, "اختر إجازة")
        if not ids:
            return
        for lid in ids:
            services.absent_from_leave(lid, username=self.username)
        self.refresh()

    def _return_absence(self):
        ids = self._need_one(self.absences_tree, "اختر سجل غياب")
        if not ids:
            return
        for aid in ids:
            services.return_from_absence(aid, username=self.username)
        self.refresh()

    # ------------------------------------------------------------- Excel
    def _import_excel(self):
        path = filedialog.askopenfilename(
            title="اختر ملف Excel", filetypes=[("Excel", "*.xlsx *.xlsm *.xls")])
        if not path:
            return
        try:
            res = import_recruits_from_excel(path, self.intake_id,
                                             username=self.username)
        except Exception as e:
            messagebox.showerror("خطأ في الاستيراد", str(e))
            return
        msg = (f"تمت الإضافة: {res['added']}\n"
               f"تخطّي المكرر: {res['skipped_duplicate']}\n"
               f"إجمالي الصفوف: {res['total_rows']}")
        if res["errors"]:
            msg += f"\nأخطاء ({len(res['errors'])}):\n" + "\n".join(res["errors"][:8])
        messagebox.showinfo("نتيجة الاستيراد", msg)
        self.refresh()

    def _export_excel(self):
        path = filedialog.asksaveasfilename(
            title="حفظ التصدير", defaultextension=".xlsx",
            initialdir=config.EXPORT_DIR,
            initialfile=f"{self.intake_var.get()}.xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        export_recruits_to_excel(self.intake_id, path,
                                 title=f"كشف المجندين — {self.intake_var.get()}")
        messagebox.showinfo("تم", f"تم التصدير:\n{path}")

    def _make_template(self):
        path = filedialog.asksaveasfilename(
            title="حفظ القالب", defaultextension=".xlsx",
            initialdir=config.EXPORT_DIR, initialfile="قالب_استيراد.xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        generate_import_template(path)
        messagebox.showinfo("تم", f"تم إنشاء القالب:\n{path}")

    # ------------------------------------------------------------- PDF
    def _sarfeya_pdf(self):
        ids = self._need_one(self.tree, "اختر مجندين للصرفية")
        if not ids:
            return
        win = self._sarfeya_options(ids)

    def _sarfeya_options(self, ids):
        win = tk.Toplevel(self.root)
        win.title("خيارات نموذج الصرفية")
        theme.apply_theme(win); theme.center_window(win, 460, 340)
        win.transient(self.root); win.grab_set()
        f = ttk.Frame(win, padding=16); f.pack(fill="both", expand=True)
        f.columnconfigure(0, weight=1)
        ttk.Label(f, text=f"عدد المجندين المختارين: {len(ids)}",
                  style="Muted.TLabel", background=theme.BG).grid(
            row=0, column=0, columnspan=2)
        ttk.Label(f, text="الجهة:").grid(row=1, column=1, sticky="e", pady=4)
        dest = tk.StringVar()
        ttk.Entry(f, textvariable=dest, justify="right").grid(
            row=1, column=0, sticky="we", pady=4)
        ttk.Label(f, text="التاريخ:").grid(row=2, column=1, sticky="e", pady=4)
        from ..core import utils as _u
        dt = tk.StringVar(value=_u.fmt_date(_u.today()))
        ttk.Entry(f, textvariable=dt, justify="right").grid(
            row=2, column=0, sticky="we", pady=4)
        ttk.Label(f, text="عنوان النموذج (قابل للتعديل):").grid(
            row=3, column=1, sticky="e", pady=4)
        title = tk.StringVar(
            value="نموذج آخر صرفية محررة من المركز الثاني للتجنيد والتوزيع")
        ttk.Entry(f, textvariable=title, justify="right").grid(
            row=4, column=0, columnspan=2, sticky="we", pady=2)
        show_train = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="إظهار جملة التدريب",
                        variable=show_train).grid(row=5, column=0, columnspan=2,
                                                  sticky="e", pady=4)
        train = tk.StringVar(value="علماً بأن المجندين مدربين قتالي")
        ttk.Entry(f, textvariable=train, justify="right").grid(
            row=6, column=0, columnspan=2, sticky="we", pady=2)

        def gen():
            recs = [services.get_recruit(i) for i in ids]
            recs = [r for r in recs if r]
            n = len(recs)
            size = "صغيرة" if n <= 6 else ("متوسط" if n <= 20 else "كبيرة")
            path = filedialog.asksaveasfilename(
                title="حفظ نموذج الصرفية", defaultextension=".pdf",
                initialdir=config.EXPORT_DIR, initialfile="صرفية.pdf",
                filetypes=[("PDF", "*.pdf")])
            if not path:
                return
            pdf_reports.sarfeya_pdf(
                recs, path, destination=dest.get().strip(),
                sarfeya_date=dt.get().strip(),
                title=title.get().strip() or None,
                training_note=train.get().strip() if show_train.get() else None,
                size_label=size)
            win.destroy()
            messagebox.showinfo("تم", f"تم إنشاء نموذج الصرفية:\n{path}")
            self._open_file(path)

        ttk.Button(f, text="إنشاء PDF", style="Success.TButton",
                   command=gen).grid(row=7, column=0, columnspan=2, pady=12)

    def _roster_pdf(self, kind):
        recs = services.list_recruits(self.intake_id)
        if not recs:
            messagebox.showwarning("تنبيه", "لا يوجد مجندون")
            return
        # سؤال الرقم
        num = tk.simpledialog.askstring(
            "رقم", "السرية" if kind == "saraya" else "الكتيبة") \
            if hasattr(tk, "simpledialog") else None
        from tkinter import simpledialog
        num = simpledialog.askstring(
            "تحديد",
            "أدخل رقم السرية:" if kind == "saraya" else "أدخل رقم الكتيبة:",
            parent=self.root)
        if not num:
            return
        try:
            num = int(num)
        except ValueError:
            messagebox.showerror("خطأ", "رقم غير صحيح"); return
        field = "saraya" if kind == "saraya" else "battalion"
        subset = [r for r in recs if r.get(field) == num]
        if not subset:
            messagebox.showinfo("فارغ", "لا يوجد مجندون بهذا الرقم"); return
        path = filedialog.asksaveasfilename(
            title="حفظ الكشف", defaultextension=".pdf",
            initialdir=config.EXPORT_DIR,
            initialfile=f"كشف_{'سرية' if kind=='saraya' else 'كتيبة'}_{num}.pdf",
            filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        if kind == "saraya":
            pdf_reports.saraya_roster_pdf(subset, path, num)
        else:
            pdf_reports.battalion_roster_pdf(subset, path, num)
        messagebox.showinfo("تم", f"تم إنشاء الكشف:\n{path}")
        self._open_file(path)

    def _card_pdf(self):
        ids = self._need_one(self.tree, "اختر مجنداً")
        if not ids:
            return
        rec = services.get_recruit(ids[0])
        path = filedialog.asksaveasfilename(
            title="حفظ البطاقة", defaultextension=".pdf",
            initialdir=config.EXPORT_DIR,
            initialfile=f"بطاقة_{rec['police_no']}.pdf",
            filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        pdf_reports.recruit_card_pdf(rec, path)
        messagebox.showinfo("تم", f"تم إنشاء البطاقة:\n{path}")
        self._open_file(path)

    # ------------------------------------------------------------- misc
    def _manual_backup(self):
        path = backup.make_backup()
        messagebox.showinfo("تم", f"تم إنشاء نسخة احتياطية:\n{path}")

    def _restore_backup(self):
        backups = backup.list_backups()
        if not backups:
            messagebox.showinfo("لا توجد نسخ", "لا توجد نسخ احتياطية بعد.")
            return
        win = tk.Toplevel(self.root)
        win.title("استعادة نسخة احتياطية")
        theme.apply_theme(win); theme.center_window(win, 560, 380)
        win.transient(self.root); win.grab_set()
        ttk.Label(win, text="اختر نسخة احتياطية لاستعادتها",
                  style="Title.TLabel").pack(pady=(12, 4))
        ttk.Label(win, text="⚠️ سيتم استبدال البيانات الحالية (تُحفظ نسخة أمان أولاً)",
                  style="Muted.TLabel", background=theme.BG).pack()
        body = ttk.Frame(win, padding=10); body.pack(fill="both", expand=True)
        lb = tk.Listbox(body, font=theme.FONT_NORMAL, activestyle="none")
        vs = ttk.Scrollbar(body, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=vs.set)
        lb.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        for b in backups:
            lb.insert("end", os.path.basename(b))
        if backups:
            lb.selection_set(0)

        def do_restore():
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning("تنبيه", "اختر نسخة", parent=win)
                return
            path = backups[sel[0]]
            if not messagebox.askyesno(
                    "تأكيد", f"استعادة:\n{os.path.basename(path)}؟\n"
                             "سيُعاد تشغيل العرض بالبيانات المستعادة.", parent=win):
                return
            backup.restore_backup(path)
            win.destroy()
            self.intakes = services.list_intakes()
            if self.intakes:
                self.intake_combo["values"] = [it["name"] for it in self.intakes]
                self.intake_var.set(self.intakes[0]["name"])
                self.intake_id = self.intakes[0]["id"]
            self.refresh()
            messagebox.showinfo("تم", "تمت الاستعادة بنجاح")

        btns = ttk.Frame(win, padding=10); btns.pack(fill="x")
        ttk.Button(btns, text="استعادة", style="Success.TButton",
                   command=do_restore).pack(side="right", padx=6)
        ttk.Button(btns, text="إلغاء", command=win.destroy).pack(side="right", padx=6)

    def _manage_users(self):
        UsersWindow(self.root, self.user)

    def _change_my_password(self):
        PasswordDialog(self.root, self.user.get("username", "admin"))

    def _open_file(self, path):
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore
            elif sys.platform == "darwin":  # noqa
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}" >/dev/null 2>&1 &')
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


import sys  # noqa: E402 (used in _open_file)

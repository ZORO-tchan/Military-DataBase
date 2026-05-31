"""
عرض البيان (الإحصائيات التفصيلية) كإطار قابل للتضمين في تبويب.
يعرض: المحافظات، المؤهلات، العهد، الكتائب، السرايا — مع الإجماليات.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk

from . import theme
from ..core import services, config


class StatsView(ttk.Frame):
    def __init__(self, parent, get_intake_id, get_intake_name=None):
        super().__init__(parent)
        self.get_intake_id = get_intake_id
        self.get_intake_name = get_intake_name or (lambda: "")
        # شريط أزرار التصدير
        bar = ttk.Frame(self, padding=(10, 6))
        bar.pack(fill="x")
        ttk.Button(bar, text="🧾 تصدير البيان PDF",
                   command=self._export_pdf).pack(side="right", padx=4)
        ttk.Button(bar, text="📤 تصدير البيان Excel", style="Accent.TButton",
                   command=self._export_excel).pack(side="right", padx=4)
        # منطقة تمرير
        self.canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, padding=10)
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(
                            scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _clear(self):
        for w in self.inner.winfo_children():
            w.destroy()

    def _table(self, parent, title, pairs, col=0):
        """جدول صغير: عنوان + صفوف (مفتاح، قيمة) + إجمالي."""
        card = tk.Frame(parent, bg="white", highlightbackground="#DCE3EC",
                        highlightthickness=1)
        card.grid(row=0, column=col, sticky="nw", padx=8, pady=8)
        tk.Label(card, text=title, bg=theme.PRIMARY, fg="white",
                 font=theme.FONT_BOLD, padx=10, pady=5, anchor="e",
                 width=24).pack(fill="x")
        total = 0
        for k, v in pairs:
            if k is None or str(k).strip() == "" or str(k) == "None":
                k = "—"
            row = tk.Frame(card, bg="white")
            row.pack(fill="x")
            tk.Label(row, text=str(v), bg="white", fg=theme.TEXT,
                     font=theme.FONT_NORMAL, width=6, anchor="center").pack(side="left",
                                                                            padx=4)
            tk.Label(row, text=str(k), bg="white", fg=theme.TEXT,
                     font=theme.FONT_NORMAL, width=18, anchor="e").pack(side="right",
                                                                        padx=8)
            try:
                total += int(v)
            except (ValueError, TypeError):
                pass
        # الإجمالي
        trow = tk.Frame(card, bg="#EAF0F7")
        trow.pack(fill="x")
        tk.Label(trow, text=str(total), bg="#EAF0F7", fg=theme.PRIMARY,
                 font=theme.FONT_BOLD, width=6, anchor="center").pack(side="left", padx=4)
        tk.Label(trow, text="الإجمالي", bg="#EAF0F7", fg=theme.PRIMARY,
                 font=theme.FONT_BOLD, width=18, anchor="e").pack(side="right", padx=8)

    def refresh(self):
        self._clear()
        intake_id = self.get_intake_id()
        if intake_id is None:
            return
        st = services.statistics(intake_id)

        # ملخّص علوي
        summ = tk.Frame(self.inner, bg=theme.BG)
        summ.pack(fill="x", pady=(0, 6))
        for key, label, color in [
            ("total", "الإجمالي", theme.PRIMARY),
            ("existing", "الموجود", "#1E8449"),
            ("on_leave", "إجازات", "#B7950B"),
            ("absent", "غياب", "#C0392B"),
            ("present", "حاضر", theme.ACCENT),
        ]:
            c = tk.Frame(summ, bg="white", highlightbackground="#DCE3EC",
                         highlightthickness=1)
            c.pack(side="right", expand=True, fill="x", padx=4)
            tk.Label(c, text=str(st.get(key, 0)), bg="white", fg=color,
                     font=theme.FONT_BIG).pack(pady=(6, 0))
            tk.Label(c, text=label, bg="white", fg=theme.MUTED,
                     font=theme.FONT_SMALL).pack(pady=(0, 6))

        # شبكة الجداول التفصيلية
        grid = ttk.Frame(self.inner)
        grid.pack(fill="x", anchor="ne")

        def sorted_pairs(d, numeric_key=False):
            items = list(d.items())
            if numeric_key:
                items.sort(key=lambda x: (x[0] is None, x[0]))
            return items

        rows = [
            ("حسب المؤهل", sorted_pairs(st["by_qualification"])),
            ("حسب العهدة", sorted_pairs(st["by_custody"])),
            ("حسب الكتيبة", sorted_pairs(st["by_battalion"], numeric_key=True)),
            ("حسب السرية", sorted_pairs(st["by_saraya"], numeric_key=True)),
        ]
        # صف أول: 4 جداول
        line1 = ttk.Frame(grid); line1.pack(fill="x", anchor="ne")
        for col, (title, pairs) in enumerate(rows):
            self._table(line1, title, pairs, col=col)

        # المحافظات (جدول واحد عريض)
        line2 = ttk.Frame(grid); line2.pack(fill="x", anchor="ne")
        self._table(line2, "حسب المحافظة",
                    sorted_pairs(st["by_governorate"]), col=0)

    # ------------------------------------------------------- تصدير البيان
    def _export_pdf(self):
        from tkinter import filedialog, messagebox
        import os
        from ..reports import pdf_reports
        intake_id = self.get_intake_id()
        if intake_id is None:
            return
        stats = services.statistics(intake_id)
        name = self.get_intake_name()
        path = filedialog.asksaveasfilename(
            title="حفظ البيان PDF", defaultextension=".pdf",
            initialdir=config.EXPORT_DIR, initialfile=f"البيان_{name}.pdf",
            filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        pdf_reports.statistics_pdf(stats, path, intake_name=name)
        messagebox.showinfo("تم", f"تم إنشاء البيان:\n{path}")
        self._open_file(path)

    def _export_excel(self):
        from tkinter import filedialog, messagebox
        from ..core.excel_io import export_statistics_to_excel
        intake_id = self.get_intake_id()
        if intake_id is None:
            return
        stats = services.statistics(intake_id)
        name = self.get_intake_name()
        path = filedialog.asksaveasfilename(
            title="حفظ البيان Excel", defaultextension=".xlsx",
            initialdir=config.EXPORT_DIR, initialfile=f"البيان_{name}.xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        export_statistics_to_excel(stats, path, intake_name=name)
        messagebox.showinfo("تم", f"تم إنشاء البيان:\n{path}")

    def _open_file(self, path):
        import os
        import sys
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore
            elif sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}" >/dev/null 2>&1 &')
        except Exception:
            pass

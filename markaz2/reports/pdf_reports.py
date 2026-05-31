"""
تقارير PDF حقيقية:
- sarfeya_pdf      : نموذج الصرفية الرسمي (صغيرة/متوسط/كبيرة) مع توقيع القائد.
- saraya_roster_pdf: كشف السرية.
- battalion_roster_pdf: كشف الكتيبة.
- recruit_card_pdf : بطاقة بيانات فردية.
كل النصوص العربية تمرّ عبر ar() للتشكيل والاتجاه الصحيح.
"""
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                Spacer, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from .arabic_pdf import register_fonts, ar, FONT_NAME, FONT_NAME_BOLD
from ..core import config


def _styles():
    register_fonts()
    ss = getSampleStyleSheet()
    title = ParagraphStyle("ar_title", parent=ss["Title"], fontName=FONT_NAME_BOLD,
                           alignment=TA_CENTER, fontSize=15, leading=20)
    head = ParagraphStyle("ar_head", parent=ss["Heading2"], fontName=FONT_NAME_BOLD,
                          alignment=TA_CENTER, fontSize=12, leading=16)
    body = ParagraphStyle("ar_body", parent=ss["Normal"], fontName=FONT_NAME,
                          alignment=TA_RIGHT, fontSize=11, leading=18)
    body_c = ParagraphStyle("ar_body_c", parent=body, alignment=TA_CENTER)
    return title, head, body, body_c


def _base_table_style():
    return TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTNAME", (0, 0), (-1, 0), FONT_NAME_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9BB7D4")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EAF0F7")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


# ---------------------------------------------------------------------------
# نموذج الصرفية الرسمي
# ---------------------------------------------------------------------------
def sarfeya_pdf(recruits: List[Dict[str, Any]], out_path: str,
                destination: str = "",
                sarfeya_date: str = "",
                title: Optional[str] = None,
                training_note: Optional[str] = "علماً بأن المجندين مدربين قتالي",
                size_label: str = "") -> str:
    """
    ينشئ نموذج صرفية رسمي.
    - title: عنوان النموذج (قابل للتعديل ليكتب فيه الجهة).
    - training_note: جملة التدريب (قابلة للتعديل/الإخفاء = None أو "").
    """
    title_text, head, body, body_c = _styles()
    register_fonts()

    if title is None:
        title = "نموذج آخر صرفية محررة من المركز الثاني للتجنيد والتوزيع"
        if destination:
            title += f" مع {destination}"

    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            rightMargin=1.5 * cm, leftMargin=1.5 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    elems: List[Any] = []

    # رأس
    elems.append(Paragraph(ar(config.CENTER_DEPARTMENT), head))
    elems.append(Paragraph(ar(config.CENTER_NAME), head))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(ar(title), title_text))
    if sarfeya_date:
        elems.append(Paragraph(ar(f"بتاريخ: {sarfeya_date}"), body_c))
    if size_label:
        elems.append(Paragraph(ar(f"({size_label})"), body_c))
    elems.append(Spacer(1, 10))

    # جدول الأسماء
    headers = ["م", "رقم الشرطة", "الاسم", "المحافظة", "المؤهل", "الدفعة",
               "العهدة", "الماهية"]
    data = [[ar(h) for h in headers]]
    for i, r in enumerate(recruits, start=1):
        data.append([
            ar(str(i)),
            ar(r.get("police_no", "")),
            ar(r.get("name", "")),
            ar(r.get("governorate", "")),
            ar(r.get("qualification", "")),
            ar(r.get("batch", "")),
            ar(r.get("custody", "")),
            ar(r.get("mahia", "")),
        ])
    col_widths = [1.0 * cm, 2.3 * cm, 4.2 * cm, 2.3 * cm, 2.0 * cm,
                  1.6 * cm, 1.8 * cm, 2.3 * cm]
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(_base_table_style())
    elems.append(tbl)
    elems.append(Spacer(1, 14))

    # النص الرسمي
    official = ("السيد العقيد/ قائد مركز الاستقبال والتوزيع — تحية طيبة وبعد،، "
                "برجاء تحرير مرتب للمجندين المنقولين طرفكم من تاريخ (الماهية) الموضح قرين كل منهم، "
                "علماً بأنه قد تم صرف كافة مستحقاتهم وتسوية عهدتهم الأميرية بالكامل.")
    elems.append(Paragraph(ar(official), body))
    if training_note:
        elems.append(Spacer(1, 6))
        elems.append(Paragraph(ar(training_note), body))
    elems.append(Spacer(1, 30))

    # التوقيع
    sign = Table(
        [[Paragraph(ar("قائد المركز الثاني"), body_c)],
         [Paragraph(ar(config.CENTER_COMMANDER), head)]],
        colWidths=[7 * cm])
    sign.hAlign = "RIGHT"
    elems.append(sign)

    doc.build(elems)
    return out_path


# ---------------------------------------------------------------------------
# كشف السرية / الكتيبة (روستر عام)
# ---------------------------------------------------------------------------
def _roster_pdf(recruits: List[Dict[str, Any]], out_path: str, title: str) -> str:
    title_text, head, body, body_c = _styles()
    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            rightMargin=1.2 * cm, leftMargin=1.2 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    elems: List[Any] = []
    elems.append(Paragraph(ar(config.CENTER_NAME), head))
    elems.append(Paragraph(ar(title), title_text))
    elems.append(Spacer(1, 10))

    headers = ["م", "رقم الشرطة", "الاسم", "المحافظة", "المؤهل", "العهدة",
               "الكتيبة", "السرية", "الحالة"]
    status_ar = {"present": "موجود", "leave": "إجازة", "absent": "غياب"}
    data = [[ar(h) for h in headers]]
    for i, r in enumerate(recruits, start=1):
        data.append([
            ar(str(i)), ar(r.get("police_no", "")), ar(r.get("name", "")),
            ar(r.get("governorate", "")), ar(r.get("qualification", "")),
            ar(r.get("custody", "")), ar(str(r.get("battalion", ""))),
            ar(str(r.get("saraya", ""))),
            ar(status_ar.get(r.get("status"), r.get("status", ""))),
        ])
    cw = [1.0 * cm, 2.2 * cm, 4.5 * cm, 2.2 * cm, 1.9 * cm, 1.8 * cm,
          1.5 * cm, 1.4 * cm, 1.6 * cm]
    tbl = Table(data, colWidths=cw, repeatRows=1)
    tbl.setStyle(_base_table_style())
    elems.append(tbl)
    elems.append(Spacer(1, 8))
    elems.append(Paragraph(ar(f"الإجمالي: {len(recruits)} مجند"), body))
    doc.build(elems)
    return out_path


def saraya_roster_pdf(recruits, out_path, saraya_no) -> str:
    return _roster_pdf(recruits, out_path, f"كشف السرية رقم {saraya_no}")


def battalion_roster_pdf(recruits, out_path, battalion_no) -> str:
    return _roster_pdf(recruits, out_path, f"كشف الكتيبة رقم {battalion_no}")


# ---------------------------------------------------------------------------
# بطاقة بيانات فردية
# ---------------------------------------------------------------------------
def recruit_card_pdf(recruit: Dict[str, Any], out_path: str) -> str:
    title_text, head, body, body_c = _styles()
    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            rightMargin=2 * cm, leftMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    elems: List[Any] = []
    elems.append(Paragraph(ar(config.CENTER_NAME), head))
    elems.append(Paragraph(ar("بطاقة بيانات مجند"), title_text))
    elems.append(Spacer(1, 14))

    fields = [
        ("رقم الشرطة", recruit.get("police_no")),
        ("الاسم", recruit.get("name")),
        ("المحافظة", recruit.get("governorate")),
        ("المؤهل", recruit.get("qualification")),
        ("الدفعة", recruit.get("batch")),
        ("العهدة", recruit.get("custody")),
        ("الماهية", recruit.get("mahia")),
        ("رقم الهاتف", recruit.get("phone")),
        ("الكتيبة", recruit.get("battalion")),
        ("السرية", recruit.get("saraya")),
        ("تاريخ الحضور", recruit.get("attend_date")),
        ("الديانة", recruit.get("religion")),
        ("الصنعة/المهنة", recruit.get("craft")),
        ("تليفون الأب", recruit.get("father_phone")),
        ("ملاحظات", recruit.get("notes")),
    ]
    data = [[Paragraph(ar(str(v if v is not None else "")), body_c),
             Paragraph(ar(label), body_c)] for label, v in fields]
    tbl = Table(data, colWidths=[10 * cm, 5 * cm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9BB7D4")),
        ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#EAF0F7")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(tbl)
    doc.build(elems)
    return out_path


# ---------------------------------------------------------------------------
# تصدير البيان (الإحصائيات) PDF
# ---------------------------------------------------------------------------
def statistics_pdf(stats: Dict[str, Any], out_path: str,
                   intake_name: str = "") -> str:
    """ينشئ تقرير البيان (الإحصائيات التفصيلية) كملف PDF."""
    title_text, head, body, body_c = _styles()
    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            rightMargin=1.5 * cm, leftMargin=1.5 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    elems: List[Any] = []
    elems.append(Paragraph(ar(config.CENTER_NAME), head))
    elems.append(Paragraph(ar(f"البيان الإحصائي — {intake_name}"), title_text))
    elems.append(Spacer(1, 10))

    # الملخّص العلوي
    summary = [["الإجمالي", "الموجود", "إجازات", "غياب", "حاضر"],
               [stats.get("total", 0), stats.get("existing", 0),
                stats.get("on_leave", 0), stats.get("absent", 0),
                stats.get("present", 0)]]
    sdata = [[ar(str(c)) for c in row] for row in summary]
    stbl = Table(sdata, colWidths=[3.4 * cm] * 5)
    stbl.setStyle(_base_table_style())
    elems.append(stbl)
    elems.append(Spacer(1, 14))

    def _section(title, mapping, numeric=False):
        if not mapping:
            return
        elems.append(Paragraph(ar(title), head))
        items = list(mapping.items())
        if numeric:
            items.sort(key=lambda x: (x[0] is None, x[0]))
        rows = [[ar("العدد"), ar("البند")]]
        total = 0
        for k, v in items:
            label = "—" if k in (None, "", "None") else str(k)
            rows.append([ar(str(v)), ar(label)])
            try:
                total += int(v)
            except (ValueError, TypeError):
                pass
        rows.append([ar(str(total)), ar("الإجمالي")])
        t = Table(rows, colWidths=[3 * cm, 9 * cm])
        t.setStyle(_base_table_style())
        elems.append(t)
        elems.append(Spacer(1, 10))

    _section("حسب المؤهل", stats.get("by_qualification", {}))
    _section("حسب العهدة", stats.get("by_custody", {}))
    _section("حسب الكتيبة", stats.get("by_battalion", {}), numeric=True)
    _section("حسب السرية", stats.get("by_saraya", {}), numeric=True)
    _section("حسب المحافظة", stats.get("by_governorate", {}))

    doc.build(elems)
    return out_path

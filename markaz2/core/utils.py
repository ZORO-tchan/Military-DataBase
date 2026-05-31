"""دوال مساعدة عامة: تواريخ، حسابات الماهية والقبض والعمالة."""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Optional

from .config import DAYS_PER_PAY_MONTH

DATE_FMT = "%Y-%m-%d"


def parse_date(value) -> Optional[date]:
    """يحوّل نص/كائن إلى date. يرجّع None لو فارغ أو غير صالح."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    # تجربة عدة صيغ شائعة
    for fmt in (DATE_FMT, "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def fmt_date(d: Optional[date]) -> str:
    """يحوّل date إلى نص قياسي YYYY-MM-DD."""
    if d is None:
        return ""
    if isinstance(d, str):
        p = parse_date(d)
        return p.strftime(DATE_FMT) if p else ""
    return d.strftime(DATE_FMT)


def today() -> date:
    return date.today()


def days_between(start, end) -> Optional[int]:
    """عدد الأيام بين تاريخين (end - start)."""
    s, e = parse_date(start), parse_date(end)
    if s is None or e is None:
        return None
    return (e - s).days


def leave_days(start, end) -> Optional[int]:
    """أيام الإجازة = العودة - النزول."""
    return days_between(start, end)


def absence_days(start, return_date=None) -> Optional[int]:
    """
    عدد أيام الغياب = من تاريخ الغياب حتى تاريخ العودة (أو اليوم الحالي لو لسه غايب).
    """
    s = parse_date(start)
    if s is None:
        return None
    e = parse_date(return_date) if return_date else today()
    return (e - s).days


def employment_days_main(return_from_leave=None, attend_date=None,
                         mode: str = "continue") -> Optional[int]:
    """
    العمالة في تاب يناير:
    - mode='reset'    : TODAY - (حضور من اجازة)   [يعيد العدّ من العودة]
    - mode='continue' : TODAY - (تاريخ الحضور)     [العدّ لا ينقطع]
    """
    base = return_from_leave if mode == "reset" else attend_date
    base = base or attend_date or return_from_leave
    d = parse_date(base)
    if d is None:
        return None
    return (today() - d).days


def employment_days_leave(start_date) -> Optional[int]:
    """العمالة في تاب الإجازة = TODAY - تاريخ النزول + 1."""
    d = parse_date(start_date)
    if d is None:
        return None
    return (today() - d).days + 1


def pay_days(mahia, months_paid: int) -> int:
    """أيام القبض = عدد الشهور المدفوعة × 30."""
    return max(0, int(months_paid)) * DAYS_PER_PAY_MONTH


def next_mahia(current_mahia, months_paid: int = 1) -> Optional[date]:
    """
    الماهية الجديدة = أول الشهر بعد آخر شهر اتعمله قبض.
    مثال: ماهية 1/5/2026 وقبض شهر واحد → 1/6/2026.
    """
    d = parse_date(current_mahia)
    if d is None:
        return None
    month = d.month - 1 + max(1, int(months_paid))
    year = d.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)

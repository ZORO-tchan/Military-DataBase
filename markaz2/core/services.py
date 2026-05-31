"""
طبقة الخدمات (Business Logic) — كل عمليات النظام تمرّ من هنا.
تضمن: منع تكرار رقم الشرطة، حساب الكتيبة تلقائياً، سجل الحركات (audit_log).
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any

from .database import get_connection
from . import config, utils


# ---------------------------------------------------------------------------
# سجل الحركات
# ---------------------------------------------------------------------------
def log_action(conn, username: str, action: str, entity: str,
               entity_id: Optional[int], details: str = "") -> None:
    conn.execute(
        "INSERT INTO audit_log (username, action, entity, entity_id, details) "
        "VALUES (?,?,?,?,?)",
        (username, action, entity, entity_id, details),
    )


def get_audit_log(limit: int = 200, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# الدفعات (Intakes)
# ---------------------------------------------------------------------------
def create_intake(month: int, year: int, db_path: Optional[str] = None) -> int:
    name = f"{config.INTAKE_MONTHS.get(month, str(month))} {year}"
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO intakes (month, year, name) VALUES (?,?,?)",
            (month, year, name),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_or_create_intake(month: int, year: int, db_path: Optional[str] = None) -> int:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM intakes WHERE month=? AND year=?", (month, year)
        ).fetchone()
        if row:
            return row["id"]
    finally:
        conn.close()
    return create_intake(month, year, db_path)


def list_intakes(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM intakes ORDER BY year DESC, month ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# المجندون (CRUD)
# ---------------------------------------------------------------------------
RECRUIT_FIELDS = [
    "police_no", "name", "governorate", "qualification", "batch", "custody",
    "mahia", "phone", "saraya", "sarfeya_note", "attend_date",
    "return_from_leave", "religion", "notes", "craft", "father_phone",
    "sarfeya_status", "count_mode",
]


class DuplicatePoliceNo(Exception):
    """يُرفع عند محاولة إضافة رقم شرطة مكرر داخل نفس الدفعة."""


def police_no_exists(intake_id: int, police_no: str,
                     exclude_id: Optional[int] = None,
                     db_path: Optional[str] = None) -> bool:
    conn = get_connection(db_path)
    try:
        q = "SELECT id FROM recruits WHERE intake_id=? AND police_no=?"
        params: list = [intake_id, str(police_no)]
        if exclude_id is not None:
            q += " AND id<>?"
            params.append(exclude_id)
        return conn.execute(q, params).fetchone() is not None
    finally:
        conn.close()


def add_recruit(intake_id: int, data: Dict[str, Any], username: str = "system",
                db_path: Optional[str] = None) -> int:
    """يضيف مجنداً. يرفع DuplicatePoliceNo لو الرقم مكرر."""
    police_no = str(data.get("police_no", "")).strip()
    if not police_no:
        raise ValueError("رقم الشرطة مطلوب")
    if not str(data.get("name", "")).strip():
        raise ValueError("الاسم مطلوب")
    if police_no_exists(intake_id, police_no, db_path=db_path):
        raise DuplicatePoliceNo(f"رقم الشرطة {police_no} مكرر في هذه الدفعة")

    governorate = (data.get("governorate") or "").strip()
    battalion = config.battalion_for(governorate)

    fields = {k: data.get(k) for k in RECRUIT_FIELDS}
    fields["police_no"] = police_no
    fields["governorate"] = governorate
    fields["battalion"] = battalion
    fields["mahia"] = utils.fmt_date(fields.get("mahia")) or None
    fields["attend_date"] = utils.fmt_date(fields.get("attend_date")) or None
    fields["return_from_leave"] = utils.fmt_date(fields.get("return_from_leave")) or None
    fields["count_mode"] = fields.get("count_mode") or "continue"

    cols = ["intake_id", "battalion"] + RECRUIT_FIELDS
    placeholders = ",".join("?" for _ in cols)
    values = [intake_id, battalion] + [fields.get(k) for k in RECRUIT_FIELDS]

    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            f"INSERT INTO recruits ({','.join(cols)}) VALUES ({placeholders})",
            values,
        )
        rid = cur.lastrowid
        log_action(conn, username, "add", "recruit", rid,
                   f"{fields['name']} ({police_no})")
        conn.commit()
        return rid
    finally:
        conn.close()


def update_recruit(recruit_id: int, data: Dict[str, Any], username: str = "system",
                   db_path: Optional[str] = None) -> None:
    """يعدّل بيانات مجند. يعيد حساب الكتيبة لو تغيّرت المحافظة. يمنع تكرار الرقم."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM recruits WHERE id=?", (recruit_id,)).fetchone()
        if not row:
            raise ValueError("المجند غير موجود")
        intake_id = row["intake_id"]

        new_police = str(data.get("police_no", row["police_no"])).strip()
        if new_police != row["police_no"] and police_no_exists(
                intake_id, new_police, exclude_id=recruit_id, db_path=db_path):
            raise DuplicatePoliceNo(f"رقم الشرطة {new_police} مكرر في هذه الدفعة")

        updates: Dict[str, Any] = {}
        for k in RECRUIT_FIELDS:
            if k in data:
                v = data[k]
                if k in ("mahia", "attend_date", "return_from_leave"):
                    v = utils.fmt_date(v) or None
                updates[k] = v
        if "governorate" in updates:
            updates["governorate"] = (updates["governorate"] or "").strip()
            updates["battalion"] = config.battalion_for(updates["governorate"])

        from datetime import datetime as _dt
        updates["updated_at"] = _dt.now().strftime("%Y-%m-%d %H:%M:%S")

        set_clause = ",".join(f"{k}=?" for k in updates)
        conn.execute(
            f"UPDATE recruits SET {set_clause} WHERE id=?",
            list(updates.values()) + [recruit_id],
        )
        log_action(conn, username, "edit", "recruit", recruit_id,
                   f"{data.get('name', row['name'])}")
        conn.commit()
    finally:
        conn.close()


def delete_recruit(recruit_id: int, username: str = "system",
                   db_path: Optional[str] = None) -> None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT name, police_no FROM recruits WHERE id=?",
                           (recruit_id,)).fetchone()
        conn.execute("DELETE FROM recruits WHERE id=?", (recruit_id,))
        if row:
            log_action(conn, username, "delete", "recruit", recruit_id,
                       f"{row['name']} ({row['police_no']})")
        conn.commit()
    finally:
        conn.close()


def get_recruit(recruit_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM recruits WHERE id=?", (recruit_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_recruits(intake_id: int, status: Optional[str] = None,
                  search: Optional[str] = None,
                  db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """يرجّع قائمة المجندين مع حساب العمالة لكل واحد."""
    conn = get_connection(db_path)
    try:
        q = "SELECT * FROM recruits WHERE intake_id=?"
        params: list = [intake_id]
        if status:
            q += " AND status=?"
            params.append(status)
        if search:
            q += " AND (name LIKE ? OR police_no LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        q += " ORDER BY id ASC"
        rows = conn.execute(q, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["employment"] = utils.employment_days_main(
                d.get("return_from_leave"), d.get("attend_date"),
                d.get("count_mode", "continue"))
            result.append(d)
        return result
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# الإجازات
# ---------------------------------------------------------------------------
def start_leave(recruit_id: int, start_date, expected_return,
                count_mode: str = "continue", username: str = "system",
                db_path: Optional[str] = None) -> int:
    """ينزّل مجنداً في إجازة (يبقى في يناير + سجل إجازة)."""
    conn = get_connection(db_path)
    try:
        days = utils.leave_days(start_date, expected_return)
        cur = conn.execute(
            "INSERT INTO leaves (recruit_id, start_date, expected_return, days, result) "
            "VALUES (?,?,?,?, 'open')",
            (recruit_id, utils.fmt_date(start_date),
             utils.fmt_date(expected_return), days),
        )
        conn.execute(
            "UPDATE recruits SET status='leave', count_mode=? WHERE id=?",
            (count_mode, recruit_id),
        )
        log_action(conn, username, "leave", "recruit", recruit_id,
                   f"إجازة {utils.fmt_date(start_date)} → {utils.fmt_date(expected_return)} ({days} يوم)")
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def return_from_leave(leave_id: int, actual_return=None, username: str = "system",
                      db_path: Optional[str] = None) -> None:
    """تسجيل عودة المجند من الإجازة (رجع 🟢)."""
    conn = get_connection(db_path)
    try:
        lv = conn.execute("SELECT * FROM leaves WHERE id=?", (leave_id,)).fetchone()
        if not lv:
            raise ValueError("سجل الإجازة غير موجود")
        ret = utils.fmt_date(actual_return) if actual_return else utils.fmt_date(utils.today())
        conn.execute(
            "UPDATE leaves SET actual_return=?, result='returned' WHERE id=?",
            (ret, leave_id),
        )
        conn.execute(
            "UPDATE recruits SET status='present', return_from_leave=? WHERE id=?",
            (ret, lv["recruit_id"]),
        )
        log_action(conn, username, "return_leave", "recruit", lv["recruit_id"],
                   f"عاد من الإجازة {ret}")
        conn.commit()
    finally:
        conn.close()


def list_leaves(intake_id: int, only_open: bool = False,
                db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        q = """SELECT l.*, r.name, r.police_no, r.governorate, r.qualification,
                      r.custody, r.battalion
               FROM leaves l JOIN recruits r ON r.id = l.recruit_id
               WHERE r.intake_id=?"""
        params = [intake_id]
        if only_open:
            q += " AND l.result='open'"
        q += " ORDER BY l.id DESC"
        rows = conn.execute(q, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["employment_leave"] = utils.employment_days_leave(d["start_date"])
            out.append(d)
        return out
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# الغياب
# ---------------------------------------------------------------------------
def mark_absent_direct(recruit_id: int, start_date, reason: str = "",
                       username: str = "system", db_path: Optional[str] = None) -> int:
    """تغييب مباشر من تاب يناير (مع سبب)."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO absences (recruit_id, start_date, source, reason) "
            "VALUES (?,?, 'direct', ?)",
            (recruit_id, utils.fmt_date(start_date), reason),
        )
        conn.execute("UPDATE recruits SET status='absent' WHERE id=?", (recruit_id,))
        log_action(conn, username, "absent", "recruit", recruit_id,
                   f"غياب مباشر {utils.fmt_date(start_date)} - {reason}")
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def absent_from_leave(leave_id: int, username: str = "system",
                      db_path: Optional[str] = None) -> int:
    """
    المجند مجاش من الإجازة → ينتقل للغياب.
    تاريخ الغياب = تاريخ العودة المفروض من الإجازة.
    """
    conn = get_connection(db_path)
    try:
        lv = conn.execute("SELECT * FROM leaves WHERE id=?", (leave_id,)).fetchone()
        if not lv:
            raise ValueError("سجل الإجازة غير موجود")
        conn.execute("UPDATE leaves SET result='absent' WHERE id=?", (leave_id,))
        cur = conn.execute(
            "INSERT INTO absences (recruit_id, start_date, source, reason) "
            "VALUES (?,?, 'from_leave', ?)",
            (lv["recruit_id"], lv["expected_return"], "لم يعد من الإجازة"),
        )
        conn.execute("UPDATE recruits SET status='absent' WHERE id=?", (lv["recruit_id"],))
        log_action(conn, username, "absent", "recruit", lv["recruit_id"],
                   f"غياب من إجازة (لم يعد) {lv['expected_return']}")
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def return_from_absence(absence_id: int, return_date=None, username: str = "system",
                        db_path: Optional[str] = None) -> None:
    """عودة الغايب (لونه في يناير يرجع طبيعي، يبقى سجل تاريخي)."""
    conn = get_connection(db_path)
    try:
        ab = conn.execute("SELECT * FROM absences WHERE id=?", (absence_id,)).fetchone()
        if not ab:
            raise ValueError("سجل الغياب غير موجود")
        ret = utils.fmt_date(return_date) if return_date else utils.fmt_date(utils.today())
        days = utils.absence_days(ab["start_date"], ret)
        conn.execute(
            "UPDATE absences SET return_date=?, days=? WHERE id=?",
            (ret, days, absence_id),
        )
        conn.execute(
            "UPDATE recruits SET status='present', return_from_leave=? WHERE id=?",
            (ret, ab["recruit_id"]),
        )
        log_action(conn, username, "return_absence", "recruit", ab["recruit_id"],
                   f"عاد من الغياب {ret} ({days} يوم)")
        conn.commit()
    finally:
        conn.close()


def list_absences(intake_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """SELECT a.*, r.name, r.police_no, r.governorate, r.qualification,
                      r.custody, r.battalion, r.mahia, r.phone
               FROM absences a JOIN recruits r ON r.id = a.recruit_id
               WHERE r.intake_id=? ORDER BY a.id DESC""",
            (intake_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            # عدد أيام الغياب المحسوب حتى الآن لو لسه مفتوح
            if not d.get("return_date"):
                d["current_days"] = utils.absence_days(d["start_date"])
            else:
                d["current_days"] = d.get("days")
            out.append(d)
        return out
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# العودات (الترحيل)
# ---------------------------------------------------------------------------
def transfer_recruits(recruit_ids: List[int], destination: str, return_date,
                      notes: str = "", username: str = "system",
                      db_path: Optional[str] = None) -> int:
    """
    ترحيل عدة مجندين دفعة واحدة لجهة واحدة.
    بياناتهم تُنقل للعودات وتُحذف من يناير. يرجّع عدد المنقولين.
    """
    conn = get_connection(db_path)
    moved = 0
    try:
        for rid in recruit_ids:
            r = conn.execute("SELECT * FROM recruits WHERE id=?", (rid,)).fetchone()
            if not r:
                continue
            conn.execute(
                """INSERT INTO returns
                   (intake_id, police_no, name, governorate, qualification, batch,
                    custody, mahia, phone, destination, return_date, battalion, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (r["intake_id"], r["police_no"], r["name"], r["governorate"],
                 r["qualification"], r["batch"], r["custody"], r["mahia"],
                 r["phone"], destination, utils.fmt_date(return_date),
                 r["battalion"], notes),
            )
            conn.execute("DELETE FROM recruits WHERE id=?", (rid,))
            log_action(conn, username, "return", "recruit", rid,
                       f"{r['name']} → {destination} ({utils.fmt_date(return_date)})")
            moved += 1
        conn.commit()
        return moved
    finally:
        conn.close()


def list_returns(intake_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM returns WHERE intake_id=? ORDER BY id DESC", (intake_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# الإحصائيات (تاب بيان 1) — تُحسب تلقائياً
# ---------------------------------------------------------------------------
def statistics(intake_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """يحسب تقرير البيان تلقائياً من قاعدة البيانات."""
    conn = get_connection(db_path)
    try:
        def count(where, params=()):
            return conn.execute(
                f"SELECT COUNT(*) c FROM recruits WHERE intake_id=? {where}",
                (intake_id, *params)).fetchone()["c"]

        total = count("")
        on_leave = count("AND status='leave'")
        absent = count("AND status='absent'")
        present = count("AND status='present'")
        existing = total - on_leave - absent  # "الموجود"

        # حسب المحافظة
        by_gov = {r["governorate"]: r["c"] for r in conn.execute(
            "SELECT governorate, COUNT(*) c FROM recruits WHERE intake_id=? "
            "GROUP BY governorate", (intake_id,)).fetchall()}
        # حسب المؤهل
        by_qual = {r["qualification"]: r["c"] for r in conn.execute(
            "SELECT qualification, COUNT(*) c FROM recruits WHERE intake_id=? "
            "GROUP BY qualification", (intake_id,)).fetchall()}
        # حسب العهدة
        by_custody = {r["custody"]: r["c"] for r in conn.execute(
            "SELECT custody, COUNT(*) c FROM recruits WHERE intake_id=? "
            "GROUP BY custody", (intake_id,)).fetchall()}
        # حسب الكتيبة
        by_battalion = {r["battalion"]: r["c"] for r in conn.execute(
            "SELECT battalion, COUNT(*) c FROM recruits WHERE intake_id=? "
            "GROUP BY battalion", (intake_id,)).fetchall()}
        # حسب السرية
        by_saraya = {r["saraya"]: r["c"] for r in conn.execute(
            "SELECT saraya, COUNT(*) c FROM recruits WHERE intake_id=? "
            "GROUP BY saraya", (intake_id,)).fetchall()}

        return {
            "total": total, "present": present, "on_leave": on_leave,
            "absent": absent, "existing": existing,
            "by_governorate": by_gov, "by_qualification": by_qual,
            "by_custody": by_custody, "by_battalion": by_battalion,
            "by_saraya": by_saraya,
        }
    finally:
        conn.close()

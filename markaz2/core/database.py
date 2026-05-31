"""
طبقة قاعدة البيانات (SQLite) لنظام المركز الثاني — V3.

التصميم:
- جدول intakes  : الدفعات (يناير/أبريل/يوليو/أكتوبر + السنة)
- جدول recruits : المجندون (مرتبطون بدفعة) — رقم الشرطة فريد داخل الدفعة
- جدول leaves   : الإجازات (سجل حركة)
- جدول absences : الغياب (سجل حركة)
- جدول returns  : العودات/الترحيل (سجل حركة)
- جدول sarfeya  : عمليات الصرفية
- جدول users    : المستخدمون (تسجيل الدخول)
- جدول audit_log: سجل الحركات الكامل
"""
from __future__ import annotations
import sqlite3
import os
from typing import Optional

from . import config


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS intakes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    month       INTEGER NOT NULL,          -- 1/4/7/10
    year        INTEGER NOT NULL,
    name        TEXT    NOT NULL,          -- مثل: يناير 2026
    created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(month, year)
);

CREATE TABLE IF NOT EXISTS recruits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    intake_id       INTEGER NOT NULL,
    police_no       TEXT    NOT NULL,      -- رقم الشرطة
    name            TEXT    NOT NULL,      -- الاسم
    governorate     TEXT,                  -- المحافظة
    qualification   TEXT,                  -- المؤهل
    batch           TEXT,                  -- دفعة (نص حر داخلي)
    custody         TEXT,                  -- العهدة (ميري/ملكي/..)
    mahia           TEXT,                  -- الماهية (تاريخ بداية القبض) YYYY-MM-DD
    phone           TEXT,                  -- رقم الهاتف
    battalion       INTEGER DEFAULT 0,     -- الكتيبة (تلقائية من المحافظة)
    saraya          INTEGER DEFAULT 0,     -- السرية (1..7)
    sarfeya_note    TEXT,                  -- نص الصرفية (K)
    attend_date     TEXT,                  -- تاريخ الحضور (L) YYYY-MM-DD
    return_from_leave TEXT,                -- حضور من اجازة (M) YYYY-MM-DD
    religion        TEXT,                  -- الديانة
    notes           TEXT,                  -- ملاحظات
    craft           TEXT,                  -- صنعة - مهنة
    father_phone    TEXT,                  -- تليفون الاب
    sarfeya_status  TEXT,                  -- الصرفية مقبولة/مرفوضة
    status          TEXT NOT NULL DEFAULT 'present',  -- present/leave/absent/returned
    count_mode      TEXT NOT NULL DEFAULT 'continue', -- continue/reset (طريقة عدّ العمالة)
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (intake_id) REFERENCES intakes(id) ON DELETE CASCADE,
    UNIQUE(intake_id, police_no)           -- منع تكرار رقم الشرطة داخل الدفعة
);

CREATE TABLE IF NOT EXISTS leaves (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    recruit_id   INTEGER NOT NULL,
    start_date   TEXT NOT NULL,            -- تاريخ نزول الإجازة
    expected_return TEXT NOT NULL,         -- تاريخ العودة المتوقع
    actual_return TEXT,                    -- تاريخ العودة الفعلي (NULL = لسه)
    days         INTEGER,                  -- (العودة - النزول)
    result       TEXT DEFAULT 'open',      -- open/returned/absent
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (recruit_id) REFERENCES recruits(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS absences (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    recruit_id   INTEGER NOT NULL,
    start_date   TEXT NOT NULL,            -- تاريخ الغياب
    return_date  TEXT,                     -- تاريخ الحضور من غياب
    days         INTEGER,                  -- عدد أيام الغياب
    source       TEXT DEFAULT 'direct',    -- direct / from_leave
    reason       TEXT,                     -- سبب التغييب
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (recruit_id) REFERENCES recruits(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS returns (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    intake_id    INTEGER NOT NULL,
    police_no    TEXT,
    name         TEXT,
    governorate  TEXT,
    qualification TEXT,
    batch        TEXT,
    custody      TEXT,
    mahia        TEXT,
    phone        TEXT,
    destination  TEXT,                     -- جهة الترحيل
    return_date  TEXT,                     -- تاريخ الترحيل
    battalion    INTEGER DEFAULT 0,
    notes        TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (intake_id) REFERENCES intakes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sarfeya (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    intake_id    INTEGER NOT NULL,
    destination  TEXT,                     -- الجهة
    sarfeya_date TEXT,                     -- تاريخ الصرفية
    size         TEXT,                     -- صغيرة/متوسط/كبيرة
    training_note TEXT,                    -- جملة "مدربين قتالي" (اختيارية)
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (intake_id) REFERENCES intakes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sarfeya_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sarfeya_id   INTEGER NOT NULL,
    recruit_id   INTEGER,
    police_no    TEXT,
    FOREIGN KEY (sarfeya_id) REFERENCES sarfeya(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'admin',  -- admin / user
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT,
    action      TEXT NOT NULL,            -- add/edit/delete/leave/absent/return/...
    entity      TEXT,                     -- recruit/leave/...
    entity_id   INTEGER,
    details     TEXT,
    ts          TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_recruits_intake ON recruits(intake_id);
CREATE INDEX IF NOT EXISTS idx_recruits_status ON recruits(status);
CREATE INDEX IF NOT EXISTS idx_leaves_recruit ON leaves(recruit_id);
CREATE INDEX IF NOT EXISTS idx_absences_recruit ON absences(recruit_id);
"""


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """يفتح اتصالاً بقاعدة البيانات مع تفعيل المفاتيح الأجنبية و row_factory."""
    path = db_path or config.DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """ينشئ الجداول إن لم تكن موجودة."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("تم إنشاء قاعدة البيانات في:", config.DB_PATH)

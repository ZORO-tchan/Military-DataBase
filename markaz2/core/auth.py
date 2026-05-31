"""
نظام تسجيل الدخول والصلاحيات.
يستخدم PBKDF2-HMAC-SHA256 من المكتبة القياسية (بدون مكتبات خارجية).
"""
from __future__ import annotations
import hashlib
import os
import binascii
from typing import Optional

from .database import get_connection

ITERATIONS = 100_000


def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return binascii.hexlify(dk).decode("ascii")


def create_user(username: str, password: str, role: str = "admin",
                db_path: Optional[str] = None) -> int:
    """ينشئ مستخدماً جديداً ويرجّع id."""
    salt = os.urandom(16)
    pwd_hash = _hash_password(password, salt)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, salt, role) VALUES (?,?,?,?)",
            (username, pwd_hash, binascii.hexlify(salt).decode("ascii"), role),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def verify_user(username: str, password: str,
                db_path: Optional[str] = None) -> Optional[dict]:
    """يتحقق من المستخدم. يرجّع dict ببياناته عند النجاح، أو None."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if not row:
            return None
        salt = binascii.unhexlify(row["salt"])
        if _hash_password(password, salt) == row["password_hash"]:
            return {"id": row["id"], "username": row["username"], "role": row["role"]}
        return None
    finally:
        conn.close()


def change_password(username: str, new_password: str,
                    db_path: Optional[str] = None) -> bool:
    salt = os.urandom(16)
    pwd_hash = _hash_password(new_password, salt)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "UPDATE users SET password_hash=?, salt=? WHERE username=?",
            (pwd_hash, binascii.hexlify(salt).decode("ascii"), username),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def users_count(db_path: Optional[str] = None) -> int:
    conn = get_connection(db_path)
    try:
        return conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    finally:
        conn.close()


def list_users(db_path: Optional[str] = None) -> list:
    """يرجّع قائمة المستخدمين (بدون كلمات المرور)."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def user_exists(username: str, db_path: Optional[str] = None) -> bool:
    conn = get_connection(db_path)
    try:
        return conn.execute(
            "SELECT 1 FROM users WHERE username=?", (username,)).fetchone() is not None
    finally:
        conn.close()


def delete_user(username: str, db_path: Optional[str] = None) -> bool:
    """يحذف مستخدماً. لا يسمح بحذف آخر مستخدم متبقٍّ."""
    if users_count(db_path) <= 1:
        raise ValueError("لا يمكن حذف آخر مستخدم في النظام")
    conn = get_connection(db_path)
    try:
        cur = conn.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def set_role(username: str, role: str, db_path: Optional[str] = None) -> bool:
    conn = get_connection(db_path)
    try:
        cur = conn.execute("UPDATE users SET role=? WHERE username=?",
                           (role, username))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def ensure_default_admin(db_path: Optional[str] = None) -> bool:
    """
    إن لم يوجد أي مستخدم، ينشئ مستخدماً افتراضياً admin/admin.
    يرجّع True لو أنشأ واحداً.
    """
    if users_count(db_path) == 0:
        create_user("admin", "admin", role="admin", db_path=db_path)
        return True
    return False

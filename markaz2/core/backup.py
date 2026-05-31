"""
النسخ الاحتياطي التلقائي لقاعدة البيانات.
- نسخة عند بدء التشغيل (مرة يومياً كحد أقصى).
- الاحتفاظ بآخر N نسخة فقط.
"""
from __future__ import annotations
import os
import shutil
import glob
from datetime import datetime
from typing import Optional, List

from . import config


def make_backup(db_path: Optional[str] = None,
                backup_dir: Optional[str] = None,
                keep: int = 30) -> Optional[str]:
    """ينشئ نسخة احتياطية ويحذف الزائد. يرجّع مسار النسخة أو None."""
    src = db_path or config.DB_PATH
    bdir = backup_dir or config.BACKUP_DIR
    if not os.path.exists(src):
        return None
    os.makedirs(bdir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(bdir, f"markaz2_backup_{stamp}.db")
    shutil.copy2(src, dest)
    _cleanup(bdir, keep)
    return dest


def auto_backup_daily(db_path: Optional[str] = None,
                      backup_dir: Optional[str] = None,
                      keep: int = 30) -> Optional[str]:
    """ينشئ نسخة فقط إن لم تُؤخذ نسخة اليوم."""
    bdir = backup_dir or config.BACKUP_DIR
    today_str = datetime.now().strftime("%Y%m%d")
    existing = glob.glob(os.path.join(bdir, f"markaz2_backup_{today_str}_*.db"))
    if existing:
        return None
    return make_backup(db_path, backup_dir, keep)


def list_backups(backup_dir: Optional[str] = None) -> List[str]:
    bdir = backup_dir or config.BACKUP_DIR
    files = glob.glob(os.path.join(bdir, "markaz2_backup_*.db"))
    return sorted(files, reverse=True)


def restore_backup(backup_path: str, db_path: Optional[str] = None) -> None:
    """يستعيد نسخة احتياطية (يأخذ نسخة أمان أولاً)."""
    dest = db_path or config.DB_PATH
    if os.path.exists(dest):
        safety = dest + ".before_restore"
        shutil.copy2(dest, safety)
    shutil.copy2(backup_path, dest)


def _cleanup(backup_dir: str, keep: int) -> None:
    files = list_backups(backup_dir)
    for old in files[keep:]:
        try:
            os.remove(old)
        except OSError:
            pass

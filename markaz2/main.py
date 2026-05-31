"""
نقطة تشغيل البرنامج — نظام إدارة المركز الثاني للمستجدين V3.
التشغيل:  python -m markaz2.main   أو   python markaz2/main.py
"""
from __future__ import annotations
import os
import sys

# دعم التشغيل المباشر (python markaz2/main.py): أضف المجلد الأب للمسار
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markaz2.core import database, auth
from markaz2.ui.login_window import LoginWindow
from markaz2.ui.main_window import MainWindow


def start_app():
    database.init_db()
    auth.ensure_default_admin()

    def on_login(user):
        MainWindow(user).run()

    LoginWindow(on_login).run()


if __name__ == "__main__":
    start_app()

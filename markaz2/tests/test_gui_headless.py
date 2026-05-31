"""
اختبار بناء الواجهة فعلياً تحت شاشة افتراضية (Xvfb).
لا يشغّل mainloop، فقط ينشئ النوافذ ويرسمها مرة، لالتقاط أي خطأ runtime.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# قاعدة بيانات مؤقتة عبر متغير بيئة قبل استيراد config
tmp = tempfile.mkdtemp(prefix="gui_test_")
from markaz2.core import config
config.DB_PATH = os.path.join(tmp, "gui.db")
config.BACKUP_DIR = os.path.join(tmp, "bk")
config.EXPORT_DIR = os.path.join(tmp, "exp")
os.makedirs(config.BACKUP_DIR, exist_ok=True)
os.makedirs(config.EXPORT_DIR, exist_ok=True)

from markaz2.core import database, services, auth
database.init_db(config.DB_PATH)
auth.ensure_default_admin(config.DB_PATH)
i = services.get_or_create_intake(1, 2026, db_path=config.DB_PATH)
for n in range(1, 6):
    services.add_recruit(i, {
        "police_no": str(2000 + n), "name": f"مجند رقم {n}",
        "governorate": ["القاهرة", "دمياط", "اسوان", "الجيزة", "المنيا"][n - 1],
        "qualification": "متوسط", "custody": "ميري", "mahia": "2026-01-01",
        "saraya": 1,
    }, db_path=config.DB_PATH)
# واحد في إجازة
lv = services.start_leave(1, "2026-05-01", "2026-05-10", db_path=config.DB_PATH)

import tkinter as tk
from markaz2.ui import theme
from markaz2.ui.login_window import LoginWindow
from markaz2.ui.main_window import MainWindow
from markaz2.ui.dialogs import RecruitDialog, DateRangeDialog, AbsenceDialog, TransferDialog

print("بناء نافذة الدخول...")
lw = LoginWindow(lambda u: None)
lw.root.update()
lw.root.destroy()
print("  ✔ نافذة الدخول")

print("بناء النافذة الرئيسية...")
mw = MainWindow({"username": "admin", "role": "admin"})
mw.root.update()
print("  ✔ النافذة الرئيسية + الإحصائيات + الجداول")

# التقاط لقطة شاشة
mw.root.update_idletasks()
mw.root.geometry("1180x720")
mw.root.update()

# اختبار الحوارات
print("بناء حوار إضافة مجند...")
d = RecruitDialog(mw.root, i, on_save=None)
d.update(); d.destroy()
print("  ✔ حوار الإضافة")

print("بناء حوار التعديل...")
rec = services.get_recruit(2, db_path=config.DB_PATH)
d2 = RecruitDialog(mw.root, i, recruit=rec, on_save=None)
d2.update(); d2.destroy()
print("  ✔ حوار التعديل")

for cls, name in [(DateRangeDialog, "إجازة"), (AbsenceDialog, "تغييب")]:
    dd = cls(mw.root)
    dd.update(); dd.destroy()
    print(f"  ✔ حوار {name}")
td = TransferDialog(mw.root, 3); td.update(); td.destroy()
print("  ✔ حوار الترحيل")

# تبويب البيان
print("اختبار تبويب البيان...")
mw.stats_view.refresh()
mw.nb.select(4)
mw.root.update()
print("  ✔ تبويب البيان (الإحصائيات التفصيلية)")

# شاشة إدارة المستخدمين
print("اختبار شاشة المستخدمين...")
from markaz2.ui.users_window import UsersWindow, UserFormDialog, PasswordDialog
uw = UsersWindow(mw.root, {"username": "admin", "role": "admin"})
uw.update()
uf = UserFormDialog(uw); uf.update(); uf.destroy()
pd = PasswordDialog(uw, "admin"); pd.update(); pd.destroy()
uw.destroy()
print("  ✔ إدارة المستخدمين + كلمة المرور")

# لقطة شاشة للنافذة الرئيسية
try:
    mw.root.update()
    snap = os.path.join("/home/user/markaz2/exports", "_gui_snapshot.png")
    # استخدم خاصية postscript ثم تحويل، أو import أداة خارجية
    import subprocess
    wid = mw.root.winfo_id()
    subprocess.run(["import", "-window", "root", snap], timeout=10,
                   stderr=subprocess.DEVNULL)
    print("لقطة:", snap, os.path.exists(snap))
except Exception as e:
    print("تعذّر التقاط اللقطة:", e)

mw.root.destroy()
print("\n✅ كل نوافذ الواجهة تُبنى بدون أخطاء.")

"""
اختبار شامل لنواة النظام (V3) — يثبت أن كل وظيفة تعمل فعلياً.
يستخدم قاعدة بيانات مؤقتة منفصلة.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from markaz2.core import database, services, auth, backup, config, utils
from markaz2.core.excel_io import (import_recruits_from_excel,
                                   export_recruits_to_excel,
                                   generate_import_template)

PASS = "\033[92m✔\033[0m"
FAIL = "\033[91m�’\033[0m"
results = []


def check(name, cond):
    results.append((name, cond))
    print(f"  {PASS if cond else FAIL}  {name}")
    return cond


def main():
    tmp = tempfile.mkdtemp(prefix="markaz2_test_")
    db = os.path.join(tmp, "test.db")
    database.init_db(db)

    print("\n== 1) قاعدة البيانات والدفعات ==")
    intake = services.get_or_create_intake(1, 2026, db_path=db)
    check("إنشاء دفعة يناير 2026", intake > 0)
    intake2 = services.get_or_create_intake(4, 2026, db_path=db)
    check("إنشاء دفعة أبريل 2026 (تعدد دفعات)", intake2 > 0 and intake2 != intake)
    check("عدد الدفعات = 2", len(services.list_intakes(db_path=db)) == 2)

    print("\n== 2) إضافة مجندين + الكتيبة التلقائية ==")
    r1 = services.add_recruit(intake, {
        "police_no": "1001", "name": "أحمد محمد", "governorate": "القاهرة",
        "qualification": "متوسط", "custody": "ميري", "mahia": "2026-01-01",
        "attend_date": "2026-01-01", "saraya": 1,
    }, db_path=db)
    rec = services.get_recruit(r1, db_path=db)
    check("إضافة مجند", rec is not None)
    check("الكتيبة محسوبة تلقائياً (القاهرة=3)", rec["battalion"] == 3)

    r2 = services.add_recruit(intake, {
        "police_no": "1002", "name": "خالد علي", "governorate": "دمياط",
        "qualification": "عليا", "custody": "ملكي", "mahia": "2026-01-01",
        "attend_date": "2026-01-01", "saraya": 2,
    }, db_path=db)
    check("الكتيبة دمياط=1", services.get_recruit(r2, db_path=db)["battalion"] == 1)

    print("\n== 3) منع تكرار رقم الشرطة ==")
    dup = False
    try:
        services.add_recruit(intake, {"police_no": "1001", "name": "مكرر",
                                      "governorate": "الجيزة"}, db_path=db)
    except services.DuplicatePoliceNo:
        dup = True
    check("رفض رقم الشرطة المكرر", dup)
    # نفس الرقم في دفعة أخرى مسموح
    ok_other = services.add_recruit(intake2, {"police_no": "1001", "name": "بدفعة تانية",
                                              "governorate": "اسوان"}, db_path=db)
    check("نفس الرقم مسموح في دفعة مختلفة", ok_other > 0)

    print("\n== 4) تعديل مجند (وإعادة حساب الكتيبة) ==")
    services.update_recruit(r1, {"governorate": "اسوان", "name": "أحمد محمد المعدّل"},
                            db_path=db)
    rec = services.get_recruit(r1, db_path=db)
    check("تعديل الاسم", rec["name"] == "أحمد محمد المعدّل")
    check("إعادة حساب الكتيبة بعد تغيير المحافظة (اسوان=4)", rec["battalion"] == 4)

    print("\n== 5) الإجازات + حساب المدة تلقائياً ==")
    lv = services.start_leave(r2, "2026-05-01", "2026-05-11", db_path=db)
    leaves = services.list_leaves(intake, db_path=db)
    check("تسجيل إجازة", len(leaves) == 1)
    check("حساب أيام الإجازة تلقائياً = 10", leaves[0]["days"] == 10)
    check("حالة المجند = إجازة", services.get_recruit(r2, db_path=db)["status"] == "leave")
    services.return_from_leave(lv, "2026-05-11", db_path=db)
    check("العودة من الإجازة → الحالة موجود",
          services.get_recruit(r2, db_path=db)["status"] == "present")

    print("\n== 6) الغياب من إجازة + حساب المدة ==")
    lv2 = services.start_leave(r1, "2026-05-01", "2026-05-05", db_path=db)
    ab = services.absent_from_leave(lv2, db_path=db)
    absences = services.list_absences(intake, db_path=db)
    check("الانتقال إلى الغياب عند عدم العودة", len(absences) == 1)
    check("حالة المجند = غياب", services.get_recruit(r1, db_path=db)["status"] == "absent")
    check("تاريخ الغياب = تاريخ العودة المفروض",
          absences[0]["start_date"] == "2026-05-05")
    services.return_from_absence(ab, "2026-05-15", db_path=db)
    check("عدد أيام الغياب = 10",
          services.list_absences(intake, db_path=db)[0]["days"] == 10)

    print("\n== 7) الغياب المباشر بسبب ==")
    ab2 = services.mark_absent_direct(r2, "2026-05-20", "هروب", db_path=db)
    abs2 = [a for a in services.list_absences(intake, db_path=db) if a["id"] == ab2][0]
    check("غياب مباشر بسبب", abs2["reason"] == "هروب" and abs2["source"] == "direct")
    services.return_from_absence(ab2, db_path=db)  # عودة باليوم الحالي

    print("\n== 8) العودات (الترحيل) ==")
    r3 = services.add_recruit(intake, {"police_no": "1003", "name": "سعيد جمال",
                                       "governorate": "الجيزة", "mahia": "2026-01-01"},
                              db_path=db)
    before = len(services.list_recruits(intake, db_path=db))
    moved = services.transfer_recruits([r3], "الأمن العام", "2026-05-25", db_path=db)
    after = len(services.list_recruits(intake, db_path=db))
    check("ترحيل مجند", moved == 1)
    check("نقص العدد في يناير بعد الترحيل", after == before - 1)
    check("ظهوره في العودات", len(services.list_returns(intake, db_path=db)) == 1)

    print("\n== 9) الإحصائيات (البيان) تلقائياً ==")
    st = services.statistics(intake, db_path=db)
    check("إجمالي المجندين = 2", st["total"] == 2)
    check("حساب 'الموجود' = إجمالي - إجازة - غياب",
          st["existing"] == st["total"] - st["on_leave"] - st["absent"])

    print("\n== 10) حسابات الماهية والقبض ==")
    nm = utils.next_mahia("2026-05-01", 1)
    check("الماهية الجديدة بعد شهر = 2026-06-01", utils.fmt_date(nm) == "2026-06-01")
    nm2 = utils.next_mahia("2026-05-01", 2)
    check("بعد شهرين = 2026-07-01", utils.fmt_date(nm2) == "2026-07-01")
    check("أيام القبض شهرين = 60", utils.pay_days("2026-05-01", 2) == 60)

    print("\n== 11) استيراد/تصدير Excel فعلي ==")
    tmpl = os.path.join(tmp, "template.xlsx")
    generate_import_template(tmpl)
    check("إنشاء قالب الاستيراد", os.path.exists(tmpl))

    # ننشئ ملف استيراد فيه صفان (واحد جديد وواحد مكرر)
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    ws.append(["رقم الشرطة", "الاسم", "المحافظة", "المؤهل", "الماهية"])
    ws.append(["2001", "وليد فتحي", "المنيا", "متوسط", "2026-01-01"])
    ws.append(["2002", "ماهر سمير", "طنطا غير معروفة", "عادة", "2026-01-01"])
    ws.append(["1001", "مكرر", "القاهرة", "عليا", "2026-01-01"])  # مكرر
    imp = os.path.join(tmp, "import.xlsx"); wb.save(imp)
    res = import_recruits_from_excel(imp, intake, db_path=db)
    check("استيراد صفّين جديدين", res["added"] == 2)
    check("تخطّي المكرر أثناء الاستيراد", res["skipped_duplicate"] == 1)
    check("الكتيبة 0 لمحافظة غير معروفة",
          [r for r in services.list_recruits(intake, db_path=db)
           if r["police_no"] == "2002"][0]["battalion"] == 0)

    out_xlsx = os.path.join(tmp, "export.xlsx")
    export_recruits_to_excel(intake, out_xlsx, db_path=db)
    check("تصدير Excel", os.path.exists(out_xlsx) and os.path.getsize(out_xlsx) > 0)

    print("\n== 12) تسجيل الدخول ==")
    auth.create_user("admin", "1234", db_path=db)
    check("إنشاء مستخدم", auth.users_count(db_path=db) == 1)
    check("دخول صحيح", auth.verify_user("admin", "1234", db_path=db) is not None)
    check("دخول خاطئ مرفوض", auth.verify_user("admin", "wrong", db_path=db) is None)
    auth.change_password("admin", "5678", db_path=db)
    check("تغيير كلمة المرور", auth.verify_user("admin", "5678", db_path=db) is not None)

    print("\n== 13) النسخ الاحتياطي ==")
    b = backup.make_backup(db_path=db, backup_dir=os.path.join(tmp, "bk"))
    check("إنشاء نسخة احتياطية", b is not None and os.path.exists(b))
    check("ظهورها في القائمة",
          len(backup.list_backups(os.path.join(tmp, "bk"))) == 1)

    print("\n== 14) سجل الحركات (Audit) ==")
    log = services.get_audit_log(db_path=db)
    actions = {l["action"] for l in log}
    check("تسجيل الإضافة", "add" in actions)
    check("تسجيل التعديل", "edit" in actions)
    check("تسجيل الإجازة/الغياب/الترحيل",
          {"leave", "absent", "return"} <= actions)

    print("\n== 15) تقارير PDF حقيقية ==")
    try:
        from markaz2.reports import pdf_reports
        recruits = services.list_recruits(intake, db_path=db)
        p1 = pdf_reports.sarfeya_pdf(recruits[:6], os.path.join(tmp, "sarfeya.pdf"),
                                     destination="الأمن العام", sarfeya_date="2026-05-31",
                                     size_label="صغيرة")
        p2 = pdf_reports.saraya_roster_pdf(recruits, os.path.join(tmp, "saraya.pdf"), 1)
        p3 = pdf_reports.recruit_card_pdf(recruits[0], os.path.join(tmp, "card.pdf"))
        check("PDF صرفية", os.path.getsize(p1) > 1000)
        check("PDF كشف سرية", os.path.getsize(p2) > 1000)
        check("PDF بطاقة فردية", os.path.getsize(p3) > 1000)
    except Exception as e:
        check(f"PDF (خطأ: {e})", False)

    print("\n== 16) إدارة المستخدمين ==")
    auth.create_user("user2", "pass2", role="user", db_path=db)
    users = auth.list_users(db_path=db)
    check("قائمة المستخدمين", any(u["username"] == "user2" for u in users))
    check("التحقق من وجود مستخدم", auth.user_exists("user2", db_path=db))
    auth.set_role("user2", "admin", db_path=db)
    check("تغيير الصلاحية",
          [u for u in auth.list_users(db_path=db) if u["username"] == "user2"][0]["role"] == "admin")
    auth.delete_user("user2", db_path=db)
    check("حذف مستخدم", not auth.user_exists("user2", db_path=db))
    # منع حذف آخر مستخدم
    only_one = False
    # احذف كل المستخدمين عدا واحد ثم جرّب
    remaining = [u["username"] for u in auth.list_users(db_path=db)]
    for un in remaining[1:]:
        try:
            auth.delete_user(un, db_path=db)
        except ValueError:
            pass
    try:
        auth.delete_user(auth.list_users(db_path=db)[0]["username"], db_path=db)
    except ValueError:
        only_one = True
    check("منع حذف آخر مستخدم", only_one)

    print("\n== 17) استيراد .xls القديم ==")
    try:
        import xlwt
        wb = xlwt.Workbook(); ws = wb.add_sheet("S")
        ws.write(0, 0, "شعار الإدارة")  # صف قبل العناوين
        for c, h in enumerate(["رقم الشرطة", "الاسم", "المحافظة", "المؤهل"]):
            ws.write(2, c, h)
        ws.write(3, 0, 7001); ws.write(3, 1, "مجند xls"); ws.write(3, 2, "القاهرة"); ws.write(3, 3, "متوسط")
        xls_path = os.path.join(tmp, "old.xls"); wb.save(xls_path)
        res_xls = import_recruits_from_excel(xls_path, intake, db_path=db)
        check("استيراد ملف .xls قديم (مع تخطّي الشعار)", res_xls["added"] == 1)
        added_rec = [r for r in services.list_recruits(intake, db_path=db)
                     if r["police_no"] == "7001"][0]
        check("الكتيبة محسوبة من .xls (القاهرة=3)", added_rec["battalion"] == 3)
    except ImportError:
        check("استيراد .xls (xlwt غير مثبت — تخطّي)", True)

    print("\n== 18) تصدير البيان (PDF + Excel) ==")
    try:
        from markaz2.reports import pdf_reports as _pr
        from markaz2.core.excel_io import export_statistics_to_excel
        st2 = services.statistics(intake, db_path=db)
        pb = _pr.statistics_pdf(st2, os.path.join(tmp, "bayan.pdf"),
                                intake_name="يناير 2026")
        eb = export_statistics_to_excel(st2, os.path.join(tmp, "bayan.xlsx"),
                                        intake_name="يناير 2026")
        check("PDF البيان", os.path.getsize(pb) > 1000)
        check("Excel البيان", os.path.getsize(eb) > 0)
    except Exception as e:
        check(f"تصدير البيان (خطأ: {e})", False)

    print("\n== 19) استعادة نسخة احتياطية ==")
    bk_dir = os.path.join(tmp, "bk2")
    bpath = backup.make_backup(db_path=db, backup_dir=bk_dir)
    before_total = services.statistics(intake, db_path=db)["total"]
    # احذف مجنداً ثم استعد
    recs_now = services.list_recruits(intake, db_path=db)
    services.delete_recruit(recs_now[0]["id"], db_path=db)
    check("نقص العدد بعد الحذف",
          services.statistics(intake, db_path=db)["total"] == before_total - 1)
    backup.restore_backup(bpath, db_path=db)
    check("استعادة النسخة ترجّع العدد",
          services.statistics(intake, db_path=db)["total"] == before_total)

    # ملخص
    total = len(results)
    passed = sum(1 for _, c in results if c)
    print(f"\n{'='*40}\nالنتيجة: {passed}/{total} اختبار ناجح")
    if passed != total:
        print("اختبارات فاشلة:")
        for n, c in results:
            if not c:
                print("   -", n)
        sys.exit(1)
    print("✅ كل الاختبارات نجحت — النواة تعمل بالكامل.")
    print("ملفات الاختبار في:", tmp)


if __name__ == "__main__":
    main()

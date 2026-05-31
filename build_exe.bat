@echo off
REM ================================================================
REM  بناء ملف EXE لنظام إدارة المركز الثاني للمستجدين - V3
REM  شغّل هذا الملف على ويندوز من المجلد الذي يحوي مجلد markaz2
REM ================================================================
chcp 65001 >nul
echo === تثبيت المتطلبات (نسخ متوافقة مع ويندوز 7) ===
REM مهم: استخدم Python 3.8 على ويندوز 7 (النسخ الأحدث لا تعمل عليه)
python -m pip install --upgrade "pip<24"
python -m pip install -r markaz2\requirements-win7.txt
python -m pip install "pyinstaller==5.13.2"

echo.
echo === بناء EXE ===
pyinstaller --noconfirm --clean ^
  --name "المركز_الثاني" ^
  --windowed ^
  --onefile ^
  --paths . ^
  --add-data "markaz2\assets;markaz2\assets" ^
  --collect-submodules markaz2 ^
  --collect-all openpyxl ^
  --collect-all reportlab ^
  --collect-all xlrd ^
  --collect-all arabic_reshaper ^
  --collect-all bidi ^
  --collect-all et_xmlfile ^
  --hidden-import tkinter ^
  markaz2\app_entry.py

echo.
echo ================================================================
echo  تم البناء! الملف الجاهز في:  dist\المركز_الثاني.exe
echo  شغّله بالدبل كليك. بيانات الدخول الأولى:  admin / admin
echo ================================================================
pause

"""مشغّل مختصر: python run.py  (بديل عن python -m markaz2.main)."""
import os
import sys
# أضف المجلد الأب حتى تُستورد حزمة markaz2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from markaz2.main import start_app  # noqa: E402

if __name__ == "__main__":
    start_app()

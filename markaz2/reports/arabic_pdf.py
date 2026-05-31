"""
أدوات مساعدة لإخراج PDF عربي صحيح:
- تسجيل خط Amiri العربي في reportlab.
- تشكيل النص العربي (reshape) وضبط الاتجاه (bidi) ليظهر سليماً.
"""
from __future__ import annotations
import os

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import arabic_reshaper
from bidi.algorithm import get_display

from ..core import config

FONT_NAME = "Amiri"
FONT_NAME_BOLD = "Amiri-Bold"
_registered = False


def register_fonts() -> None:
    """يسجّل خطوط Amiri مرة واحدة. يرجع لخط افتراضي لو غير موجود."""
    global _registered
    if _registered:
        return
    reg = os.path.join(config.ASSETS_DIR, "Amiri-Regular.ttf")
    bold = os.path.join(config.ASSETS_DIR, "Amiri-Bold.ttf")
    if os.path.exists(reg):
        pdfmetrics.registerFont(TTFont(FONT_NAME, reg))
        if os.path.exists(bold):
            pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, bold))
        else:
            pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, reg))
        _registered = True


def ar(text) -> str:
    """يشكّل النص العربي ويضبط اتجاهه ليُعرض صحيحاً في reportlab."""
    if text is None:
        return ""
    s = str(text)
    if not s:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(s)
        return get_display(reshaped)
    except Exception:
        return s

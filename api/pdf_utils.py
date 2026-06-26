#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공통 유틸리티: 단위 변환, 좌표 함수, 재단선, 폰트 등록
배경색: 먹 1도 K:20% → RGB (0.8, 0.8, 0.8)
"""

import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import Color, black

# ── 폰트 경로 ────────────────────────────────────────────────────────
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")

# ── 폰트 등록 (앱 시작 시 1회) ──────────────────────────────────────
_fonts_registered = False

def register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return
    fonts = {
        "Paperlogy-9":         "Paperlogy-9Black.ttf",
        "Paperlogy-6":         "Paperlogy-6SemiBold.ttf",
        "Paperlogy-4":         "Paperlogy-4Regular.ttf",
        "KoPub-Light":         "KoPubWorld-Light.ttf",
        "KoPub-Bold":          "KoPubWorld-Bold.ttf",
        "Pretendard-Regular":  "Pretendard-Regular.ttf",
        "Pretendard-Bold":     "Pretendard-Bold.ttf",
        "Pretendard-Medium":   "Pretendard-Medium.ttf",
        "Pretendard-Light":    "Pretendard-Light.ttf",
        "Pretendard-SemiBold": "Pretendard-SemiBold.ttf",
    }
    for name, filename in fonts.items():
        path = os.path.join(FONT_DIR, filename)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                pass
    _fonts_registered = True

# ── 단위 변환 ────────────────────────────────────────────────────────
def mm(x):
    """mm → pt"""
    return x * 72 / 25.4

# ── 페이지 치수 (A5 기준) ────────────────────────────────────────────
PW = mm(148)    # A5 가로
PH = mm(210)    # A5 세로
BD = mm(5)      # 도련 5mm
CW = PW + 2*BD  # 캔버스 가로 (158mm)
CH = PH + 2*BD  # 캔버스 세로 (220mm)

# ── 좌표 변환 ────────────────────────────────────────────────────────
def cx(x_mm):
    """A5 기준 x(mm) → 캔버스 pt"""
    return BD + mm(x_mm)

def cy(y_mm):
    """A5 기준 y(mm, 하단기준) → 캔버스 pt"""
    return BD + mm(y_mm)

def cy_t(y_mm):
    """A5 상단에서 y_mm 아래 → 캔버스 pt"""
    return BD + PH - mm(y_mm)

# ── 배경색: 먹 1도 K:20% = RGB(0.8, 0.8, 0.8) ──────────────────────
BG_COLOR = Color(0.8, 0.8, 0.8)

def draw_bg(c):
    """회색 배경 전체 채우기"""
    c.setFillColor(BG_COLOR)
    c.rect(0, 0, CW, CH, fill=1, stroke=0)

# ── 재단선 ───────────────────────────────────────────────────────────
def draw_cropmarks(c):
    c.saveState()
    c.setStrokeColor(black)
    c.setLineWidth(0.25)
    mark = mm(10)
    corners = [
        (BD,      BD,      -1, -1),
        (BD + PW, BD,      +1, -1),
        (BD,      BD + PH, -1, +1),
        (BD + PW, BD + PH, +1, +1),
    ]
    for px, py, dx, dy in corners:
        c.line(px, py, px + dx * mark, py)
        c.line(px, py, px, py + dy * mark)
    c.restoreState()

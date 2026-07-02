#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
내지 PDF 생성 (Vercel 배포용 — PyMuPDF 제거, pypdf 사용)
- 1p: 제목 페이지 (reportlab)
- 2p~: 부제목 + 본문 (fpdf2)
- 합치기: pypdf
"""

import io
import os
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.colors import Color, black, white
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage
from pypdf import PdfWriter, PdfReader

from pdf_utils import (
    mm, PW, PH, BD, CW, CH,
    cx, cy, cy_t,
    draw_cropmarks,
    FONT_DIR,
    register_fonts,
)

register_fonts()

TITLE_SIZE     = 26
TITLE_LEADING  = 34
TITLE_TRACK    = -0.10
TITLE_OPACITY  = 0.20
TITLE_TOP_MM   = 70

LOGO_BOT_MM    = 35
LOGO_W_MM      = 30
LOGO_OPACITY   = 1.0
LOGO_PATH      = os.path.join(os.path.dirname(__file__), "assets", "logo.png")

SUB_SIZE       = 26
SUB_LEADING    = 34
SUB_TRACK      = -0.10
SUB_TOP_MM     = 32
SUB_LEFT_MM    = 25


def normalize_quotes(text):
    result = []
    for i, ch in enumerate(text):
        prev = text[i - 1] if i > 0 else " "
        if ch == "'":
            result.append("\u2018" if prev in (" ", "\n", "\t", "(") else "\u2019")
        elif ch == '"':
            result.append("\u201c" if prev in (" ", "\n", "\t", "(") else "\u201d")
        else:
            result.append(ch)
    return "".join(result)


def _prepare_logo(opacity):
    path = LOGO_PATH
    if not os.path.exists(path):
        return None, None
    img = PILImage.open(path).convert("RGBA")
    arr = np.array(img)
    orig_alpha = arr[:, :, 3].astype(float) / 255.0
    out = np.zeros_like(arr)
    out[:, :, 0] = 0
    out[:, :, 1] = 0
    out[:, :, 2] = 0
    out[:, :, 3] = (orig_alpha * opacity * 255).astype(np.uint8)
    result = PILImage.fromarray(out, "RGBA")
    buf = io.BytesIO()
    result.save(buf, "PNG")
    buf.seek(0)
    return ImageReader(buf), img.size


def _draw_title_page(c, title):
    c.saveState()
    c.setFillColor(white)
    c.rect(0, 0, CW, CH, fill=1, stroke=0)

    title_ascender = TITLE_SIZE * 0.88
    title_y = cy_t(TITLE_TOP_MM) - (TITLE_SIZE - title_ascender)
    tc = TITLE_SIZE * TITLE_TRACK

    title_color = Color(0, 0, 0, alpha=TITLE_OPACITY)
    c.setFillColor(title_color)
    c.setFont("Paperlogy-9", TITLE_SIZE)
    c._charSpace = tc

    max_title_w = mm(70)
    raw_lines = title.strip().split("\n")
    lines = []
    for raw_line in raw_lines:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        lw = pdfmetrics.stringWidth(raw_line, "Paperlogy-9", TITLE_SIZE) + tc * (len(raw_line) - 1) if len(raw_line) > 1 else pdfmetrics.stringWidth(raw_line, "Paperlogy-9", TITLE_SIZE)
        if lw <= max_title_w:
            lines.append(raw_line)
        else:
            cur = ""
            for ch in raw_line:
                test = cur + ch
                n_test = len(test)
                tw_test = pdfmetrics.stringWidth(test, "Paperlogy-9", TITLE_SIZE) + tc * (n_test - 1) if n_test > 1 else pdfmetrics.stringWidth(test, "Paperlogy-9", TITLE_SIZE)
                if tw_test > max_title_w and cur:
                    lines.append(cur)
                    cur = ch
                else:
                    cur = test
            if cur:
                lines.append(cur)

    y = title_y
    for line in lines:
        if not line:
            continue
        c.setFont("Paperlogy-9", TITLE_SIZE)
        c.drawCentredString(BD + PW / 2, y, line)
        y -= TITLE_LEADING

    logo_cy = cy(LOGO_BOT_MM)
    logo_w = mm(LOGO_W_MM)
    ir, size = _prepare_logo(LOGO_OPACITY)
    if ir and size:
        iw, ih = size
        lh = logo_w * (ih / iw)
        lx = BD + PW / 2 - logo_w / 2
        ly = logo_cy - lh / 2
        c.drawImage(ir, lx, ly, width=logo_w, height=lh, mask="auto")
    else:
        c.setFont("Pretendard-Regular", 8)
        c.setFillColor(Color(0, 0, 0, alpha=TITLE_OPACITY))
        c.drawCentredString(BD + PW / 2, logo_cy, "자라다소년논술")

    draw_cropmarks(c)
    c.restoreState()


def _generate_body_pdf(subtitle, content, title_text=""):
    from fpdf import FPDF

    FONT_PATH = os.path.join(FONT_DIR, "KoPubWorld-Light.ttf")
    FONT_BOLD_PATH = os.path.join(FONT_DIR, "Paperlogy-9Black.ttf")
    PNUM_FONT_PATH = os.path.join(FONT_DIR, "Pretendard-Light.ttf")

    # 도련 포함 페이지: 158x220mm
    BD_MM = 5  # 도련
    MARK_MM = 10  # 재단선 길이

    class MiniBookPDF(FPDF):
        def __init__(self, title_str):
            super().__init__(unit="mm", format=(158, 220))
            self._title_str = title_str
            self._page_start = 2  # 본문 시작 페이지 번호

        def footer(self):
            # 재단선 그리기
            pw_a5 = 148  # A5 가로
            ph_a5 = 210  # A5 세로
            self.set_draw_color(0, 0, 0)
            self.set_line_width(0.09)  # 약 0.25pt
            corners = [
                (BD_MM, BD_MM, -1, -1),
                (BD_MM + pw_a5, BD_MM, 1, -1),
                (BD_MM, BD_MM + ph_a5, -1, 1),
                (BD_MM + pw_a5, BD_MM + ph_a5, 1, 1),
            ]
            for px, py, dx, dy in corners:
                self.line(px, py, px + dx * MARK_MM, py)
                self.line(px, py, px, py + dy * MARK_MM)

            # 페이지 번호
            page_num = self.page + 1  # 1p는 제목이므로 +1
            self.set_font("Pretendard", size=7.5)
            self.set_text_color(0, 0, 0)
            pnum_y = BD_MM + 195  # 하단에서 약 15mm 위

            if page_num % 2 == 0:  # 짝수: 좌하단
                self.set_xy(BD_MM + 20, pnum_y)
                self.cell(0, 0, str(page_num))
            else:  # 홀수: 우하단에 번호 + 책제목
                # 책 제목 (우측 정렬)
                title_clean = " ".join(self._title_str.split()).strip()
                title_w = self.get_string_width(title_clean)
                num_w = self.get_string_width(str(page_num))
                right_x = BD_MM + pw_a5 - 20
                self.set_xy(right_x - num_w, pnum_y)
                self.cell(0, 0, str(page_num))
                self.set_xy(right_x - num_w - 3 - title_w, pnum_y)
                self.cell(0, 0, title_clean)

    pdf = MiniBookPDF(title_text)
    pdf.set_auto_page_break(auto=True, margin=35)
    pdf.set_top_margin(30)
    pdf.t_margin = 30

    BOX_X = 30  # 도련5 + 좌여백25
    pdf.set_left_margin(BOX_X)
    pdf.set_right_margin(158 - BOX_X - 98)

    pdf.add_font("KoPub", "", FONT_PATH)
    pdf.add_font("PaperlogyBlack", "", FONT_BOLD_PATH)
    pdf.add_font("Pretendard", "", PNUM_FONT_PATH)

    BODY_SIZE = 12
    LEADING = 8.1

    pdf.add_page()

    if subtitle and subtitle.strip():
        pdf.set_font("PaperlogyBlack", size=26)
        pdf.set_xy(BOX_X, 30)
        pdf.multi_cell(w=99, h=12, text=subtitle.strip(), align='L')

    pdf.set_y(220 - 35 - 80.5)
    pdf.set_font("KoPub", size=BODY_SIZE)

    content_clean = normalize_quotes(content.strip())
    paras = [p.strip() for p in content_clean.split('\n') if p.strip()]
    INDENT = ' '
    full_text = ('\n\n' + INDENT).join(paras)
    full_text = INDENT + full_text

    pdf.multi_cell(w=98, h=LEADING, text=full_text, align='J', wrapmode='CHAR')

    return pdf.output()


def generate_inner(title, subtitle, content):
    """내지 PDF를 bytes로 반환"""
    # 1p: 제목 페이지 (reportlab)
    buf1 = io.BytesIO()
    c = canvas.Canvas(buf1, pagesize=(CW, CH))
    _draw_title_page(c, title)
    c.showPage()
    c.save()
    buf1.seek(0)
    title_pdf = buf1.read()

    # 2p~: 본문 (fpdf2)
    body_pdf = _generate_body_pdf(subtitle, content, title)

    # 합치기 (pypdf — PyMuPDF 대체)
    writer = PdfWriter()
    reader1 = PdfReader(io.BytesIO(title_pdf))
    for page in reader1.pages:
        writer.add_page(page)
    reader2 = PdfReader(io.BytesIO(body_pdf))
    for page in reader2.pages:
        writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

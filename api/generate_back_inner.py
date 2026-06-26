#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""뒤속지 PDF 생성"""

import io
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black

from pdf_utils import (
    mm, PW, PH, BD, CW, CH,
    cx, cy, cy_t,
    draw_bg, draw_cropmarks,
    register_fonts,
)

register_fonts()

T_FONT    = "Paperlogy-9"
T_SIZE    = 14
LBL_FONT  = "Pretendard-Bold"
VAL_FONT  = "Pretendard-Regular"
INFO_SIZE = 9

INFO_LEFT_MM   = 42.4
TITLE_TOP_MM   = 103.9
TITLE_LEAD     = mm(6.5)
EDITION_TOP_MM = 123.4
CR_TOP_MM      = 185.0
RIGHT_END_MM   = 116.9

ROW_H      = mm(8)
LABEL_COL  = mm(12)
SEP_W      = mm(3)
SEP_GAP    = mm(2)


def generate_back_inner(book_title, author_name, teacher_name,
                        publisher="자라다교육(주)  ㅣ  자라다소년논술"):
    today = datetime.now()
    year = today.year
    date_str = f"{today.year}년 {today.month}월 {today.day}일"

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(CW, CH))
    c.setTitle("뒤속지")

    c.saveState()
    draw_bg(c)
    c.setFillColor(black)

    tx = cx(INFO_LEFT_MM)
    ty = cy_t(TITLE_TOP_MM)
    c.setFont(T_FONT, T_SIZE)
    for line in (book_title or "제목 없음").strip().split("\n"):
        c.drawString(tx, ty, line.strip())
        ty -= TITLE_LEAD

    ix = cx(INFO_LEFT_MM)
    top_y = cy_t(EDITION_TOP_MM)
    bot_y = cy_t(CR_TOP_MM)

    c.setFont(LBL_FONT, INFO_SIZE)
    c.drawString(ix, top_y, "초판 1쇄 펴냄")
    sep_pos_ed = ix + LABEL_COL + mm(3)
    c.setFont(VAL_FONT, INFO_SIZE)
    c.drawString(sep_pos_ed, top_y, "ㅣ")
    val_pos_ed = sep_pos_ed + c.stringWidth("ㅣ", VAL_FONT, INFO_SIZE) + mm(3)
    c.drawString(val_pos_ed, top_y, date_str)

    rows = [
        ("지 은 이", author_name or "이름 입력 필요"),
        ("지도교사", teacher_name or "이름 입력 필요"),
        ("감     수", "김태형"),
        ("디 자 인", "구혜림"),
        ("펴 낸 곳", publisher),
    ]

    iy = top_y - ROW_H * 1.5
    for label, value in rows:
        c.setFont(LBL_FONT, INFO_SIZE)
        label_chars = label.replace(" ", "")
        n_chars = len(label_chars)
        if n_chars > 1:
            total_char_w = sum(c.stringWidth(ch, LBL_FONT, INFO_SIZE) for ch in label_chars)
            total_gap = LABEL_COL - total_char_w
            gap_per = total_gap / (n_chars - 1)
            cur_x = ix
            for i, ch in enumerate(label_chars):
                c.drawString(cur_x, iy, ch)
                cur_x += c.stringWidth(ch, LBL_FONT, INFO_SIZE)
                if i < n_chars - 1:
                    cur_x += gap_per
        else:
            c.drawString(ix, iy, label_chars)

        sep_pos = ix + LABEL_COL + mm(3)
        c.setFont(VAL_FONT, INFO_SIZE)
        c.drawString(sep_pos, iy, "ㅣ")
        val_pos = sep_pos + c.stringWidth("ㅣ", VAL_FONT, INFO_SIZE) + mm(3)
        c.drawString(val_pos, iy, value)
        iy -= ROW_H

    cr_y = bot_y
    cr_text = f"© {year}. 자라다소년논술 All rights reserved."
    nc_text = "〈비매품〉"
    c.setFont(VAL_FONT, INFO_SIZE)
    c.drawString(ix, cr_y, cr_text)
    nc_w = c.stringWidth(nc_text, VAL_FONT, INFO_SIZE)
    c.drawString(cx(RIGHT_END_MM) - nc_w, cr_y, nc_text)

    draw_cropmarks(c)
    c.restoreState()
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

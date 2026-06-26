#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
앞속지 PDF 생성
- 배경: K:20% 회색
- 작가 사진 (35×40mm) + 작가명 + 작가의 말
"""

import io
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color, black
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage, ImageOps

from pdf_utils import (
    mm, PW, PH, BD, CW, CH,
    cx, cy, cy_t,
    BG_COLOR, draw_bg, draw_cropmarks,
    register_fonts,
)

register_fonts()

PHOTO_LEFT_MM = 22
PHOTO_TOP_MM  = 102
PHOTO_W_MM    = 35
PHOTO_H_MM    = 40

NOTE_LEFT_MM  = 65
NOTE_TOP_MM   = 102
NOTE_W_MM     = 55
NOTE_H_MM     = 80
NOTE_FONT     = "Pretendard-Regular"
NOTE_SIZE     = 9
NOTE_LEADING  = 14


def _crop_photo(img, target_w, target_h):
    iw, ih = img.size
    tr = target_w / target_h
    ir = iw / ih
    if ir > tr:
        nw = int(ih * tr)
        left = (iw - nw) // 2
        img = img.crop((left, 0, left + nw, ih))
    else:
        nh = int(iw / tr)
        top = (ih - nh) // 2
        img = img.crop((0, top, iw, top + nh))
    return img


def _wrap_text(c, text, font, size, avail_w):
    lines = []
    for para in text.replace("\r\n", "\n").split("\n"):
        para = para.strip()
        if not para:
            continue
        cur = ""
        for ch in para:
            test = cur + ch
            if c.stringWidth(test, font, size) <= avail_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines


def generate_front_inner(author_name, photo_bytes, author_note):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(CW, CH))
    c.setTitle("앞속지")

    c.saveState()
    draw_bg(c)
    c.setFillColor(black)

    px = cx(PHOTO_LEFT_MM)
    pw = mm(PHOTO_W_MM)
    ph = mm(PHOTO_H_MM)
    py = cy_t(PHOTO_TOP_MM + PHOTO_H_MM)

    if photo_bytes:
        try:
            img = PILImage.open(io.BytesIO(photo_bytes)).convert("RGB")
            img = ImageOps.exif_transpose(img)
            img = _crop_photo(img, PHOTO_W_MM, PHOTO_H_MM)
            img_buf = io.BytesIO()
            img.save(img_buf, format="JPEG", quality=95)
            img_buf.seek(0)
            c.drawImage(ImageReader(img_buf), px, py, width=pw, height=ph)
        except Exception:
            pass

    # 작가명
    name_y = py - mm(7)
    name_x = cx(PHOTO_LEFT_MM)
    name = author_name or "작가명"

    c.setFillColor(black)
    c.setFont("Paperlogy-6", 10)
    nm_w = c.stringWidth(name, "Paperlogy-6", 10)
    c.drawString(name_x, name_y, name)
    c.setFont("Paperlogy-4", 10)
    c.drawString(name_x + nm_w + mm(1), name_y, " 작가")

    # 작가의 말
    nx = cx(NOTE_LEFT_MM)
    nw = mm(NOTE_W_MM)
    nh = mm(NOTE_H_MM)
    ny = cy_t(NOTE_TOP_MM + NOTE_H_MM)
    pad = mm(3)
    avail_w = nw - pad * 2

    if author_note and author_note.strip():
        c.setFont(NOTE_FONT, NOTE_SIZE)
        c.setFillColor(black)
        lines = _wrap_text(c, author_note, NOTE_FONT, NOTE_SIZE, avail_w)
        ascender = NOTE_SIZE * 0.75
        yt = (py + ph) - ascender
        for line in lines:
            if yt < ny + mm(2):
                break
            c.drawString(nx + pad, yt, line)
            yt -= NOTE_LEADING

    draw_cropmarks(c)
    c.restoreState()
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

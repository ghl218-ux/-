#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
표지(앞표지/뒤표지) PDF 생성
- 이미지 1장을 158×220mm 전체에 꽉 채워서 1페이지 PDF로
"""

import io
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage, ImageOps

from pdf_utils import mm, CW, CH


def generate_cover(image_bytes: bytes) -> bytes:
    if not image_bytes:
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(CW, CH))
        c.showPage()
        c.save()
        buf.seek(0)
        return buf.read()

    img = PILImage.open(io.BytesIO(image_bytes)).convert("RGB")
    img = ImageOps.exif_transpose(img)

    target_ratio = 158 / 220
    iw, ih = img.size
    img_ratio = iw / ih

    if img_ratio > target_ratio:
        new_w = int(ih * target_ratio)
        left = (iw - new_w) // 2
        img = img.crop((left, 0, left + new_w, ih))
    else:
        new_h = int(iw / target_ratio)
        top = (ih - new_h) // 2
        img = img.crop((0, top, iw, top + new_h))

    img_buf = io.BytesIO()
    img.save(img_buf, format="JPEG", quality=95)
    img_buf.seek(0)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(CW, CH))
    c.drawImage(ImageReader(img_buf), 0, 0, width=CW, height=CH)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

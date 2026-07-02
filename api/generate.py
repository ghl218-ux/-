"""
Vercel Serverless Function: PDF 생성
엔드포인트: POST /api/generate
"""

from flask import Flask, request, Response
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(__file__))

from pdf_utils import register_fonts
from generate_front_inner import generate_front_inner
from generate_inner import generate_inner
from generate_back_inner import generate_back_inner
from generate_cover import generate_cover

register_fonts()

app = Flask(__name__)


@app.route('/api/generate', methods=['POST', 'OPTIONS'])
def generate():
    if request.method == 'OPTIONS':
        return Response('', headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        })

    try:
        pdf_type = request.form.get('pdf_type', 'front')

        if pdf_type == 'front_cover':
            f = request.files.get('front_cover')
            img_bytes = f.read() if f else b''
            pdf_bytes = generate_cover(img_bytes)

        elif pdf_type == 'front':
            author_name = request.form.get('author_name', '작가명')
            author_note = request.form.get('author_note', '')
            f = request.files.get('photo')
            photo_bytes = f.read() if f else None
            pdf_bytes = generate_front_inner(author_name, photo_bytes, author_note)

        elif pdf_type == 'inner':
            title = request.form.get('title', '제목')
            subtitle = request.form.get('subtitle', '부제목')
            content = request.form.get('content', '')
            pdf_bytes = generate_inner(title, subtitle, content)

        elif pdf_type == 'back':
            book_title = request.form.get('book_title', '책 제목')
            author_name = request.form.get('author_name', '')
            teacher_name = request.form.get('teacher_name', '')
            publisher = request.form.get('publisher', '자라다교육(주)  ㅣ  자라다소년논술')
            pdf_bytes = generate_back_inner(book_title, author_name, teacher_name, publisher)

        elif pdf_type == 'back_cover':
            f = request.files.get('back_cover')
            img_bytes = f.read() if f else b''
            pdf_bytes = generate_cover(img_bytes)

        else:
            return Response(f'{{"error":"Unknown pdf_type: {pdf_type}"}}',
                          status=400, content_type='application/json')

        return Response(pdf_bytes, content_type='application/pdf', headers={
            'Access-Control-Allow-Origin': '*',
            'Content-Disposition': 'attachment; filename="output.pdf"',
        })

    except Exception as e:
        return Response(
            f'{{"error":"{str(e)}","trace":"{traceback.format_exc()}"}}',
            status=500, content_type='application/json',
            headers={'Access-Control-Allow-Origin': '*'}
        )

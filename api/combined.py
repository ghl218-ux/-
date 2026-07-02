"""
Vercel Serverless Function: 통합 PDF 생성
엔드포인트: POST /api/combined
"""

from flask import Flask, request, Response
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(__file__))

from pdf_utils import register_fonts
from generate_front_inner import generate_front_inner
from generate_inner import generate_inner
from generate_back_inner import generate_back_inner
from generate_cover import generate_cover
from pypdf import PdfWriter, PdfReader

register_fonts()

app = Flask(__name__)


@app.route('/api/combined', methods=['POST', 'OPTIONS'])
def combined():
    if request.method == 'OPTIONS':
        return Response('', headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        })

    try:
        pdfs = []

        # 1. 앞표지
        fc = request.files.get('front_cover')
        if fc:
            pdfs.append(generate_cover(fc.read()))

        # 2. 앞속지
        author_name = request.form.get('author_name', '')
        author_note = request.form.get('author_note', '')
        photo = request.files.get('photo')
        photo_bytes = photo.read() if photo else None
        pdfs.append(generate_front_inner(author_name, photo_bytes, author_note))

        # 3. 내지
        title = request.form.get('title', '제목')
        subtitle = request.form.get('subtitle', '부제목')
        content = request.form.get('content', '본문')
        pdfs.append(generate_inner(title, subtitle, content))

        # 4. 뒤속지
        book_title = request.form.get('book_title', '책 제목')
        back_author = request.form.get('back_author', '')
        teacher_name = request.form.get('teacher_name', '')
        pdfs.append(generate_back_inner(
            book_title, back_author, teacher_name,
            '자라다교육(주)  ㅣ  자라다소년논술'
        ))

        # 5. 뒤표지
        bc = request.files.get('back_cover')
        if bc:
            pdfs.append(generate_cover(bc.read()))

        # PDF 합치기
        writer = PdfWriter()
        for pdf_bytes in pdfs:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                writer.add_page(page)

        output = io.BytesIO()
        writer.write(output)
        result = output.getvalue()

        return Response(result, content_type='application/pdf', headers={
            'Access-Control-Allow-Origin': '*',
            'Content-Disposition': 'attachment; filename="minibook.pdf"',
        })

    except Exception as e:
        return Response(
            f'{{"error":"{str(e)}"}}',
            status=500, content_type='application/json',
            headers={'Access-Control-Allow-Origin': '*'}
        )

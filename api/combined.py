"""
Vercel Serverless Function: 통합 PDF 생성
엔드포인트: POST /api/combined

모든 파트(앞표지 + 앞속지 + 내지 + 뒤속지 + 뒤표지)를 합쳐서 1개 PDF 반환
"""

from http.server import BaseHTTPRequestHandler
import json
import io
import cgi
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


def _parse_multipart(handler):
    content_type = handler.headers.get('Content-Type', '')
    environ = {
        'REQUEST_METHOD': 'POST',
        'CONTENT_TYPE': content_type,
        'CONTENT_LENGTH': handler.headers.get('Content-Length', '0'),
    }
    form = cgi.FieldStorage(
        fp=handler.rfile,
        headers=handler.headers,
        environ=environ,
    )
    fields = {}
    files = {}
    for key in form.keys():
        item = form[key]
        if isinstance(item, list):
            item = item[0]
        if item.filename:
            files[key] = item.file.read()
        else:
            fields[key] = item.value
    return fields, files


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            fields, files = _parse_multipart(self)

            pdfs = []

            # 1. 앞표지
            fc_bytes = files.get('front_cover')
            if fc_bytes:
                pdfs.append(generate_cover(fc_bytes))

            # 2. 앞속지
            author_name = fields.get('author_name', '')
            author_note = fields.get('author_note', '')
            photo_bytes = files.get('photo', None)
            pdfs.append(generate_front_inner(author_name or '', photo_bytes, author_note))

            # 3. 내지
            title = fields.get('title', '제목')
            subtitle = fields.get('subtitle', '부제목')
            content = fields.get('content', '본문')
            pdfs.append(generate_inner(title, subtitle, content))

            # 4. 뒤속지
            book_title = fields.get('book_title', '책 제목')
            back_author = fields.get('back_author', '')
            teacher_name = fields.get('teacher_name', '')
            pdfs.append(generate_back_inner(
                book_title, back_author, teacher_name,
                '자라다교육(주)  ㅣ  자라다소년논술'
            ))

            # 5. 뒤표지
            bc_bytes = files.get('back_cover')
            if bc_bytes:
                pdfs.append(generate_cover(bc_bytes))

            # PDF 합치기 (pypdf 사용)
            writer = PdfWriter()
            for pdf_bytes in pdfs:
                reader = PdfReader(io.BytesIO(pdf_bytes))
                for page in reader.pages:
                    writer.add_page(page)

            output = io.BytesIO()
            writer.write(output)
            result = output.getvalue()

            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', 'attachment; filename="minibook.pdf"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(result)

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': str(e),
                'trace': traceback.format_exc()
            }).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

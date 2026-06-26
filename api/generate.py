"""
Vercel Serverless Function: PDF 생성
엔드포인트: POST /api/generate

요청 body (multipart/form-data):
  - pdf_type: front_cover | front | inner | back | back_cover
  - author_name, author_note, photo, front_cover, back_cover
  - title, subtitle, content, book_title, teacher_name
"""

from http.server import BaseHTTPRequestHandler
import json
import io
import cgi
import os
import sys
import traceback

# API 폴더를 path에 추가 (같은 폴더의 모듈 import용)
sys.path.insert(0, os.path.dirname(__file__))

from pdf_utils import register_fonts
from generate_front_inner import generate_front_inner
from generate_inner import generate_inner
from generate_back_inner import generate_back_inner
from generate_cover import generate_cover


register_fonts()


def _parse_multipart(handler):
    """multipart/form-data 파싱"""
    content_type = handler.headers.get('Content-Type', '')
    if 'multipart/form-data' not in content_type:
        # JSON body
        length = int(handler.headers.get('Content-Length', 0))
        body = handler.rfile.read(length)
        return json.loads(body), {}

    # multipart 파싱
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
            pdf_type = fields.get('pdf_type', 'front')

            if pdf_type == 'front_cover':
                img_bytes = files.get('front_cover', b'')
                pdf_bytes = generate_cover(img_bytes) if img_bytes else generate_cover(b'')

            elif pdf_type == 'front':
                author_name = fields.get('author_name', '작가명')
                author_note = fields.get('author_note', '')
                photo_bytes = files.get('photo', None)
                pdf_bytes = generate_front_inner(author_name, photo_bytes, author_note)

            elif pdf_type == 'inner':
                title = fields.get('title', '제목')
                subtitle = fields.get('subtitle', '부제목')
                content = fields.get('content', '')
                pdf_bytes = generate_inner(title, subtitle, content)

            elif pdf_type == 'back':
                book_title = fields.get('book_title', '책 제목')
                author_name = fields.get('author_name', '')
                teacher_name = fields.get('teacher_name', '')
                publisher = fields.get('publisher', '자라다교육(주)  ㅣ  자라다소년논술')
                pdf_bytes = generate_back_inner(book_title, author_name, teacher_name, publisher)

            elif pdf_type == 'back_cover':
                img_bytes = files.get('back_cover', b'')
                pdf_bytes = generate_cover(img_bytes) if img_bytes else generate_cover(b'')

            else:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Unknown pdf_type: {pdf_type}'}).encode())
                return

            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', 'attachment; filename="output.pdf"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(pdf_bytes)

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

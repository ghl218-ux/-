# 소년논술 미니북 PDF 생성기 — Vercel 배포 가이드

## 배포 구조

```
deploy/
├── api/                    ← Vercel Python Serverless Functions
│   ├── generate.py         ← /api/generate (PDF 생성 엔드포인트)
│   ├── pdf_utils.py        ← 공통 유틸리티
│   ├── generate_front_inner.py
│   ├── generate_inner.py
│   ├── generate_back_inner.py
│   ├── generate_cover.py
│   ├── fonts/              ← TTF 폰트 파일들
│   │   ├── Paperlogy-9Black.ttf
│   │   ├── Paperlogy-6SemiBold.ttf
│   │   ├── Paperlogy-4Regular.ttf
│   │   ├── KoPubWorld-Light.ttf
│   │   ├── KoPubWorld-Bold.ttf
│   │   ├── Pretendard-Regular.ttf
│   │   ├── Pretendard-Bold.ttf
│   │   ├── Pretendard-Medium.ttf
│   │   ├── Pretendard-Light.ttf
│   │   └── Pretendard-SemiBold.ttf
│   ├── assets/
│   │   └── logo.png
│   └── requirements.txt    ← Python 패키지 (reportlab, Pillow, fpdf2, pypdf)
├── public/
│   └── index.html          ← 프론트엔드 (정적 HTML)
├── vercel.json             ← Vercel 설정
├── .gitignore
└── README.md
```

## 핵심 변경 사항 (로컬 → Vercel)

1. **PyMuPDF(fitz) 제거** → `pypdf`로 대체 (PDF 합치기)
2. **미리보기 PNG 렌더링** → 클라이언트 `pdf.js`로 대체
3. **FastAPI → Vercel Serverless Functions** (각 엔드포인트 = 1개 파일)
4. **HTML을 별도 정적 파일로 분리**

## 배포 절차

### 1단계: GitHub 저장소 생성
```bash
cd deploy
git init
git add .
git commit -m "초기 배포"
git remote add origin https://github.com/YOUR_USERNAME/minibook-pdf.git
git push -u origin main
```

### 2단계: Vercel 프로젝트 연결
1. https://vercel.com 로그인
2. "Add New Project" → GitHub 저장소 선택
3. Framework Preset: "Other"
4. 배포 클릭

### 3단계: Supabase (선택사항)
- 생성된 PDF를 저장하거나 사용자 관리가 필요한 경우
- Supabase Storage로 PDF 임시 저장 → 다운로드 링크 공유
- 환경변수로 SUPABASE_URL, SUPABASE_KEY 설정

## 주의사항

- Vercel Serverless Function은 **50MB 배포 크기 제한**이 있음
  - 폰트 파일(TTF)이 많으면 용량 초과 가능
  - 필요한 폰트만 포함할 것
- **실행 시간 제한**: 무료 플랜 10초, Pro 60초
  - 내지 PDF 생성이 긴 경우 타임아웃 주의
- **메모리**: 1024MB (기본)

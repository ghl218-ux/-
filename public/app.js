// pdf.js 워커 설정
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

let currentTab = 'front_cover';
let zoomLevel = 1.0;
let cachedPdfs = {}; // pdf_type → ArrayBuffer

// ── 파일 업로드 핸들러 ──
function setupFileUpload(inputId) {
  const input = document.getElementById(inputId);
  const zone = document.getElementById('zone-' + inputId);
  const result = document.getElementById('result-' + inputId);
  const fname = document.getElementById('fname-' + inputId);
  input.addEventListener('change', () => {
    if (input.files.length > 0) {
      fname.textContent = input.files[0].name;
      zone.style.display = 'none';
      result.classList.add('show');
    }
  });
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => { zone.classList.remove('dragover'); });
  zone.addEventListener('drop', (e) => {
    e.preventDefault(); zone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type.startsWith('image/')) {
      const dt = new DataTransfer(); dt.items.add(files[0]); input.files = dt.files;
      input.dispatchEvent(new Event('change'));
    }
  });
}
function clearFile(inputId) {
  document.getElementById(inputId).value = '';
  document.getElementById('zone-' + inputId).style.display = 'flex';
  document.getElementById('result-' + inputId).classList.remove('show');
}
setupFileUpload('front_cover');
setupFileUpload('photo');
setupFileUpload('back_cover');

// ── 글자수 카운터 ──
function setupCounter(id, cntId, max) {
  const el = document.getElementById(id); if (!el) return;
  const cnt = document.getElementById(cntId);
  el.addEventListener('input', () => {
    const len = el.value.replace(/\n/g, '').length;
    cnt.textContent = len + ' / ' + max + '자';
    cnt.className = 'char-count' + (len > max ? ' over' : len > max * 0.85 ? ' warn' : '');
  });
}
setupCounter('author_note', 'cnt-note', 300);
setupCounter('title', 'cnt-title', 30);
setupCounter('subtitle', 'cnt-subtitle', 30);
setupCounter('book_title', 'cnt-book-title', 30);

// ── 상태바 ──
function setStatus(t, m) { const e = document.getElementById('status-bar'); e.className = 'status-bar ' + t; e.textContent = m; }
function clearStatus() { document.getElementById('status-bar').className = 'status-bar'; }

// ── 이미지 압축 (항상 압축하여 전송 크기 줄임) ──
function compressImage(file) {
  return new Promise((resolve) => {
    // 1MB 이하면 그냥 보냄
    if (file.size <= 1 * 1024 * 1024) { resolve(file); return; }
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let w = img.width, h = img.height;
        const maxDim = 1800;
        if (w > maxDim || h > maxDim) {
          if (w > h) { h = Math.round(h * maxDim / w); w = maxDim; }
          else { w = Math.round(w * maxDim / h); h = maxDim; }
        }
        canvas.width = w; canvas.height = h;
        canvas.getContext('2d').drawImage(img, 0, 0, w, h);
        canvas.toBlob((blob) => {
          resolve(new File([blob], file.name.replace(/\.\w+$/, '.jpg'), { type: 'image/jpeg' }));
        }, 'image/jpeg', 0.7);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}

// ── 줌 ──
function zoomIn() { zoomLevel = Math.min(+(zoomLevel + 0.2).toFixed(1), 3); renderCurrentPage(); }
function zoomOut() { zoomLevel = Math.max(+(zoomLevel - 0.2).toFixed(1), 0.3); renderCurrentPage(); }

// ── 탭 전환 ──
function switchPreview(tab) {
  currentTab = tab;
  document.querySelectorAll('.preview-tab').forEach(b => b.classList.remove('active'));
  document.getElementById('ptab-' + tab).classList.add('active');
  if (cachedPdfs[tab]) {
    renderPdfPreview(cachedPdfs[tab]);
  }
}

// ── FormData 빌더 ──
async function buildFormData(tab) {
  const fd = new FormData();
  fd.append('pdf_type', tab);
  if (tab === 'back') {
    fd.append('author_name', document.getElementById('back_author').value || '');
  } else {
    fd.append('author_name', document.getElementById('author_name').value || '작가명');
  }
  fd.append('author_note', document.getElementById('author_note').value);
  const pf = document.getElementById('photo').files[0];
  if (pf) { const compressed = await compressImage(pf); fd.append('photo', compressed); }
  const fc = document.getElementById('front_cover').files[0];
  if (fc) { const compressed = await compressImage(fc); fd.append('front_cover', compressed); }
  const bc = document.getElementById('back_cover').files[0];
  if (bc) { const compressed = await compressImage(bc); fd.append('back_cover', compressed); }
  fd.append('title', document.getElementById('title').value || '제목');
  fd.append('subtitle', document.getElementById('subtitle').value || '부제목');
  fd.append('content', document.getElementById('content').value || '본문');
  fd.append('book_title', document.getElementById('book_title').value || '책 제목');
  fd.append('teacher_name', document.getElementById('teacher_name').value || '');
  return fd;
}

// ── 확인 버튼 → PDF 생성 + 미리보기 ──
async function confirmSection(tab) {
  currentTab = tab;
  document.querySelectorAll('.preview-tab').forEach(b => b.classList.remove('active'));
  document.getElementById('ptab-' + tab).classList.add('active');

  document.getElementById('preview-placeholder').style.display = 'none';
  document.getElementById('preview-loading').style.display = 'flex';
  document.getElementById('preview-canvas').style.display = 'none';
  clearStatus();

  try {
    const fd = await buildFormData(tab);
    const res = await fetch('/api/generate', { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: '오류' }));
      throw new Error(err.error || '서버 오류');
    }
    const pdfBuffer = await res.arrayBuffer();
    cachedPdfs[tab] = pdfBuffer.slice(0);  // 복사본 저장 (pdf.js가 원본을 소비하므로)
    await renderPdfPreview(pdfBuffer);
    document.getElementById('btn-dl-preview').style.display = 'block';
  } catch (e) {
    document.getElementById('preview-placeholder').style.display = 'flex';
    setStatus('error', '미리보기 오류: ' + e.message);
  } finally {
    document.getElementById('preview-loading').style.display = 'none';
  }
}

// ── pdf.js로 PDF를 Canvas에 렌더링 ──
let currentPdfDoc = null;
let currentPageIdx = 0;

async function renderPdfPreview(pdfBuffer) {
  const pdf = await pdfjsLib.getDocument({ data: pdfBuffer }).promise;
  currentPdfDoc = pdf;
  currentPageIdx = 0;

  // 썸네일 생성
  const thumbList = document.getElementById('thumb-list');
  thumbList.innerHTML = '';
  document.getElementById('thumb-placeholder').style.display = 'none';

  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const vp = page.getViewport({ scale: 0.3 });
    const card = document.createElement('div'); card.className = 'thumb-card';
    const cvs = document.createElement('canvas');
    cvs.width = vp.width; cvs.height = vp.height;
    if (i === 1) cvs.classList.add('active-thumb');
    const idx = i - 1;
    cvs.onclick = () => { currentPageIdx = idx; renderCurrentPage(); updateThumbActive(idx); };
    await page.render({ canvasContext: cvs.getContext('2d'), viewport: vp }).promise;
    const num = document.createElement('div'); num.className = 'thumb-page-num'; num.textContent = i;
    card.appendChild(cvs); card.appendChild(num); thumbList.appendChild(card);
  }

  renderCurrentPage();
}

function updateThumbActive(idx) {
  document.querySelectorAll('.thumb-card canvas').forEach((c, i) => c.classList.toggle('active-thumb', i === idx));
}

async function renderCurrentPage() {
  if (!currentPdfDoc) return;
  const page = await currentPdfDoc.getPage(currentPageIdx + 1);
  const vp = page.getViewport({ scale: 1.5 * zoomLevel });
  const cvs = document.getElementById('preview-canvas');
  cvs.width = vp.width; cvs.height = vp.height;
  cvs.style.display = 'block';
  await page.render({ canvasContext: cvs.getContext('2d'), viewport: vp }).promise;
}

// ── 개별 다운로드 ──
function downloadCurrent() {
  const pdfBuffer = cachedPdfs[currentTab];
  if (!pdfBuffer) { setStatus('error', '먼저 확인 버튼을 눌러주세요.'); return; }
  const names = { front_cover: '앞표지.pdf', front: '앞속지.pdf', inner: '내지.pdf', back: '뒤속지.pdf', back_cover: '뒤표지.pdf' };
  const blob = new Blob([pdfBuffer], { type: 'application/pdf' });
  const u = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = u; a.download = names[currentTab] || 'download.pdf'; a.click();
  setTimeout(() => URL.revokeObjectURL(u), 1000);
}

// ── 전체 PDF 다운로드 ──
async function generateAll() {
  const a = document.getElementById('author_name').value.trim();
  const t = document.getElementById('title').value.trim();
  const s = document.getElementById('subtitle').value.trim();
  const c = document.getElementById('content').value.trim();
  const bt = document.getElementById('book_title').value.trim();
  const ba = document.getElementById('back_author').value.trim();
  const tn = document.getElementById('teacher_name').value.trim();

  if (!a) { setStatus('error', '❌ 앞속지: 작가 이름을 입력해주세요.'); return; }
  if (!t) { setStatus('error', '❌ 내지: 책 제목을 입력해주세요.'); return; }
  if (!s) { setStatus('error', '❌ 내지: 부제목을 입력해주세요.'); return; }
  if (!c) { setStatus('error', '❌ 내지: 본문 내용을 입력해주세요.'); return; }
  if (!bt) { setStatus('error', '❌ 뒤속지: 책 제목을 입력해주세요.'); return; }
  if (!ba) { setStatus('error', '❌ 뒤속지: 지은이를 입력해주세요.'); return; }
  if (!tn) { setStatus('error', '❌ 뒤속지: 지도교사를 입력해주세요.'); return; }

  const btn = document.getElementById('btn-gen'); btn.disabled = true;
  setStatus('loading', '⏳ 통합 PDF 생성 중...');

  try {
    const fd = new FormData();
    fd.append('author_name', a);
    fd.append('author_note', document.getElementById('author_note').value);
    const pf = document.getElementById('photo').files[0]; if (pf) fd.append('photo', pf);
    const fc = document.getElementById('front_cover').files[0]; if (fc) fd.append('front_cover', fc);
    const bc = document.getElementById('back_cover').files[0]; if (bc) fd.append('back_cover', bc);
    fd.append('title', t);
    fd.append('subtitle', s);
    fd.append('content', c);
    fd.append('book_title', bt);
    fd.append('back_author', ba);
    fd.append('teacher_name', tn);

    const r = await fetch('/api/combined', { method: 'POST', body: fd });
    if (!r.ok) { const j = await r.json().catch(() => ({ error: '오류' })); throw new Error(j.error); }
    const blob = await r.blob();
    const u = URL.createObjectURL(blob);
    const fname = t.replace(/\n/g, ' ').trim() + '.pdf';
    const a2 = document.createElement('a'); a2.href = u; a2.download = fname; a2.click();
    setTimeout(() => URL.revokeObjectURL(u), 1000);
    setStatus('success', '✅ 통합 PDF 생성 완료!');
  } catch (e) {
    setStatus('error', '❌ ' + e.message);
  } finally {
    btn.disabled = false;
  }
}

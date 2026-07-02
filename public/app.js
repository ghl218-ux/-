// pdf.js 워커 설정
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

let currentTab = 'front_cover';
let zoomLevel = 1.0;
let tabData = {};
// tabData[tab] = { pdfDoc, pdfBytes, pdfUrl, thumbDataUrls, pageIdx }

// 렌더링 제어 — 단순화
let renderVersion = 0;
let currentRenderTask = null;

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

// ── 이미지 압축 ──
function compressImage(file) {
  return new Promise((resolve) => {
    if (file.size <= 500 * 1024) { resolve(file); return; }
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let w = img.width, h = img.height;
        const maxDim = 1500;
        if (w > maxDim || h > maxDim) {
          if (w > h) { h = Math.round(h * maxDim / w); w = maxDim; }
          else { w = Math.round(w * maxDim / h); h = maxDim; }
        }
        canvas.width = w; canvas.height = h;
        canvas.getContext('2d').drawImage(img, 0, 0, w, h);
        canvas.toBlob((blob) => {
          resolve(new File([blob], file.name.replace(/\.\w+$/, '.jpg'), { type: 'image/jpeg' }));
        }, 'image/jpeg', 0.6);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}

// ── 줌 ──
function zoomIn() { zoomLevel = Math.min(+(zoomLevel + 0.2).toFixed(1), 3); requestRender(); }
function zoomOut() { zoomLevel = Math.max(+(zoomLevel - 0.2).toFixed(1), 0.3); requestRender(); }

// ── 렌더링 요청 ──
function requestRender() {
  renderVersion++;
  const v = renderVersion;
  // 진행 중인 렌더 task 취소
  if (currentRenderTask) {
    try { currentRenderTask.cancel(); } catch(e) {}
    currentRenderTask = null;
  }
  // 약간의 딜레이로 연속 클릭 병합
  setTimeout(() => {
    if (renderVersion === v) doRender(v);
  }, 30);
}

async function doRender(myVersion) {
  const myTab = currentTab;
  const data = tabData[myTab];
  if (!data || !data.pdfDoc) return;
  if (renderVersion !== myVersion) return;

  try {
    const pageIdx = data.pageIdx || 0;
    const page = await data.pdfDoc.getPage(pageIdx + 1);
    if (renderVersion !== myVersion) return;

    const vp = page.getViewport({ scale: 1.5 * zoomLevel });
    const cvs = document.getElementById('preview-canvas');
    cvs.width = vp.width; cvs.height = vp.height;
    cvs.style.display = 'block';

    const task = page.render({ canvasContext: cvs.getContext('2d'), viewport: vp });
    currentRenderTask = task;
    await task.promise;
    currentRenderTask = null;

    if (renderVersion !== myVersion) return;
    updateThumbActive(pageIdx);
  } catch(e) {
    if (e && e.name === 'RenderingCancelledException') return;
    console.error('렌더링 오류:', e);
  }
}

// ── 탭 전환 ──
function switchPreview(tab) {
  currentTab = tab;
  document.querySelectorAll('.preview-tab').forEach(b => b.classList.remove('active'));
  document.getElementById('ptab-' + tab).classList.add('active');

  const data = tabData[tab];
  if (data && data.pdfDoc) {
    document.getElementById('preview-placeholder').style.display = 'none';
    document.getElementById('preview-canvas').style.display = 'block';
    document.getElementById('btn-dl-preview').style.display = 'block';
    document.getElementById('thumb-list').innerHTML = buildThumbHtml(data.thumbDataUrls, data.pageIdx || 0);
    document.getElementById('thumb-placeholder').style.display = 'none';
    rebindThumbnails();
    requestRender();
  } else {
    document.getElementById('preview-canvas').style.display = 'none';
    document.getElementById('preview-placeholder').style.display = 'flex';
    document.getElementById('btn-dl-preview').style.display = 'none';
    document.getElementById('thumb-list').innerHTML = '';
    document.getElementById('thumb-placeholder').style.display = 'block';
  }
}

function rebindThumbnails() {
  document.querySelectorAll('.thumb-card img').forEach((img, idx) => {
    img.onclick = () => {
      const data = tabData[currentTab];
      if (data) data.pageIdx = idx;
      requestRender();
      updateThumbActive(idx);
    };
  });
}

function updateThumbActive(idx) {
  document.querySelectorAll('.thumb-card img').forEach((c, i) => c.classList.toggle('active-thumb', i === idx));
}

// dataURL 배열을 받아서 썸네일 목록 HTML을 생성 (img 태그 사용 — 저장/복원이 완벽함)
function buildThumbHtml(dataUrls, activeIdx) {
  return dataUrls.map((url, i) => (
    '<div class="thumb-card">' +
    '<img src="' + url + '" class="' + (i === activeIdx ? 'active-thumb' : '') + '">' +
    '<div class="thumb-page-num">' + (i + 1) + '</div>' +
    '</div>'
  )).join('');
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

  const requestedTab = tab;

  try {
    const fd = await buildFormData(tab);
    const res = await fetch('/api/generate', { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: '오류' }));
      throw new Error(err.error || '서버 오류');
    }
    const arrayBuf = await res.arrayBuffer();
    const pdfBytes = new Uint8Array(arrayBuf);

    // 이전 탭 데이터의 Blob URL 정리
    if (tabData[requestedTab] && tabData[requestedTab].pdfUrl) {
      URL.revokeObjectURL(tabData[requestedTab].pdfUrl);
    }

    // pdf.js 문서 로드 (Blob URL 사용 — buffer detach 방지)
    const pdfBlob = new Blob([pdfBytes], { type: 'application/pdf' });
    const pdfUrl = URL.createObjectURL(pdfBlob);
    const pdfDoc = await pdfjsLib.getDocument(pdfUrl).promise;

    // 썸네일 생성 (dataURL 배열로 저장 — canvas는 innerHTML로 직렬화되지 않으므로
    // 반드시 이미지 문자열로 변환해서 저장해야 나중에 정상 복원됨)
    const thumbDataUrls = [];
    for (let i = 1; i <= pdfDoc.numPages; i++) {
      const page = await pdfDoc.getPage(i);
      const vp = page.getViewport({ scale: 0.3 });
      const cvs = document.createElement('canvas');
      cvs.width = vp.width; cvs.height = vp.height;
      await page.render({ canvasContext: cvs.getContext('2d'), viewport: vp }).promise;
      thumbDataUrls.push(cvs.toDataURL('image/png'));
    }

    // 탭 데이터 저장
    tabData[requestedTab] = {
      pdfDoc: pdfDoc,
      pdfBytes: pdfBytes,
      pdfUrl: pdfUrl,
      thumbDataUrls: thumbDataUrls,
      pageIdx: 0
    };

    // 현재 탭이 요청한 탭이면 화면 업데이트
    if (currentTab === requestedTab) {
      document.getElementById('thumb-list').innerHTML = buildThumbHtml(thumbDataUrls, 0);
      document.getElementById('thumb-placeholder').style.display = 'none';
      rebindThumbnails();
      document.getElementById('preview-canvas').style.display = 'block';
      document.getElementById('btn-dl-preview').style.display = 'block';
      requestRender();
    }
  } catch (e) {
    if (currentTab === requestedTab) {
      document.getElementById('preview-placeholder').style.display = 'flex';
      setStatus('error', '미리보기 오류: ' + e.message);
    }
  } finally {
    if (currentTab === requestedTab) {
      document.getElementById('preview-loading').style.display = 'none';
    }
  }
}

// ── 개별 다운로드 ──
function downloadCurrent() {
  const data = tabData[currentTab];
  if (!data || !data.pdfBytes) { setStatus('error', '먼저 확인 버튼을 눌러주세요.'); return; }
  const names = { front_cover: '앞표지.pdf', front: '앞속지.pdf', inner: '내지.pdf', back: '뒤속지.pdf', back_cover: '뒤표지.pdf' };
  const copy = data.pdfBytes.slice(0);
  const blob = new Blob([copy], { type: 'application/pdf' });
  const u = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = u; a.download = names[currentTab] || 'download.pdf';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(u), 3000);
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
    const pf = document.getElementById('photo').files[0];
    if (pf) { const cpf = await compressImage(pf); fd.append('photo', cpf); }
    const fc = document.getElementById('front_cover').files[0];
    if (fc) { const cfc = await compressImage(fc); fd.append('front_cover', cfc); }
    const bc = document.getElementById('back_cover').files[0];
    if (bc) { const cbc = await compressImage(bc); fd.append('back_cover', cbc); }
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
    const a2 = document.createElement('a'); a2.href = u; a2.download = fname;
    document.body.appendChild(a2); a2.click(); document.body.removeChild(a2);
    setTimeout(() => URL.revokeObjectURL(u), 3000);
    setStatus('success', '✅ 통합 PDF 생성 완료!');
  } catch (e) {
    setStatus('error', '❌ ' + e.message);
  } finally {
    btn.disabled = false;
  }
}

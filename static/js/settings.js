document.addEventListener('DOMContentLoaded', () => {
  loadKeys();
  loadTables();
  document.getElementById('keys-form').addEventListener('submit', saveKeys);
  document.getElementById('refresh-tables').addEventListener('click', loadTables);
  document.getElementById('db-tables').addEventListener('change', loadSelectedTable);
});

async function loadKeys() {
  try {
    const r = await fetch('/api/bitunix/keys');
    const j = await r.json();
    document.getElementById('bitunix_api_key').value = j.bitunix_api_key || '';
    document.getElementById('bitunix_api_secret').value = '';
  } catch (e) {
    setStatus('keys-status', 'خطا در خواندن کلیدها');
  }
}

async function saveKeys(e) {
  e.preventDefault();
  try {
    const apiKey = document.getElementById('bitunix_api_key').value.trim();
    const apiSecret = document.getElementById('bitunix_api_secret').value.trim();
    const r = await fetch('/api/bitunix/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bitunix_api_key: apiKey, bitunix_api_secret: apiSecret })
    });
    const j = await r.json();
    if (j.success) setStatus('keys-status', 'ذخیره شد و اتصال Bitunix به‌روزرسانی شد');
    else setStatus('keys-status', 'خطا در ذخیره');
  } catch (e) {
    setStatus('keys-status', 'خطا در ذخیره کلیدها');
  }
}

async function loadTables() {
  try {
    const r = await fetch('/api/db/tables');
    const j = await r.json();
    const sel = document.getElementById('db-tables');
    sel.innerHTML = '';
    (j.tables || []).forEach(t => {
      const opt = document.createElement('option');
      opt.value = t; opt.textContent = t; sel.appendChild(opt);
    });
    if (sel.options.length > 0) {
      sel.selectedIndex = 0;
      loadSelectedTable();
    }
  } catch (e) {
    setGrid([], []);
  }
}

async function loadSelectedTable() {
  const sel = document.getElementById('db-tables');
  const table = sel.value;
  if (!table) return;
  try {
    const r = await fetch(`/api/db/table/${table}?limit=200`);
    const j = await r.json();
    setGrid(j.columns || [], j.rows || []);
  } catch (e) {
    setGrid([], []);
  }
}

function setGrid(cols, rows) {
  const head = document.getElementById('db-grid-head');
  const body = document.getElementById('db-grid-body');
  if (!cols.length) {
    head.innerHTML = '';
    body.innerHTML = '<tr><td class="loading">داده‌ای موجود نیست</td></tr>';
    return;
  }
  head.innerHTML = cols.map(c => `<th>${c}</th>`).join('');
  body.innerHTML = rows.map(r => {
    return `<tr>${cols.map(c => `<td>${escapeCell(r[c])}</td>`).join('')}</tr>`;
  }).join('');
}

function escapeCell(v) {
  if (v === null || v === undefined) return '';
  return String(v);
}

function setStatus(id, txt) {
  const el = document.getElementById(id);
  if (el) el.textContent = txt;
}

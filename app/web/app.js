'use strict';
/* Интерфейс программы «Расшифровка». Без сборки и внешних библиотек: всё работает офлайн. */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const view = $('#view');
const PALETTE = ['#2f6fed', '#e8890c', '#16a374', '#d6455d', '#8a5cf6', '#d64fa8', '#0f9fb3', '#7c9a12', '#a0653a', '#c99a06'];

const ICONS = {
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
  check: '<path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14.2a6.5 6.5 0 0 1 3.5 5.8"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z"/><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>',
  gear: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  play: '<path d="M7 4.5v15l13-7.5z"/>',
  pause: '<path d="M6.5 4h4v16h-4zM13.5 4h4v16h-4z"/>',
  stop: '<rect x="5" y="5" width="14" height="14" rx="2.5"/>',
  star: '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
  back: '<path d="M15 18l-6-6 6-6"/>',
  word: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13l1.5 5 2.5-5 2.5 5L16 13"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  more: '<circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/>',
  edit: '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
  doc: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
  screen: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
  call: '<path d="M3 14v-2a9 9 0 0 1 18 0v2"/><path d="M21 15a2 2 0 0 1-2 2h-1v-6h1a2 2 0 0 1 2 2zM3 15a2 2 0 0 0 2 2h1v-6H5a2 2 0 0 0-2 2z"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5M4 20h16"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
  wave: '<path d="M3 12h1M7 8v8M11 5v14M15 9v6M19 7v10"/>',
  spark: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/>',
  download: '<path d="M12 4v12M7 11l5 5 5-5M4 20h16"/>',
  shrink: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M16 10l-2 2 2 2"/>',
  grow: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M14 10l2 2-2 2"/>',
  mini: '<rect x="3" y="4" width="18" height="16" rx="2"/><rect x="12" y="12" width="6" height="5" rx="1"/>',
  pin: '<path d="M12 17v5M9 3h6M10 3v6l-4 4v4h12v-4l-4-4V3"/>',
  chart: '<path d="M3 3v16a2 2 0 0 0 2 2h16M8 17v-4M13 17V7M18 17v-7"/>',
};
const icon = (n, cls = '') => `<svg class="i ${cls}" viewBox="0 0 24 24">${ICONS[n] || ''}</svg>`;
$$('[data-icon]').forEach(e => { e.outerHTML = icon(e.dataset.icon); });

const MINI = location.pathname === '/mini';            // мини-окно (тот же интерфейс, свой адрес)
const MAC_SHELL = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.qamyal;
$('#mini-tg').onclick = () => miniAction('open').catch(fail);

/* Компактный вид — для тех, кто уже освоился: в панели слева только значки, подсказки скрыты */
function drawCompactToggle() {
  const on = document.documentElement.classList.contains('compact'), b = $('#compact-tg');
  b.innerHTML = on ? icon('grow') : `${icon('shrink')}<span class="nt">Компактный вид</span>`;
  b.title = on ? 'Полный вид' : 'Компактный вид: только значки, без подсказок';
}
$('#compact-tg').onclick = () => {
  store('compact', document.documentElement.classList.toggle('compact'));
  drawCompactToggle();
};
drawCompactToggle();

/* ---------- мелочи ---------- */

function fmtT(sec) {
  sec = Math.max(0, Math.round(sec || 0));
  const h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60;
  return (h ? h + ':' + String(m).padStart(2, '0') : String(m).padStart(2, '0')) + ':' + String(s).padStart(2, '0');
}
function fmtDur(sec) {
  const m = Math.round((sec || 0) / 60);
  return m >= 60 ? `${Math.floor(m / 60)} ч ${String(m % 60).padStart(2, '0')} мин` : `${Math.max(m, sec > 0 ? 1 : 0)} мин`;
}
function parseT(t) { return String(t).split(':').reduce((a, x) => a * 60 + +x, 0); }
function plural(n, one, few, many) {
  const a = n % 10, b = n % 100;
  return a === 1 && b !== 11 ? one : a >= 2 && a <= 4 && (b < 12 || b > 14) ? few : many;
}
function initials(name) { return name.split(/\s+/).map(w => w[0] || '').join('').slice(0, 2).toUpperCase(); }
let COLORS = {};      // постоянные цвета людей (с сервера): один человек — один цвет везде
async function loadColors() { try { COLORS = await api('/api/colors'); } catch { /* останутся прежние */ } }
function colorFor(name) {
  if (!name || name.startsWith('Спикер') || name === '?') return '#8e98ab';
  if (COLORS[name]) return COLORS[name];
  const i = [...name].reduce((a, c) => a + c.charCodeAt(0), 0);   // проекты и пока неизвестные имена
  return PALETTE[i % PALETTE.length];
}
function projChip(name, attrs = '') {
  return `<span class="proj" style="--c:${colorFor(name, [])}" ${attrs}>${icon('folder')}${esc(name)}</span>`;
}
function chip(name, color) { return `<span class="chip" style="--c:${color || colorFor(name, [])}"><span class="dot"></span>${esc(name)}</span>`; }
function store(k, v) { try { if (v === undefined) return JSON.parse(localStorage.getItem(k)); localStorage.setItem(k, JSON.stringify(v)); } catch { return null; } }

async function api(path, data, method) {
  const opt = { method: method || (data !== undefined ? 'POST' : 'GET'), headers: {} };
  if (data instanceof FormData) opt.body = data;
  else if (data !== undefined) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(data); }
  const r = await fetch(path, opt);
  let j = null;
  try { j = await r.json(); } catch { /* пусто */ }
  if (!r.ok) throw new Error((j && j.error) || `Ошибка ${r.status}`);
  return j;
}

function toast(msg, err) {
  const t = document.createElement('div');
  t.className = 'toast' + (err ? ' err' : '');
  t.textContent = msg;
  $('#toasts').append(t);
  setTimeout(() => t.remove(), err ? 7000 : 3500);
}
const fail = e => toast(e.message || String(e), true);

function modal(html, sticky) {
  const back = document.createElement('div');
  back.className = 'modal-back';
  back.innerHTML = `<div class="card modal">${html}</div>`;
  if (!sticky) back.addEventListener('mousedown', e => { if (e.target === back) back.remove(); });
  document.body.append(back);
  return back;
}

function popover(anchor, html) {
  $$('.pop').forEach(p => p.remove());
  const p = document.createElement('div');
  p.className = 'card pop';
  p.innerHTML = html;
  document.body.append(p);
  const r = anchor.getBoundingClientRect();
  p.style.left = Math.max(10, Math.min(r.left, innerWidth - 350)) + 'px';
  p.style.top = Math.min(r.bottom + 6, innerHeight - p.offsetHeight - 10) + 'px';
  const off = e => { if (!p.contains(e.target) && e.target !== anchor) { p.remove(); document.removeEventListener('mousedown', off); } };
  setTimeout(() => document.addEventListener('mousedown', off));
  return p;
}

/** Ответ Claude → HTML: **жирный**, ссылки на места записей, переносы строк. */
function fmtAnswer(text, titles) {
  let h = esc(text).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
  h = h.replace(/\[#([0-9a-f]{10})\s+(\d{1,2}:\d{2}(?::\d{2})?)\]/g,
    (m, id, t) => `<a class="cite" href="#/job/${id}?t=${parseT(t)}">${esc((titles || {})[id] || 'запись')} · ${t}</a>`);
  h = h.replace(/\[(\d{1,2}:\d{2}(?::\d{2})?)\]/g, (m, t) => `<a class="cite" href="#" data-seek="${parseT(t)}">${t}</a>`);
  return h.replace(/\n/g, '<br>');
}

function highlight(raw, words) {
  if (!words.length) return esc(raw);
  const re = new RegExp('(' + words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + ')', 'gi');
  return raw.split(re).map((part, i) => i % 2 ? `<mark>${esc(part)}</mark>` : esc(part)).join('');
}

/* ---------- навигация ---------- */

let cleanups = [];
let PAGE = 0;          // номер текущей страницы: запоздавшие ответы со старой страницы её не трогают
const onLeave = fn => cleanups.push(fn);
function every(ms, fn) { const id = setInterval(fn, ms); onLeave(() => clearInterval(id)); }
function pageGuard() { const my = PAGE; return () => my !== PAGE; }

function route() {
  PAGE++;
  cleanups.forEach(f => { try { f(); } catch { /* ничего */ } });
  cleanups = [];
  $$('.pop, .modal-back').forEach(p => p.remove());
  const h = location.hash.slice(2) || 'lib';
  const [path, qs] = h.split('?');
  const parts = path.split('/');
  const q = new URLSearchParams(qs || '');
  const nav = parts[0] === 'job' ? 'lib' : parts[0];
  $$('#side a.nav').forEach(a => a.classList.toggle('active', a.dataset.nav === nav));
  view.scrollTop = 0;
  if (MINI) return pageMini();
  const pages = { rec: pageRec, lib: pageLib, job: () => pageJob(parts[1], q), tasks: pageTasks, insights: pageInsights,
    voices: pageVoices, glossary: pageGlossary, settings: pageSettings, about: pageAbout };
  (pages[parts[0]] || pageLib)(q);
}
window.addEventListener('hashchange', route);
document.addEventListener('click', e => {
  const go = e.target.closest('[data-go]');
  if (go && !e.target.closest('button, a, input')) location.hash = go.dataset.go;
});

/* ---------- состояние в боковой панели ---------- */

/** Тема: system — как в Windows, light / dark — выбор в Настройках (запоминается и в окне, чтобы не мигало). */
function applyTheme(t) {
  const el = document.documentElement;
  if (t === 'dark' || t === 'light') el.dataset.theme = t; else delete el.dataset.theme;
  store('theme', t || 'system');
}

let ST = null, lost = 0, retried = false;
async function pollState() {
  try {
    ST = await api('/api/state');
    if (lost >= 2) {                          // программа могла перезапуститься с новой версией — перечитываем окно
      store('reconnected', 1);
      ST = null;
      location.reload();
      return;
    }
    if (store('reconnected')) { store('reconnected', 0); toast('Связь с программой восстановлена'); }
    if (ST.theme && ST.theme !== (store('theme') || 'system')) applyTheme(ST.theme);
    // язык хранится в окне; из настроек программы берём его, только если окно его забыло (новый профиль)
    if (store('lang') == null && ST.lang && ST.lang !== window.LANG) { store('lang', ST.lang); location.reload(); return; }
    lost = 0; retried = false;
    renderSide();
  } catch {
    if (++lost < 2) return;                   // один сорвавшийся опрос — не повод пугать
    const box = $('#side-status');
    if (!$('#reconnect')) {                   // кнопку не пересоздаём при каждом опросе — иначе нажатие теряется
      box.onclick = null;
      box.classList.remove('clickable');
      box.title = '';
      box.innerHTML = `<b style="color:#ff8a8a">Нет связи с программой</b>
        <button class="btn sm" id="reconnect" style="margin-top:8px;width:100%;justify-content:center" title="Нет связи с программой — переподключить">${icon('refresh')}Переподключить</button>
        <div id="rchint" style="margin-top:8px;display:none">Программа не отвечает. Запустите ярлык Qamyal на рабочем столе — это окно подключится само, закрывать его не нужно.</div>`;
      $('#reconnect').onclick = async () => {
        const b = $('#reconnect');
        b.disabled = true; retried = true;
        await pollState();
        if ($('#reconnect')) $('#reconnect').disabled = false;
      };
    }
    $('#rchint').style.display = retried ? '' : 'none';
  }
}
function renderSide() {
  const box = $('#side-status');
  const r = ST.rec;
  $('a[data-nav="rec"]').classList.toggle('recording', r.state === 'recording' || r.state === 'paused');
  $('#b-tasks').textContent = ST.my_open_tasks || '';
  const bl = $('#b-lib');
  bl.textContent = ST.errors ? '!' : (ST.work.length || '');
  bl.classList.toggle('red', !!ST.errors);
  box.onclick = null;
  box.classList.remove('clickable');
  if (r.state === 'recording' || r.state === 'paused') {
    box.innerHTML = `<b style="color:#ff8a8a">● ${r.state === 'paused' ? 'Запись на паузе' : 'Идёт запись'}</b> ${fmtT(r.elapsed)}` +
      (r.live ? '<br>живая расшифровка включена' : '');
    box.classList.add('clickable');
    box.onclick = () => { location.hash = '#/rec'; };
  } else if (ST.download) {
    const dl = ST.download, pct = dl.total ? Math.min(100, Math.round(dl.done * 100 / dl.total)) : 0;
    box.innerHTML = `<b>Скачиваю</b><br>${esc(dl.step || 'Начинаю…')}${dl.total ? ` · ${pct}%` : ''}` +
      `<div class="bar${dl.total ? '' : ' busy'}"><i style="width:${dl.total ? pct : 100}%"></i></div>` +
      (dl.more ? `<div style="margin-top:6px">${plural(dl.more, 'и ещё {n} загрузка', 'и ещё {n} загрузки', 'и ещё {n} загрузок').replace('{n}', dl.more)}</div>` : '');
    box.classList.add('clickable');
    box.onclick = () => { location.hash = '#/settings'; };
  } else if (ST.work.length && ST.speech === false) {
    box.innerHTML = `<b>${ST.work.length} ${plural(ST.work.length, 'запись ждёт', 'записи ждут', 'записей ждут')} расшифровки</b><br>Скачайте распознавание речи в Настройках`;
    box.classList.add('clickable');
    box.onclick = () => { location.hash = '#/settings'; };
  } else if (ST.work.length) {
    const w = ST.work[0];
    const cur = w.status === 'working';
    box.innerHTML = `<b>${esc(w.name)}</b><br>` +
      (cur ? `${esc(w.stage_label)} · ${w.progress}%${w.paused ? '<br>пауза: идёт живая расшифровка' : ''}` +
        (w.eta > 60 ? `<br>осталось ≈ ${fmtDur(w.eta)}` : '') : 'ждёт очереди') +
      `<div class="bar"><i style="width:${cur ? w.progress : 0}%"></i></div>` +
      (ST.work.length > 1 ? `<div style="margin-top:6px">и ещё ${ST.work.length - 1} в очереди</div>` : '');
    box.classList.add('clickable');
    box.onclick = () => { location.hash = '#/job/' + w.id; };
  } else {
    box.innerHTML = '<span>Все записи обработаны</span>';
  }
  box.title = box.textContent.replace(/\s+/g, ' ').trim();   // в компактном виде от карточки остаётся полоска
}
setInterval(pollState, 1500);

/** Пока распознавание речи не скачано, записи только сохраняются — говорим об этом там, где записывают. */
function speechNote() {
  return ST && ST.speech === false ? `<div class="note speech-note">Чтобы записи расшифровывались, скачайте распознавание речи (≈ 720 МБ).
    <a class="btn sm primary" href="#/settings">${icon('download')}Скачать</a></div>` : '';
}

/** Вопрос голосом: первое нажатие — слушаем микрофон, второе — GigaAM превращает сказанное в текст. */
function voiceBtn(btn, input, onText) {
  const hint = input.placeholder;
  let on = false, busy = false, poll = null;
  const look = (cls, ph, title) => {
    btn.classList.toggle('on', cls === 'on');
    btn.classList.toggle('wait', cls === 'wait');
    btn.style.removeProperty('--lv');
    input.placeholder = ph;
    btn.title = title;
  };
  const stop = async () => {
    on = false;
    clearInterval(poll);
    busy = true;
    look('wait', 'Распознаю сказанное…', 'Распознаю сказанное…');
    try {
      const r = await api('/api/dictate/stop', {});
      if (r.text) onText(r.text);
      else toast('Не удалось разобрать вопрос — попробуйте ещё раз', true);
    } catch (e) { fail(e); }
    busy = false;
    look('', hint, 'Спросить голосом');
  };
  btn.onclick = async () => {
    if (busy) return;
    if (on) return stop();
    busy = true;
    try { await api('/api/dictate/start', {}); } catch (e) { busy = false; return fail(e); }
    busy = false;
    on = true;
    look('on', 'Говорите… нажмите на микрофон ещё раз, чтобы закончить', 'Закончить и спросить');
    poll = setInterval(async () => {
      try {
        const s = await api('/api/dictate');
        if (on) btn.style.setProperty('--lv', s.level);
        if (on && !s.on) stop();            // микрофон отвалился или вопрос слишком длинный
      } catch { /* ничего */ }
    }, 150);
  };
  onLeave(() => { if (on) { on = false; clearInterval(poll); api('/api/dictate/stop', {}).catch(() => {}); } });
}

/* ---------- загрузка файлов (перетаскивание в любое место окна) ---------- */

async function uploadFiles(files) {
  files = [...files];
  if (!files.length) return;
  const fd = new FormData();
  files.forEach(f => { fd.append('files', f, f.name); fd.append('lastModified', f.lastModified); });
  toast(`Добавляю ${files.length} ${plural(files.length, 'файл', 'файла', 'файлов')}…`);
  try {
    await api('/api/upload', fd);
    toast('Записи встали в очередь на расшифровку');
    if (!location.hash.startsWith('#/lib')) location.hash = '#/lib'; else route();
    pollState();
  } catch (e) { fail(e); }
}
let dragDepth = 0;
window.addEventListener('dragenter', e => { if (e.dataTransfer.types.includes('Files')) { dragDepth++; $('#drop').classList.add('on'); } });
window.addEventListener('dragleave', () => { if (--dragDepth <= 0) { dragDepth = 0; $('#drop').classList.remove('on'); } });
window.addEventListener('dragover', e => e.preventDefault());
window.addEventListener('drop', e => {
  e.preventDefault(); dragDepth = 0; $('#drop').classList.remove('on');
  if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
});
$('#filepick').addEventListener('change', e => { uploadFiles(e.target.files); e.target.value = ''; });
const pickFiles = () => $('#filepick').click();

/* =====================================================================
   ДИКТОФОН
   ===================================================================== */

function pageRec() {
  const gone = pageGuard();
  view.innerHTML = `<div class="page rec-page">
    <div class="head"><h1>Диктофон</h1><div class="grow"></div>
      <button class="btn" id="upl">${icon('upload')}Загрузить готовую запись</button></div>
    ${speechNote()}
    <div class="rec-layout"><div class="card rec-main" id="rm"></div><div class="card live" id="rs"></div></div>
  </div>`;
  $('#upl').onclick = pickFiles;
  let cfg = { rec_source: 'mic', rec_live: true, rec_service: 'skype' }, services = {}, skypeProbe = false, scr = { supported: false, monitors: [] };
  let mode = null, liveFrom = 0, marksN = -1, lastJob = null, sysHeard = Date.now();
  api('/api/settings').then(r => { if (gone()) return; cfg = r.settings; services = r.services || {}; skypeProbe = !!r.skype_probe; scr = r.screen || scr; if (mode === 'idle') renderIdle(); }).catch(() => {});

  function renderIdle() {
    mode = 'idle';
    const src = cfg.rec_source;
    $('#rm').innerHTML = `
      <div class="field">
        <div class="seg" id="src" style="display:flex">
          <button data-v="mic" class="${src === 'mic' ? 'on' : ''}" style="flex:1">${icon('mic')}Разговор</button>
          <button data-v="both" class="${src === 'both' ? 'on' : ''}" style="flex:1">${icon('call')}Созвон</button>
          <button data-v="system" class="${src === 'system' ? 'on' : ''}" style="flex:1">${icon('screen')}Звук ПК</button>
        </div>
        <div class="small muted tip" id="srchelp" style="margin-top:5px"></div></div>
      <div class="field svc" id="svcrow"><label class="lbl" for="svc">Через что созвон</label>
        <select class="input" id="svc">${Object.entries(services).map(([k, v]) => `<option value="${k}" ${k === cfg.rec_service ? 'selected' : ''}>${esc(v[0].toUpperCase() + v.slice(1))}</option>`).join('')}</select>
        <span class="small muted tip" id="svchelp"></span></div>
      <div class="field"><input class="input" id="rname" placeholder="Название, например: Созвон с Рафаэлем про моторы"
        title="Имена в названии помогают правильно подписать участников"></div>
      <div class="field"><label class="lbl">Сколько человек будет говорить, вместе с вами</label>
        <div class="seg" id="npl" style="display:flex" title="Если знаете — укажите: голоса разделятся точнее">${['не знаю', 2, 3, 4, 5, '6+'].map((v, k) => `<button data-n="${k ? (v === '6+' ? 6 : v) : 0}" class="${k === 0 ? 'on' : ''}" style="flex:${k ? 1 : 1.6};justify-content:center;white-space:nowrap">${v}</button>`).join('')}</div></div>
      <div class="field"><label class="switch"><input type="checkbox" id="rlive" ${cfg.rec_live ? 'checked' : ''}><i></i>
        <span>Живая расшифровка <span class="small muted tip">— текст появляется во время записи</span></span></label></div>
      ${scr.supported ? `<div class="field"><label class="switch"><input type="checkbox" id="rscr" ${cfg.rec_screen ? 'checked' : ''}><i></i>
        <span>Записывать экран <span class="small muted tip">— презентации, показ экрана; получится видео</span></span></label>
        <div id="scrrow" style="margin-top:8px;${cfg.rec_screen ? '' : 'display:none'}">
          <div class="seg" id="sq" style="display:flex">${[['low', 'Экономно'], ['normal', 'Обычно'], ['high', 'Высоко']].map(([v, l]) =>
            `<button data-v="${v}" class="${(cfg.rec_screen_quality || 'normal') === v ? 'on' : ''}" style="flex:1;justify-content:center">${l}</button>`).join('')}</div>
          <div class="small muted tip" id="sqhelp" style="margin-top:5px"></div>
          ${scr.monitors.length > 1 ? `<select class="input" id="smon" style="margin-top:8px">${scr.monitors.map((m, i) =>
            `<option value="${i}" ${i === (cfg.rec_screen_monitor || 0) ? 'selected' : ''}>${i ? 'Монитор ' + (i + 1) : 'Основной монитор'} · ${m.w}×${m.h}</option>`).join('')}</select>` : ''}
        </div></div>` : ''}
      <div class="rec-go"><button class="bigbtn" id="go" title="Начать запись">${icon('mic')}</button>
        <div><div class="timer muted">00:00</div><div class="rec-state">Нажмите, чтобы начать запись</div></div></div>
      ${lastJob ? `<div class="note" style="margin-top:12px">Запись сохранена и отправлена на расшифровку. <a href="#/job/${lastJob}">Открыть</a></div>` : ''}`;
    const help = {
      mic: 'Микрофон ноутбука — для разговоров вживую.',
      both: 'Ваш микрофон + звук компьютера (Skype, Zoom, Телемост). Лучше в наушниках — без эха.',
      system: 'Только то, что звучит из компьютера: вебинар, видео, чужой доклад.',
    };
    const setSvc = v => {
      cfg.rec_service = v;
      $('#svchelp').textContent = v === 'skype' && skypeProbe ? 'Skype сам подскажет, кто говорит' : 'кто говорит — по голосам';
    };
    const setSrc = v => {
      cfg.rec_source = v;
      $$('#src button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
      $('#srchelp').textContent = help[v];
      $('#svcrow').style.display = v === 'mic' || !Object.keys(services).length ? 'none' : '';
    };
    setSrc(src);
    setSvc(cfg.rec_service);
    $('#svc').onchange = e => { setSvc(e.target.value); api('/api/settings', { rec_service: e.target.value }).catch(() => {}); };
    $$('#src button').forEach(b => b.onclick = () => { setSrc(b.dataset.v); api('/api/settings', { rec_source: b.dataset.v }).catch(() => {}); });
    $('#rlive').onchange = e => api('/api/settings', { rec_live: e.target.checked }).catch(() => {});
    if (ST && ST.speech === false) { $('#rlive').checked = false; $('#rlive').disabled = true; }
    if ($('#rscr')) {
      const sqHelp = {
        low: '720p, 5 кадров в секунду — хватает для слайдов. Около 100–150 МБ за час.',
        normal: '1080p, 15 кадров в секунду — слайды и показ программ. Около 300–500 МБ за час.',
        high: 'Полное разрешение экрана, 30 кадров в секунду — плавное видео. 1 ГБ за час и больше.',
      };
      const setSq = v => {
        cfg.rec_screen_quality = v;
        $$('#sq button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
        $('#sqhelp').textContent = sqHelp[v];
      };
      setSq(cfg.rec_screen_quality || 'normal');
      $('#rscr').onchange = e => {
        cfg.rec_screen = e.target.checked;
        $('#scrrow').style.display = e.target.checked ? '' : 'none';
        api('/api/settings', { rec_screen: e.target.checked }).catch(() => {});
      };
      $$('#sq button').forEach(b => b.onclick = () => { setSq(b.dataset.v); api('/api/settings', { rec_screen_quality: b.dataset.v }).catch(() => {}); });
      if ($('#smon')) $('#smon').onchange = e => { cfg.rec_screen_monitor = +e.target.value; api('/api/settings', { rec_screen_monitor: +e.target.value }).catch(() => {}); };
    }
    let speakers = 0;
    $$('#npl button').forEach(b => b.onclick = () => { speakers = +b.dataset.n; $$('#npl button').forEach(x => x.classList.toggle('on', x === b)); });
    $('#go').onclick = async () => {
      try {
        $('#go').disabled = true;
        await api('/api/rec/start', { source: cfg.rec_source, name: $('#rname').value, live: $('#rlive').checked, speakers, service: cfg.rec_service,
          screen: !!($('#rscr') && $('#rscr').checked), screen_quality: cfg.rec_screen_quality || 'normal', monitor: cfg.rec_screen_monitor || 0 });
        liveFrom = 0; marksN = -1; lastJob = null;
        tick();
      } catch (e) { if ($('#go')) $('#go').disabled = false; fail(e); }
    };
    $('#rs').classList.add('tip');
    $('#rs').innerHTML = `<h2>Подсказки</h2>
      <div class="muted small" style="display:grid;gap:9px">
        <div>${icon('call')} <b>Созвон</b> пишет вас и собеседников одновременно: ваш голос — в левом канале, их — в правом.</div>
        <div>${icon('star')} Во время записи жмите <b>★ Отметить момент</b> или клавишу <kbd>M</kbd> — важные места подсветятся в расшифровке.</div>
        <div>${icon('spark')} После «Стоп» запись сама уйдёт в расшифровку: два черновика, голоса, редактура и краткое содержание.</div>
        <div>${icon('upload')} Есть запись с телефона или диктофона? Просто перетащите файл в это окно.</div>
      </div>`;
  }

  function renderActive(st) {
    mode = 'active';
    const both = st.source === 'both';
    $('#rm').innerHTML = `
      <div class="rec-go"><button class="bigbtn stop" id="stop" title="Стоп и расшифровать">${icon('stop')}</button>
        <div><div class="timer" id="tmr">00:00</div><div class="rec-state" id="rst"></div>
          <div class="muted small">${esc(st.name || 'Без названия')}${st.service ? ` · ${esc(st.service)}` : ''}</div></div></div>
      <div class="meters">
        ${st.source !== 'system' ? `<div class="meter"><span>${icon('mic')} Микрофон</span><div class="lv"><i id="lm"></i></div></div>` : ''}
        ${st.source !== 'mic' ? `<div class="meter"><span>${icon('screen')} Звук компьютера</span><div class="lv"><i id="ls"></i></div></div>` : ''}
      </div>
      ${st.source !== 'mic' ? `<div class="note warn small" id="syswarn" style="display:none;margin-top:10px">
        Звук компьютера не слышен уже полминуты. Если собеседник говорит по телефону или сидит рядом — это нормально, его пишет микрофон
        (в следующий раз выбирайте «Разговор»). «Созвон» нужен, когда собеседник звучит из этого компьютера: Skype, Zoom, Телемост.</div>` : ''}
      <div class="rec-actions">
        <button class="btn" id="pz"></button>
        <button class="btn" id="mk">${icon('star')}Отметить момент <kbd>M</kbd></button>
        <span class="grow"></span>
        <button class="btn ghost sm danger" id="cancel" title="Удалить запись, не сохраняя">${icon('trash')}Удалить</button>
      </div>
      <div class="marks" id="mks"></div>`;
    $('#stop').onclick = () => stop(false);
    $('#cancel').onclick = () => { if (confirm('Удалить эту запись без сохранения?')) stop(true); };
    $('#mk').onclick = mark;
    $('#pz').onclick = () => api('/api/rec/' + ($('#pz').dataset.s === 'paused' ? 'resume' : 'pause'), {}).then(tick).catch(fail);
    $('#rs').classList.toggle('tip', !st.live);
    $('#rs').innerHTML = st.live
      ?`<div class="live-head"><h2 style="margin:0">Живая расшифровка</h2><span class="grow"></span><span class="small muted" id="lag"></span></div>
         <div class="live-text" id="lt"></div><div class="live-pending" id="lp"></div>`
      : `<h2>Живая расшифровка выключена</h2><div class="muted">Текст появится после остановки записи — в полной расшифровке.</div>`;
    if (both) $('#rm').classList.add('both');
  }

  async function stop(discard) {
    try {
      const r = await api('/api/rec/stop', { discard });
      lastJob = r.job;
      if (r.job) toast('Запись сохранена — началась расшифровка');
      renderIdle();
      pollState();
    } catch (e) { fail(e); }
  }
  async function mark() {
    try { await api('/api/rec/mark', {}); toast('★ Момент отмечен'); tick(); } catch (e) { fail(e); }
  }

  let busy = false;
  async function tick() {
    if (busy) return;               // сервер может отвечать медленно — запросы не должны накладываться
    busy = true;
    try { await tickOnce(); } finally { busy = false; }
  }
  async function tickOnce() {
    let st;
    try { st = await api('/api/rec?from=' + liveFrom); } catch { return; }
    if (gone()) return;
    const active = st.state === 'recording' || st.state === 'paused';
    if (!active) { if (mode !== 'idle') renderIdle(); return; }
    if (mode !== 'active') renderActive(st);
    $('#rm').parentElement.classList.toggle('recording-now', st.state === 'recording');
    $('#tmr').textContent = fmtT(st.elapsed);
    $('#rst').innerHTML = st.error ? `<span style="color:var(--rec)">${esc(st.error)}</span>`
      : st.state === 'paused' ? 'Пауза' : `<span style="color:var(--rec)">● Идёт запись${st.screen ? ' · экран' : ''}</span>`;
    const pz = $('#pz');
    pz.dataset.s = st.state;
    pz.innerHTML = st.state === 'paused' ? `${icon('play')}Продолжить` : `${icon('pause')}Пауза`;
    if ($('#lm')) $('#lm').style.width = (st.levels.mic * 100) + '%';
    if ($('#ls')) $('#ls').style.width = (st.levels.system * 100) + '%';
    if ($('#syswarn')) {
      if (st.levels.system > 0.08 || st.state !== 'recording') sysHeard = Date.now();
      $('#syswarn').style.display = Date.now() - sysHeard > 30000 ? '' : 'none';
    }
    if (st.marks.length !== marksN) {
      marksN = st.marks.length;
      $('#mks').innerHTML = st.marks.map((m, i) => `<div class="mark"><span class="star">${icon('star')}</span>
        <span class="muted">${fmtT(m.t)}</span><input class="input" data-i="${i}" value="${esc(m.note)}" placeholder="Что здесь важного? (необязательно)"></div>`).join('');
      $$('#mks input').forEach(inp => inp.onchange = () => api('/api/rec/note', { i: +inp.dataset.i, text: inp.value }).catch(fail));
    }
    if (st.live && $('#lt')) {
      const lt = $('#lt');
      const atBottom = lt.scrollHeight - lt.scrollTop - lt.clientHeight < 40;
      (st.live_segments || []).forEach((s, k) => {
        if (st.live_from + k < liveFrom) return;      // эту фразу уже показали
        lt.insertAdjacentHTML('beforeend', `<div class="live-line"><span class="t">${fmtT(s.t)}</span><span>${esc(s.text)}</span></div>`);
      });
      liveFrom = Math.max(liveFrom, st.live_from + (st.live_segments || []).length);
      if (atBottom) lt.scrollTop = lt.scrollHeight;
      $('#lp').textContent = !st.live_ready ? 'Загружаю модель распознавания…' : st.state === 'recording' ? 'Слушаю…' : '';
      $('#lag').textContent = st.live_ready && st.live_lag > 4 ? `отстаёт на ${Math.round(st.live_lag)} с` : '';
    }
  }

  const onKey = e => {
    if ((e.key === 'm' || e.key === 'M' || e.key === 'ь' || e.key === 'Ь') && mode === 'active' && !e.target.closest('input, textarea')) {
      e.preventDefault(); mark();
    }
  };
  document.addEventListener('keydown', onKey);
  onLeave(() => document.removeEventListener('keydown', onKey));
  renderIdle();
  tick();
  every(300, () => { if (mode === 'active') tick(); });
  every(2000, () => { if (mode === 'idle') tick(); });
}

window.addEventListener('beforeunload', e => {
  if (!MINI && ST && (ST.rec.state === 'recording' || ST.rec.state === 'paused')) { e.preventDefault(); e.returnValue = ''; }
});

/* =====================================================================
   МИНИ-ОКНО: запись, таймер, «Отметить момент», ход обработки
   ===================================================================== */

/** Окнами на Mac управляет оболочка Qamyal.app (ей пишем сами), в Windows — программа (sysdeps). */
async function miniAction(action, extra = {}) {
  const r = await api('/api/mini', { action, ...extra });
  if (MAC_SHELL) MAC_SHELL.postMessage({ do: action, top: r.top });
  return r;
}

function pageMini() {
  document.title = 'Qamyal · ' + tr('мини');
  view.innerHTML = `<div class="mini-box">
    <div class="mini-rec">
      <button class="bigbtn" id="mgo"></button>
      <div class="mini-mid"><div class="timer" id="mt">00:00</div><div class="rec-state" id="mst"></div></div>
      <button class="btn" id="mmk" title="Отметить момент (M)" hidden>${icon('star')}</button>
      <button class="btn" id="mpz" hidden></button>
    </div>
    <div class="mini-foot">
      <div class="mini-work" id="mw"></div>
      <button class="btn ghost mini-ic" id="mtop" title="Поверх всех окон">${icon('pin')}</button>
      <button class="btn ghost mini-ic" id="mmain" title="Открыть Qamyal">${icon('grow')}</button></div>
    <div class="bar" id="mbar"><i></i></div></div>`;
  const SRC = { mic: 'Разговор', both: 'Созвон', system: 'Звук ПК' };
  let state = '', busy = false, src = '', lastWork = '';
  const loadSrc = () => api('/api/settings').then(r => {
    const s = r.settings;
    src = SRC[s.rec_source] + (s.rec_source !== 'mic' && r.services[s.rec_service] ? ' · ' + r.services[s.rec_service] : '')
      + (s.rec_screen && r.screen && r.screen.supported ? ' · экран' : '');
  }).catch(() => {});

  async function tick() {
    if (busy) return;
    busy = true;
    try {
      const st = await api('/api/rec?from=999999');
      const active = st.state === 'recording' || st.state === 'paused';
      if (st.state !== state) {
        state = st.state;
        $('#mgo').classList.toggle('stop', active);
        $('#mgo').innerHTML = icon(active ? 'stop' : 'mic');
        $('#mgo').title = active ? 'Стоп и расшифровать' : 'Начать запись';
        $('#mmk').hidden = $('#mpz').hidden = !active;
        $('#mpz').innerHTML = icon(state === 'paused' ? 'play' : 'pause');
        $('#mpz').title = state === 'paused' ? 'Продолжить' : 'Пауза';
        $('.mini-rec').classList.toggle('recording-now', state === 'recording');
        if (!active) loadSrc();            // источник могли поменять в основном окне
      }
      $('#mt').textContent = fmtT(active ? st.elapsed : 0);
      $('#mt').classList.toggle('muted', !active);
      $('#mst').innerHTML = st.error ? `<span style="color:var(--rec)">${esc(st.error)}</span>`
        : state === 'paused' ? 'Пауза' : active ? `<span style="color:var(--rec)">● Идёт запись${st.screen ? ' · экран' : ''}</span>` : esc(src);
    } catch { /* программа перезапускается — следующий опрос покажет */ } finally { busy = false; }
  }

  function work() {
    if (!ST) return;
    let h, pct = -1, busyBar = false;     // pct < 0 — полоски нет
    // одна строка и тонкая полоска внизу окна: подробности — в основном окне и в подсказке
    if (ST.download) {
      const dl = ST.download;
      pct = dl.total ? Math.min(100, Math.round(dl.done * 100 / dl.total)) : 100;
      busyBar = !dl.total;
      h = `<span title="${esc(dl.step || '')}"><b>Скачиваю</b>${dl.total ? ` · ${pct}%` : ''}</span>`;
    } else if (ST.work.length) {
      const w = ST.work[0], cur = w.status === 'working', more = ST.work.length - 1;
      pct = cur ? w.progress : 0;
      h = `<span title="${esc(w.name)}${more ? ' · ' + esc(`и ещё ${more} в очереди`) : ''}">${cur ? `${esc(w.stage_label)} · ${w.progress}%` : 'ждёт очереди'}${more ? ` · +${more}` : ''}</span>`;
    } else h = `${icon('check')}<span>Все записи обработаны</span>`;
    if (h !== lastWork) { lastWork = h; $('#mw').innerHTML = h; }
    $('#mbar').hidden = pct < 0;
    $('#mbar').classList.toggle('busy', busyBar);
    $('#mbar > i').style.width = Math.max(pct, 0) + '%';
  }

  $('#mgo').onclick = async () => {
    const active = state === 'recording' || state === 'paused';
    try {
      if (active) {
        const r = await api('/api/rec/stop', { discard: false });
        if (r.job) toast('Запись сохранена — началась расшифровка');
      } else await api('/api/rec/start', {});
    } catch (e) { fail(e); }
    tick();
  };
  const mark = () => api('/api/rec/mark', {}).then(() => toast('★ Момент отмечен')).catch(fail);
  $('#mmk').onclick = mark;
  $('#mpz').onclick = () => api('/api/rec/' + (state === 'paused' ? 'resume' : 'pause'), {}).then(tick).catch(fail);
  $('#mmain').onclick = () => miniAction('main').catch(fail);
  const showTop = on => {
    $('#mtop').classList.toggle('on', on);
    $('#mtop').title = on ? 'Поверх всех окон: включено' : 'Поверх всех окон: выключено';
  };
  api('/api/mini').then(r => showTop(r.top)).catch(() => {});
  $('#mtop').onclick = () => miniAction('top', { top: !$('#mtop').classList.contains('on') }).then(r => showTop(r.top)).catch(fail);
  const onKey = e => {
    if ((e.key === 'm' || e.key === 'M' || e.key === 'ь' || e.key === 'Ь') && (state === 'recording' || state === 'paused')) {
      e.preventDefault(); mark();
    }
  };
  document.addEventListener('keydown', onKey);
  onLeave(() => document.removeEventListener('keydown', onKey));
  // Размер мини-окна постоянный: столько, сколько нужно содержимому. На Mac его задаёт оболочка;
  // в Windows рамку окна знает только страница — она и просит программу поставить нужный размер.
  const W = 260, H = 88;
  // /mini, открытый обычной вкладкой браузера (с адресной строкой), окном мини-окна не командует
  const appWin = () => !MAC_SHELL && outerHeight - innerHeight < 80;
  const fit = first => {                   // первый раз — всегда: программа заодно убирает растягивание
    if (!appWin() || (!first && innerWidth === W && innerHeight === H)) return;
    api('/api/mini', { size: [outerWidth - innerWidth + W, outerHeight - innerHeight + H] }).catch(() => {});
  };
  let fitT = 0;
  const onResize = () => { clearTimeout(fitT); fitT = setTimeout(fit, 300); };
  addEventListener('resize', onResize);
  onLeave(() => removeEventListener('resize', onResize));
  setTimeout(() => fit(true), 800);
  // Windows: Chrome не помнит место мини-окна — запоминает программа (на Mac помнит оболочка)
  let lastRect = '';
  const saveRect = () => {
    const rect = [screenX, screenY, outerWidth, outerHeight];     // те же точки, что видит программа в Windows
    if (!appWin() || rect.join() === lastRect) return;
    if (lastRect) api('/api/mini', { rect }).catch(() => {});
    lastRect = rect.join();                // первое измерение — только запоминаем: окно ещё ставится на место
  };
  loadSrc().then(() => { state = ''; tick(); });
  every(500, tick);
  every(1500, () => { work(); saveRect(); });
  work();
}

/* =====================================================================
   ЗАПИСИ
   ===================================================================== */

function pageLib() {
  const gone = pageGuard();
  view.innerHTML = `<div class="page">
    <div class="head"><h1>Записи</h1>
      <div class="search">${icon('search')}<input class="input" id="q" placeholder="Поиск по всем расшифровкам" value="${esc(store('libq') || '')}"></div>
      <div class="grow"></div>
      <button class="btn" id="add">${icon('upload')}Добавить файлы</button>
      <a class="btn red" href="#/rec">${icon('mic')}Записать</a></div>
    <div class="card" id="ask"><div class="ask-all">
      <input class="input" id="aq" placeholder="Спросите что угодно по всем записям: что решили про сервер? какие задачи на мне?">
      <button class="btn voice" id="av" title="Спросить голосом">${icon('mic')}</button>
      <button class="btn primary" id="ab">${icon('spark')}Спросить</button></div><div class="qa" id="aqa"></div></div>
    ${speechNote()}
    <div class="projbar" id="pb"></div>
    <div id="lb"></div></div>`;
  $('#add').onclick = pickFiles;
  let lastJson = '', titles = {};

  let qaItems = [];
  async function loadQA() {
    try {
      const r = await api('/api/ask-all');
      if (gone()) return;
      titles = r.titles;
      qaItems = r.qa.slice(-3);
      renderQA(qaItems);
    } catch { /* ничего */ }
  }
  function renderQA(items, pending) {
    $('#aqa').innerHTML = (items.length && !pending ? `<button class="btn ghost sm qa-clear" id="aclr" title="Очистить историю вопросов — Claude начнёт разговор заново">${icon('trash')}Очистить</button>` : '') +
      items.map(x => `<div><div class="q">${esc(x.q)}</div><div class="a">${fmtAnswer(x.a, titles)}</div></div>`).join('') +
      (pending ? `<div><div class="q">${esc(pending)}</div><div class="thinking">Читаю все расшифровки и думаю…</div></div>` : '');
    const clr = $('#aclr');
    if (clr) clr.onclick = () => api('/api/ask-all/clear', {}).then(() => { qaItems = []; renderQA(qaItems); }).catch(fail);
  }
  const ask = async text => {
    if (text) $('#aq').value = text;
    const q = $('#aq').value.trim();
    if (!q) return;
    $('#aq').value = '';
    renderQA(qaItems, q);
    try {
      const r = await api('/api/ask-all', { q });
      if (gone()) return;
      titles = r.titles;
      qaItems = [...qaItems, r].slice(-3);
      renderQA(qaItems);
    } catch (e) { renderQA(qaItems); fail(e); }
  };
  $('#ab').onclick = () => ask();
  $('#aq').onkeydown = e => { if (e.key === 'Enter') ask(); };
  voiceBtn($('#av'), $('#aq'), ask);
  loadQA().then(() => {});

  async function load() {
    const q = $('#q').value.trim();
    if (q) return;
    try {
      const r = await api('/api/jobs');
      if (gone() || $('#q').value.trim()) return;
      const js = JSON.stringify(r.jobs);
      if (js === lastJson) return;
      lastJson = js;
      await loadColors();
      if (gone()) return;
      renderJobs(r.jobs);
    } catch { /* сеть */ }
  }

  function renderJobs(jobs) {
    const work = jobs.filter(j => j.status === 'queued' || j.status === 'working');
    const errs = jobs.filter(j => j.status === 'error');
    const allDone = jobs.filter(j => j.status === 'done');
    // фильтр по проекту: '' — все, '-' — без проекта
    const counts = {};
    const projOf = j => (j.projects && j.projects.length ? j.projects : ['-']);
    allDone.forEach(j => projOf(j).forEach(p => { counts[p] = (counts[p] || 0) + 1; }));
    let pf = store('libproj') || '';
    if (pf && !counts[pf]) pf = '';
    const done = allDone.filter(j => !pf || projOf(j).includes(pf));
    const names = Object.keys(counts).filter(k => k !== '-').sort((a, b) => counts[b] - counts[a]);
    $('#pb').innerHTML = names.length ? [['', 'Все', allDone.length], ...names.map(n => [n, n, counts[n]]),
      ...(counts['-'] ? [['-', 'Без проекта', counts['-']]] : [])].map(([k, label, n]) =>
      `<button class="chip pick${pf === k ? ' on' : ''}" data-pf="${esc(k)}" ${k && k !== '-' ? `style="--c:${colorFor(k, [])}"` : ''}>
        ${k && k !== '-' ? icon('folder') : ''}${esc(label)} <span class="muted">${n}</span></button>`).join('') : '';
    $$('#pb [data-pf]').forEach(b => b.onclick = () => { store('libproj', b.dataset.pf); lastJson = ''; load(); });
    if (!jobs.length) {
      $('#lb').innerHTML = `<div class="empty">${icon('wave')}<div style="font-size:16px;color:var(--text);margin-bottom:6px">Пока нет ни одной записи</div>
        Запишите разговор на вкладке <a href="#/rec">Диктофон</a> или перетащите файлы записей прямо в это окно.</div>`;
      return;
    }
    let h = '';
    if (work.length) {
      h += `<div class="section-title">В работе</div><div class="grid">` + work.map(j => `
        <div class="card workcard" data-go="#/job/${j.id}">
          <div class="t">${esc(j.name)}</div><div class="small muted">${j.duration ? fmtDur(j.duration) : ''}</div>
          <div class="small muted">${j.status === 'working' ? `${esc(j.stage_label)} · ${j.progress}%${j.paused ? ' · пауза на время записи' : ''}` : 'ждёт очереди'}</div>
          <div class="small muted">${j.eta > 60 ? 'осталось ≈ ' + fmtDur(j.eta) : ''}</div>
          <div class="bar"><i style="width:${j.status === 'working' ? j.progress : 0}%"></i></div></div>`).join('') + '</div>';
    }
    if (errs.length) {
      h += `<div class="section-title">Не получилось</div><div class="grid">` + errs.map(j => `
        <div class="card" data-go="#/job/${j.id}"><div style="font-weight:600">${esc(j.name)}</div>
          <div class="note err small" style="margin:8px 0">${esc(j.error)}</div>
          <button class="btn sm" data-retry="${j.id}">${icon('refresh')}Повторить</button></div>`).join('') + '</div>';
    }
    if (done.length) {
      h += `<div class="section-title">Готово · ${done.length}</div><div class="grid">` + done.map(j => `
        <div class="card jobcard" data-go="#/job/${j.id}">
          ${(j.projects || []).length ? `<div class="projs">${j.projects.map(p => projChip(p)).join('')}</div>` : ''}
          <div class="t">${esc(j.title)}</div>
          <div class="meta">${icon(j.recorded ? 'mic' : 'wave')}${esc(j.date)} · ${fmtDur(j.duration)}${j.tasks ? ` · ${j.tasks} ${plural(j.tasks, 'задача', 'задачи', 'задач')}` : ''}${j.marks ? ` · ★ ${j.marks}` : ''}</div>
          <div class="lead">${esc(j.lead)}</div>
          <div class="chips">${j.participants.map(p => chip(p, colorFor(p, j.participants))).join('')}</div></div>`).join('') + '</div>';
    }
    $('#lb').innerHTML = h;
    $$('[data-retry]').forEach(b => b.onclick = () => api(`/api/job/${b.dataset.retry}/retry`, {}).then(() => { lastJson = ''; load(); }).catch(fail));
  }

  let timer = null;
  async function doSearch() {
    const q = $('#q').value.trim();
    store('libq', q);
    $('#pb').style.display = q ? 'none' : '';
    if (!q) { lastJson = ''; $('#ask').style.display = ''; return load(); }
    $('#ask').style.display = 'none';
    try {
      const r = await api('/api/search?q=' + encodeURIComponent(q));
      if (gone() || $('#q').value.trim() !== q) return;
      const words = q.toLowerCase().split(/\s+/).filter(Boolean);
      $('#lb').innerHTML = `<div class="section-title">Найдено: ${r.hits.length}${r.hits.length >= 200 ? '+' : ''}</div>` +
        (r.hits.length ? '<div class="card" style="padding:4px 14px">' + r.hits.map(x => `
          <div class="hit" data-go="#/job/${x.id}?t=${Math.floor(x.t)}">
            <div><b>${esc(x.title)}</b> <span class="muted small">· ${esc(x.date)} · ${fmtT(x.t)} · ${esc(x.who)}</span></div>
            <div>${highlight(x.snippet, words)}</div></div>`).join('') + '</div>'
          : `<div class="empty">Ничего не нашлось. Попробуйте другое слово или спросите по всем записям.</div>`);
    } catch (e) { fail(e); }
  }
  $('#q').oninput = () => { clearTimeout(timer); timer = setTimeout(doSearch, 300); };
  doSearch();
  every(2500, load);
}

/* =====================================================================
   СТРАНИЦА ЗАПИСИ
   ===================================================================== */

let player = null;   // { id, audio } — плеер живёт, пока открыта запись

async function pageJob(id, q) {
  if (!player || player.id !== id) {
    if (player) player.audio.pause();
    player = { id, audio: new Audio('/media/' + id) };
    player.audio.preload = 'metadata';
  }
  onLeave(() => { if (!location.hash.startsWith('#/job/' + id)) { player.audio.pause(); } });
  const gone = pageGuard();
  view.innerHTML = '<div class="page"><div class="empty">Открываю…</div></div>';
  let data;
  await loadColors();                      // после переименований могли появиться новые имена
  try { data = await api('/api/job/' + id); } catch (e) { if (!gone()) view.innerHTML = `<div class="page"><div class="empty">${esc(e.message)}</div></div>`; return; }
  if (gone()) return;
  if (data.job.status !== 'done' || !data.result) return jobProgress(id, data);
  jobDone(id, data, q);
}

function jobProgress(id, data) {
  const render = d => {
    const j = d.job;
    const stages = [['prepare', 'подготовка'], ...(j.screen ? [['video', 'видео']] : []), ['gigaam', 'GigaAM'], ['diar', 'голоса'], ['voices', 'кто есть кто'], ['whisper', 'Whisper'], ['edit', 'редактура'], ['render', 'оформление']];
    const doneKeys = Object.keys(d.times || {});
    view.innerHTML = `<div class="page">
      <div class="job-head"><a class="btn ghost sm" href="#/lib">${icon('back')}</a>
        <div style="flex:1"><div class="title">${esc(j.name)}</div><div class="meta">${esc(j.date)}${j.duration ? ' · ' + fmtDur(j.duration) : ''}</div></div>
        <button class="btn sm danger" id="del">${icon('trash')}Удалить</button></div>
      <div class="card progress-card">
        ${j.status === 'error' ? `<div class="note err"><b>Не получилось:</b> ${esc(j.error)}</div><div><button class="btn primary" id="retry">${icon('refresh')}Повторить</button></div>`
          : `<h2 style="margin:0">${j.status === 'queued' ? 'Ждёт очереди' : esc(j.stage_label) + ' · ' + j.progress + '%'}</h2>
             <div class="bar"><i style="width:${j.status === 'working' ? j.progress : 0}%"></i></div>
             <div class="muted">${j.paused ? 'Пауза: процессор занят живой расшифровкой. ' : ''}${j.eta > 60 ? 'Осталось примерно ' + fmtDur(j.eta) + '.' : ''}
               Можно закрыть окно — обработка продолжится, а когда закончится, придёт уведомление.</div>`}
        <div class="stages">${stages.map(([k, l]) => `<span class="${doneKeys.includes(k) ? 'done' : j.stage === k ? 'cur' : ''}">${l}</span>`).join('')}</div>
      </div>
      ${d.live && d.live.length ? `<div class="card"><h2>Черновик живой расшифровки</h2><div class="muted small tip" style="margin-bottom:8px">Это быстрый черновик, записанный во время разговора. Чистовой текст с именами появится после обработки.</div>
        ${d.live.map(s => `<div class="live-line"><span class="t">${fmtT(s.t)}</span><span>${esc(s.text)}</span></div>`).join('')}</div>` : ''}
    </div>`;
    if ($('#retry')) $('#retry').onclick = () => api(`/api/job/${id}/retry`, {}).then(() => toast('Снова в очереди')).catch(fail);
    $('#del').onclick = () => { if (confirm('Удалить эту запись?')) api(`/api/job/${id}/delete`, {}).then(() => { location.hash = '#/lib'; }).catch(fail); };
  };
  render(data);
  const gone = pageGuard();
  every(3000, async () => {
    try {
      const d = await api(`/api/job/${id}?lite=1`);
      if (gone()) return;
      if (d.job.status === 'done') return route();
      render({ ...d, live: data.live });
    } catch { /* сеть */ }
  });
}

function jobDone(id, data, q) {
  const R = data.result;
  const audio = player.audio;
  const turns = R.turns;
  const dur = R.duration || audio.duration || 1;
  const order = [];
  turns.forEach(t => { if (!order.includes(t.who)) order.push(t.who); });
  (R.stats || []).forEach(s => { if (!order.includes(s.who)) order.push(s.who); });
  const col = n => colorFor(n, order);
  const marks = data.marks || R.marks || [];
  const starAt = new Set(marks.map(m => { let k = 0; turns.forEach((t, i) => { if (t.t <= m.t + 1) k = i; }); return k; }));
  let peaks = [], filter = store('filter-' + id) || null, follow = store('follow') !== false, editing = false;
  const PJ = (data.job && data.job.projects) || [];

  view.innerHTML = `<div class="page wide" style="max-width:1440px">
    <div class="job-head"><a class="btn ghost sm" href="#/lib" title="К записям">${icon('back')}</a>
      <div style="flex:1;min-width:0"><div class="title" id="jt" title="Щёлкните, чтобы переименовать">${esc(R.title)}</div>
        <div class="meta"><button class="projbtn" id="pj" title="Проекты — щёлкните, чтобы изменить">${PJ.length ? PJ.map(p => projChip(p)).join('') : `<span class="proj empty">${icon('folder')}указать проект</span>`}</button>
          ${esc(R.date)} · ${fmtDur(R.duration)}${data.job.service ? ` · ${esc(data.job.service)}` : ''}${data.versions ? ` · <a href="#" id="undo1">${icon('refresh')} отменить последнее изменение</a>` : ''}</div></div>
      ${data.has_video ? `<button class="btn sm" id="bvid" title="Открыть видео с экрана">${icon('screen')}Видео</button>` : ''}
      <button class="btn sm" id="bw">${icon('word')}Word</button>
      <button class="btn sm" id="bf">${icon('folder')}Папка</button>
      <button class="btn sm ghost" id="bm" title="Ещё">${icon('more')}</button></div>
    <div class="player"><div class="card">
      <button class="play" id="pp">${icon('play')}</button>
      <div class="ptime"><span id="tc">00:00</span> / ${fmtT(dur)}</div>
      <canvas class="wave" id="wv"></canvas>
      <select class="input" id="sp" style="width:78px;height:32px;padding:0 8px">${[1, 1.25, 1.5, 1.75, 2].map(v => `<option value="${v}">${v}×</option>`).join('')}</select>
    </div></div>
    <div class="job-grid">
      <div class="card" style="padding:12px 10px">
        <div class="tools" style="padding:0 8px">
          <label class="switch small"><input type="checkbox" id="fl" ${follow ? 'checked' : ''}><i></i>Следить за звуком</label>
          <span class="grow"></span>
          <button class="btn sm" id="ed">${icon('edit')}Править текст</button></div>
        <div class="people" id="ppl"></div>
        <div class="turns" id="tr"></div></div>
      <div class="side-col" id="sc"></div>
    </div></div>`;

  /* --- текст --- */
  // кадры записи экрана: каждый — перед репликой, во время которой он появился
  const shotsAt = {};
  (data.frames || []).forEach(f => {
    let k = 0;
    turns.forEach((t, i) => { if (t.t <= f.t + 0.5) k = i; });
    (shotsAt[k] = shotsAt[k] || []).push(f);
  });
  const shotHtml = i => (shotsAt[i] || []).map(f => `<figure class="shot" data-seek="${f.t}" title="Слушать с этого места">
      <img loading="lazy" src="${f.src}" alt=""><figcaption>${esc(f.caption)}</figcaption></figure>`).join('');
  function renderTurns() {
    $('#tr').innerHTML = turns.map((t, i) => (filter ? '' : shotHtml(i)) + `<div class="turn${filter && t.who !== filter ? ' hidden' : ''}" data-i="${i}">
      <button class="ts" data-seek="${t.t}">${fmtT(t.t)}</button>
      <div>${starAt.has(i) ? `<span class="star" title="Отмеченный момент">★</span>` : ''}<span class="who" style="--c:${col(t.who)}" data-who="${esc(t.who)}">${esc(t.who)}</span><span class="tx">${esc(t.text)}</span></div></div>`).join('');
    renderPeople();
    cur = -1;
    sync();
  }
  $('#tr').addEventListener('click', e => {
    const s = e.target.closest('[data-seek]');
    if (s && !editing) { audio.currentTime = +s.dataset.seek; audio.play(); return; }
    const w = e.target.closest('.who');
    if (w && !editing) turnPop(w, +w.closest('.turn').dataset.i);
  });

  /* --- участники: кто есть кто, слияние «спикеров», число людей --- */
  const names = () => order.filter(n => turns.some(t => t.who === n));
  const candidates = except => [...new Set([...names(), ...(data.known_voices || [])])].filter(n => n !== except);
  const nameChips = (list, attr) => list.map(n => `<button class="chip pick" ${attr}="${esc(n)}" style="--c:${col(n)}"><span class="dot"></span>${esc(n)}</button>`).join('');

  function renderPeople() {
    const list = names();
    const talk = n => turns.filter(t => t.who === n).length;
    $('#ppl').innerHTML = `<span class="muted small">Участники:</span>
      ${list.map(n => `<button class="chip pick${filter === n ? ' on' : ''}" data-person="${esc(n)}" style="--c:${col(n)}" title="Щёлкните: показать только его реплики или сказать, кто это">
        <span class="dot"></span>${esc(n)} <span class="muted">${talk(n)}</span></button>`).join('')}
      <button class="btn sm ghost" id="wrongppl">${icon('users')}Не те участники?</button>`;
    $$('#ppl [data-person]').forEach(b => b.onclick = () => personPop(b, b.dataset.person));
    $('#wrongppl').onclick = () => countPop($('#wrongppl'));
  }

  function act(path, payload, msg) {
    $$('.pop').forEach(p => p.remove());
    return api(path, payload).then(() => { toast(msg); reload(); }).catch(fail);
  }

  function turnPop(anchor, i) {
    const t = turns[i], same = turns.filter(x => x.who === t.who).length;
    const p = popover(anchor, `
      <div style="font-weight:600">Кто говорит в этой реплике?</div>
      <div class="sugg">${nameChips(candidates(t.who), 'data-one')}</div>
      <input class="input" id="one" placeholder="Другое имя и Enter">
      ${same > 1 ? `<div style="font-weight:600;margin-top:14px">Все ${same} ${plural(same, 'реплика', 'реплики', 'реплик')} «${esc(t.who)}» — это:</div>
        <div class="sugg">${nameChips(candidates(t.who), 'data-all')}</div>
        <input class="input" id="all" placeholder="Другое имя и Enter">` : ''}
      <div class="small muted" style="margin-top:10px">Голоса запомнятся заново — следующие записи подпишутся точнее.</div>`);
    const one = who => act(`/api/job/${id}/turn`, { i, who }, `Реплика ${fmtT(t.t)} — ${who}`);
    const all = who => act(`/api/job/${id}/rename`, { from: t.who, to: who }, `«${t.who}» → ${who}`);
    $$('[data-one]', p).forEach(b => b.onclick = () => one(b.dataset.one));
    $$('[data-all]', p).forEach(b => b.onclick = () => all(b.dataset.all));
    $('#one', p).onkeydown = e => { if (e.key === 'Enter' && e.target.value.trim()) one(e.target.value.trim()); };
    if ($('#all', p)) $('#all', p).onkeydown = e => { if (e.key === 'Enter' && e.target.value.trim()) all(e.target.value.trim()); };
  }

  function personPop(anchor, name) {
    const n = turns.filter(x => x.who === name).length;
    const p = popover(anchor, `
      <div style="font-weight:600">${esc(name)} · ${n} ${plural(n, 'реплика', 'реплики', 'реплик')}</div>
      <button class="btn sm" id="flt1" style="margin:8px 0">${icon('search')}${filter === name ? 'Показать всех' : 'Показать только его реплики'}</button>
      <div style="font-weight:600;margin-top:6px">${name.startsWith('Спикер') ? 'Кто это на самом деле?' : 'Это на самом деле:'}</div>
      <div class="sugg">${nameChips(candidates(name), 'data-to')}</div>
      <input class="input" id="to" placeholder="Имя и Enter">
      <div class="small muted" style="margin-top:8px">Все его реплики перейдут к выбранному человеку. Если это часть одного и того же — так и сливаются лишние «спикеры».</div>`);
    $('#flt1', p).onclick = () => { p.remove(); filter = filter === name ? null : name; store('filter-' + id, filter); renderTurns(); };
    const go = to => act(`/api/job/${id}/rename`, { from: name, to }, `«${name}» → ${to}`);
    $$('[data-to]', p).forEach(b => b.onclick = () => go(b.dataset.to));
    $('#to', p).onkeydown = e => { if (e.key === 'Enter' && e.target.value.trim()) go(e.target.value.trim()); };
  }

  function countPop(anchor) {
    const p = popover(anchor, `
      <div style="font-weight:600">Сколько человек на самом деле говорило?</div>
      <div class="sugg">${[2, 3, 4, 5, 6].map(n => `<button class="chip pick" data-n="${n}" style="min-width:38px;justify-content:center">${n}</button>`).join('')}</div>
      <div class="small muted">Голоса будут размечены заново ровно на столько людей, потом заново сведётся итог. Текст заново не распознаётся — это несколько минут.</div>
      <div class="small" style="margin-top:10px">Или напишите в <b>чат с записью</b> справа, что не так, — например: «тут говорят только я и Рафаэль».</div>`);
    $$('[data-n]', p).forEach(b => b.onclick = async () => {
      p.remove();
      try { await api(`/api/job/${id}/speakers`, { n: +b.dataset.n }); toast(`Размечаю голоса заново: ${b.dataset.n} ${plural(+b.dataset.n, 'человек', 'человека', 'человек')}`); route(); } catch (e) { fail(e); }
    });
  }

  $('#pj').onclick = () => {
    const picked = [...PJ];
    const all = [...new Set([...PJ, ...(data.projects || [])])];
    const p = popover($('#pj'), `<div style="font-weight:600">О каких проектах был разговор?</div>
      <div class="sugg" id="plst"></div>
      <input class="input" id="pnew" placeholder="Новый проект и Enter">
      <div style="display:flex;gap:8px;margin-top:10px"><button class="btn sm primary" id="psv">Сохранить</button></div>
      <div class="small muted" style="margin-top:8px">Можно отметить несколько — задачи разложатся по ним. Выбранное вручную ИИ больше не меняет. Описания проектов — в Настройках.</div>`);
    const draw = () => {
      $('#plst', p).innerHTML = all.map(n => `<button class="chip pick${picked.includes(n) ? ' on' : ''}" data-p="${esc(n)}" style="--c:${colorFor(n, [])}">${icon('folder')}${esc(n)}</button>`).join('');
      $$('[data-p]', p).forEach(b => b.onclick = () => {
        const n = b.dataset.p, k = picked.indexOf(n);
        if (k >= 0) picked.splice(k, 1); else picked.push(n);
        draw();
      });
    };
    draw();
    $('#pnew', p).onkeydown = e => {
      const n = e.target.value.trim();
      if (e.key !== 'Enter' || !n) return;
      if (!all.includes(n)) all.push(n);
      if (!picked.includes(n)) picked.push(n);
      e.target.value = ''; draw();
    };
    $('#psv', p).onclick = () => act(`/api/job/${id}/project`, { projects: picked },
      picked.length ? `${plural(picked.length, 'Проект', 'Проекты', 'Проекты')}: ${picked.join(', ')}` : 'Проект снят');
  };

  async function undoLast() {
    try { await api(`/api/job/${id}/undo`, {}); toast('Последнее изменение отменено'); reload(); } catch (e) { fail(e); }
  }
  if ($('#undo1')) $('#undo1').onclick = e => { e.preventDefault(); undoLast(); };

  $('#ed').onclick = async () => {
    if (!editing) {
      editing = true;
      filter = null; renderTurns();
      $$('#tr .tx').forEach(x => x.contentEditable = 'true');
      $('#ed').innerHTML = `${icon('check')}Сохранить правки`;
      $('#ed').classList.add('primary');
      toast('Правьте текст прямо в репликах, потом нажмите «Сохранить правки»');
    } else {
      const edited = $$('#tr .turn').map(el => { const t = turns[+el.dataset.i]; return { t: t.t, who: t.who, text: $('.tx', el).innerText.trim() }; });
      try { await api(`/api/job/${id}/turns`, { turns: edited }); toast('Правки сохранены, Word обновлён'); reload(); } catch (e) { fail(e); }
    }
  };

  /* --- плеер и волна --- */
  const cv = $('#wv');
  let cur = -1;
  function draw() {
    const dpr = devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
    if (!w) return;
    cv.width = w * dpr; cv.height = h * dpr;
    const g = cv.getContext('2d');
    g.scale(dpr, dpr);
    const css = getComputedStyle(document.documentElement);
    const acc = css.getPropertyValue('--accent').trim(), dim = css.getPropertyValue('--line').trim();
    const wh = h - 12, mid = 4 + wh / 2, pos = (audio.currentTime || 0) / dur;
    if (peaks.length) {
      for (let x = 0; x < w; x += 3) {
        const p = peaks[Math.min(peaks.length - 1, Math.floor(x / w * peaks.length))];
        const bh = Math.max(1.5, p * (wh - 2));
        g.fillStyle = x / w <= pos ? acc : dim;
        g.fillRect(x, mid - bh / 2, 2, bh);
      }
    }
    (data.speakers || []).forEach(s => { g.fillStyle = col(s.who); g.fillRect(s.s / dur * w, h - 5, Math.max(1, (s.e - s.s) / dur * w), 5); });
    g.fillStyle = '#e0a400';
    marks.forEach(m => { const x = m.t / dur * w; g.beginPath(); g.moveTo(x - 5, 0); g.lineTo(x + 5, 0); g.lineTo(x, 7); g.fill(); });
    g.fillStyle = acc;
    g.fillRect(pos * w - 1, 0, 2, h - 6);
  }
  const seekFromEvent = e => { const r = cv.getBoundingClientRect(); return (e.clientX - r.left) / r.width * dur; };
  cv.onclick = e => { audio.currentTime = seekFromEvent(e); draw(); sync(); };
  cv.onmousemove = e => {
    const t = seekFromEvent(e);
    const sp = (data.speakers || []).find(s => s.s <= t && t <= s.e);
    cv.title = fmtT(t) + (sp ? ' · ' + sp.who : '');
  };
  api(`/api/job/${id}/peaks`).then(r => { peaks = r.peaks; draw(); }).catch(() => {});

  const pp = $('#pp');
  const setBtn = () => { pp.innerHTML = icon(audio.paused ? 'play' : 'pause'); };
  pp.onclick = () => { if (audio.paused) audio.play(); else audio.pause(); };
  $('#sp').value = String(audio.playbackRate || 1);
  $('#sp').onchange = e => { audio.playbackRate = +e.target.value; };
  $('#fl').onchange = e => { follow = e.target.checked; store('follow', follow); };

  function sync() {
    const t = audio.currentTime || 0;
    $('#tc').textContent = fmtT(t);
    let lo = 0, hi = turns.length - 1, k = -1;
    while (lo <= hi) { const m = (lo + hi) >> 1; if (turns[m].t <= t + 0.3) { k = m; lo = m + 1; } else hi = m - 1; }
    if (k !== cur) {
      const prev = $(`#tr .turn[data-i="${cur}"]`);
      if (prev) prev.classList.remove('now');
      const el = $(`#tr .turn[data-i="${k}"]`);
      if (el) {
        el.classList.add('now');
        if (follow && !audio.paused && !editing) {
          const r = el.getBoundingClientRect();
          if (r.top < 120 || r.bottom > innerHeight - 20) el.scrollIntoView({ block: 'center' });
        }
      }
      cur = k;
    }
  }
  const onTime = () => { sync(); draw(); };
  audio.addEventListener('timeupdate', onTime);
  audio.addEventListener('play', setBtn);
  audio.addEventListener('pause', setBtn);
  const onResize = () => draw();
  window.addEventListener('resize', onResize);
  const onKey = e => {
    if (e.target.closest('input, textarea, [contenteditable="true"]')) return;
    if (e.code === 'Space') { e.preventDefault(); pp.click(); }
    if (e.code === 'ArrowLeft') audio.currentTime = Math.max(0, audio.currentTime - 5);
    if (e.code === 'ArrowRight') audio.currentTime = audio.currentTime + 5;
  };
  document.addEventListener('keydown', onKey);
  onLeave(() => {
    audio.removeEventListener('timeupdate', onTime); audio.removeEventListener('play', setBtn); audio.removeEventListener('pause', setBtn);
    window.removeEventListener('resize', onResize); document.removeEventListener('keydown', onKey);
  });
  setBtn();

  /* --- шапка --- */
  const jt = $('#jt');
  jt.onclick = () => { if (jt.contentEditable !== 'true') { jt.contentEditable = 'true'; jt.focus(); } };
  jt.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); jt.blur(); } };
  jt.onblur = () => {
    if (jt.contentEditable !== 'true') return;
    jt.contentEditable = 'false';
    const t = jt.innerText.trim();
    if (t && t !== R.title) api(`/api/job/${id}/title`, { title: t }).then(() => { R.title = t; toast('Название сохранено'); }).catch(fail);
  };
  $('#bw').onclick = () => api(`/api/job/${id}/open`, { what: 'docx' }).catch(fail);
  if ($('#bvid')) $('#bvid').onclick = () => api(`/api/job/${id}/open`, { what: 'video' }).catch(fail);
  $('#bf').onclick = () => api(`/api/job/${id}/open`, { what: 'folder' }).catch(fail);
  $('#bm').onclick = () => {
    const p = popover($('#bm'), `<div style="display:grid;gap:6px">
      ${data.versions ? `<button class="btn sm ghost" data-a="undo" style="justify-content:flex-start">${icon('refresh')}Отменить последнее изменение</button>` : ''}
      <button class="btn sm ghost" data-a="redo" style="justify-content:flex-start">${icon('refresh')}Свести итог заново (после правки словаря)</button>
      <button class="btn sm ghost" data-a="rerun" style="justify-content:flex-start">${icon('wave')}Распознать заново (всё с нуля)</button>
      <button class="btn sm ghost" data-a="html" style="justify-content:flex-start">${icon('doc')}Страница для печати</button>
      <button class="btn sm ghost danger" data-a="delete" style="justify-content:flex-start">${icon('trash')}Удалить запись</button></div>`);
    p.style.left = Math.max(10, $('#bm').getBoundingClientRect().right - 290) + 'px';
    $$('[data-a]', p).forEach(b => b.onclick = async () => {
      p.remove();
      const a = b.dataset.a;
      try {
        if (a === 'html') return api(`/api/job/${id}/open`, { what: 'html' });
        if (a === 'undo') return undoLast();
        if (a === 'redo') { await api(`/api/job/${id}/redo`, {}); toast('Итог сводится заново — это несколько минут'); return route(); }
        if (a === 'rerun') {
          if (!confirm(`Распознать запись заново с нуля? Это примерно ${fmtDur(dur * 1.8)}. Ручные правки пропадут, но прежний вариант можно будет вернуть через «Отменить».`)) return;
          await api(`/api/job/${id}/rerun`, {}); toast('Запись распознаётся заново'); return route();
        }
        if (a === 'delete' && confirm('Удалить запись вместе с расшифровкой? Исходный файл останется на месте.')) {
          await api(`/api/job/${id}/delete`, {}); audio.pause(); player = null; location.hash = '#/lib';
        }
      } catch (e) { fail(e); }
    });
  };

  /* --- правая колонка --- */
  const list = (items, empty) => items && items.length ? `<ul>${items.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : `<div class="muted small">${empty}</div>`;
  const tasks = (R.tasks || []).map((t, i) => ({ ...(typeof t === 'string' ? { what: t } : t), ...(data.tasks_state || [])[i] }));
  const total = (R.stats || []).reduce((a, s) => a + s.sec, 0) || 1;
  const recog = Object.values(data.recognized || {});
  $('#sc').innerHTML = `
    <div class="card"><h2>Кратко</h2>${list(R.summary, 'Краткого содержания нет')}</div>
    ${R.decisions && R.decisions.length ? `<div class="card"><h2>Решения</h2>${list(R.decisions)}</div>` : ''}
    ${tasks.length ? `<div class="card"><h2>Задачи</h2>${tasks.map((t, i) => `<label class="task${t.done ? ' done' : ''}">
        <input type="checkbox" data-k="${t.key || ''}" ${t.done ? 'checked' : ''}>
        <div><div class="what">${esc(t.what)}</div><div class="who">${esc([t.who, t.when].filter(Boolean).join(' · '))}
          ${PJ.length > 1 && t.project ? `<button class="projbtn" data-tp="${i}" title="Другой проект">${projChip(t.project)}</button>` : ''}</div></div></label>`).join('')}</div>` : ''}
    ${R.stats && R.stats.length ? `<div class="card"><h2>Кто сколько говорил</h2>${R.stats.map(s => `<div class="stat" style="--c:${col(s.who)}">
        <span>${esc(s.who)}</span><div class="bar"><i style="width:${s.sec * 100 / total}%"></i></div><span class="muted">${fmtDur(s.sec)}</span></div>`).join('')}
        ${recog.length ? `<div class="small muted" style="margin-top:8px">Узнаны по голосу: ${recog.map(r => esc(r.name)).join(', ')}</div>` : ''}</div>` : ''}
    ${marks.length ? `<div class="card"><h2>Отмеченные моменты</h2>${marks.map(m => `<div style="margin:4px 0"><a href="#" class="cite" data-seek="${m.t}">★ ${fmtT(m.t)}</a> ${esc(m.note || nearText(m.t))}</div>`).join('')}</div>` : ''}
    <div class="card"><h2>${icon('spark')} Чат с записью</h2>
      <div class="muted small tip">Спросите о разговоре или скажите, что исправить в расшифровке — правка сразу применится, её можно отменить.</div>
      <div class="suggest">${['Что решили?', 'Что я пообещал сделать?', 'Проверь, правильно ли подписаны участники', 'Что осталось нерешённым?'].map(s => `<button>${s}</button>`).join('')}</div>
      <div class="qa" id="qa"></div>
      <div style="display:flex;gap:8px;margin-top:10px;align-items:flex-end"><textarea class="input" id="qi" rows="2" placeholder="Например: тут говорят только я и Рафаэль — исправь"></textarea><button class="btn voice" id="qv" title="Спросить голосом">${icon('mic')}</button><button class="btn primary" id="qb" title="Отправить (Enter)">${icon('chat')}</button></div></div>
    <div class="card"><h2>Документы по записи</h2><div style="display:grid;gap:8px">
      <button class="btn" data-doc="letter">${icon('mail')}Письмо участникам с итогами</button>
      <button class="btn" data-doc="protocol">${icon('doc')}Протокол встречи</button></div></div>`;
  function nearText(t) { const n = turns.reduce((b, x) => Math.abs(x.t - t) < Math.abs(b.t - t) ? x : b, turns[0]); return n ? `${n.who}: ${n.text.slice(0, 90)}…` : ''; }
  $('#sc').addEventListener('click', e => {
    const s = e.target.closest('[data-seek]');
    if (s) { e.preventDefault(); audio.currentTime = +s.dataset.seek; audio.play(); }
  });
  $$('#sc [data-tp]').forEach(b => b.onclick = e => {
    e.preventDefault();
    const i = +b.dataset.tp;
    const p = popover(b, `<div style="font-weight:600">К какому проекту эта задача?</div>
      <div class="sugg">${PJ.map(n => `<button class="chip pick${n === tasks[i].project ? ' on' : ''}" data-p="${esc(n)}" style="--c:${colorFor(n, [])}">${icon('folder')}${esc(n)}</button>`).join('')}</div>`);
    $$('[data-p]', p).forEach(x => x.onclick = () => act(`/api/job/${id}/task-project`, { i, project: x.dataset.p }, `Задача — в «${x.dataset.p}»`));
  });
  $$('#sc .task input').forEach(c => c.onchange = () => {
    c.closest('.task').classList.toggle('done', c.checked);
    if (c.dataset.k) api('/api/tasks/' + c.dataset.k, { done: c.checked }).then(pollState).catch(fail);
  });

  const qa = (data.qa || []).slice(-6);
  const renderQA = pending => {
    $('#qa').innerHTML = qa.map((x, k) => `<div><div class="q">${esc(x.q)}</div><div class="a">${fmtAnswer(x.a)}</div>
        ${x.changed ? `<div class="fixed">${icon('check')} исправлено: ${x.changed}${k === qa.length - 1 && data.versions ? ` · <a href="#" class="undo2">отменить</a>` : ''}</div>` : ''}</div>`).join('') +
      (pending ? `<div><div class="q">${esc(pending)}</div><div class="thinking">Читаю расшифровку… если нужно исправить — исправляю и обновляю краткое содержание (до пары минут)</div></div>` : '');
    $$('#qa .undo2').forEach(a => a.onclick = e => { e.preventDefault(); undoLast(); });
  };
  renderQA();
  const askJob = async text => {
    const qq = (text || $('#qi').value).trim();
    if (!qq) return;
    $('#qi').value = '';
    renderQA(qq);
    try {
      const r = await api(`/api/job/${id}/ask`, { q: qq });
      qa.push(r);
      if (r.changed) { toast(`Исправлено: ${r.changed}. Отменить можно в чате или в меню ⋯`); reload(); } else renderQA();
    } catch (e) { renderQA(); fail(e); }
  };
  $('#qb').onclick = () => askJob();
  voiceBtn($('#qv'), $('#qi'), askJob);
  $('#qi').onkeydown = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); askJob(); } };
  $$('#sc .suggest button').forEach(b => b.onclick = () => askJob(b.textContent));
  $$('#sc [data-doc]').forEach(b => b.onclick = () => openDoc(id, b.dataset.doc, b.textContent.trim()));

  renderTurns();
  if (q && q.get('t')) {
    audio.currentTime = +q.get('t');
    setTimeout(() => { sync(); const el = $(`#tr .turn[data-i="${cur}"]`); if (el) el.scrollIntoView({ block: 'center' }); }, 50);
  }
  requestAnimationFrame(draw);
  function reload() {
    const t = audio.currentTime;
    cleanups.forEach(f => { try { f(); } catch { /* ничего */ } });
    cleanups = [];
    pageJob(id, new URLSearchParams('t=' + Math.floor(t)));
  }
}

async function openDoc(id, kind, title, fresh) {
  const m = modal(`<h2 style="margin:0">${esc(title)}</h2><textarea class="input" id="dt" placeholder="Готовлю текст…" disabled></textarea>
    <div class="foot"><span class="muted small" style="margin-right:auto;align-self:center" id="dn">Готовлю — это до минуты…</span>
      <button class="btn" id="dr">${icon('refresh')}Заново</button><button class="btn" id="dw">${icon('word')}Открыть в Word</button>
      <button class="btn primary" id="dc">${icon('copy')}Копировать</button></div>`);
  try {
    const r = await api(`/api/job/${id}/doc`, { kind, fresh: !!fresh });
    $('#dt', m).value = r.text; $('#dt', m).disabled = false; $('#dn', m).textContent = 'Текст можно поправить перед отправкой.';
  } catch (e) { $('#dn', m).textContent = e.message; }
  $('#dc', m).onclick = () => navigator.clipboard.writeText($('#dt', m).value).then(() => toast('Скопировано — вставьте в письмо'));
  $('#dw', m).onclick = () => api(`/api/job/${id}/doc-word`, { kind, text: $('#dt', m).value }).catch(fail);
  $('#dr', m).onclick = () => { m.remove(); openDoc(id, kind, title, true); };
}

/* =====================================================================
   ЗАДАЧИ
   ===================================================================== */

async function pageTasks() {
  const gone = pageGuard();
  view.innerHTML = '<div class="page"><div class="empty">Собираю задачи…</div></div>';
  let r;
  try { r = await api('/api/tasks'); } catch (e) { return fail(e); }
  if (gone()) return;
  let who = store('tw') || 'mine', state = store('ts') || 'open', proj = store('tp') || '';
  const me = r.user.toLowerCase();
  const projects = [...new Set(r.tasks.map(t => t.project).filter(Boolean))].sort();
  if (proj && !projects.includes(proj)) proj = '';
  const isMine = t => (t.who || '').toLowerCase().includes(me);
  const owedMe = t => t.who && !isMine(t);           // «мне должны» — что обещали другие
  const ageDays = t => Math.max(0, Math.floor((Date.now() / 1000 - t.ts) / 86400));
  const render = () => {
    const owed = who === 'owed';
    const items = r.tasks.filter(t => (!proj || t.project === proj) && (who === 'all' || (owed ? owedMe(t) : isMine(t))) &&
      (state === 'all' || (state === 'open' ? !t.done : t.done)));
    // группы — проекты (свежие сверху) или, в «Мне должны», люди (у кого больше открытого — выше);
    // внутри — задачи от новых разговоров к старым
    const groups = {};
    items.forEach(t => {
      const k = owed ? t.who : t.project || '';
      const g = groups[k] = groups[k] || { ts: 0, open: 0, items: [] };
      g.items.push(t); g.ts = Math.max(g.ts, t.ts); g.open += t.done ? 0 : 1;
    });
    const order = Object.keys(groups).sort((a, b) => owed ? groups[b].open - groups[a].open || groups[b].ts - groups[a].ts
      : (!a) - (!b) || groups[b].ts - groups[a].ts);
    order.forEach(k => groups[k].items.sort((a, b) => b.ts - a.ts));
    const open = r.tasks.filter(t => !t.done && isMine(t)).length;
    const owedOpen = r.tasks.filter(t => !t.done && owedMe(t)).length;
    const line = owed ? (owedOpen ? `Другие обещали и пока не отметили сделанным: ${owedOpen} ${plural(owedOpen, 'задача', 'задачи', 'задач')}.` : 'Открытых обещаний других людей нет.')
      : open ? `На вас ${open} ${plural(open, 'открытая задача', 'открытые задачи', 'открытых задач')} из всех встреч.` : 'Открытых задач на вас нет.';
    const age = t => { const n = ageDays(t); return n ? `${n} ${plural(n, 'день', 'дня', 'дней')} назад` : 'сегодня'; };
    const taskRow = t => `<label class="task${t.done ? ' done' : ''}"><input type="checkbox" data-k="${t.key}" ${t.done ? 'checked' : ''}>
          <div class="grow"><div class="what">${esc(t.what)}</div><div class="who">${esc([owed ? '' : t.who || 'не назначено', t.when].filter(Boolean).join(' · '))}
            ${owed && !t.when ? '' : '· '}<a href="#/job/${t.job}${t.t != null ? '?t=' + Math.floor(t.t) : ''}" title="Открыть разговор">${esc(t.title)}</a>, ${esc((t.date || '').slice(0, 5))}
            ${owed ? `· <span class="${!t.done && ageDays(t) >= 5 ? 'late' : ''}">${age(t)}</span>` : ''}</div></div>
          ${owed && !t.done ? `<button class="btn sm ghost" data-rem="${t.key}" title="Скопировать напоминание: что и когда договорились">${icon('copy')}Напомнить</button>` : ''}</label>`;
    view.innerHTML = `<div class="page"><div class="head"><h1>Задачи</h1><div class="grow"></div>
      <div class="seg" id="fw"><button data-v="mine">Мои</button><button data-v="owed">Мне должны</button><button data-v="all">Все</button></div>
      ${projects.length ? `<select class="input" id="fp" style="width:auto;max-width:260px"><option value="">Все проекты</option>
        ${projects.map(p => `<option ${p === proj ? 'selected' : ''}>${esc(p)}</option>`).join('')}</select>` : ''}
      <div class="seg" id="fs"><button data-v="open">Открытые</button><button data-v="done">Сделанные</button><button data-v="all">Все</button></div></div>
      <div class="muted" style="margin:-8px 0 16px">${line} <span class="tip">${owed ? 'Здесь задачи, которые на созвонах взяли на себя другие люди. «Напомнить» копирует, что и когда договорились.' : 'Задачи берутся из кратких содержаний расшифровок.'}</span></div>
      ${order.map(k => { const g = groups[k]; return `<div class="card taskgroup">
        <div class="gh"><span class="pgh">${owed ? chip(k) : k ? projChip(k) : '<span class="proj empty">Без проекта</span>'}</span>
          <span class="muted small">${g.items.length} ${plural(g.items.length, 'задача', 'задачи', 'задач')}</span></div>
        ${g.items.map(taskRow).join('')}</div>`; }).join('')
        || `<div class="empty">${icon('check')}<div>Здесь пусто${who === 'mine' ? ` — задач на «${esc(r.user)}» с таким фильтром нет` : ''}.</div></div>`}</div>`;
    $$('#fw button').forEach(b => { b.classList.toggle('on', b.dataset.v === who); b.onclick = () => { who = b.dataset.v; store('tw', who); render(); }; });
    $$('#fs button').forEach(b => { b.classList.toggle('on', b.dataset.v === state); b.onclick = () => { state = b.dataset.v; store('ts', state); render(); }; });
    if ($('#fp')) $('#fp').onchange = e => { proj = e.target.value; store('tp', proj); render(); };
    $$('[data-rem]').forEach(b => b.onclick = e => {
      e.preventDefault();
      const t = r.tasks.find(x => x.key === b.dataset.rem);
      const text = `${t.who}, напоминаю: ${t.what}${t.when ? ` (срок: ${t.when})` : ''}. Договорились ${(t.date || '').slice(0, 5)} — «${t.title}».`;
      navigator.clipboard.writeText(text).then(() => toast('Напоминание скопировано')).catch(fail);
    });
    $$('.task input').forEach(c => c.onchange = () => {
      const t = r.tasks.find(x => x.key === c.dataset.k);
      t.done = c.checked;
      api('/api/tasks/' + t.key, { done: t.done }).then(pollState).catch(fail);
      setTimeout(render, 350);
    });
  };
  render();
}

/* =====================================================================
   ОБЗОР: итог недели, хронология проекта, моя речь
   ===================================================================== */

async function pageInsights() {
  const gone = pageGuard();
  let tab = store('it') || 'week', lists = null;
  view.innerHTML = `<div class="page"><div class="head"><h1>Обзор</h1><div class="grow"></div>
    <div class="seg" id="itab"><button data-v="week">${icon('doc')}Итог недели</button><button data-v="time">${icon('list')}Хронология проекта</button>
      <button data-v="speech">${icon('mic')}Моя речь</button></div></div><div id="ib"></div></div>`;
  const draw = async () => {
    $$('#itab button').forEach(b => b.classList.toggle('on', b.dataset.v === tab));
    const box = $('#ib');
    box.innerHTML = '<div class="empty">Собираю…</div>';
    try {
      if (tab === 'speech') return await speechTab(box, gone);
      lists = lists || await api('/api/insights/lists');
      if (!gone()) (tab === 'week' ? weekTab : timeTab)(box, lists, gone);
    } catch (e) { box.innerHTML = ''; fail(e); }
  };
  $$('#itab button').forEach(b => b.onclick = () => { tab = b.dataset.v; store('it', tab); draw(); });
  draw();
}

/** «Ещё не собрано» — с кнопкой, которая зовёт Claude (сам по себе он не вызывается: это его лимиты). */
function notYet(box, text, btn, onclick) {
  box.innerHTML = `<div class="empty" style="padding:30px 20px"><div>${text}</div>
    <button class="btn primary" style="margin-top:12px">${icon('spark')}${btn}</button></div>`;
  $('button', box).onclick = onclick;
}

function weekTab(box, lists, gone) {
  if (!lists.weeks.length) { box.innerHTML = `<div class="empty">${icon('doc')}<div>Пока нет готовых записей.</div></div>`; return; }
  let start = store('iw');
  if (!lists.weeks.some(w => w.start === start)) start = lists.weeks[0].start;
  box.innerHTML = `<div class="card"><div class="ins-bar">
      <select class="input" id="ws">${lists.weeks.map(w => `<option value="${w.start}" ${w.start === start ? 'selected' : ''}>${w.label} · ${w.count} ${plural(w.count, 'запись', 'записи', 'записей')}</option>`).join('')}</select>
      <div class="grow"></div><button class="btn" id="wr" hidden>${icon('refresh')}Заново</button>
      <button class="btn" id="ww" hidden>${icon('word')}Открыть в Word</button><button class="btn primary" id="wc" hidden>${icon('copy')}Копировать</button></div>
    <div class="muted small tip ins-tip">Итог собирает Claude из кратких содержаний, решений и задач созвонов недели — только сказанное и решённое. Отметки «сделано» берутся со страницы «Задачи».</div>
    <div id="wbody"></div></div>`;
  const body = $('#wbody', box), tools = $$('#wr, #ww, #wc', box);
  const load = async mode => {
    tools.forEach(b => { b.hidden = true; });
    body.innerHTML = mode === 'peek' ? '' : '<div class="thinking ins-wait">Собираю итог недели — это до пары минут…</div>';
    let r;
    try { r = await api('/api/insights/week', { start, peek: mode === 'peek', fresh: mode === 'fresh' }); } catch (e) { body.innerHTML = ''; return fail(e); }
    if (gone()) return;
    if (r.text == null) return notYet(body, `Итога за ${esc(r.label)} ещё нет.`, 'Собрать итог недели', () => load('make'));
    body.innerHTML = '<textarea class="input ins-text" id="wt"></textarea>';
    $('#wt', body).value = r.text;
    tools.forEach(b => { b.hidden = false; });
  };
  $('#ws', box).onchange = e => { start = e.target.value; store('iw', start); load('peek'); };
  $('#wr', box).onclick = () => load('fresh');
  $('#wc', box).onclick = () => navigator.clipboard.writeText($('#wt', box).value).then(() => toast('Скопировано'));
  $('#ww', box).onclick = () => api('/api/insights/week-word', { start, text: $('#wt', box).value }).catch(fail);
  load('peek');
}

function timeTab(box, lists, gone) {
  if (!lists.projects.length) { box.innerHTML = `<div class="empty">${icon('folder')}<div>Пока нет записей с проектами.</div></div>`; return; }
  let project = store('ip');
  if (!lists.projects.some(p => p.name === project)) project = lists.projects[0].name;
  box.innerHTML = `<div class="card"><div class="ins-bar">
      <select class="input" id="ps">${lists.projects.map(p => `<option value="${esc(p.name)}" ${p.name === project ? 'selected' : ''}>${esc(p.name)} · ${p.count} ${plural(p.count, 'запись', 'записи', 'записей')}</option>`).join('')}</select>
      <div class="grow"></div><span class="muted small" id="pat"></span><button class="btn" id="pr" hidden>${icon('refresh')}Обновить</button></div>
    <div class="muted small tip ins-tip">Решения по проекту из всех созвонов по порядку. Если позже решение поменяли или отменили, это отмечено у самого решения — со ссылкой на созвон, где это случилось.</div>
    <div id="pbody"></div></div>`;
  const body = $('#pbody', box);
  const STATUS = { 'в силе': ['ok', 'в силе'], 'изменено': ['warn', 'изменено'], 'отменено': ['gone', 'отменено'] };
  const load = async mode => {
    $('#pr', box).hidden = true;
    $('#pat', box).textContent = '';
    body.innerHTML = mode === 'peek' ? '' : '<div class="thinking ins-wait">Собираю хронологию — это до пары минут…</div>';
    let r;
    try { r = await api('/api/insights/timeline', { project, peek: mode === 'peek', fresh: mode === 'fresh' }); } catch (e) { body.innerHTML = ''; return fail(e); }
    if (gone()) return;
    if (r.items == null) return notYet(body, 'Хронология этого проекта ещё не собрана.', 'Собрать хронологию', () => load('make'));
    $('#pr', box).hidden = false;
    if (r.at) $('#pat', box).textContent = 'собрано ' + new Date(r.at * 1000).toLocaleDateString('ru-RU');
    const groups = [];
    r.items.forEach(x => { if (!groups.length || groups[groups.length - 1].job !== x.job) groups.push({ job: x.job, items: [] }); groups[groups.length - 1].items.push(x); });
    const rec = id => r.records[id] || { title: 'запись', date: '' };
    body.innerHTML = groups.map(g => `<div class="tl-rec"><div class="tl-date">${esc(rec(g.job).date.slice(0, 5))}</div>
      <div class="tl-body"><a href="#/job/${g.job}" class="tl-title">${esc(rec(g.job).title)}</a>
        ${g.items.map(x => { const [cls, label] = STATUS[x.status] || STATUS['в силе'];
          return `<div class="tl-item ${cls}"><span class="tl-badge">${label}</span><span class="tl-what">${esc(x.what)}</span>
            ${x.note || x.later ? `<div class="tl-note">→ ${x.later && r.records[x.later] ? `<a href="#/job/${x.later}">${esc(rec(x.later).date.slice(0, 5))}, «${esc(rec(x.later).title)}»</a>${x.note ? ': ' : ''}` : ''}${esc(x.note || '')}</div>` : ''}</div>`; }).join('')}
      </div></div>`).join('') || '<div class="empty">В записях по этому проекту решений не нашлось.</div>';
  };
  $('#ps', box).onchange = e => { project = e.target.value; store('ip', project); load('peek'); };
  $('#pr', box).onclick = () => load('fresh');
  load('peek');
}

async function speechTab(box, gone) {
  const r = await api('/api/insights/speech');
  if (gone()) return;
  if (!r.all) {
    box.innerHTML = `<div class="empty">${icon('mic')}<div>Ни в одной записи пока не узнан голос «${esc(r.me)}». Подпишите себя в записи — дальше голос будет узнаваться сам.</div></div>`;
    return;
  }
  const a = r.all;
  const fillers = x => x.top_fillers.map(([f, n]) => `«${esc(f)}» ${n}`).join(', ') || '—';
  const per100 = x => { const n = Object.values(x.fillers).reduce((s, v) => s + v, 0); return x.words ? (100 * n / x.words).toFixed(1) : '—'; };
  const tile = (big, small) => `<div class="ins-tile"><b>${big}</b><span>${small}</span></div>`;
  box.innerHTML = `<div class="card"><h2>Все записи, где узнан ваш голос: ${a.records}</h2>
      <div class="ins-tiles">
        ${tile(a.share + '%', 'вашей речи в разговорах')}
        ${tile(a.wpm ?? '—', 'слов в минуту')}
        ${tile(a.fillers_per100, 'слов-паразитов на 100 слов')}
        ${tile(`${a.by_me_h} / ${a.to_me_h}`, 'перебили вы / вас — в час')}
        ${tile(fmtT(a.longest), 'самый длинный монолог')}
      </div>
      <div class="small" style="margin-top:10px"><span class="muted">Чаще всего:</span> ${fillers(a)}</div>
      <div class="muted small tip ins-tip">Считается на этом компьютере, без ИИ: кто где говорит — по разметке голосов, слова — по черновику GigaAM (в нём паразиты ещё не вычищены). Перебивания — примерно: один вступает, когда другой говорит ещё хотя бы секунду. Темп для разговорной речи обычно 120–160 слов в минуту.</div></div>
    <div class="card"><h2>По неделям</h2><div class="ins-scroll"><table class="vt ins-table">
      <thead><tr><th>Неделя</th><th>Записей</th><th>Ваша доля</th><th>Темп</th><th>Паразиты на 100 слов</th><th>Чаще всего</th><th>Перебили вы / вас в час</th><th>Монолог</th></tr></thead>
      <tbody>${r.weeks.map(w => `<tr><td class="nowrap">${w.label}</td><td>${w.records}</td>
        <td><div class="ins-share"><div class="bar"><i style="width:${w.share}%"></i></div>${w.share}%</div></td>
        <td>${w.wpm ?? '—'}</td><td>${w.fillers_per100}</td><td class="small">${fillers(w)}</td><td>${w.by_me_h} / ${w.to_me_h}</td><td>${fmtT(w.longest)}</td></tr>`).join('')}</tbody></table></div></div>
    <div class="card"><h2>Последние записи</h2><div class="ins-scroll"><table class="vt ins-table">
      <thead><tr><th>Дата</th><th>Запись</th><th>Ваша доля</th><th>Темп</th><th>Паразиты на 100 слов</th><th>Перебили вы / вас</th></tr></thead>
      <tbody>${r.records.map(x => `<tr><td class="nowrap">${esc(x.date.slice(0, 5))}</td><td><a href="#/job/${x.job}">${esc(x.title)}</a></td>
        <td>${x.total ? Math.round(100 * x.mine / x.total) : 0}%</td><td>${x.my_dia >= 30 ? Math.round(x.words / (x.my_dia / 60)) : '—'}</td>
        <td>${per100(x)}</td><td>${x.by_me} / ${x.to_me}</td></tr>`).join('')}</tbody></table></div></div>`;
}

/* =====================================================================
   ГОЛОСА
   ===================================================================== */

const sampleAudio = new Audio();       // проигрыватель образцов голоса: играет кусок и останавливается
let sampleBtn = null;                  // кнопка образца, который сейчас звучит (на ней ⏸)
sampleAudio.ontimeupdate = () => { if (sampleAudio.dataset.end && sampleAudio.currentTime >= +sampleAudio.dataset.end) sampleAudio.pause(); };
const sampleIcon = () => $$('[data-play]').forEach(x => { x.innerHTML = icon(x === sampleBtn && !sampleAudio.paused ? 'pause' : 'play'); });
sampleAudio.onplay = sampleIcon;
sampleAudio.onpause = sampleIcon;

async function pageVoices() {
  const gone = pageGuard();
  onLeave(() => sampleAudio.pause());
  const load = async () => {
    let r;
    try { r = await api('/api/voices'); await loadColors(); } catch (e) { return fail(e); }
    if (gone()) return;
    window.VOICE_NAMES = r.voices.map(v => v.name);
    const L = r.learning;
    view.innerHTML = `<div class="page"><div class="head"><h1>Голоса</h1></div>
      <div class="note" style="margin-bottom:16px">Программа запоминает голоса участников по готовым расшифровкам и дальше сама подсказывает, кто говорит, — даже если в названии и разговоре нет имён. Голос перезапоминается, когда вы исправляете имя в расшифровке.</div>
      ${L.running ? `<div class="card" style="margin-bottom:14px"><b>Запоминаю голоса из готовых записей…</b> ${L.done} из ${L.total}<div class="bar" style="margin-top:8px"><i style="width:${L.total ? L.done * 100 / L.total : 0}%"></i></div></div>`
        : r.untrained ? `<div class="card" style="margin-bottom:14px;display:flex;gap:12px;align-items:center"><div style="flex:1">${r.untrained} ${plural(r.untrained, 'готовая запись ещё не использована', 'готовые записи ещё не использованы', 'готовых записей ещё не использованы')} для запоминания голосов.</div>
            <button class="btn primary" id="la">${icon('spark')}Запомнить голоса</button></div>` : ''}
      ${L.message ? `<div class="note err" style="margin-bottom:14px">${esc(L.message)}</div>` : ''}
      <div class="grid wide">${r.voices.map(v => `<div class="card person" style="--c:${colorFor(v.name)}">
        <div class="avatar">${esc(initials(v.name))}</div>
        <div><div style="font-weight:650;font-size:15px">${esc(v.name)}</div>
          <div class="jobs">узнан в ${v.jobs.length} ${plural(v.jobs.length, 'записи', 'записях', 'записях')} · ${fmtDur(v.sec)} образцов голоса</div>
          <div class="samples">${v.jobs.map(j => `<div class="sample">
            <button class="btn sm ghost" data-play="${j.id}" data-s="${j.clip[0] ?? ''}" data-e="${j.clip[1] ?? ''}" ${j.clip.length ? '' : 'disabled'} title="Послушать этот образец">${icon('play')}</button>
            <a href="#/job/${j.id}${j.clip.length ? '?t=' + Math.floor(j.clip[0]) : ''}">${esc(j.title)}</a>
            ${j.manual ? '<span class="chip" title="Вы сами подписали эту реплику">подтверждён</span>' : ''}
            <span class="muted" title="${j.clip.length ? 'с ' + fmtT(j.clip[0]) + ' в записи' : ''}">${j.clip.length ? Math.round(j.clip[1] - j.clip[0]) + ' с' : ''}</span>
            <span><button class="btn sm ghost" data-move="${esc(v.name)}" data-key="${esc(j.key)}" ${j.clip.length ? '' : 'disabled'} title="Это голос другого человека — перенести образец">${icon('users')}</button><button class="btn sm ghost danger" data-forget="${esc(v.name)}" data-key="${esc(j.key)}" title="Голос чужой — убрать образец">${icon('trash')}</button></span></div>`).join('')}</div></div>
        <div style="display:grid;gap:4px"><button class="btn sm ghost" data-rn="${esc(v.name)}">${icon('edit')}</button><button class="btn sm ghost danger" data-del="${esc(v.name)}">${icon('trash')}</button></div></div>`).join('')
        || `<div class="empty" style="grid-column:1/-1">${icon('users')}<div>Голосов пока нет — они появятся после первой расшифровки с именами.</div></div>`}</div></div>`;
    if ($('#la')) $('#la').onclick = () => api('/api/voices/learn-all', {}).then(load).catch(fail);
    $$('[data-rn]').forEach(b => b.onclick = () => {
      const to = prompt('Как подписывать этого человека?', b.dataset.rn);
      if (to && to.trim()) api('/api/voices/rename', { from: b.dataset.rn, to: to.trim() }).then(load).catch(fail);
    });
    $$('[data-play]').forEach(b => b.onclick = () => {
      const a = sampleAudio;
      if (sampleBtn === b && !a.paused) { a.pause(); return; }          // ⏸ — остановить
      a.pause();
      sampleBtn = b;
      a.dataset.end = b.dataset.e;
      const go = () => { a.currentTime = +b.dataset.s; a.play(); };
      if (a.src.endsWith('/media/' + b.dataset.play)) go();
      else { a.src = '/media/' + b.dataset.play; a.onloadedmetadata = go; }
    });
    $$('[data-move]').forEach(b => b.onclick = () => {
      const others = r.voices.map(x => x.name).filter(n => n !== b.dataset.move);
      const p = popover(b, `<div style="font-weight:600">Чей это голос?</div>
        <div class="sugg">${others.map(n => `<button class="chip pick" data-to="${esc(n)}" style="--c:${colorFor(n)}"><span class="dot"></span>${esc(n)}</button>`).join('')}</div>
        <input class="input" id="mvto" placeholder="Другой человек и Enter">
        <div class="small muted" style="margin-top:8px">Образец уйдёт к выбранному человеку как подтверждённый — по тому куску, что вы слушали.</div>`);
      const go = to => { p.remove(); api('/api/voices/move', { name: b.dataset.move, key: b.dataset.key, to }).then(() => { toast(`Образец перенесён: ${to}`); load(); }).catch(fail); };
      $$('[data-to]', p).forEach(x => x.onclick = () => go(x.dataset.to));
      $('#mvto', p).onkeydown = e => { if (e.key === 'Enter' && e.target.value.trim()) go(e.target.value.trim()); };
    });
    $$('[data-forget]').forEach(b => b.onclick = () => {
      if (confirm(`Убрать этот образец из голоса «${b.dataset.forget}»? Из этой записи он больше не возьмётся.`))
        api('/api/voices/forget', { name: b.dataset.forget, key: b.dataset.key }).then(() => { toast('Образец убран'); load(); }).catch(fail);
    });
    $$('[data-del]').forEach(b => b.onclick = () => {
      if (confirm(`Забыть голос «${b.dataset.del}»?`)) api('/api/voices/delete', { name: b.dataset.del }).then(load).catch(fail);
    });
    return L.running;
  };
  let wasRunning = await load();
  every(2500, async () => {
    const r = await api('/api/voices').catch(() => null);
    if (r && !gone() && (r.learning.running || wasRunning)) wasRunning = await load();
  });
}

/* =====================================================================
   СЛОВАРЬ
   ===================================================================== */

async function pageGlossary() {
  const gone = pageGuard();
  let r;
  try { r = await api('/api/glossary'); } catch (e) { return fail(e); }
  if (gone()) return;
  view.innerHTML = `<div class="page"><div class="head"><h1>Словарь</h1><div class="grow"></div>
      <button class="btn primary" id="gs" disabled>Сохранить</button></div>
    <div class="note" style="margin-bottom:14px">Термины и имена, которые модели часто путают. Редактор сверяется со словарём при каждой расшифровке. Чтобы применить правки к готовой записи, откройте её → ⋯ → «Свести итог заново».</div>
    <div class="card" style="margin-bottom:14px" id="gsug"></div>
    <div class="card" style="margin-bottom:14px"><h2>Быстро добавить</h2>
      <div class="gloss-add"><input class="input" id="g1" placeholder="Как правильно: JewelSuite"><input class="input" id="g2" placeholder="Что это (необязательно)">
        <input class="input" id="g3" placeholder="Как ошибаются: джил сьют, джуэл сьют"><button class="btn" id="ga">Добавить</button></div></div>
    <div class="card"><textarea class="input gloss" id="gt" spellcheck="false">${esc(r.text)}</textarea>
      <div class="small muted" style="margin-top:8px">Формат строки: <code>Правильно (пояснение) — ошибка, ошибка</code>. Строки с # — комментарии.</div></div></div>`;
  const ta = $('#gt'), save = $('#gs');
  let dirty = false;
  ta.oninput = () => { dirty = true; save.disabled = false; };
  save.onclick = () => api('/api/glossary', { text: ta.value }).then(() => { dirty = false; save.disabled = true; toast('Словарь сохранён'); }).catch(fail);
  const addLine = (a, b, c) => {
    ta.value = ta.value.replace(/\s*$/, '\n') + a + (b ? ` (${b})` : '') + (c ? ` — ${c}` : '') + '\n';
    return api('/api/glossary', { text: ta.value }).then(() => { toast(`«${a}» добавлено в словарь`); ta.scrollTop = ta.scrollHeight; }).catch(fail);
  };
  $('#ga').onclick = () => {
    const a = $('#g1').value.trim(), b = $('#g2').value.trim(), c = $('#g3').value.trim();
    if (!a) return;
    ['#g1', '#g2', '#g3'].forEach(s => { $(s).value = ''; });
    addLine(a, b, c);
  };
  // предложения из записей: ищет Claude по кнопке, добавлять или нет — решает человек
  const drawSugg = (s, busy) => {
    const box = $('#gsug');
    if (!box) return;
    box.innerHTML = `<div class="ins-bar"><h2 style="margin:0">Предложения из записей</h2><div class="grow"></div>
        ${s.at && !busy ? `<span class="muted small">искали ${new Date(s.at * 1000).toLocaleDateString('ru-RU')}</span>` : ''}
        <button class="btn" id="gfind" ${busy ? 'disabled' : ''}>${icon('search')}${busy ? 'Ищу — это до пары минут…' : 'Поискать в записях'}</button></div>
      <div class="muted small tip ins-tip">Claude просматривает последние расшифровки и предлагает термины, названия и имена, которые GigaAM пишет с ошибками. Добавлять или нет — решаете вы.</div>
      ${s.items.length ? `<div class="sugg-list">${s.items.map((x, i) => `<div class="sugg-row"><div class="grow"><b>${esc(x.term)}</b>${x.note ? ` <span class="muted">(${esc(x.note)})</span>` : ''}
          ${x.errors.length ? `<div class="err">GigaAM пишет: ${esc(x.errors.join(', '))}</div>` : ''}</div>
          <button class="btn sm" data-sa="${i}">Добавить</button><button class="btn sm ghost" data-sd="${i}">Не надо</button></div>`).join('')}</div>`
        : s.at && !busy ? '<div class="muted small" style="margin-top:8px">Новых предложений нет.</div>' : ''}`;
    $('#gfind', box).onclick = () => {
      drawSugg(s, true);
      api('/api/glossary/suggest', {}).then(n => { if (!gone()) drawSugg(n); }).catch(e => { if (!gone()) drawSugg(s); fail(e); });
    };
    $$('[data-sa]', box).forEach(b => b.onclick = () => {
      const x = s.items.splice(+b.dataset.sa, 1)[0];
      addLine(x.term, x.note, x.errors.join(', '));
      drawSugg(s);
    });
    $$('[data-sd]', box).forEach(b => b.onclick = () => api('/api/glossary/suggest/dismiss', { term: s.items[+b.dataset.sd].term }).then(drawSugg).catch(fail));
  };
  api('/api/glossary/suggest').then(s => { if (!gone()) drawSugg(s); }).catch(() => { /* ничего */ });
  const warn = e => { if (dirty) { e.preventDefault(); e.returnValue = ''; } };
  window.addEventListener('beforeunload', warn);
  onLeave(() => { window.removeEventListener('beforeunload', warn); if (dirty && confirm('Сохранить правки словаря?')) api('/api/glossary', { text: ta.value }).catch(fail); });
}

/* =====================================================================
   НАСТРОЙКИ
   ===================================================================== */

async function pageSettings() {
  const gone = pageGuard();
  let r;
  try { r = await api('/api/settings'); } catch (e) { return fail(e); }
  if (gone()) return;
  const s = r.settings, d = r.devices, cx = r.codex || {};
  view.innerHTML = `<div class="page"><div class="head"><h1>Настройки</h1></div>
    <div class="card comps" id="comps" hidden></div><div class="card"><div class="form">
    <div class="row"><label>Ваше имя</label><div><input class="input" id="un" value="${esc(s.user_name)}" style="max-width:280px">
      <div class="help">Так вас подписывает редактор; по нему же собираются «Мои задачи».</div></div></div>
    <div class="row"><label>Кто делает итог</label><div>
      <label class="radio"><input type="radio" name="ed" value="claude" ${s.editor === 'claude' ? 'checked' : ''}><span><b>Claude Code</b> (подписка Claude)<br><span class="help">Текст расшифровки (не звук) уходит в Claude.</span></span></label>
      <label class="radio"><input type="radio" name="ed" value="codex" ${s.editor === 'codex' ? 'checked' : ''} ${cx.installed ? '' : 'disabled'}><span><b>Codex</b> (подписка ChatGPT)<br><span class="help">Текст расшифровки (не звук) уходит в ChatGPT.</span>
        ${!cx.installed ? '<div class="help err" style="color:var(--rec)">Codex на этом компьютере не установлен.</div>'
          : !cx.logged_in ? `<div style="margin-top:6px"><button class="btn sm" id="cxl">Войти в ChatGPT</button> <span class="help">откроется браузер, вход — на сайте OpenAI</span></div>` : ''}</span></label>
      <label class="radio"><input type="radio" name="ed" value="openai" ${s.editor === 'openai' ? 'checked' : ''}><span><b>Локальная модель</b> (Ollama, LM Studio)<br><span class="help">Всё на компьютере, но на этом ноутбуке медленно и слабее.</span>
        <div id="localcfg" style="display:${s.editor === 'openai' ? 'grid' : 'none'};grid-template-columns:1fr 160px;gap:4px 8px;margin-top:8px">
          <span class="help">Адрес программы с моделью</span><span class="help">Модель</span>
          <input class="input" id="ou" value="${esc(s.openai_url)}"><input class="input" id="om" value="${esc(s.openai_model)}">
          <span class="help" style="grid-column:1/-1">Обычно: Ollama — <code translate="no">http://localhost:11434/v1</code>, LM Studio — <code translate="no">http://localhost:1234/v1</code>.</span></div></span></label>
      <label class="radio"><input type="radio" name="ed" value="none" ${s.editor === 'none' ? 'checked' : ''}><span><b>Без редактора</b><br><span class="help">Ничего не уходит с компьютера: итог — черновик GigaAM с заменами из словаря. Вопросы и письма недоступны.</span></span></label></div></div>
    <div class="row"><label>Второй черновик</label><div><label class="switch"><input type="checkbox" id="wh" ${s.whisper ? 'checked' : ''}><i></i>Распознавать ещё и Whisper</label>
      <div class="help">Лучше английские слова и имена. Без него обработка почти вдвое быстрее.</div></div></div>
    <div class="row"><label>Микрофон</label><div><select class="input" id="mc" style="max-width:420px"><option value="">По умолчанию (${esc(d.default_mic || '—')})</option>
      ${(d.mics || []).map(m => `<option ${m === s.mic_device ? 'selected' : ''}>${esc(m)}</option>`).join('')}</select>
      ${d.error ? `<div class="help err" style="color:var(--rec)">${esc(d.error)}</div>` : ''}</div></div>
    <div class="row"><label>Язык</label><div><div class="seg" id="lg" translate="no">
      ${[['ru', 'Русский'], ['en', 'English'], ['ce', 'Нохчийн']].map(([v, l]) => `<button data-v="${v}" class="${window.LANG === v ? 'on' : ''}">${l}</button>`).join('')}</div></div></div>
    <div class="row"><label>Тема</label><div><div class="seg" id="th">
      ${[['system', 'Системная'], ['light', 'Светлая'], ['dark', 'Тёмная']].map(([v, l]) => `<button data-v="${v}" class="${(s.theme || 'system') === v ? 'on' : ''}">${l}</button>`).join('')}</div></div></div>
    <div class="row"><label>Уведомления</label><div><label class="switch"><input type="checkbox" id="nt" ${s.notify ? 'checked' : ''}><i></i>Сообщать, когда расшифровка готова</label></div></div>
    <div class="row"><label>Подключение MCP</label><div id="mcp"></div></div>
    <div class="row"><label>Где лежат записи</label><div><code>${esc(r.paths.jobs)}</code> <button class="btn sm" id="of" style="margin-left:8px">${icon('folder')}Открыть</button></div></div>
  </div></div>
  <div class="card" style="margin-top:14px"><h2>Проекты</h2>
    <div class="muted small tip" style="margin-bottom:10px">По описанию ИИ решает, к какому проекту относится разговор. Новые проекты он добавляет сам; здесь их можно переименовать, уточнить описание или удалить (у записей пометка снимется).</div>
    <div id="plist" style="display:grid;gap:8px"></div>
    <div style="display:flex;gap:8px;margin-top:10px"><button class="btn sm" id="padd">Добавить проект</button><button class="btn sm primary" id="psave" disabled>Сохранить проекты</button></div></div></div>`;
  let projs = [];
  const drawProjects = () => {
    $('#plist').innerHTML = projs.map((p, i) => `<div style="display:grid;grid-template-columns:220px 1fr auto auto;gap:8px;align-items:center">
      <input class="input" data-i="${i}" data-f="name" value="${esc(p.name)}" placeholder="Название" style="font-weight:600;color:${colorFor(p.name || '?', [])}">
      <input class="input" data-i="${i}" data-f="about" value="${esc(p.about)}" placeholder="О чём проект: темы, люди, системы">
      <span class="muted small" style="min-width:70px">${p.count ? `${p.count} ${plural(p.count, 'запись', 'записи', 'записей')}` : ''}</span>
      <button class="btn sm ghost danger" data-del="${i}" title="Удалить">${icon('trash')}</button></div>`).join('') || '<div class="muted">Проектов пока нет — они появятся после расшифровок.</div>';
    $$('#plist input').forEach(x => x.oninput = () => { projs[+x.dataset.i][x.dataset.f] = x.value; $('#psave').disabled = false; });
    $$('#plist [data-del]').forEach(b => b.onclick = () => { projs.splice(+b.dataset.del, 1); $('#psave').disabled = false; drawProjects(); });
  };
  api('/api/projects').then(x => { projs = x.projects.map(p => ({ ...p, old: p.name })); drawProjects(); }).catch(fail);
  $('#padd').onclick = () => { projs.push({ name: '', about: '' }); drawProjects(); $$('#plist input[data-f=name]').pop().focus(); };
  $('#psave').onclick = () => api('/api/projects', { items: projs }).then(x => {
    projs = x.projects.map(p => ({ ...p, old: p.name })); drawProjects(); $('#psave').disabled = true; toast('Проекты сохранены');
  }).catch(fail);
  const put = (patch, msg) => api('/api/settings', patch).then(() => toast(msg || 'Сохранено')).catch(fail);
  let t1;
  $('#un').oninput = e => { clearTimeout(t1); t1 = setTimeout(() => put({ user_name: e.target.value.trim() || 'Дэни' }), 600); };
  $$('[name=ed]').forEach(x => x.onchange = () => { $('#localcfg').style.display = x.value === 'openai' ? 'grid' : 'none'; put({ editor: x.value }); });
  if ($('#cxl')) $('#cxl').onclick = e => { e.preventDefault(); api('/api/codex-login', {}).then(() => toast('Войдите в ChatGPT в открывшемся окне, потом откройте настройки заново')).catch(fail); };
  $('#ou').onchange = e => put({ openai_url: e.target.value.trim() });
  $('#om').onchange = e => put({ openai_model: e.target.value.trim() });
  $('#wh').onchange = e => put({ whisper: e.target.checked });
  $('#mc').onchange = e => put({ mic_device: e.target.value });
  $('#nt').onchange = e => put({ notify: e.target.checked });
  $$('#th button').forEach(b => b.onclick = () => {
    $$('#th button').forEach(x => x.classList.toggle('on', x === b));
    applyTheme(b.dataset.v);
    if (ST) ST.theme = b.dataset.v;
    put({ theme: b.dataset.v }, 'Тема сохранена');
  });
  $$('#lg button').forEach(b => b.onclick = () => {
    if (b.dataset.v === window.LANG) return;
    api('/api/settings', { lang: b.dataset.v }).then(() => { store('lang', b.dataset.v); location.reload(); }).catch(fail);
  });
  $('#of').onclick = () => api('/api/open-folder', {}).catch(fail);
  drawMcp(gone);
  drawComps(gone);
}

/** Настройки → «Подключение MCP»: Qamyal как MCP-сервер. Строка «Claude» — сразу чат (Claude Desktop) и Code
 *  (у них разные файлы настроек), строка «ChatGPT Codex» — Codex; не установленная — серым.
 *  Обратное направление к «Кто делает итог». */
async function drawMcp(gone, m) {
  try { m = m || await api('/api/claude-link'); } catch { m = null; }
  if (gone()) return;
  $('#mcp').closest('.row').hidden = !m;           // сервер не ответил — пустую строку не показываем
  if (!m) return;
  const apps = [['claude', 'Claude', ['desktop', 'code']], ['codex', 'ChatGPT Codex', ['codex']]];
  $('#mcp').innerHTML = `<div class="mcp-list">${apps.map(([k, name, parts]) => {
    const got = parts.filter(p => m[p + '_installed']), has = got.length > 0,
          on = has && got.every(p => m[p]);        // подключён, когда подключены все установленные части
    return `<div class="mcp-app${has ? '' : ' off'}">
      <span class="mcp-dot${on ? ' on' : ''}">${on ? '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>' : ''}</span><b translate="no">${name}</b>
      <span class="muted small">${on ? 'подключён' : has ? 'установлен, можно подключить' : 'не установлен'}</span>
      ${has ? `<button class="btn sm${on ? ' ghost' : ' primary'}" data-mcp="${k}" data-on="${on ? 0 : 1}">${on ? 'Отключить' : 'Подключить'}</button>` : ''}</div>`;
  }).join('')}</div>
    <div class="help">Это не про итог: здесь вы задаёте вопрос в чате Claude или Codex, а они сами смотрят записи в Qamyal. Можно искать по записям, читать расшифровки и задачи, отмечать и добавлять задачи. Записи остаются на компьютере: в чат уходит только то, что нужно для ответа.</div>`;
  $$('#mcp [data-mcp]').forEach(b => b.onclick = () => {
    const on = b.dataset.on === '1', [, name, parts] = apps.find(a => a[0] === b.dataset.mcp);
    b.disabled = true;
    api('/api/claude-link', { on, which: parts }).then(x => {
      drawMcp(gone, x);
      if (x.errors.length) return toast(x.errors.join('; '), true);
      toast(on ? `${name}: подключено — перезапустите программу, чтобы она увидела записи` : `${name}: отключено`);
    }).catch(e => { b.disabled = false; fail(e); });
  });
}

/** Новая версия (только Mac): Qamyal сам скачивает образ с GitHub, ставит и перезапускается. */
async function drawUpdate(gone) {
  let u;
  try { u = await api('/api/update?now=1'); } catch { return; }
  if (gone() || !u.supported) return;
  markUpdate(u);
  const box = $('#upd');
  if (!u.available) {
    box.innerHTML = `<div class="muted small upd-ok">${icon('check')}Установлена последняя версия Qamyal</div>`;
    return;
  }
  box.innerHTML = `<div class="card upd">${icon('download')}<div class="grow"><b>Доступна новая версия Qamyal</b>
    <div class="muted small"><span>сборка от</span> <span translate="no">${esc(u.version)}</span></div></div>
    <button class="btn primary" id="updgo">${icon('download')}Обновить</button></div>`;
  $('#updgo').onclick = async () => {
    try { await api('/api/update', {}); } catch (e) { return fail(e); }
    box.innerHTML = `<div class="card upd">${icon('refresh')}<div class="grow"><b>Скачиваю и ставлю новую версию…</b>
      <div class="muted small">Qamyal закроется и откроется сам примерно через минуту.</div></div></div>`;
  };
}

/** Точка у «О приложении», когда вышла новая версия. */
function markUpdate(u) {
  const b = $('#b-about');
  if (b) { b.textContent = u && u.available ? '1' : ''; b.title = u && u.available ? 'Доступна новая версия' : ''; }
}

/** «О приложении»: версия, статистика по всем записям, как устроена обработка, компьютер. */
async function pageAbout() {
  const gone = pageGuard();
  view.innerHTML = `<div class="page"><div class="head"><h1>О приложении</h1></div><div id="upd"></div><div class="card about" id="about"></div></div>`;
  drawUpdate(gone);
  let a;
  try { a = await api('/api/about'); } catch (e) { return fail(e); }
  if (gone()) return;
  const s = a.stats, m = a.machine, num = n => Math.round(n).toLocaleString('ru-RU');
  const tile = (n, label) => `<div class="ab-tile"><b>${n}</b><span>${label}</span></div>`;
  const days = s.first ? Math.max(1, Math.round((Date.now() / 1000 - s.first) / 86400)) : 0;
  const editor = { claude: 'Claude Code (Anthropic) сверяет два черновика слово за словом и пишет чистый текст, краткое содержание, решения и задачи',
    codex: 'Codex (ChatGPT) сверяет два черновика слово за словом и пишет чистый текст, краткое содержание, решения и задачи',
    openai: 'Локальная модель сверяет два черновика слово за словом и пишет чистый текст, краткое содержание, решения и задачи',
    none: 'Без редактора: итог — черновик GigaAM с заменами из словаря' }[a.models.editor] || '';
  // суть — два независимых распознавателя: Whisper показываем всегда, даже если он ещё не скачан
  const steps = [
    ['Запись', 'микрофон и звук компьютера; звук никуда не уходит'],
    ['GigaAM v3 (Сбер)', 'первый черновик: лучше всех понимает русскую речь'],
    [`Whisper ${a.models.whisper || ''} (OpenAI)`.replace('  ', ' '), 'второй, независимый черновик: английские слова, имена, термины' +
      (a.models.whisper ? '' : ' — пока не скачан: Настройки → «Модели и дополнения»')],
    ['pyannote и WeSpeaker', 'делят разговор по голосам и узнают знакомых людей'],
    ['Редактура', editor],
    ['Итог', 'Word и HTML в папке записи, задачи — по проектам'],
  ];
  $('#about').innerHTML = `
    <div class="about-head"><img class="logo" src="/static/icon.svg" alt=""><div>
      <div><b translate="no">Qamyal</b> <span class="muted">— говори благое</span></div>
      <div class="muted small"><span>версия от</span> <span translate="no">${esc(a.version)}</span> · <span translate="no">${esc(m.os)}</span></div></div></div>
    <p class="purpose">Qamyal записывает рабочие разговоры — созвоны в Skype, Zoom, Телемосте и встречи вживую — и превращает их в текст: кто что сказал, краткое содержание, решения и задачи по проектам. Можно спросить что угодно по всем записям сразу или попросить письмо участникам.</p>
    <h3>В цифрах</h3>
    <div class="ab-tiles">
      ${tile(num(s.jobs), plural(s.jobs, 'запись', 'записи', 'записей'))}
      ${tile(esc(fmtDur(s.hours * 3600)), 'записано')}
      ${tile(num(s.words), plural(s.words, 'слово расшифровано', 'слова расшифровано', 'слов расшифровано'))}
      ${tile(esc(fmtDur(s.work_hours * 3600)), 'компьютер расшифровывал')}
      ${tile(num(s.voices), plural(s.voices, 'голос узнаёт', 'голоса узнаёт', 'голосов узнаёт'))}
      ${tile(`${num(s.tasks_done)} / ${num(s.tasks)}`, 'задач выполнено')}
    </div>
    <ul class="facts">
      ${days ? `<li><span>Первая запись:</span> <b translate="no">${new Date(s.first * 1000).toLocaleDateString('ru-RU')}</b>
        <span class="muted">${days} ${plural(days, 'день назад', 'дня назад', 'дней назад')}</span></li>` : ''}
      ${s.words >= 250 ? `<li><span>Весь расшифрованный текст — примерно как книга на</span> <b>${num(s.words / 250)}</b>
        <span>${plural(Math.round(s.words / 250), 'страницу', 'страницы', 'страниц')}</span></li>` : ''}
      ${s.hours > 0.1 && s.work_hours ? `<li><span>На час разговора уходит обработки:</span> <b>${esc(fmtDur(s.work_hours / s.hours * 3600))}</b></li>` : ''}
      ${s.talkers.length ? `<li><span>Больше всех говорят:</span> ${s.talkers.map(t => `<span translate="no">${chip(t.who)}</span> <span class="muted small">${esc(fmtDur(t.sec))}</span>`).join(' ')}</li>` : ''}
      ${s.longest ? `<li><span>Самая длинная запись:</span> <a href="#/job/${s.longest.id}" translate="no">${esc(s.longest.title)}</a> <span class="muted small">${esc(fmtDur(s.longest.duration))}</span></li>` : ''}
    </ul>
    <h3>Как это работает</h3>
    <ol class="steps">${steps.map(([n, w]) => `<li><b>${esc(n)}</b> — <span>${esc(w)}</span></li>`).join('')}</ol>
    <div class="muted small" style="margin-top:8px">Две модели слушают запись независимо и ошибаются в разных местах — сверка двух черновиков даёт итог точнее любой из них. Всё, кроме редактуры, работает прямо на этом компьютере; в редактуру уходит только текст, звук — никогда.</div>
    <h3>Компьютер</h3>
    <div class="small" translate="no">${[m.model, m.chip, m.ram_gb ? m.ram_gb + ' ГБ' : '', m.cores ? m.cores + ' потоков' : '', m.os, 'Python ' + m.python].filter(Boolean).map(esc).join(' · ')}</div>
    <div class="small muted" style="margin-top:4px"><span>Программа:</span> <code translate="no">${esc(a.paths.root)}</code>
      · <span>Записи:</span> <code translate="no">${esc(a.paths.jobs)}</code></div>
    <div class="support"><span>Поддержать автора можно</span> <a href="#" id="support">здесь</a>.</div>`;
  $('#support').onclick = e => {
    e.preventDefault();
    const m = modal(`<div class="support-box">
      <div class="support-mark">${icon('star')}</div>
      <p>Лучшая поддержка — ваше дуа за автора приложения Qamyal и его брата Муслима.</p>
      <button class="btn primary" id="supok">Добро</button></div>`);
    $('#supok', m).onclick = () => m.remove();
  };
}

/** Модели и дополнения: распознавание, Whisper (на выбор из нескольких вариантов), Claude Code.
 *  Что скачивается — расписано у каждого пункта: пользователь видит, что ставит к себе. */
function drawComps(gone) {
  let last = '';
  const mb = n => Math.round(n / 1e6);          // как в подписях размеров: 449 МБ = 449 000 000 байт
  const load = async () => {
    let c;
    try { c = await api('/api/components'); } catch { return; }
    if (gone()) return;
    const js = JSON.stringify(c);
    if (js === last) return;
    last = js;
    // загрузки идут независимо: у каждой своё состояние — «speech», «whisper-small»…
    const J = c.jobs || {}, jobOf = (id, model) => J[id + (model ? '-' + model : '')] || {};
    const running = (id, model) => jobOf(id, model).state === 'running';
    const ready = Object.fromEntries(c.items.map(x => [x.id, x.ready]));
    const wh = $('#wh');
    if (wh) { wh.disabled = !ready.whisper; wh.closest('div').querySelector('.help').textContent = ready.whisper ? 'Лучше английские слова и имена. Без него обработка почти вдвое быстрее.' : 'Whisper не скачан — его можно скачать выше.'; }
    const box = $('#comps');
    box.hidden = false;
    const progress = job => {
      const pct = job.total ? Math.min(100, Math.round(job.done * 100 / job.total)) : 0;
      return `<div class="dl"><div class="small">${esc(job.step || 'Начинаю…')}${job.total ? ` · ${mb(job.done)} из ${mb(job.total)} МБ` : ''}</div>
        <div class="bar${job.total ? '' : ' busy'}"><i style="width:${job.total ? pct : 100}%"></i></div></div>`;
    };
    // «Скачать» — стрелка вниз (к себе на компьютер), под кнопкой — сколько скачается
    const getBtn = (attrs, resume, size) =>
      `<button class="btn sm primary" ${attrs}>${icon('download')}${resume ? 'Продолжить' : 'Скачать'}</button>` +
      (size ? `<div class="dlsize">${esc(size)}</div>` : '');
    const failed = (id, model) => jobOf(id, model).state === 'error';
    const errLine = (id, model) => failed(id, model) ? `<div class="help err" style="color:var(--rec)">${esc(jobOf(id, model).error)}</div>` : '';
    const variant = v => {
      let right;
      if (running('whisper', v.key)) right = progress(jobOf('whisper', v.key));
      else if (v.active && v.downloaded) right = `<span class="ok">${icon('check')}Установлено</span>`;
      else if (v.downloaded) right = `<button class="btn sm" data-use="${v.key}">Использовать</button>` +
        (v.deletable ? ` <button class="btn sm ghost danger" data-del="${v.key}" title="Удалить с компьютера">${icon('trash')}Удалить</button>` : '');
      else right = getBtn(`data-get="whisper" data-model="${v.key}"`, failed('whisper', v.key), v.size);
      return `<tr class="${v.best ? 'best' : ''}"><td class="nowrap"><b translate="no">${esc(v.key)}</b>${v.best ? '<div><span class="need">советуем</span></div>' : ''}</td>
        <td><i class="what">${esc(v.what)}</i>${errLine('whisper', v.key)}</td><td class="comp-r">${right}</td></tr>`;
    };
    const variants = x => {
      const a = x.advice || {}, m = a.machine || {};
      const pc = [m.model, m.chip].filter(Boolean).map(s => `<span translate="no">${esc(s)}</span>`).join(', ');
      return `<table class="vt"><tbody>${x.variants.map(variant).join('')}</tbody></table>
        ${a.key ? `<div class="advice tip">${icon('screen')}<div><span>Ваш компьютер:</span> ${pc}${m.ram_gb ? `, <span>${m.ram_gb} ГБ памяти</span>` : ''}.<br>
          <span>Советуем:</span> <b translate="no">${esc(a.key)}</b> — <span>${esc(a.why)}</span>.</div></div>` : ''}`;
    };
    const row = x => {
      let right = '';
      if (x.variants) right = '';
      else if (x.ready) right = `<span class="ok">${icon('check')}Установлено</span>`;
      else if (running(x.id)) right = progress(jobOf(x.id));
      else if (x.id === 'claude' || x.id === 'codex') right = `<button class="btn sm" data-get="${x.id}">${icon('spark')}Установить</button>`;
      else if (x.id === 'browser') right = `<button class="btn sm primary" data-ext="1">${icon('screen')}Установить</button>`;
      else right = getBtn(`data-get="${x.id}"`, failed(x.id), x.size);
      return `<div class="comp"><div><b class="ctitle">${esc(x.title)}</b>${x.need ? ' <span class="need">нужно</span>' : ''}
        <div class="help">${esc(x.about)}</div>
        <ul class="parts">${(x.parts || []).map(p => `<li><b>${esc(p.name)}</b> — <i>${esc(p.what)}</i>
          <span class="src">${p.size ? `<span>${esc(p.size)}</span> · ` : ''}<span translate="no">${esc(p.from)}</span></span></li>`).join('')}</ul>
        ${x.note ? `<div class="comp-note tip">${esc(x.note)}</div>` : ''}${x.ready ? '' : errLine(x.id)}</div>
        <div class="comp-r">${right}</div>
        ${x.variants ? `<div class="variants">${variants(x)}</div>` : ''}</div>`;
    };
    box.innerHTML = `<h2>Модели и дополнения</h2>
      <div class="muted small tip" style="margin-bottom:6px">Модели распознавания работают прямо на этом компьютере — записи никуда не уходят. Загрузку можно оставить: она идёт, даже если закрыть окно.</div>
      ${c.items.map(row).join('')}`;
    const act = async (b, path, data, after) => {
      b.disabled = true;
      try { await api(path, data); if (after) after(); last = ''; load(); } catch (e) { b.disabled = false; fail(e); }
    };
    $$('#comps [data-get]').forEach(b => b.onclick = () => act(b, '/api/components/' + b.dataset.get, { model: b.dataset.model || '' },
      b.dataset.get === 'claude' ? () => toast('Откроется Терминал: установка Claude Code, затем вход в ваш аккаунт Claude')
        : b.dataset.get === 'codex' ? () => toast('Откроется Терминал: установка Codex, затем вход в ваш аккаунт ChatGPT') : null));
    // Chrome не даёт другим программам открыть chrome://extensions (вместо неё — пустое окно),
    // поэтому только шаги и кнопки «Копировать»
    $$('#comps [data-ext]').forEach(b => b.onclick = () => {
      const folder = (c.items.find(x => x.id === 'browser') || {}).folder || '';
      const mac = /Mac/.test(navigator.userAgent);
      const copyBtn = text => `<button class="btn sm ghost" data-copy="${esc(text)}">${icon('copy')}Копировать</button>`;
      const m = modal(`<h2>Расширение для Chrome</h2>
        <p class="muted">Ставится один раз, вручную: Chrome не даёт программам открывать свою страницу расширений.</p>
        <ol class="ext-steps">
          <li>Откройте Chrome, вставьте в адресную строку <code translate="no">chrome://extensions</code> и нажмите Enter. ${copyBtn('chrome://extensions')}</li>
          <li>В Chrome справа вверху включите <b>«Режим разработчика»</b>.</li>
          <li>Нажмите <b>«Загрузить распакованное расширение»</b> и выберите папку
            <div class="ext-path"><code translate="no">${esc(folder)}</code>${copyBtn(folder)}</div><div class="muted small">${mac ? 'В окне выбора нажмите ⌘⇧G и вставьте путь.' : 'Путь можно вставить в поле «Папка» внизу окна выбора.'}</div></li>
        </ol>
        <p class="muted small">Готово, когда здесь у расширения появится «Установлено». В созвоне выберите в Диктофоне «Созвон» и сервис.</p>
        <div style="text-align:right"><button class="btn primary" id="extok">Понятно</button></div>`);
      $$('[data-copy]', m).forEach(x => x.onclick = () => navigator.clipboard.writeText(x.dataset.copy).then(() => toast('Скопировано')));
      $('#extok', m).onclick = () => m.remove();
    });
    $$('#comps [data-use]').forEach(b => b.onclick = () => act(b, '/api/components/whisper/use', { model: b.dataset.use },
      () => toast('Whisper ' + b.dataset.use + ' — для следующих записей')));
    $$('#comps [data-del]').forEach(b => b.onclick = () => {
      if (confirm(`Удалить Whisper ${b.dataset.del} с компьютера? Его можно будет скачать снова.`)) act(b, '/api/components/whisper/delete', { model: b.dataset.del });
    });
  };
  load();
  every(1500, load);
}

/* ---------- старт ---------- */
api('/api/voices').then(r => { window.VOICE_NAMES = r.voices.map(v => v.name); }).catch(() => {});
Promise.all([loadColors(), pollState()]).then(route).then(() => { if (ST && ST.user === '') welcome(); });
api('/api/update').then(markUpdate).catch(() => {});

/** Первый запуск (имя ещё не задано — так ставит приложение для Mac): знакомимся и ведём к моделям. */
function welcome() {
  const m = modal(`<div class="welcome">
    <img class="logo" src="/static/icon.svg" alt="">
    <h2>Добро пожаловать в Qamyal</h2>
    <p class="muted">Как вас зовут? Так вы будете подписаны в записях и задачах.</p>
    <input class="input" id="wname" placeholder="Имя" autofocus>
    <button class="btn primary" id="wgo" disabled>Дальше</button></div>`, true);   // без имени не закрываем
  const inp = $('#wname', m), go = $('#wgo', m);
  inp.oninput = () => { go.disabled = !inp.value.trim(); };
  inp.onkeydown = e => { if (e.key === 'Enter' && !go.disabled) go.click(); };
  go.onclick = async () => {
    try { await api('/api/settings', { user_name: inp.value.trim() }); } catch (e) { return fail(e); }
    m.remove();
    pollState();
    if (ST && ST.speech === false) {
      location.hash = '#/settings';
      toast('Осталось скачать распознавание речи — кнопка «Скачать» в «Моделях и дополнениях»');
    }
  };
  setTimeout(() => inp.focus(), 50);
}

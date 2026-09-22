// app.js - the Jeeves cockpit. Every ability is a panel you can drag, dock, tab,
// close, re-open (+ Panel) and pop out into its own window (the square button).
// Your layout is saved in this browser and comes back next time.
//
// One lesson from the original is built in: a panel's content is wired up when
// the panel MOUNTS, never at page load. The original's Status panel looked for
// its box before the layout had built it, and stayed empty.
import { createDockview } from '/static/vendor/dockview/dockview-core.esm.min.js';

const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const api = async (p) => { const r = await fetch(p); return r.json(); };
const fmt = n => { n = +n || 0; if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B'; if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'; if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k'; return '' + n; };
let CFG = { name: 'Jeeves', models: { best: 'opus', deep: 'sonnet', fast: 'haiku' } };
let orbTop = null, orbBig = null;

// ------------------------------------------------------------------ markdown
// A small, safe renderer: everything is escaped first, so a note can never run code.
function inline(s) {
  s = esc(s);
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  s = s.replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<i>$2</i>');
  s = s.replace(/(^|\s)_([^_\s][^_]*)_(?=\s|$|[.,;:!?])/g, '$1<i>$2</i>');
  s = s.replace(/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g, (m, a, b) => `<span class="wl" data-note="${a}">${b || a}</span>`);
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  return s;
}
function md(text) {
  text = String(text || '').replace(/\r/g, '');
  if (text.startsWith('---\n')) { const e = text.indexOf('\n---', 4); if (e > 0) text = text.slice(text.indexOf('\n', e + 1) + 1); }
  const L = text.split('\n'), out = [];
  let i = 0;
  while (i < L.length) {
    let l = L[i];
    if (/^```/.test(l)) { const buf = []; i++; while (i < L.length && !/^```/.test(L[i])) buf.push(L[i++]); i++; out.push('<pre>' + esc(buf.join('\n')) + '</pre>'); continue; }
    let m = l.match(/^(#{1,4})\s+(.*)$/);
    if (m) { out.push(`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`); i++; continue; }
    if (/^\s*\|.*\|\s*$/.test(l) && i + 1 < L.length && /^\s*\|[\s:|-]+\|\s*$/.test(L[i + 1])) {
      const row = r => r.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
      const h = row(l); i += 2; const rows = [];
      while (i < L.length && /^\s*\|.*\|\s*$/.test(L[i])) rows.push(row(L[i++]));
      out.push('<table><tr>' + h.map(c => '<th>' + inline(c) + '</th>').join('') + '</tr>' + rows.map(r => '<tr>' + r.map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>').join('') + '</table>');
      continue;
    }
    if (/^\s*[-*]\s+/.test(l)) {
      const items = [];
      while (i < L.length && /^\s*[-*]\s+/.test(L[i])) {
        let t = L[i].replace(/^\s*[-*]\s+/, ''); let cls = '';
        const tm = t.match(/^\[( |x|X)\]\s*(.*)$/);
        if (tm) { cls = ' class="task"'; t = (tm[1] === ' ' ? '☐ ' : '☑ ') + tm[2]; }
        items.push(`<li${cls}>` + inline(t) + '</li>'); i++;
      }
      out.push('<ul>' + items.join('') + '</ul>'); continue;
    }
    if (/^\s*\d+\.\s+/.test(l)) {
      const items = [];
      while (i < L.length && /^\s*\d+\.\s+/.test(L[i])) items.push('<li>' + inline(L[i++].replace(/^\s*\d+\.\s+/, '')) + '</li>');
      out.push('<ol>' + items.join('') + '</ol>'); continue;
    }
    if (/^>\s?/.test(l)) { const buf = []; while (i < L.length && /^>\s?/.test(L[i])) buf.push(L[i++].replace(/^>\s?/, '')); out.push('<blockquote>' + inline(buf.join(' ')) + '</blockquote>'); continue; }
    if (/^\s*(---|\*\*\*)\s*$/.test(l)) { out.push('<hr>'); i++; continue; }
    if (!l.trim()) { i++; continue; }
    const buf = [];
    while (i < L.length && L[i].trim() && !/^(#{1,4}\s|```|\s*[-*]\s|\s*\d+\.\s|>|\s*\|)/.test(L[i])) buf.push(L[i++]);
    if (!buf.length) buf.push(L[i++]);
    out.push('<p>' + inline(buf.join(' ')) + '</p>');
  }
  return '<div class="md">' + out.join('\n') + '</div>';
}

// ------------------------------------------------------------------ panel shell
function shell(hint, bodyClass = '') {
  const d = document.createElement('div');
  d.className = 'pane';
  d.innerHTML = `<div class="ptools"><span class="hint">${esc(hint)}</span><button class="refresh" title="Refresh">↻</button><button class="pop" title="Pop out into its own window">⧉</button></div><div class="pbody ${bodyClass}"></div>`;
  return d;
}
function wire(el, name, refresh) {
  el.querySelector('.refresh').onclick = refresh;
  el.querySelector('.pop').onclick = () => popout(name);
  el.__refresh = refresh;
  refresh();
}
function popout(name) {
  window.open(location.origin + '/?only=' + encodeURIComponent(name), 'jeeves-' + name, 'width=1100,height=800');
}
function setStatus(t) { const s = $('#status-line'); if (s) s.textContent = t; }

// ------------------------------------------------------------------ Chat
const SESSION = 'main';
function chatPanel() {
  const d = document.createElement('div');
  d.className = 'pane';
  d.innerHTML = `
    <div class="ptools"><span class="hint">Answered by your own Claude Code, working in your second brain</span>
      <button class="newchat" title="Start a fresh conversation">New conversation</button><button class="pop" title="Pop out">⧉</button></div>
    <div class="chat">
      <div class="chat-head"><div class="orb-big"><svg class="orb-svg"></svg></div>
        <div><div class="who">${esc(CFG.name)}</div><div class="sub">Ask about anything in your notes or your CRM. It can read all of it. Whether it may change files is your choice, set in config.json.</div></div></div>
      <div class="chips"></div>
      <div class="log"></div>
      <div class="composer"><textarea rows="1" placeholder="Ask ${esc(CFG.name)}… (Enter to send, Shift+Enter for a new line)"></textarea>
        <button class="btn send">Send</button><button class="btn ghost stop" style="display:none">Stop</button></div>
    </div>`;
  return d;
}
function mountChat(el) {
  el.querySelector('.pop').onclick = () => popout('chat');
  const log = $('.log', el), ta = $('textarea', el), send = $('.send', el), stopb = $('.stop', el);
  if (window.JeevesOrb && !orbBig) orbBig = window.JeevesOrb($('.orb-svg', el), CFG.orb || {});
  const chips = ['What needs me today?', 'Who in my CRM should I speak to first, and why?', 'Summarise what moved in my second brain this week', 'Which of my agents should I use to write a follow-up?'];
  $('.chips', el).innerHTML = chips.map(c => `<span class="chip">${esc(c)}</span>`).join('');
  $('.chips', el).onclick = e => { if (e.target.classList.contains('chip')) { ta.value = e.target.textContent; ta.focus(); } };
  $('.newchat', el).onclick = async () => {
    await fetch('/api/chat/new', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session: SESSION }) });
    log.innerHTML = ''; setStatus('New conversation.');
  };
  const add = (cls, html) => { const m = document.createElement('div'); m.className = cls; m.innerHTML = html; log.appendChild(m); log.scrollTop = log.scrollHeight; return m; };
  const orbs = s => { [orbTop, orbBig].forEach(o => o && o.setState(s)); };
  async function go() {
    const text = ta.value.trim(); if (!text) return;
    ta.value = ''; add('msg you', esc(text));
    const bot = add('msg bot', '<span class="dim">Thinking…</span>');
    let acc = '', gotText = false;
    orbs('thinking'); setStatus('Working on it…'); send.disabled = true; stopb.style.display = '';
    try {
      const r = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, model: $('#model').value, session: SESSION }) });
      const rd = r.body.getReader(), dec = new TextDecoder(); let buf = '';
      for (;;) {
        const { value, done } = await rd.read(); if (done) break;
        buf += dec.decode(value, { stream: true });
        let k;
        while ((k = buf.indexOf('\n\n')) >= 0) {
          const chunk = buf.slice(0, k); buf = buf.slice(k + 2);
          if (!chunk.startsWith('data: ')) continue;
          let ev; try { ev = JSON.parse(chunk.slice(6)); } catch (e) { continue; }
          if (ev.type === 'delta') { if (!gotText) { orbs('speaking'); gotText = true; } acc += ev.text; bot.innerHTML = md(acc); }
          else if (ev.type === 'activity') { const a = document.createElement('div'); a.className = 'act'; a.textContent = ev.text; log.insertBefore(a, bot); setStatus(ev.text); }
          else if (ev.type === 'done') { if (ev.text) { acc = ev.text; bot.innerHTML = md(acc); } }
          else if (ev.type === 'error') { add('msg err', esc(ev.text)); }
          log.scrollTop = log.scrollHeight;
        }
      }
      if (!acc) bot.innerHTML = '<span class="dim">(no reply)</span>';
    } catch (e) { add('msg err', 'Lost the connection to Jeeves: ' + esc(e)); }
    orbs('idle'); setStatus('Ready.'); send.disabled = false; stopb.style.display = 'none';
  }
  send.onclick = go;
  stopb.onclick = () => fetch('/api/chat/stop', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session: SESSION }) });
  ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); go(); } });
  ta.addEventListener('input', () => { ta.style.height = 'auto'; ta.style.height = Math.min(160, ta.scrollHeight) + 'px'; });
  window.__jeevesAsk = (t) => { ta.value = t; ta.focus(); };
}

// ------------------------------------------------------------------ Today
async function renderToday(body) {
  const d = await api('/api/today');
  let h = '';
  if (d.crm) {
    h += `<div class="card"><h3>From your CRM${d.crm.built ? ' · built ' + esc(d.crm.built) : ''}</h3>`;
    h += d.crm.found ? md(d.crm.text) : `<div class="empty">${esc(d.crm.hint)}</div>`;
    h += '</div>';
  } else h += '<div class="empty">No CRM folder is set in config.json, so there is no ranked list of people here.</div>';
  const b = d.brain;
  if (b) {
    h += '<div class="card"><h3>From your second brain</h3>';
    if (b.daily) h += `<div class="dim">${esc(b.daily.path)}</div>` + md(b.daily.text);
    if (b.moved.length) h += '<div class="muted" style="margin-top:6px">Moved in the last 3 days</div><ul>' + b.moved.map(m => `<li><span class="dim">${esc(m.when)}</span> <span class="wl" data-note="${esc(m.path)}">${esc(m.path)}</span></li>`).join('') + '</ul>';
    if (b.open.length) h += '<div class="muted" style="margin-top:6px">Left unfinished</div><ul>' + b.open.map(o => `<li>☐ ${inline(o.text)} <span class="dim">· ${esc(o.path)}</span></li>`).join('') + '</ul>';
    if (!b.daily && !b.moved.length && !b.open.length) h += '<div class="empty">Nothing has moved and nothing is left open. That is a real answer, not an empty one.</div>';
    h += '</div>';
  }
  body.innerHTML = h;
}

// ------------------------------------------------------------------ Vault browser
function vaultPanel() {
  const d = shell('Read-only. Click a note to open it; [[links]] inside a note open too.', 'flush');
  d.querySelector('.pbody').innerHTML = `<div class="vb"><div class="vb-side"><div class="vb-tabs"></div>
    <input type="search" placeholder="Filter this vault, or press Enter to search both…"><div class="vb-list"></div></div><div class="vb-note"><div class="empty">Pick a note on the left.</div></div></div>`;
  return d;
}
const VB = { key: 'brain', files: [], el: null };
async function openNote(key, path) {
  const el = VB.el; if (!el) return;
  const d = await api(`/api/vault/file?v=${encodeURIComponent(key)}&p=${encodeURIComponent(path)}`);
  const note = $('.vb-note', el);
  if (d.error) { note.innerHTML = `<div class="empty">${esc(d.error)}</div>`; return; }
  note.innerHTML = `<div class="vb-path">${esc(key === 'crm' ? 'CRM' : 'Second brain')} / ${esc(path)}</div>` + md(d.text);
  el.querySelectorAll('.vb-file').forEach(f => f.classList.toggle('on', f.dataset.p === path));
}
function findNote(name) {
  const n = name.toLowerCase().replace(/\.md$/, '');
  return VB.files.find(f => f.path.toLowerCase() === n + '.md' || f.path.toLowerCase().endsWith('/' + n + '.md'));
}
async function mountVault(el) {
  VB.el = el;
  const tabs = $('.vb-tabs', el), list = $('.vb-list', el), q = $('input', el);
  const vs = await api('/api/vaults');
  tabs.innerHTML = vs.map(v => `<button data-k="${esc(v.key)}" title="${esc(v.path)}">${esc(v.label)}${v.exists ? '' : ' (missing)'}</button>`).join('') || '<div class="empty">No vaults set in config.json.</div>';
  const draw = () => {
    const f = q.value.trim().toLowerCase();
    let last = null, h = '';
    VB.files.filter(x => !f || x.path.toLowerCase().includes(f)).slice(0, 1500).forEach(x => {
      const dir = x.path.includes('/') ? x.path.slice(0, x.path.lastIndexOf('/')) : '(top level)';
      if (dir !== last) { h += `<div class="vb-dir">${esc(dir)}</div>`; last = dir; }
      h += `<div class="vb-file" data-p="${esc(x.path)}">${esc(x.path.split('/').pop().replace(/\.md$/, ''))}</div>`;
    });
    list.innerHTML = h || '<div class="empty" style="margin:8px">No notes match.</div>';
  };
  const load = async (key) => {
    VB.key = key;
    tabs.querySelectorAll('button').forEach(b => b.classList.toggle('on', b.dataset.k === key));
    const t = await api('/api/vault/tree?v=' + encodeURIComponent(key));
    VB.files = t.files || [];
    if (t.exists === false) list.innerHTML = '<div class="empty" style="margin:8px">That folder does not exist. Check the path in config.json.</div>'; else draw();
  };
  tabs.onclick = e => { const b = e.target.closest('button'); if (b) load(b.dataset.k); };
  list.onclick = e => { const f = e.target.closest('.vb-file'); if (f) openNote(VB.key, f.dataset.p); const h = e.target.closest('.vb-hit'); if (h) { load(h.dataset.k).then(() => openNote(h.dataset.k, h.dataset.p)); } };
  q.oninput = draw;
  q.onkeydown = async e => {
    if (e.key !== 'Enter') return;
    const r = await api('/api/vault/search?q=' + encodeURIComponent(q.value));
    list.innerHTML = (r.hits || []).map(x => `<div class="vb-hit" data-k="${esc(x.key)}" data-p="${esc(x.path)}"><b>${esc(x.path)}</b> <span class="pill">${esc(x.label)}</span><small>${esc(x.snippet)}</small></div>`).join('') || '<div class="empty" style="margin:8px">Nothing found in either vault.</div>';
  };
  el.querySelector('.refresh').onclick = () => load(VB.key);
  el.querySelector('.pop').onclick = () => popout('vaults');
  if (vs.length) await load(vs[0].key);
}
// Clicking a [[link]] anywhere opens it in the vault browser.
document.addEventListener('click', async e => {
  const w = e.target.closest('.wl'); if (!w || !dock) return;
  openPanel('vaults');
  setTimeout(async () => {
    let f = findNote(w.dataset.note);
    if (!f && VB.key !== 'brain') { VB.key = 'brain'; }
    if (f) openNote(VB.key, f.path); else openNote(VB.key, w.dataset.note.endsWith('.md') ? w.dataset.note : w.dataset.note + '.md');
  }, 150);
});

// ------------------------------------------------------------------ Agents
async function renderAgents(body) {
  const d = await api('/api/agents');
  const looked = d.folders.map(f => `<span class="pill ${f.exists ? 'up' : ''}" title="${esc(f.path)}">${esc(f.label)}${f.exists ? '' : ' · none'}</span>`).join('');
  if (!d.agents.length) { body.innerHTML = `<div class="empty">No agents found yet. Looked in: ${looked}<br>An agent is a markdown file in one of those folders.</div>`; return; }
  body.innerHTML = `<div class="dim" style="margin-bottom:8px">${d.agents.length} agents · looked in ${looked}</div><div class="agents">` + d.agents.map(a => `
    <div class="agent"><div class="an">${esc(a.name)}</div><div class="ad" title="Click to read it all">${esc(a.description || 'No description written.')}</div>
      <div class="foot"><span class="pill">${esc(a.where)}</span>${a.model ? `<span class="pill">${esc(a.model)}</span>` : ''}<span style="flex:1"></span><button class="btn small ask" data-n="${esc(a.name)}">Ask in chat</button></div></div>`).join('') + '</div>';
  body.onclick = e => {
    const ad = e.target.closest('.ad'); if (ad) ad.classList.toggle('open');
    const b = e.target.closest('.ask'); if (b) { openPanel('chat'); setTimeout(() => window.__jeevesAsk && window.__jeevesAsk(`Use the ${b.dataset.n} agent to `), 120); }
  };
}

// ------------------------------------------------------------------ Activity
async function renderActivity(body) {
  const d = await api('/api/activity');
  if (!d.sessions.length) { body.innerHTML = '<div class="empty">No Claude Code conversations in the last 7 days were found.</div>'; return; }
  body.innerHTML = `<div class="dim" style="margin-bottom:6px">${d.total_sessions} conversations in the last ${d.days} days · newest first</div>
    <table class="t"><tr><th>When</th><th>Folder</th><th>What it was</th><th>Turns</th><th>Tokens</th></tr>` +
    d.sessions.map(s => `<tr><td class="dim">${esc(s.last)}</td><td title="${esc(s.folder)}">${esc(s.folder_name)}</td><td>${esc(s.title || '(untitled)')}<div class="dim">${esc(s.models.join(', '))}${s.minutes ? ' · ' + s.minutes + ' min' : ''}</div></td><td class="n">${s.turns}</td><td class="n">${fmt(s.tokens)}</td></tr>`).join('') + '</table>';
}

// ------------------------------------------------------------------ Tokens
async function renderTokens(body) {
  const d = await api('/api/tokens');
  const t = d.today, tot = t.total || 1;
  const row = (label, n) => `<div class="kv"><span class="muted">${label}</span><b>${fmt(n)}</b></div><div class="bar"><i style="width:${(100 * n / tot).toFixed(1)}%"></i></div>`;
  let h = `<div class="card"><h3>Today · ${esc(d.date)}</h3><div class="big">${fmt(t.total)}</div><div class="dim" style="margin-bottom:8px">tokens across ${d.sessions_today} conversation(s)</div>
    ${row('Re-read from memory (cache read)', t.cache_read)}${row('Written to memory (cache write)', t.cache_write)}${row('Written by Claude (output)', t.output)}${row('New input', t.input)}</div>`;
  const bm = Object.entries(d.by_model || {});
  if (bm.length) h += '<div class="card"><h3>By model, today</h3><div class="kv">' + bm.map(([m, v]) => `<span class="muted">${esc(m)}</span><b>${fmt(v.total)}</b>`).join('') + '</div></div>';
  h += `<div class="card"><h3>Last 5 hours</h3><div class="kv"><span class="muted">All tokens</span><b>${fmt(d.last_5_hours.total)}</b></div></div>`;
  const c = d.ccusage || {};
  h += '<div class="card"><h3>Your 5-hour usage window (ccusage)</h3>';
  if (!c.available) h += `<div class="muted">${esc(c.reason || 'not available')}</div>`;
  else if (!c.active) h += '<div class="muted">No window is open right now.</div>';
  else h += `<div class="kv"><span class="muted">Tokens in this window</span><b>${fmt(c.tokens)}</b><span class="muted">Window ends</span><b>${esc(new Date(c.end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))}</b><span class="muted">Minutes left</span><b>${esc(c.remaining_minutes ?? '?')}</b></div>`;
  h += '</div><div class="dim">Most tokens are cache reads: Claude re-reading the conversation so far. They count towards your limits but are the cheapest kind.</div>';
  body.innerHTML = h;
}

// ------------------------------------------------------------------ Inbox
async function renderInbox(body) {
  const d = await api('/api/inbox');
  body.innerHTML = d.found ? `<div class="dim">${esc(d.path)}</div>` + md(d.text)
    : `<div class="empty">${esc(d.hint || 'No recommendations file.')}</div>`;
}

// ------------------------------------------------------------------ Embedded apps
function appPanel(name) {
  const d = shell(name === 'board' ? 'Your work board (ProjectForge)' : 'FleetView: every agent session on one screen', 'flush');
  return d;
}
async function mountApp(el, name) {
  const key = name === 'board' ? 'projectforge' : 'fleetview';
  const title = name === 'board' ? 'ProjectForge' : 'FleetView';
  const body = el.querySelector('.pbody');
  const draw = async () => {
    body.innerHTML = '<div style="padding:14px" class="dim">Checking whether ' + esc(title) + ' is running…</div>';
    const st = (await api('/api/apps'))[key] || {};
    if (st.up) {
      // Load the page only once the panel has real height: an app that starts
      // inside a hidden, zero-size panel can paint blank and stay blank.
      body.innerHTML = '<iframe class="appframe"></iframe>';
      const fr = body.querySelector('iframe');
      const load = () => { if (fr.clientHeight > 0 && !fr.src) { fr.src = st.url; return true; } return false; };
      if (!load()) { const ro = new ResizeObserver(() => { if (load()) ro.disconnect(); }); ro.observe(fr); }
      el.querySelector('.hint').innerHTML = `${esc(title)} · <a href="${esc(st.url)}" target="_blank" rel="noopener">open in its own tab</a>`;
    } else {
      body.innerHTML = `<div style="padding:14px"><div class="empty"><b>${esc(title)} is not running on this computer.</b><br>
        Nothing answered at <code>${esc(st.url || '(no address set)')}</code>.<br><br>
        If you have not installed it yet, here is the link: <a href="${esc(st.repo)}" target="_blank" rel="noopener">${esc(st.repo)}</a><br>
        If you have, start it, then press ↻ above. The address lives in <code>config.json</code> under <code>apps</code>.</div></div>`;
    }
  };
  el.querySelector('.refresh').onclick = draw;
  el.querySelector('.pop').onclick = () => popout(name);
  draw();
}

// ------------------------------------------------------------------ Across everything
async function renderOverview(body) {
  const [td, act, tok, ag, ap, ib] = await Promise.all(['/api/today', '/api/activity', '/api/tokens', '/api/agents', '/api/apps', '/api/inbox'].map(p => api(p).catch(() => ({}))));
  const crmRows = [];
  if (td.crm && td.crm.found) td.crm.text.split('\n').forEach(l => { const m = l.match(/^\|\s*(\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|/); if (m) crmRows.push({ who: m[2].trim(), why: m[3].trim() }); });
  const inboxItems = ib.found ? ib.text.split('\n').filter(l => /^\s*[-*]\s+/.test(l)).slice(0, 4).map(l => l.replace(/^\s*[-*]\s+(\[.\]\s*)?/, '')) : [];
  const today = (act.sessions || []).filter(s => new Date(s.last_ts * 1000).toDateString() === new Date().toDateString());
  const card = (t, inner) => `<div class="card"><h3>${t}</h3>${inner}</div>`;
  body.innerHTML = '<div class="ov">' +
    card('People to speak to', crmRows.length ? '<ul>' + crmRows.slice(0, 4).map(r => `<li><b>${inline(r.who)}</b> <span class="muted">· ${inline(r.why)}</span></li>`).join('') + '</ul>' + (crmRows.length > 4 ? `<div class="dim">and ${crmRows.length - 4} more in Today</div>` : '') : '<div class="muted">Nobody is waiting on you in the CRM.</div>') +
    card('Waiting for your decision', inboxItems.length ? '<ul>' + inboxItems.map(x => `<li>${inline(x)}</li>`).join('') + '</ul>' : '<div class="muted">The recommendations file is empty or missing.</div>') +
    card('Your second brain', td.brain ? `<div class="kv"><span class="muted">Notes moved (3 days)</span><b>${td.brain.moved.length}</b><span class="muted">Left unfinished</span><b>${td.brain.open.length}</b><span class="muted">Daily note today</span><b>${td.brain.daily ? 'yes' : 'no'}</b></div>` : '<div class="muted">Not set.</div>') +
    card('Claude today', `<div class="kv"><span class="muted">Conversations</span><b>${today.length}</b><span class="muted">Tokens</span><b>${fmt(tok.today && tok.today.total)}</b><span class="muted">Agents you have</span><b>${(ag.agents || []).length}</b></div>` + (today[0] ? `<div class="dim" style="margin-top:6px">Latest: ${esc(today[0].title || today[0].folder_name)}</div>` : '')) +
    card('Your other apps', Object.entries(ap).map(([k, v]) => `<div><span class="pill ${v.up ? 'up' : 'down'}">${v.up ? 'running' : 'not running'}</span> ${k === 'projectforge' ? 'Work board (ProjectForge)' : k === 'fleetview' ? 'FleetView' : esc(k)}</div>`).join('') || '<div class="muted">None set.</div>') +
    '</div>';
}

// ------------------------------------------------------------------ the dock
const PANELS = {
  chat:     { title: 'Chat',               make: chatPanel, mount: el => mountChat(el) },
  overview: { title: 'Across everything',  make: () => shell('What is moving across your CRM, notes, agents and apps'), render: renderOverview },
  today:    { title: 'Today',              make: () => shell('Your CRM’s Today.md and your second brain’s day'), render: renderToday },
  inbox:    { title: 'Recommendations',    make: () => shell('A markdown file in your second brain that you and your agents write to'), render: renderInbox },
  vaults:   { title: 'Vaults',             make: vaultPanel, mount: el => mountVault(el) },
  agents:   { title: 'Agents',             make: () => shell('Your Claude Code agents and what each one is for'), render: renderAgents },
  activity: { title: 'Activity',           make: () => shell('Recent Claude Code conversations, from its own log files'), render: renderActivity },
  tokens:   { title: 'Tokens',             make: () => shell('Tokens used today, read from Claude Code’s log files'), render: renderTokens },
  board:    { title: 'Work board',         make: () => appPanel('board'), mount: el => mountApp(el, 'board') },
  fleet:    { title: 'FleetView',          make: () => appPanel('fleet'), mount: el => mountApp(el, 'fleet') },
};
const CACHE = {};
function build(name) {
  if (!CACHE[name]) {
    const p = PANELS[name]; const el = p.make(); el.__mounted = false; CACHE[name] = el;
  }
  return CACHE[name];
}
function mount(name, el) {
  if (el.__mounted) return; el.__mounted = true;
  const p = PANELS[name];
  try {
    if (p.mount) p.mount(el);
    else wire(el, name, () => p.render(el.querySelector('.pbody')).catch(e => { el.querySelector('.pbody').innerHTML = '<div class="empty">Could not load: ' + esc(e) + '</div>'; }));
  } catch (e) { el.querySelector('.pbody') && (el.querySelector('.pbody').innerHTML = '<div class="empty">' + esc(e) + '</div>'); }
}

let dock = null;
function openPanel(name) {
  if (!dock || !PANELS[name]) return;
  const ex = dock.getPanel(name);
  if (ex) { ex.api.setActive(); return; }
  dock.addPanel({ id: name, component: name, title: PANELS[name].title });
}
function defaultLayout() {
  dock.addPanel({ id: 'chat', component: 'chat', title: PANELS.chat.title });
  dock.addPanel({ id: 'today', component: 'today', title: PANELS.today.title, position: { referencePanel: 'chat', direction: 'right' } });
  dock.addPanel({ id: 'inbox', component: 'inbox', title: PANELS.inbox.title, position: { referencePanel: 'today', direction: 'within' }, inactive: true });
  dock.addPanel({ id: 'overview', component: 'overview', title: PANELS.overview.title, position: { referencePanel: 'today', direction: 'right' } });
  dock.addPanel({ id: 'tokens', component: 'tokens', title: PANELS.tokens.title, position: { referencePanel: 'overview', direction: 'below' } });
  dock.addPanel({ id: 'activity', component: 'activity', title: PANELS.activity.title, position: { referencePanel: 'tokens', direction: 'within' }, inactive: true });
  dock.addPanel({ id: 'vaults', component: 'vaults', title: PANELS.vaults.title, position: { referencePanel: 'today', direction: 'below' } });
  dock.addPanel({ id: 'agents', component: 'agents', title: PANELS.agents.title, position: { referencePanel: 'vaults', direction: 'within' }, inactive: true });
  dock.addPanel({ id: 'board', component: 'board', title: PANELS.board.title, position: { referencePanel: 'vaults', direction: 'within' }, inactive: true });
  dock.addPanel({ id: 'fleet', component: 'fleet', title: PANELS.fleet.title, position: { referencePanel: 'vaults', direction: 'within' }, inactive: true });
  try { dock.getPanel('today').api.setActive(); dock.getPanel('vaults').api.setActive(); dock.getPanel('tokens').api.setActive(); } catch (e) {}
}
const LKEY = 'jeeves.layout.v1';

async function start() {
  try { CFG = Object.assign(CFG, await api('/api/config')); } catch (e) {}
  document.title = CFG.name;
  $('#brand-name').textContent = CFG.name;
  $('#today-date').textContent = new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' });
  const sel = $('#model');
  sel.innerHTML = Object.entries(CFG.models || {}).map(([k, v]) => `<option value="${esc(k)}">${esc(k)} · ${esc(v)}</option>`).join('');
  sel.value = CFG.default_model || 'best';
  try { const m = localStorage.getItem('jeeves.model'); if (m && CFG.models[m]) sel.value = m; } catch (e) {}
  sel.onchange = () => { try { localStorage.setItem('jeeves.model', sel.value); } catch (e) {} };
  if (window.JeevesOrb) orbTop = window.JeevesOrb($('#orb-top'), CFG.orb || {});
  if (!CFG.claude_found) setStatus('Claude Code was not found on this computer, so Chat cannot answer. Every other panel works.');

  dock = createDockview($('#dock'), {
    createComponent: (o) => { const element = build(o.name); return { element, init: () => mount(o.name, element) }; },
  });
  const solo = new URLSearchParams(location.search).get('only');
  if (solo && PANELS[solo]) {
    document.body.classList.add('solo');
    document.title = CFG.name + ' · ' + PANELS[solo].title;
    dock.addPanel({ id: solo, component: solo, title: PANELS[solo].title });
  } else {
    let restored = false;
    try { const saved = localStorage.getItem(LKEY); if (saved) { dock.fromJSON(JSON.parse(saved)); restored = dock.panels.length > 0; } } catch (e) { restored = false; }
    if (!restored) { try { dock.clear(); } catch (e) {} defaultLayout(); }
    dock.onDidLayoutChange(() => { try { localStorage.setItem(LKEY, JSON.stringify(dock.toJSON())); } catch (e) {} });
  }

  // + Panel: nothing is ever gone for good.
  const menu = $('#add-menu');
  menu.innerHTML = Object.entries(PANELS).map(([k, p]) => `<div class="row"><button data-open="${k}">+ ${esc(p.title)}</button><button class="pop" data-pop="${k}" title="Pop out">⧉</button></div>`).join('');
  menu.onclick = e => { const o = e.target.dataset.open, p = e.target.dataset.pop; if (o) openPanel(o); if (p) popout(p); menu.classList.remove('open'); e.stopPropagation(); };
  $('#add-btn').onclick = e => { e.stopPropagation(); menu.classList.toggle('open'); };
  document.addEventListener('click', () => menu.classList.remove('open'));
  $('#reset-btn').onclick = () => { try { localStorage.removeItem(LKEY); } catch (e) {} location.reload(); };

  // Reading local files costs no tokens, so the reading panels refresh once a
  // minute while this tab is visible. Nothing here ever starts Claude on a timer.
  setInterval(() => {
    if (document.hidden) return;
    ['today', 'tokens', 'activity', 'overview'].forEach(n => { const el = CACHE[n]; if (el && el.__refresh && el.offsetParent) el.__refresh(); });
  }, 60000);
  window.__jeevesReady = true;
}
start();

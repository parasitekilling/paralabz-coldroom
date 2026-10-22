(() => {
  'use strict';

  const POLL_MS = 1000;
  const FRAME_MS = 250; // ~4 fps, slow and calm: no flashing
  const WINDOW_S = 300;
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const $ = (id) => document.getElementById(id);
  const pageMode = document.body.dataset.mode;

  // The operator token lives ONLY in this variable (memory). It is never
  // written to any browser storage, URL, or page element.
  let operatorToken = '';
  let latest = null;
  let auditEntries = [];
  let tick = 0;
  let reloading = false;

  const fmt = (v) => `${Number(v).toFixed(1)} °C`;
  const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  // ---------------------------------------------------------------- scene
  const sceneCanvas = $('scene');
  const sc = sceneCanvas.getContext('2d');
  sc.imageSmoothingEnabled = false;

  const GLYPHS = {
    '0': ['111', '101', '101', '101', '111'], '1': ['010', '110', '010', '010', '111'],
    '2': ['111', '001', '111', '100', '111'], '3': ['111', '001', '111', '001', '111'],
    '4': ['101', '101', '111', '001', '001'], '5': ['111', '100', '111', '001', '111'],
    '6': ['111', '100', '111', '101', '111'], '7': ['111', '001', '001', '001', '001'],
    '8': ['111', '101', '111', '101', '111'], '9': ['111', '101', '111', '001', '111'],
    '-': ['000', '000', '111', '000', '000'], '.': ['0', '0', '0', '0', '1'],
    'C': ['111', '100', '100', '100', '111'], 'D': ['110', '101', '101', '101', '110'],
    'A': ['010', '101', '111', '101', '101'], '>': ['100', '010', '001', '010', '100'],
  };

  const rect = (x, y, w, h, color) => { sc.fillStyle = color; sc.fillRect(x, y, w, h); };

  function pixelText(str, x, y, color) {
    let cx = x;
    for (const ch of str) {
      const g = GLYPHS[ch];
      if (!g) continue;
      for (let r = 0; r < g.length; r++) {
        for (let c = 0; c < g[r].length; c++) {
          if (g[r][c] === '1') rect(cx + c, y + r, 1, 1, color);
        }
      }
      cx += g[0].length + 1;
    }
  }

  const FROST = (() => {
    const out = [];
    let s = 12345;
    const rnd = () => { s = (Math.imul(s, 1103515245) + 12345) & 0x7fffffff; return s / 0x7fffffff; };
    for (let i = 0; i < 60; i++) out.push([68 + Math.floor(rnd() * 44), 23 + Math.floor(rnd() * 54)]);
    return out;
  })();

  const SHELVES = [
    { y: 37, items: [[70, 8, 8, '#9b5cff'], [80, 6, 6, '#eef0f7'], [88, 10, 11, '#7df3ff'], [100, 9, 7, '#9b5cff']] },
    { y: 51, items: [[70, 10, 8, '#7df3ff'], [82, 7, 11, '#eef0f7'], [91, 8, 6, '#9b5cff'], [101, 9, 9, '#eef0f7']] },
    { y: 65, items: [[70, 12, 9, '#9b5cff'], [84, 9, 7, '#7df3ff'], [95, 14, 10, '#eef0f7']] },
  ];

  function drawScene() {
    const sim = latest ? latest.simulation : null;
    const measured = sim ? sim.measured_c : -18;
    const setpoint = sim ? sim.setpoint_c : -18;
    const on = sim ? sim.compressor_on : false;
    const defrost = sim ? sim.phase === 'defrost' : false;
    const alarm = sim ? sim.alarm.active : false;
    const t = motion.matches ? 0 : tick;

    // wall + floor
    rect(0, 0, 160, 100, '#120d20');
    for (let x = 0; x < 160; x += 20) rect(x, 0, 1, 83, '#1a1330');
    rect(0, 83, 160, 1, '#3a2b66');
    rect(0, 84, 160, 16, '#1c1532');
    for (let y = 84; y < 100; y += 4) {
      const off = (((y - 84) / 4) % 2) * 8;
      for (let x = -8 + off; x < 160; x += 16) rect(x, y, 8, 4, '#241b40');
    }
    rect(58, 84, 64, 3, '#0a0714');

    // wall display
    rect(6, 12, 48, 36, '#2a1d4f');
    rect(7, 13, 46, 34, '#05040a');
    pixelText(`${measured.toFixed(1)}C`, 10, 16, '#7df3ff');
    pixelText(`>${setpoint.toFixed(1)}`, 10, 25, '#c7a6ff');
    const leds = [[10, 'C', on, '#7df3ff'], [24, 'D', defrost, '#c7a6ff'], [38, 'A', alarm, '#ff4d5e']];
    for (const [x, letter, lit, color] of leds) {
      rect(x, 34, 6, 3, lit ? color : '#241b40');
      pixelText(letter, x + 1, 39, lit ? color : '#6f6a8f');
    }

    // fridge body
    rect(62, 6, 56, 78, '#0a0814');
    rect(63, 7, 54, 76, '#aebcd9');
    rect(63, 7, 54, 1, '#dfe8f7');
    rect(115, 7, 2, 76, '#8294b8');
    rect(64, 8, 50, 13, '#8b9cc0');
    rect(64, 20, 50, 1, '#5d6d92');
    rect(67, 83, 6, 3, '#0a0814');
    rect(107, 83, 6, 3, '#0a0814');

    // open door (slab on the left)
    rect(50, 8, 12, 76, '#0a0814');
    rect(51, 9, 10, 74, '#c9d4ea');
    rect(51, 9, 2, 74, '#e8eefa');
    rect(59, 9, 2, 74, '#98a8c8');
    rect(56, 38, 2, 16, '#9b5cff');
    rect(60, 14, 2, 4, '#5d6d92');
    rect(60, 68, 2, 4, '#5d6d92');

    // interior
    rect(67, 22, 46, 57, '#050a14');
    for (let i = 0; i < 55; i++) {
      const f = i / 55;
      rect(68, 23 + i, 44, 1, `rgb(${Math.round(16 - 8 * f)},${Math.round(40 - 22 * f)},${Math.round(64 - 32 * f)})`);
    }
    for (const shelf of SHELVES) {
      rect(68, shelf.y, 44, 1, '#7fe8f8');
      rect(68, shelf.y + 1, 44, 1, '#2b8fa3');
      for (const [x, w, h, color] of shelf.items) {
        rect(x, shelf.y - h, w, h, color);
        rect(x, shelf.y - h, w, 1, 'rgba(255,255,255,0.45)');
        rect(x + w - 1, shelf.y - h + 1, 1, h - 1, 'rgba(0,0,0,0.3)');
      }
    }
    rect(68, 72, 44, 7, '#14304d');
    rect(86, 74, 8, 2, '#7fe8f8');

    // frost grows when it is colder
    const frostCount = Math.round(Math.min(1, Math.max(0, (-measured - 3) / 22)) * FROST.length);
    for (let i = 0; i < frostCount; i++) rect(FROST[i][0], FROST[i][1], 1, 1, '#e6fbff');

    // cooling fan, vents, alarm beacon (steady, never blinking)
    rect(69, 9, 10, 10, '#2c2450');
    const fan = on ? '#7df3ff' : '#4a4570';
    const frame = on ? Math.floor(t / 2) % 2 : 0;
    if (frame === 0) {
      rect(73, 10, 2, 8, fan);
      rect(70, 13, 8, 2, fan);
    } else {
      for (let i = 0; i < 8; i++) { rect(70 + i, 10 + i, 1, 1, fan); rect(77 - i, 10 + i, 1, 1, fan); }
    }
    rect(73, 13, 2, 2, '#eef0f7');
    for (let i = 0; i < 3; i++) rect(86, 10 + i * 3, 22, 1, '#5d6d92');
    rect(108, 9, 5, 5, alarm ? '#ff4d5e' : '#3a1c28');
    if (alarm) rect(109, 10, 2, 1, '#ffd0d5');

    // cold-air particles while the compressor runs
    if (on && !defrost) {
      for (let i = 0; i < 7; i++) rect(70 + i * 6 + (i % 2) * 2, 23 + ((t * 2 + i * 8) % 54), 1, 2, '#bff7ff');
    }
    // meltwater drips during defrost
    if (defrost) {
      for (let i = 0; i < 4; i++) {
        const x = 75 + i * 12;
        rect(x - 1, 23, 3, 1, '#9fd8ff');
        rect(x, 24 + ((t * 2 + i * 13) % 50), 1, 2, '#9fd8ff');
      }
    }
  }

  // ---------------------------------------------------------------- chart
  const chart = $('chart');
  const cc = chart.getContext('2d');

  function drawChart() {
    const box = chart.getBoundingClientRect();
    if (box.width === 0) return;
    const dpr = window.devicePixelRatio || 1;
    const w = box.width;
    const h = box.height;
    if (chart.width !== Math.round(w * dpr) || chart.height !== Math.round(h * dpr)) {
      chart.width = Math.round(w * dpr);
      chart.height = Math.round(h * dpr);
    }
    cc.setTransform(dpr, 0, 0, dpr, 0, 0);
    cc.clearRect(0, 0, w, h);
    const f = Math.max(12, w / 48);
    cc.font = `${f}px monospace`;
    cc.textBaseline = 'middle';

    const hist = latest && latest.simulation.history;
    if (!hist || hist.length < 2) {
      cc.fillStyle = '#b4b0cc';
      cc.fillText('Collecting data…', f, h / 2);
      return;
    }
    const tEnd = hist[hist.length - 1][0];
    const tStart = tEnd - WINDOW_S;
    const vis = hist.filter((p) => p[0] >= tStart - 2);
    const lim = latest.limits;
    let lo = Math.min(-30, lim.alarm_min_c - 2);
    let hi = Math.max(0, lim.alarm_max_c + 2);
    for (const p of vis) { lo = Math.min(lo, p[1], p[2]); hi = Math.max(hi, p[1], p[2]); }
    lo = Math.floor(lo / 5) * 5;
    hi = Math.ceil(hi / 5) * 5;

    const padL = f * 3.8, padR = f, padT = f * 2.4, padB = f * 1.8;
    const pw = w - padL - padR, ph = h - padT - padB;
    const X = (t) => padL + ((t - tStart) / WINDOW_S) * pw;
    const Y = (v) => padT + ((hi - v) / (hi - lo)) * ph;

    cc.fillStyle = 'rgba(155,92,255,0.18)';
    cc.fillRect(padL, Y(lim.alarm_max_c), pw, Y(lim.alarm_min_c) - Y(lim.alarm_max_c));

    cc.strokeStyle = '#2a2250';
    cc.lineWidth = 1;
    cc.fillStyle = '#b4b0cc';
    cc.textAlign = 'right';
    for (let v = lo; v <= hi; v += 5) {
      cc.beginPath(); cc.moveTo(padL, Y(v)); cc.lineTo(padL + pw, Y(v)); cc.stroke();
      cc.fillText(String(v), padL - f * 0.5, Y(v));
    }
    cc.textAlign = 'left';
    cc.fillText('-5 min', padL, h - padB / 2);
    cc.textAlign = 'right';
    cc.fillText('now', padL + pw, h - padB / 2);

    cc.save();
    cc.beginPath(); cc.rect(padL, padT, pw, ph); cc.clip();
    cc.setLineDash([10, 6]);
    cc.strokeStyle = '#c7a6ff';
    cc.lineWidth = 3;
    cc.beginPath();
    let prev = vis[0][2];
    cc.moveTo(X(vis[0][0]), Y(prev));
    for (const p of vis) { cc.lineTo(X(p[0]), Y(prev)); cc.lineTo(X(p[0]), Y(p[2])); prev = p[2]; }
    cc.stroke();
    cc.setLineDash([]);
    cc.strokeStyle = '#7df3ff';
    cc.lineWidth = 3;
    cc.beginPath();
    vis.forEach((p, i) => (i === 0 ? cc.moveTo(X(p[0]), Y(p[1])) : cc.lineTo(X(p[0]), Y(p[1]))));
    cc.stroke();
    cc.restore();

    // legend (line style + text, not colour alone)
    cc.textAlign = 'left';
    cc.lineWidth = 3;
    cc.strokeStyle = '#7df3ff';
    cc.beginPath(); cc.moveTo(padL, f); cc.lineTo(padL + f * 2, f); cc.stroke();
    cc.fillStyle = '#eef0f7';
    cc.fillText('measured', padL + f * 2.4, f);
    const lx = padL + f * 2.4 + f * 6;
    cc.setLineDash([6, 4]);
    cc.strokeStyle = '#c7a6ff';
    cc.beginPath(); cc.moveTo(lx, f); cc.lineTo(lx + f * 2, f); cc.stroke();
    cc.setLineDash([]);
    cc.fillText('setpoint', lx + f * 2.4, f);
    cc.fillStyle = '#c7a6ff';
    cc.textAlign = 'right';
    cc.fillText(`demo range ${lim.alarm_min_c}…${lim.alarm_max_c} °C`, padL + pw, f);
  }

  // --------------------------------------------------------------- render
  const PHASE = { cooling: 'COOLING', holding: 'HOLDING', defrost: 'DEFROST' };

  function render() {
    if (!latest) return;
    if (latest.mode !== pageMode) {
      if (!reloading) { reloading = true; window.location.reload(); }
      return;
    }
    const sim = latest.simulation;
    $('conn').hidden = true;
    $('v-setpoint').textContent = fmt(sim.setpoint_c);
    $('v-measured').textContent = fmt(sim.measured_c);
    $('v-phase').textContent = PHASE[sim.phase] || sim.phase.toUpperCase();
    $('v-compressor').textContent = sim.compressor_on ? 'Compressor ON' : 'Compressor OFF';
    $('v-defrost').textContent = sim.phase === 'defrost' ? 'Defrost running…' : `Next defrost in ${mmss(sim.next_defrost_in_s)}`;

    const a = sim.alarm;
    const card = $('card-alarm');
    card.classList.toggle('alarm-on', a.active);
    card.classList.toggle('alarm-pending', a.pending);
    $('scene-panel').classList.toggle('alarm-on', a.active);
    if (a.active) $('v-alarm').textContent = a.kind === 'high' ? 'ALARM: TOO WARM' : 'ALARM: TOO COLD';
    else if (a.pending) $('v-alarm').textContent = 'OUT OF RANGE (pending)';
    else $('v-alarm').textContent = 'OK';
    $('v-alarm-range').textContent = `Demo range ${a.min_c} to ${a.max_c} °C, alarm after ${a.delay_s} s outside`;
    $('cooling-bar').classList.toggle('active', sim.compressor_on);

    drawChart();
    drawScene();
  }

  function renderAudit() {
    const body = $('audit-body');
    body.replaceChildren();
    for (const e of auditEntries.slice(0, 10)) {
      const tr = document.createElement('tr');
      const cells = [
        String(e.timestamp).slice(11, 19),
        e.action,
        e.outcome,
        e.requested_c === null ? '–' : `${e.requested_c} °C`,
      ];
      for (const text of cells) {
        const td = document.createElement('td');
        td.textContent = text;
        tr.appendChild(td);
      }
      body.appendChild(tr);
    }
  }

  async function getJson(path) {
    const res = await fetch(path, { cache: 'no-store', credentials: 'omit', headers: { Accept: 'application/json' } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async function poll() {
    try {
      const [st, au] = await Promise.all([getJson('/api/status'), getJson('/api/audit')]);
      latest = st;
      auditEntries = au.entries || [];
      render();
      renderAudit();
    } catch (_err) {
      $('conn').hidden = false;
    }
    window.setTimeout(poll, POLL_MS);
  }

  // ------------------------------------------------------------- operator
  function setResult(text, kind) {
    const el = $('op-result');
    el.textContent = text;
    el.className = `result ${kind}`;
  }

  function showTokenState(text) {
    const el = $('token-state');
    if (el) el.textContent = text;
  }

  function forgetToken(message) {
    operatorToken = '';
    const input = $('token-input');
    if (input) input.value = '';
    showTokenState(message || 'No token in memory.');
  }

  async function applySetpoint() {
    const raw = $('sp-input').value.trim();
    const value = Number(raw);
    if (raw === '' || !Number.isFinite(value)) {
      setResult('Enter a number first.', 'err');
      return;
    }
    const headers = { 'Content-Type': 'application/json', Accept: 'application/json' };
    if (operatorToken) headers.Authorization = `Bearer ${operatorToken}`;
    const button = $('sp-apply');
    button.disabled = true;
    try {
      const res = await fetch('/api/setpoint', {
        method: 'POST',
        headers,
        body: JSON.stringify({ setpoint_c: value }),
        cache: 'no-store',
        credentials: 'omit',
      });
      let data = {};
      try { data = await res.json(); } catch (_e) { /* non-JSON error body */ }
      if (res.ok) {
        setResult(`HTTP ${res.status} – accepted: setpoint is now ${fmt(data.setpoint_c)}`, 'ok');
      } else {
        setResult(`HTTP ${res.status} – ${data.error || 'error'}: ${data.message || ''}`, 'err');
        if (res.status === 401) forgetToken('No token in memory (missing or rejected).');
      }
    } catch (_err) {
      setResult('Could not reach the local app.', 'err');
    } finally {
      button.disabled = false;
    }
  }

  $('sp-apply').addEventListener('click', applySetpoint);
  $('sp-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') applySetpoint(); });

  const useButton = $('token-use');
  if (useButton) {
    const tokenInput = $('token-input');
    const useToken = () => {
      const value = tokenInput.value.trim();
      tokenInput.value = '';
      if (!value) { showTokenState('Nothing entered.'); return; }
      operatorToken = value;
      showTokenState(`Token held in memory (${value.length} characters). Reloading the page forgets it.`);
    };
    useButton.addEventListener('click', useToken);
    tokenInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') useToken(); });
    $('token-clear').addEventListener('click', () => forgetToken('Token forgotten.'));
  }

  // ------------------------------------------------------------ animation
  let looping = false;
  let lastFrame = 0;
  function loop(ts) {
    if (motion.matches) { looping = false; drawScene(); return; }
    if (ts - lastFrame >= FRAME_MS) { lastFrame = ts; tick += 1; drawScene(); }
    window.requestAnimationFrame(loop);
  }
  function startLoop() {
    if (!motion.matches && !looping) { looping = true; window.requestAnimationFrame(loop); }
  }
  motion.addEventListener('change', () => { drawScene(); startLoop(); });
  window.addEventListener('resize', drawChart);

  drawScene();
  startLoop();
  poll();
})();

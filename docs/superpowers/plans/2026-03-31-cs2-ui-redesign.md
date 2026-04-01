# CS2 UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing light-theme frontend with a dark CS2 military-briefing style UI (T-side orange palette, responsive two-column desktop / single-column mobile layout, logo in header + watermark on heatmap).

**Architecture:** Single-file rewrite of `server/templates/index.html` — all CSS replaced, HTML structure changed to header + left-panel + right-panel layout, all JS logic kept verbatim. A new `server/static/` directory holds the logo asset served via Flask's default static route.

**Tech Stack:** Plain HTML/CSS/JS, Flask static serving (`/static/logo.webp`)

---

### Task 1: Copy logo to Flask static folder

**Files:**
- Create dir: `server/static/`
- Create: `server/static/logo.webp` (copy from root)

- [ ] **Step 1: Create static directory and copy logo**

```bash
mkdir -p D:/CSAI/server/static
cp D:/CSAI/Icon-t-patch-small.webp D:/CSAI/server/static/logo.webp
```

- [ ] **Step 2: Verify file exists**

```bash
ls D:/CSAI/server/static/logo.webp
```

Expected: file listed, non-zero size.

- [ ] **Step 3: Confirm Flask will serve it**

Flask app is instantiated in `server/web_server.py` line 24 as:
```python
app = Flask(__name__, template_folder=os.path.join(config.BASE_DIR, "templates"))
```
`__name__` resolves to the `server/` directory. Flask's default `static_folder` is `'static'` relative to the app root — so `server/static/` is served at `/static/`. **No code change needed.**

---

### Task 2: Rewrite index.html

**Files:**
- Modify: `server/templates/index.html` (full rewrite — CSS + HTML, JS preserved verbatim)

- [ ] **Step 1: Replace the entire file with the new CS2 UI**

Write `server/templates/index.html` with the following content:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CSAI — T-Side Tactical Prep</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0a0a0a;
            color: #ccc;
            min-height: 100vh;
        }

        /* === HEADER === */
        .app-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 24px;
            background: #080808;
            border-bottom: 1px solid #e8a02033;
            position: sticky;
            top: 0;
            z-index: 100;
            height: 56px;
        }
        .header-left { display: flex; align-items: center; gap: 12px; }
        .header-logo { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; }
        .header-name { color: #e8a020; font-size: 13px; font-weight: 700; letter-spacing: 3px; }
        .header-sub  { color: #444; font-size: 9px; letter-spacing: 2px; margin-top: 2px; }
        .header-right { color: #2a2a2a; font-size: 9px; letter-spacing: 2px; }

        /* === LAYOUT === */
        .app-body {
            display: grid;
            grid-template-columns: 240px 1fr;
            min-height: calc(100vh - 56px);
        }

        /* === LEFT PANEL === */
        .left-panel {
            background: #080808;
            border-right: 1px solid #151515;
            padding: 20px 16px;
            display: flex;
            flex-direction: column;
        }
        .panel-label {
            color: #444;
            font-size: 9px;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .name-inputs { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
        .name-row { display: flex; align-items: center; gap: 8px; }
        .name-num {
            color: #2a2a2a; font-size: 10px; width: 14px;
            text-align: center; font-family: monospace; flex-shrink: 0;
        }
        .name-row input {
            flex: 1;
            background: #0f0f0f;
            border: 1px solid #1e1e1e;
            color: #bbb;
            padding: 8px 10px;
            font-size: 11px;
            outline: none;
            transition: border-color 0.15s;
        }
        .name-row input::placeholder { color: #2a2a2a; font-style: italic; }
        .name-row input:focus { border-color: #e8a02066; }

        .slider-section { margin-bottom: 16px; }
        .slider-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 8px;
        }
        .slider-label { color: #555; font-size: 9px; letter-spacing: 1px; text-transform: uppercase; }
        .slider-value { color: #e8a020; font-size: 11px; font-weight: 700; font-family: monospace; }
        input[type="range"] {
            width: 100%; -webkit-appearance: none;
            height: 3px; background: #1a1a1a; outline: none; cursor: pointer;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 12px; height: 12px; border-radius: 50%;
            background: #e8a020; cursor: pointer;
        }
        input[type="range"]::-moz-range-thumb {
            width: 12px; height: 12px; border-radius: 50%;
            background: #e8a020; border: none; cursor: pointer;
        }

        .btn-analyze {
            width: 100%; padding: 11px;
            background: #e8a020; color: #000; border: none;
            font-size: 10px; font-weight: 700; letter-spacing: 3px;
            text-transform: uppercase; cursor: pointer; transition: background 0.15s;
            margin-bottom: 16px;
        }
        .btn-analyze:hover { background: #ffb830; }
        .btn-analyze:disabled { background: #2a2a2a; color: #555; cursor: not-allowed; }

        .divider { height: 1px; background: #111; margin-bottom: 14px; }

        .status-box {
            padding: 8px 10px; font-size: 9px; letter-spacing: 1px;
            display: none; align-items: center; gap: 8px; margin-bottom: 10px;
        }
        .status-box.running, .status-box.done {
            display: flex; background: #0a140a;
            border: 1px solid #1e3a1e; color: #5aaa5a;
        }
        .status-box.error {
            display: flex; background: #140a0a;
            border: 1px solid #3a1e1e; color: #aa5a5a;
        }
        .status-dot {
            width: 6px; height: 6px; border-radius: 50%;
            background: currentColor; flex-shrink: 0;
        }
        .status-dot.spinning { animation: pulse 1s ease-in-out infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        .status-text { flex: 1; line-height: 1.4; }

        .adequacy-section { display: none; }
        .adequacy-section.visible { display: block; }
        .adequacy-rows { display: flex; flex-direction: column; gap: 5px; }
        .adeq-row { display: flex; align-items: center; gap: 6px; }
        .adeq-name {
            color: #555; font-size: 9px; width: 80px;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .adeq-track { flex: 1; height: 2px; background: #1a1a1a; }
        .adeq-fill  { height: 2px; background: #e8a020; }
        .adeq-pct   { font-size: 9px; font-family: monospace; width: 32px; text-align: right; }
        .pct-full  { color: #5aaa5a; }
        .pct-high  { color: #7aaa3a; }
        .pct-mid   { color: #aa7030; }
        .pct-low   { color: #aa4040; }

        /* === RIGHT PANEL === */
        .right-panel { padding: 20px 24px; overflow-y: auto; }

        .player-tabs {
            display: flex; flex-wrap: wrap; gap: 6px;
            margin-bottom: 16px;
            border-bottom: 1px solid #141414; padding-bottom: 14px;
        }
        .player-tab {
            padding: 5px 16px; font-size: 10px; font-weight: 600; letter-spacing: 1px;
            border: 1px solid #1e1e1e; background: #0f0f0f; color: #444;
            cursor: pointer; transition: all 0.15s;
        }
        .player-tab:hover { border-color: #e8a02066; color: #888; }
        .player-tab.active { background: #e8a02018; border-color: #e8a020; color: #e8a020; }

        .card-header {
            display: flex; justify-content: space-between; align-items: baseline;
            padding-bottom: 10px; border-bottom: 1px solid #141414; margin-bottom: 16px;
        }
        .opponent-name { font-size: 18px; font-weight: 700; color: #e8a020; letter-spacing: 1px; }
        .opponent-meta { color: #333; font-size: 9px; letter-spacing: 1px; font-family: monospace; }

        .heatmap-wrap {
            position: relative; display: inline-block;
            width: 100%; max-width: 600px; margin-bottom: 20px;
        }
        .heatmap-img { width: 100%; display: block; border: 1px solid #1a1a1a; }
        .heatmap-watermark {
            position: absolute; right: 10px; bottom: 10px;
            width: 48px; height: 48px; border-radius: 50%;
            object-fit: cover; opacity: 0.07; pointer-events: none;
        }

        .zone-stats { max-width: 600px; }
        .zone-stats-title {
            color: #333; font-size: 8px; letter-spacing: 3px; text-transform: uppercase;
            margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid #111;
        }
        .rtype-group { margin-bottom: 14px; }
        .rtype-badge {
            display: inline-block; padding: 2px 10px;
            font-size: 8px; font-weight: 700; letter-spacing: 2px;
            text-transform: uppercase; margin-bottom: 6px;
        }
        .rtype-fullbuy  { background: #3a0a0a; color: #cc4040; border: 1px solid #6a1a1a; }
        .rtype-forcebuy { background: #2a1500; color: #cc7030; border: 1px solid #5a3010; }
        .rtype-eco      { background: #1a1a00; color: #aaaa40; border: 1px solid #4a4a10; }
        .rtype-pistol   { background: #001525; color: #4090cc; border: 1px solid #102a40; }
        .zone-row { display: flex; align-items: center; gap: 8px; padding: 3px 0; }
        .zone-tag { width: 20px; text-align: center; font-size: 9px; font-weight: 700; padding: 1px 0; }
        .tag-D { color: #444; }
        .tag-K { color: #5aaa5a; }
        .tag-A { color: #cc4040; }
        .tag-\? { color: #333; }
        .zone-name { color: #555; font-size: 10px; width: 150px; }
        .zone-bar { flex: 1; height: 3px; background: #1a1a1a; max-width: 280px; }
        .zone-bar-fill { height: 3px; }
        .zone-pct { color: #444; font-size: 10px; font-family: monospace; width: 38px; text-align: right; }

        .failed-section {
            background: #140a0a; border: 1px solid #3a1e1e;
            padding: 12px 16px; margin-bottom: 20px; display: none;
        }
        .failed-section.visible { display: block; }
        .failed-title { color: #aa4040; font-size: 9px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; }
        .failed-item {
            display: flex; gap: 12px; padding: 5px 0;
            border-bottom: 1px solid #2a1515; font-size: 11px;
        }
        .failed-item:last-child { border-bottom: none; }
        .failed-name   { color: #cc4040; font-weight: 600; }
        .failed-reason { color: #664040; }

        /* === RESPONSIVE === */
        @media (max-width: 767px) {
            .header-right { display: none; }
            .app-body { grid-template-columns: 1fr; }
            .left-panel { border-right: none; border-bottom: 1px solid #151515; }
            .right-panel { padding: 14px; }
            .heatmap-wrap { max-width: 100%; }
            .zone-stats { max-width: 100%; }
            .zone-bar { max-width: none; }
            .opponent-meta { display: none; }
        }
    </style>
</head>
<body>
    <header class="app-header">
        <div class="header-left">
            <img class="header-logo" src="/static/logo.webp" alt="CSAI">
            <div>
                <div class="header-name">CSAI</div>
                <div class="header-sub">T-SIDE TACTICAL PREP · MIRAGE</div>
            </div>
        </div>
        <div class="header-right">// OPPONENT INTELLIGENCE SYSTEM</div>
    </header>

    <div class="app-body">
        <aside class="left-panel">
            <div class="panel-label">Target Designations</div>
            <div class="name-inputs" id="nameInputs">
                <div class="name-row"><span class="name-num">1</span><input type="text" class="name-input" placeholder="5E 用户名"></div>
                <div class="name-row"><span class="name-num">2</span><input type="text" class="name-input" placeholder="5E 用户名"></div>
                <div class="name-row"><span class="name-num">3</span><input type="text" class="name-input" placeholder="5E 用户名"></div>
                <div class="name-row"><span class="name-num">4</span><input type="text" class="name-input" placeholder="5E 用户名"></div>
                <div class="name-row"><span class="name-num">5</span><input type="text" class="name-input" placeholder="5E 用户名"></div>
            </div>

            <div class="slider-section">
                <div class="slider-header">
                    <span class="slider-label">Demo Depth</span>
                    <span class="slider-value"><span id="maxDemosVal">10</span> 局/人</span>
                </div>
                <input type="range" id="maxDemos" min="1" max="10" value="10"
                    oninput="document.getElementById('maxDemosVal').textContent=this.value">
            </div>

            <button class="btn-analyze" id="btnAnalyze" onclick="startAnalysis()">▶ Execute Scan</button>

            <div class="divider"></div>

            <div class="status-box" id="statusBar">
                <div class="status-dot" id="statusDot"></div>
                <span class="status-text" id="statusText"></span>
            </div>

            <div class="adequacy-section" id="adequacyBar">
                <div class="panel-label" style="margin-bottom:8px;">Data Coverage</div>
                <div class="adequacy-rows" id="adequacyPlayers"></div>
                <div style="color:#333;font-size:9px;margin-top:8px;font-family:monospace;" id="adequacyTotal"></div>
            </div>
        </aside>

        <main class="right-panel">
            <div class="failed-section" id="failedSection">
                <div class="failed-title">// Failed Targets</div>
                <div id="failedList"></div>
            </div>
            <div id="resultsContainer"></div>
        </main>
    </div>

    <script>
        let pollTimer = null;
        let submittedCount = 0;
        let maxDemosPerPlayer = 10;

        function parseUsernames() {
            const inputs = document.querySelectorAll('.name-input');
            for (const inp of inputs) {
                const v = inp.value.trim();
                if (v.startsWith('[')) {
                    const inner = v.replace(/^\[|\]$/g, '');
                    return inner.split(',').map(s => s.trim()).filter(Boolean).slice(0, 5);
                }
            }
            const names = [];
            inputs.forEach(inp => { const v = inp.value.trim(); if (v) names.push(v); });
            return names;
        }

        function startAnalysis() {
            const usernames = parseUsernames();
            if (usernames.length === 0) { alert('请至少输入一个 5E 用户名'); return; }
            submittedCount = usernames.length;
            maxDemosPerPlayer = parseInt(document.getElementById('maxDemos').value);
            document.getElementById('btnAnalyze').disabled = true;
            document.getElementById('resultsContainer').innerHTML = '';
            document.getElementById('adequacyBar').classList.remove('visible');
            document.getElementById('failedSection').classList.remove('visible');
            setStatus('running', 'Scanning...');
            fetch('/api/analyze_by_names', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ usernames, max_demos: maxDemosPerPlayer, key: 'csai_2026' })
            })
            .then(r => r.json())
            .then(data => {
                if (data.error) { setStatus('error', data.error); document.getElementById('btnAnalyze').disabled = false; return; }
                pollTimer = setInterval(pollStatus, 2000);
            })
            .catch(e => { setStatus('error', 'Request failed: ' + e); document.getElementById('btnAnalyze').disabled = false; });
        }

        function pollStatus() {
            fetch('/api/status').then(r => r.json()).then(data => {
                setStatus(data.status, data.message);
                if (data.status === 'done' || data.status === 'error') {
                    clearInterval(pollTimer); pollTimer = null;
                    document.getElementById('btnAnalyze').disabled = false;
                    if (data.status === 'done') {
                        if (data.total_players) submittedCount = data.total_players;
                        if (data.max_demos)     maxDemosPerPlayer = data.max_demos;
                        renderAdequacy(data.results);
                        renderResults(data.results);
                        renderFailed(data.failed || []);
                    }
                }
            });
        }

        function setStatus(status, msg) {
            const bar = document.getElementById('statusBar');
            bar.className = 'status-box ' + status;
            document.getElementById('statusText').textContent = msg;
            const dot = document.getElementById('statusDot');
            dot.className = 'status-dot' + (status === 'running' ? ' spinning' : '');
        }

        function pctClass(pct) {
            if (pct >= 100) return 'pct-full';
            if (pct >= 70)  return 'pct-high';
            if (pct >= 40)  return 'pct-mid';
            return 'pct-low';
        }

        function renderAdequacy(results) {
            const bar = document.getElementById('adequacyBar');
            bar.classList.add('visible');
            const totalDemos = results.reduce((s, r) => s + (r.demos_found || 0), 0);
            const maxTotal   = submittedCount * maxDemosPerPlayer;
            const totalPct   = maxTotal > 0 ? Math.round(totalDemos / maxTotal * 100) : 0;
            document.getElementById('adequacyTotal').textContent = totalDemos + ' / ' + maxTotal + ' demos (' + totalPct + '%)';
            document.getElementById('adequacyPlayers').innerHTML = results.map(r => {
                const pct = maxDemosPerPlayer > 0 ? Math.round((r.demos_found || 0) / maxDemosPerPlayer * 100) : 0;
                return `<div class="adeq-row">
                    <span class="adeq-name">${r.username}</span>
                    <div class="adeq-track"><div class="adeq-fill" style="width:${Math.min(pct,100)}%"></div></div>
                    <span class="adeq-pct ${pctClass(pct)}">${pct}%</span>
                </div>`;
            }).join('');
        }

        const RTYPE_COLORS = {
            'Full Buy':  { cls: 'rtype-fullbuy',  bar: '#cc4040' },
            'Force Buy': { cls: 'rtype-forcebuy', bar: '#cc7030' },
            'Eco':       { cls: 'rtype-eco',       bar: '#aaaa40' },
            'Pistol':    { cls: 'rtype-pistol',    bar: '#4090cc' },
        };

        function renderResults(results) {
            const container = document.getElementById('resultsContainer');
            container.innerHTML = '';
            if (results.length === 0) return;
            const tabBar = document.createElement('div');
            tabBar.className = 'player-tabs'; tabBar.id = 'playerTabs';
            results.forEach((r, i) => {
                const tab = document.createElement('button');
                tab.className = 'player-tab' + (i === 0 ? ' active' : '');
                tab.textContent = r.username;
                tab.onclick = () => switchPlayer(i);
                tabBar.appendChild(tab);
            });
            container.appendChild(tabBar);
            results.forEach((r, i) => {
                const card = document.createElement('div');
                card.className = 'opponent-card';
                card.setAttribute('data-player-idx', i);
                if (i !== 0) card.style.display = 'none';
                const pct = maxDemosPerPlayer > 0 ? Math.round((r.demos_found || 0) / maxDemosPerPlayer * 100) : 0;
                let statsHtml = '';
                for (const [rtype, items] of Object.entries(r.zone_stats || {})) {
                    if (!items || items.length === 0) continue;
                    const rc = RTYPE_COLORS[rtype] || { cls: '', bar: '#888' };
                    const rows = items.map(z => `
                        <div class="zone-row">
                            <span class="zone-tag tag-${z.tag}">${z.tag}</span>
                            <span class="zone-name">${z.zone}</span>
                            <div class="zone-bar"><div class="zone-bar-fill" style="width:${z.percent}%;background:${rc.bar}"></div></div>
                            <span class="zone-pct">${z.percent}%</span>
                        </div>`).join('');
                    statsHtml += `<div class="rtype-group"><div class="rtype-badge ${rc.cls}">${rtype}</div>${rows}</div>`;
                }
                card.innerHTML = `
                    <div class="card-header">
                        <span class="opponent-name">${r.username}</span>
                        <span class="opponent-meta">${r.demos_found}/${maxDemosPerPlayer} demos · ${r.round_count} CT rounds · ${r.record_count} samples</span>
                    </div>
                    <div class="heatmap-wrap">
                        <img class="heatmap-img" src="${r.heatmap}?t=${Date.now()}" alt="Heatmap">
                        <img class="heatmap-watermark" src="/static/logo.webp" alt="">
                    </div>
                    <div class="zone-stats">
                        <div class="zone-stats-title">Zone Distribution</div>
                        ${statsHtml}
                    </div>`;
                container.appendChild(card);
            });
        }

        function switchPlayer(index) {
            document.querySelectorAll('#playerTabs .player-tab').forEach((tab, i) => tab.classList.toggle('active', i === index));
            document.querySelectorAll('#resultsContainer .opponent-card').forEach((card, i) => { card.style.display = i === index ? '' : 'none'; });
        }

        function renderFailed(failedList) {
            const section = document.getElementById('failedSection');
            const container = document.getElementById('failedList');
            if (!failedList || failedList.length === 0) { section.classList.remove('visible'); return; }
            section.classList.add('visible');
            container.innerHTML = failedList.map(f =>
                `<div class="failed-item"><span class="failed-name">${f.username}</span><span class="failed-reason">${f.reason}</span></div>`
            ).join('');
        }

        fetch('/api/status').then(r => r.json()).then(statusData => {
            if (statusData.status === 'running') {
                if (statusData.total_players) submittedCount = statusData.total_players;
                if (statusData.max_demos)     maxDemosPerPlayer = statusData.max_demos;
                document.getElementById('btnAnalyze').disabled = true;
                setStatus('running', statusData.message);
                pollTimer = setInterval(pollStatus, 2000);
            } else if (statusData.status === 'done') {
                if (statusData.total_players) submittedCount = statusData.total_players;
                if (statusData.max_demos)     maxDemosPerPlayer = statusData.max_demos;
                renderAdequacy(statusData.results);
                renderResults(statusData.results);
                renderFailed(statusData.failed || []);
                setStatus('done', statusData.message);
            } else {
                fetch('/api/results').then(r => r.json()).then(data => {
                    const results = data.results || [];
                    const failed = data.failed || [];
                    if (results.length === 0 && failed.length === 0) return;
                    results.forEach(r => { if (r.heatmap && !r.heatmap.startsWith('/output/')) r.heatmap = '/output/' + r.heatmap; });
                    submittedCount = results.length + failed.length;
                    maxDemosPerPlayer = data.max_demos || 10;
                    document.getElementById('maxDemos').value = maxDemosPerPlayer;
                    document.getElementById('maxDemosVal').textContent = maxDemosPerPlayer;
                    renderAdequacy(results);
                    renderResults(results);
                    renderFailed(failed);
                    setStatus('done', `显示上次结果：${results.length} 位玩家`);
                });
            }
        });
    </script>
</body>
</html>
```

- [ ] **Step 2: Verify file was written**

```bash
wc -l D:/CSAI/server/templates/index.html
```

Expected: ~300+ lines.

- [ ] **Step 3: Open the page in browser to verify visual result**

Start Flask server locally (or check on VPS), open `http://localhost:5000`.

Verify:
- Background is near-black `#0a0a0a` ✓
- Header shows logo (circle-cropped) + "CSAI" in amber + subtitle ✓
- Left panel (240px) has dark input fields with amber focus ring ✓
- "▶ Execute Scan" button is amber on black ✓
- Right panel is empty initially (no results loaded) ✓
- Browser width < 768px: layout collapses to single column ✓

---

### Task 3: Deploy to VPS

**Files:**
- Remote: `/home/ubuntu/server/templates/index.html`
- Remote: `/home/ubuntu/server/static/logo.webp` (new file)

- [ ] **Step 1: Upload logo to VPS**

```bash
scp D:/CSAI/server/static/logo.webp ubuntu@<VPS_IP>:/home/ubuntu/server/static/logo.webp
```

- [ ] **Step 2: Upload updated index.html to VPS**

```bash
scp D:/CSAI/server/templates/index.html ubuntu@<VPS_IP>:/home/ubuntu/server/templates/index.html
```

- [ ] **Step 3: Restart Flask server on VPS**

```bash
ssh ubuntu@<VPS_IP> "cd /home/ubuntu/server && pkill -f web_server.py; source venv/bin/activate && nohup python web_server.py > server.log 2>&1 &"
```

- [ ] **Step 4: Open browser to verify live site**

Open `http://<VPS_IP>:5000` and confirm new dark CS2 UI is live.

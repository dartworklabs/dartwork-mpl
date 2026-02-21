"""HTML template for the Dartwork interactive figure viewer.

Light corporate theme with Lucide icons. No gradients, no emojis.
"""

from __future__ import annotations


def get_html(title: str = "Dartwork Viewer") -> str:
    """Return the complete HTML page as a string."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lucide@latest"></script>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --bg: #ffffff;
  --bg-secondary: #f8f9fa;
  --bg-hover: #f1f3f5;
  --bg-input: #ffffff;
  --border: #e1e4e8;
  --border-focus: #0969da;
  --text: #1f2328;
  --text-secondary: #656d76;
  --text-muted: #8b949e;
  --accent: #0969da;
  --accent-light: rgba(9, 105, 218, 0.08);
  --success: #1a7f37;
  --danger: #cf222e;
  --radius: 6px;
  --radius-lg: 8px;
  --transition: 0.15s ease;
  --sidebar-w: 280px;
  --font: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
  --figure-bg: #ffffff;
}}

html, body {{
  height: 100%;
  font-family: var(--font);
  font-size: 13px;
  color: var(--text);
  background: var(--bg);
  overflow: hidden;
}}

/* ── Layout ───────────────────────────────────────── */
.app {{ display: flex; height: 100vh; }}

/* ── Sidebar ──────────────────────────────────────── */
.sidebar {{
  width: var(--sidebar-w);
  min-width: var(--sidebar-w);
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}

.sidebar-header {{
  padding: 0 14px;
  min-height: 41px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}}

.sidebar-header h2 {{
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: 6px;
}}

.sidebar-params {{
  flex: 1;
  overflow-y: auto;
  padding: 10px 14px;
}}

.sidebar-params::-webkit-scrollbar {{ width: 3px; }}
.sidebar-params::-webkit-scrollbar-track {{ background: transparent; }}
.sidebar-params::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

/* ── Controls ─────────────────────────────────────── */
.param-group {{ margin-bottom: 14px; }}

.param-label {{
  display: block;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 4px;
}}

.param-input {{
  width: 100%;
  padding: 6px 8px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-family: var(--font);
  font-size: 13px;
  outline: none;
  transition: border-color var(--transition);
}}

.param-input:focus {{
  border-color: var(--border-focus);
  box-shadow: 0 0 0 2px var(--accent-light);
}}

.param-select {{
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23656d76' d='M3 4.5L6 7.5L9 4.5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  padding-right: 24px;
}}

input[type="range"] {{
  -webkit-appearance: none;
  width: 100%;
  height: 3px;
  border-radius: 2px;
  background: var(--border);
  outline: none;
  border: none;
  margin: 6px 0;
}}

input[type="range"]::-webkit-slider-thumb {{
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  transition: transform var(--transition);
}}

input[type="range"]::-webkit-slider-thumb:hover {{ transform: scale(1.15); }}

.range-row {{ display: flex; align-items: center; gap: 8px; }}

.range-value {{
  font-size: 11px;
  font-weight: 500;
  color: var(--accent);
  min-width: 40px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}}

.param-color {{
  width: 100%;
  height: 30px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  padding: 2px;
  background: var(--bg-input);
}}

.param-color::-webkit-color-swatch-wrapper {{ padding: 0; }}
.param-color::-webkit-color-swatch {{ border: none; border-radius: 4px; }}

.param-checkbox {{
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
}}

.param-checkbox input {{ accent-color: var(--accent); width: 14px; height: 14px; }}
.param-checkbox span {{ font-size: 13px; }}

/* ── Main ─────────────────────────────────────────── */
.main {{
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}

/* ── Topbar ───────────────────────────────────────── */
.topbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  min-height: 41px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  gap: 10px;
}}

.topbar-left {{ display: flex; align-items: center; gap: 10px; }}

.topbar-title {{
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}}

.topbar-right {{ display: flex; align-items: center; gap: 6px; }}

/* ── Buttons ──────────────────────────────────────── */
.btn {{
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition);
  white-space: nowrap;
}}

.btn:hover {{ background: var(--bg-hover); border-color: #d0d4d9; }}

.btn-primary {{
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}}
.btn-primary:hover {{ background: #0860ca; }}

.toggle {{
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}}

.toggle input {{ accent-color: var(--accent); width: 13px; height: 13px; }}

.topbar-divider {{ width: 1px; height: 18px; background: var(--border); flex-shrink: 0; }}

.topbar-color {{
  width: 24px;
  height: 24px;
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  padding: 2px;
  background: var(--bg);
}}
.topbar-color::-webkit-color-swatch-wrapper {{ padding: 0; }}
.topbar-color::-webkit-color-swatch {{ border: none; border-radius: 2px; }}

/* Width slider in topbar */
.width-control {{
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-secondary);
}}

.width-control input[type="range"] {{
  width: 80px;
  margin: 0;
}}

.width-control span {{
  font-variant-numeric: tabular-nums;
  min-width: 32px;
}}

/* ── Tab bar ──────────────────────────────────────── */
.tab-bar {{
  display: flex;
  align-items: center;
  padding: 0 16px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  gap: 0;
  overflow-x: auto;
}}

.tab-bar::-webkit-scrollbar {{ height: 0; }}

.tab {{
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all var(--transition);
  white-space: nowrap;
  user-select: none;
}}

.tab:hover {{ color: var(--text-secondary); background: var(--bg-hover); }}

.tab.active {{
  color: var(--accent);
  border-bottom-color: var(--accent);
}}

.tab-close {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  font-size: 10px;
  opacity: 0;
  transition: opacity var(--transition);
}}

.tab:hover .tab-close {{ opacity: 0.5; }}
.tab-close:hover {{ opacity: 1 !important; background: rgba(207,34,46,0.1); color: var(--danger); }}

.tab-add {{
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  margin-left: 2px;
  border-radius: var(--radius);
  color: var(--text-muted);
  cursor: pointer;
  font-size: 14px;
  transition: all var(--transition);
  flex-shrink: 0;
}}

.tab-add:hover {{ color: var(--accent); background: var(--accent-light); }}

/* ── Figure area ──────────────────────────────────── */
.figure-area {{
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 24px 16px;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--bg-secondary);
}}

.figure-area::-webkit-scrollbar {{ width: 4px; }}
.figure-area::-webkit-scrollbar-track {{ background: transparent; }}
.figure-area::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}

.figure-container {{
  position: relative;
  background: var(--figure-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  transition: width var(--transition);
}}

.figure-container img {{
  display: block;
  width: 100%;
  height: auto;
}}

.figure-placeholder {{
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 280px;
  min-width: 460px;
  color: var(--text-muted);
  font-size: 13px;
}}

/* ── Loading ──────────────────────────────────────── */
.loading-overlay {{
  position: absolute;
  inset: 0;
  background: rgba(255,255,255,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
}}

.loading-overlay.active {{ opacity: 1; pointer-events: auto; }}

.spinner {{
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}}

@keyframes spin {{ to {{ transform: rotate(360deg); }} }}

/* ── Status ───────────────────────────────────────── */
.status {{
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 10px;
  font-weight: 500;
}}

.status-ok {{ background: rgba(26,127,55,0.08); color: var(--success); }}
.status-rendering {{ background: var(--accent-light); color: var(--accent); }}
.status-error {{ background: rgba(207,34,46,0.08); color: var(--danger); }}

/* ── Toast ────────────────────────────────────────── */
.toast-container {{
  position: fixed;
  bottom: 16px;
  right: 16px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 6px;
}}

.toast {{
  padding: 12px 20px;
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 500;
  animation: fadeInUp 0.25s ease;
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  min-width: 200px;
}}

.toast-success {{ background: #f0fdf4; border: 1px solid #bbf7d0; color: var(--success); }}
.toast-error {{ background: #fef2f2; border: 1px solid #fecaca; color: var(--danger); }}

@keyframes fadeInUp {{
  from {{ opacity: 0; transform: translateY(8px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

/* ── Modal ────────────────────────────────────────── */
.modal-overlay {{
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
}}

.modal-overlay.active {{ opacity: 1; pointer-events: auto; }}

.modal {{
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  min-width: 340px;
  max-width: 440px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}}

.modal h3 {{ font-size: 14px; font-weight: 600; margin-bottom: 14px; }}

.modal-actions {{ display: flex; gap: 6px; margin-top: 14px; justify-content: flex-end; }}

.preset-list {{ max-height: 200px; overflow-y: auto; margin: 6px 0; }}

.preset-item {{
  padding: 7px 10px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background var(--transition);
  font-size: 13px;
}}

.preset-item:hover {{ background: var(--accent-light); color: var(--accent); }}

/* ── Tooltip ──────────────────────────────────────── */
#tooltip {{
  position: fixed;
  padding: 5px 10px;
  background: var(--text);
  color: var(--bg);
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  border-radius: 4px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.1s;
  z-index: 1000;
}}

#tooltip.visible {{
  opacity: 1;
}}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="sidebar-header">
      <h2><i data-lucide="sliders-horizontal" style="width:14px;height:14px"></i> Parameters</h2>
    </div>
    <div class="sidebar-params" id="params-container"></div>
  </aside>

  <div class="main">
    <header class="topbar">
      <div class="topbar-left">
        <span class="topbar-title">{title}</span>
        <span class="status status-ok" id="status">Ready</span>
      </div>
      <div class="topbar-right">
        <label class="toggle" data-tip="Auto-redraw on parameter change">
          <input type="checkbox" id="auto-redraw" checked>
          Auto
        </label>
        <button class="btn" onclick="renderFigure()" data-tip="Re-render figure (Cmd+Enter)"><i data-lucide="refresh-cw" style="width:12px;height:12px"></i> Redraw</button>

        <span class="topbar-divider"></span>

        <button class="btn" onclick="showSaveModal()" data-tip="Save current parameters as preset"><i data-lucide="save" style="width:12px;height:12px"></i> Save</button>
        <button class="btn" onclick="showLoadModal()" data-tip="Load a saved preset"><i data-lucide="folder-open" style="width:12px;height:12px"></i> Load</button>

        <span class="topbar-divider"></span>

        <div class="width-control" data-tip="Adjust figure display width">
          <i data-lucide="arrows-horizontal" style="width:12px;height:12px"></i>
          <input type="range" id="fig-width" min="30" max="100" value="70" oninput="setFigureWidth(this.value)">
          <span id="fig-width-label">70%</span>
        </div>

        <span class="topbar-divider"></span>

        <label class="toggle" data-tip="Figure container background color">
          <input type="color" class="topbar-color" id="fig-bg-color" value="#ffffff"
                 onchange="setFigureBg(this.value)">
          BG
        </label>

        <span class="topbar-divider"></span>

        <select id="export-fmt" class="param-input param-select" data-tip="Image export format" style="width:60px;padding:4px 20px 4px 6px;font-size:11px">
          <option value="png">PNG</option>
          <option value="svg">SVG</option>
          <option value="pdf">PDF</option>
        </select>
        <button class="btn" onclick="exportFigure()" data-tip="Download image to browser"><i data-lucide="download" style="width:12px;height:12px"></i></button>
        <button class="btn" onclick="saveImageServer()" data-tip="Save image to server directory"><i data-lucide="hard-drive-download" style="width:12px;height:12px"></i></button>

        <span class="topbar-divider"></span>

        <button class="btn" onclick="downloadScript()" data-tip="Download Python reproduction script"><i data-lucide="file-code" style="width:12px;height:12px"></i> Script</button>
        <button class="btn" onclick="saveScriptServer()" data-tip="Save script to server directory"><i data-lucide="hard-drive-download" style="width:12px;height:12px"></i></button>

        <span class="topbar-divider"></span>

        <button class="btn" onclick="reloadServer()" data-tip="Reload server (pick up code changes)"><i data-lucide="rotate-cw" style="width:12px;height:12px"></i></button>
      </div>
    </header>

    <div class="tab-bar" id="tab-bar">
      <div class="tab-add" onclick="addTab()" title="New tab">+</div>
    </div>

    <div class="figure-area">
      <div class="figure-container" id="figure-container" style="width:70%">
        <div class="figure-placeholder" id="placeholder">Waiting for render...</div>
        <img id="figure-img" src="" alt="Figure" style="display:none">
        <div class="loading-overlay" id="loading"><div class="spinner"></div></div>
      </div>
    </div>
  </div>
</div>

<!-- Save modal -->
<div class="modal-overlay" id="save-modal">
  <div class="modal">
    <h3>Save Preset</h3>
    <label class="param-label">Name</label>
    <input type="text" class="param-input" id="preset-name" placeholder="My preset"
           onkeydown="if(event.key==='Enter'){{event.preventDefault();savePreset()}}">
    <div class="modal-actions">
      <button class="btn" onclick="closeSaveModal()">Cancel</button>
      <button class="btn btn-primary" onclick="savePreset()">Save</button>
    </div>
  </div>
</div>

<!-- Load modal -->
<div class="modal-overlay" id="load-modal">
  <div class="modal">
    <h3>Load Preset</h3>
    <div class="preset-list" id="preset-list">
      <div style="color:var(--text-muted);padding:16px;text-align:center">No presets yet</div>
    </div>
    <div class="modal-actions">
      <button class="btn" onclick="closeLoadModal()">Cancel</button>
    </div>
  </div>
</div>

<div class="toast-container" id="toast-container"></div>
<div id="tooltip"></div>

<script>
let descriptors = [];
let tabs = [{{ id: 1, name: "Tab 1", params: {{}} }}];
let activeTabId = 1;
let nextTabId = 2;
let renderTimer = null;
const DEBOUNCE_MS = 300;

async function init() {{
  const resp = await fetch("/api/descriptors");
  descriptors = await resp.json();

  const cfgResp = await fetch("/api/config");
  let saved = null;
  if (cfgResp.ok) {{
    const cfg = await cfgResp.json();
    if (cfg && cfg.params) saved = cfg.params;
  }}

  if (saved) tabs[0].params = saved;
  buildControls(saved);
  renderTabBar();
  renderFigure();
  lucide.createIcons();
}}

// ── Tabs ─────────────────────────────────────────────────
function getActiveTab() {{ return tabs.find(t => t.id === activeTabId); }}

function addTab() {{
  const tab = {{ id: nextTabId++, name: "Tab " + (tabs.length + 1), params: {{}} }};
  tabs.push(tab);
  switchTab(tab.id);
}}

function removeTab(id, e) {{
  if (e) e.stopPropagation();
  if (tabs.length <= 1) return;
  tabs = tabs.filter(t => t.id !== id);
  if (activeTabId === id) {{
    activeTabId = tabs[0].id;
    buildControls(getActiveTab().params);
    renderFigure();
  }}
  renderTabBar();
}}

function switchTab(id) {{
  saveCurrentParams();
  activeTabId = id;
  buildControls(getActiveTab().params);
  renderTabBar();
  renderFigure();
}}

function saveCurrentParams() {{
  const tab = getActiveTab();
  if (tab) tab.params = collectParams();
}}

function renderTabBar() {{
  const bar = document.getElementById("tab-bar");
  const addBtn = bar.querySelector(".tab-add");
  bar.querySelectorAll(".tab").forEach(el => el.remove());

  for (const t of tabs) {{
    const el = document.createElement("div");
    el.className = "tab" + (t.id === activeTabId ? " active" : "");
    el.onclick = () => switchTab(t.id);
    let closeHtml = tabs.length > 1
      ? `<span class="tab-close" onclick="removeTab(${{t.id}}, event)">&times;</span>`
      : "";
    el.innerHTML = t.name + closeHtml;
    bar.insertBefore(el, addBtn);
  }}
}}

// ── Controls ─────────────────────────────────────────────
function buildControls(overrides) {{
  const c = document.getElementById("params-container");
  c.innerHTML = "";

  for (const d of descriptors) {{
    const val = (overrides && overrides[d.name] !== undefined) ? overrides[d.name] : d.default;
    const g = document.createElement("div");
    g.className = "param-group";

    if (d.choices) {{
      g.innerHTML = `<label class="param-label">${{d.label}}</label>
        <select class="param-input param-select" data-name="${{d.name}}">
          ${{d.choices.map(c => `<option value="${{c}}" ${{c==val?"selected":""}}>${{c}}</option>`).join("")}}
        </select>`;
    }} else if (d.widget_hint === "color") {{
      g.innerHTML = `<label class="param-label">${{d.label}}</label>
        <input type="color" class="param-color" data-name="${{d.name}}" value="${{val||"#000000"}}">`;
    }} else if (d.type_name === "bool") {{
      g.innerHTML = `<label class="param-checkbox">
          <input type="checkbox" data-name="${{d.name}}" ${{val?"checked":""}}>
          <span>${{d.label}}</span></label>`;
    }} else if ((d.type_name==="int"||d.type_name==="float") && d.min_value!==null && d.max_value!==null) {{
      const step = d.step || (d.type_name==="int" ? 1 : 0.01);
      const disp = d.type_name==="float" ? Number(val).toFixed(2) : val;
      g.innerHTML = `<label class="param-label">${{d.label}}</label>
        <div class="range-row">
          <input type="range" data-name="${{d.name}}" data-type="${{d.type_name}}"
                 min="${{d.min_value}}" max="${{d.max_value}}" step="${{step}}" value="${{val}}">
          <span class="range-value" id="rv-${{d.name}}">${{disp}}</span></div>`;
    }} else if (d.type_name==="int"||d.type_name==="float") {{
      g.innerHTML = `<label class="param-label">${{d.label}}</label>
        <input type="number" class="param-input" data-name="${{d.name}}" data-type="${{d.type_name}}"
               value="${{val||0}}" step="${{d.step||(d.type_name==="int"?1:0.01)}}"
               ${{d.min_value!==null?`min="${{d.min_value}}"`:""}}
               ${{d.max_value!==null?`max="${{d.max_value}}"`:""}}>`;
    }} else {{
      g.innerHTML = `<label class="param-label">${{d.label}}</label>
        <input type="text" class="param-input" data-name="${{d.name}}" value="${{val||""}}">`;
    }}
    c.appendChild(g);
  }}

  c.querySelectorAll("[data-name]").forEach(el => {{
    const evt = el.type==="checkbox" ? "change" : el.type==="range" ? "input" : "change";
    el.addEventListener(evt, () => {{
      if (el.type==="range") {{
        const rv = document.getElementById("rv-"+el.dataset.name);
        if (rv) rv.textContent = el.dataset.type==="float" ? Number(el.value).toFixed(2) : el.value;
      }}
      saveCurrentParams();
      if (document.getElementById("auto-redraw").checked) debouncedRender();
    }});
  }});
}}

function collectParams() {{
  const p = {{}};
  document.querySelectorAll("[data-name]").forEach(el => {{
    const n = el.dataset.name;
    if (el.type==="checkbox") p[n] = el.checked;
    else if (el.type==="range"||el.type==="number") p[n] = el.dataset.type==="int" ? parseInt(el.value) : parseFloat(el.value);
    else p[n] = el.value;
  }});
  return p;
}}

// ── Render ────────────────────────────────────────────────
function debouncedRender() {{ clearTimeout(renderTimer); renderTimer = setTimeout(renderFigure, DEBOUNCE_MS); }}

async function renderFigure() {{
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  const loading = document.getElementById("loading");
  const img = document.getElementById("figure-img");
  const ph = document.getElementById("placeholder");
  const status = document.getElementById("status");

  loading.classList.add("active");
  status.textContent = "Rendering";
  status.className = "status status-rendering";

  try {{
    const resp = await fetch("/api/render", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify(params),
    }});
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    img.src = "data:image/png;base64," + data.image;
    img.style.display = "block";
    ph.style.display = "none";
    status.textContent = "Ready";
    status.className = "status status-ok";
  }} catch (err) {{
    status.textContent = "Error";
    status.className = "status status-error";
    toast("Render failed: " + err.message, "error");
  }} finally {{
    loading.classList.remove("active");
  }}
}}

// ── Figure size / bg ─────────────────────────────────────
function setFigureWidth(pct) {{
  document.getElementById("figure-container").style.width = pct + "%";
  document.getElementById("fig-width-label").textContent = pct + "%";
}}

function setFigureBg(color) {{
  document.getElementById("figure-container").style.backgroundColor = color;
}}

// ── Export ────────────────────────────────────────────────
async function exportFigure() {{
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  const fmt = document.getElementById("export-fmt").value;
  try {{
    const resp = await fetch("/api/export/" + fmt, {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify(params),
    }});
    if (!resp.ok) throw new Error(await resp.text());
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "figure." + fmt; a.click();
    URL.revokeObjectURL(url);
    toast("Exported as " + fmt.toUpperCase(), "success");
  }} catch (err) {{ toast("Export failed: " + err.message, "error"); }}
}}

async function saveImageServer() {{
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  const fmt = document.getElementById("export-fmt").value;
  try {{
    const resp = await fetch("/api/save-server/image/" + fmt, {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify(params),
    }});
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    toast("Saved to server: " + data.filename, "success");
  }} catch (err) {{ toast("Server save failed: " + err.message, "error"); }}
}}

async function downloadScript() {{
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  try {{
    const resp = await fetch("/api/script", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify(params),
    }});
    if (!resp.ok) throw new Error(await resp.text());
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "generate_figure.py"; a.click();
    URL.revokeObjectURL(url);
    toast("Script downloaded", "success");
  }} catch (err) {{ toast("Script failed: " + err.message, "error"); }}
}}

async function saveScriptServer() {{
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  try {{
    const resp = await fetch("/api/save-server/script", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify(params),
    }});
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    toast("Script saved: " + data.filename, "success");
  }} catch (err) {{ toast("Script save failed: " + err.message, "error"); }}
}}

// ── Presets ──────────────────────────────────────────────
function showSaveModal() {{ document.getElementById("save-modal").classList.add("active"); document.getElementById("preset-name").focus(); }}
function closeSaveModal() {{ document.getElementById("save-modal").classList.remove("active"); }}

async function savePreset() {{
  const modal = document.getElementById("save-modal");
  if (!modal.classList.contains("active")) return;
  const label = document.getElementById("preset-name").value.trim();
  if (!label) {{ toast("Enter a name", "error"); return; }}
  modal.classList.remove("active");
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  try {{
    await fetch("/api/preset", {{ method: "POST", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{ label, params }}) }});
    document.getElementById("preset-name").value = "";
    toast("Saved: " + label, "success");
  }} catch (err) {{ toast("Save failed", "error"); }}
}}

async function showLoadModal() {{
  const list = document.getElementById("preset-list");
  list.innerHTML = '<div style="color:var(--text-muted);padding:10px;text-align:center">Loading...</div>';
  document.getElementById("load-modal").classList.add("active");
  const resp = await fetch("/api/presets");
  const presets = await resp.json();
  if (!presets.length) {{
    list.innerHTML = '<div style="color:var(--text-muted);padding:16px;text-align:center">No presets</div>';
    return;
  }}
  list.innerHTML = presets.map((p, i) => `
    <div class="preset-item" onclick="loadPreset(${{i}})">
      <strong>${{p.label}}</strong>
      <span style="color:var(--text-muted);font-size:11px;margin-left:6px">${{p.timestamp?.slice(0,19)||""}}</span>
    </div>`).join("");
  window._presets = presets;
}}
function closeLoadModal() {{ document.getElementById("load-modal").classList.remove("active"); }}

function loadPreset(idx) {{
  const p = window._presets[idx];
  if (!p) return;
  const tab = getActiveTab();
  if (tab) tab.params = p.params;
  buildControls(p.params);
  renderFigure();
  closeLoadModal();
  toast("Loaded: " + p.label, "success");
}}

// ── Toast ────────────────────────────────────────────────
function toast(msg, type) {{
  const tc = document.getElementById("toast-container");
  const t = document.createElement("div"); t.className = "toast toast-" + type; t.textContent = msg;
  tc.appendChild(t);
  setTimeout(() => t.remove(), 6000);
}}

// ── Reload ───────────────────────────────────────────────
async function reloadServer() {{
  toast("Reloading server...", "success");
  try {{
    await fetch("/api/reload", {{ method: "POST" }});
  }} catch (e) {{}}
  // Poll until server is back
  const poll = setInterval(async () => {{
    try {{
      const r = await fetch("/api/descriptors");
      if (r.ok) {{
        clearInterval(poll);
        location.reload();
      }}
    }} catch (e) {{}}
  }}, 500);
}}

// ── Smart tooltip ─────────────────────────────────────────
{{
  const tip = document.getElementById("tooltip");
  document.addEventListener("mouseover", (e) => {{
    const el = e.target.closest("[data-tip]");
    if (!el) return;
    tip.textContent = el.getAttribute("data-tip");
    tip.classList.add("visible");
    const rect = el.getBoundingClientRect();
    const tipW = tip.offsetWidth;
    const vw = window.innerWidth;
    let left = rect.left + rect.width / 2 - tipW / 2;
    // Clamp to viewport edges with 6px margin
    if (left < 6) left = 6;
    if (left + tipW > vw - 6) left = vw - 6 - tipW;
    tip.style.top = (rect.bottom + 6) + "px";
    tip.style.left = left + "px";
  }});
  document.addEventListener("mouseout", (e) => {{
    const el = e.target.closest("[data-tip]");
    if (el) tip.classList.remove("visible");
  }});
}}

// ── Keyboard ─────────────────────────────────────────────
document.addEventListener("keydown", (e) => {{
  if ((e.metaKey||e.ctrlKey) && e.key === "Enter") {{ e.preventDefault(); renderFigure(); }}
}});

init();
</script>
</body>
</html>'''

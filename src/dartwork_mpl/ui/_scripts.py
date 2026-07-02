"""Client-side JavaScript for the Dartwork interactive figure viewer.

Extracted verbatim from ``_template.py``. Kept as a plain string (real
JS ``${{...}}`` template literals, no f-string brace doubling) so the
template module is readable. Assembled by :func:`_template.get_html`.
"""

JS_BLOCK = """
let descriptors = [];
// HTML-escape dynamic text before innerHTML interpolation (XSS guard
// for param labels, choices, group names, preset names, free-text
// values — some of which come from on-disk preset JSON).
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[ch]);
}
let tabs = [{ id: 1, name: "Tab 1", params: {} }];
let activeTabId = 1;
let nextTabId = 2;
let renderTimer = null;
let saveStateTimer = null;
let _functionName = "figure";
const DEBOUNCE_MS = 300;
const SAVE_STATE_MS = 1000;

async function init() {
  const resp = await fetch("/api/descriptors");
  descriptors = await resp.json();

  // Load function meta
  try {
    const metaResp = await fetch("/api/meta");
    if (metaResp.ok) {
      const meta = await metaResp.json();
      if (meta.function_name) _functionName = meta.function_name;
    }
  } catch (e) {}

  // Load saved config (params + tabs + figWidth)
  const cfgResp = await fetch("/api/config");
  let saved = null;
  let savedFigWidth = null;
  if (cfgResp.ok) {
    const cfg = await cfgResp.json();
    if (cfg && cfg.params) saved = cfg.params;
    if (cfg && cfg.tabs && cfg.tabs.length) {
      tabs = cfg.tabs;
      activeTabId = tabs[0].id;
      nextTabId = Math.max(...tabs.map(t => t.id)) + 1;
    }
    if (cfg && cfg.figWidth) savedFigWidth = cfg.figWidth;
  }

  const activeTab = getActiveTab();
  const hasTabParams = activeTab && activeTab.params && Object.keys(activeTab.params).length > 0;
  const overrides = hasTabParams ? activeTab.params : saved;
  if (saved && !hasTabParams) tabs[0].params = saved;
  buildControls(overrides);
  renderTabBar();
  renderFigure();
  if (savedFigWidth) setFigureWidth(savedFigWidth);
  lucide.createIcons();
  startHeartbeat();
}

// ── Tabs ─────────────────────────────────────────────────
function getActiveTab() { return tabs.find(t => t.id === activeTabId); }

function addTab() {
  const tab = { id: nextTabId++, name: "Tab " + (tabs.length + 1), params: {} };
  tabs.push(tab);
  switchTab(tab.id);
}

function removeTab(id, e) {
  if (e) e.stopPropagation();
  if (tabs.length <= 1) return;
  tabs = tabs.filter(t => t.id !== id);
  if (activeTabId === id) {
    activeTabId = tabs[0].id;
    buildControls(getActiveTab().params);
    renderFigure();
  }
  renderTabBar();
  debouncedSaveState();
}

function switchTab(id) {
  saveCurrentParams();
  activeTabId = id;
  const tab = getActiveTab();
  buildControls(tab.params);
  renderTabBar();

  // Show cached image instantly if available
  const img = document.getElementById("figure-img");
  const ph = document.getElementById("placeholder");
  if (tab._cachedImage) {
    img.src = tab._cachedImage;
    img.style.display = "block";
    ph.style.display = "none";
  } else {
    renderFigure();
  }
}

function saveCurrentParams() {
  const tab = getActiveTab();
  if (tab) {
    const oldParams = JSON.stringify(tab.params);
    tab.params = collectParams();
    // Invalidate cache if params changed
    if (JSON.stringify(tab.params) !== oldParams) {
      tab._cachedImage = null;
    }
  }
  debouncedSaveState();
}

function debouncedSaveState() {
  clearTimeout(saveStateTimer);
  saveStateTimer = setTimeout(persistState, SAVE_STATE_MS);
}

async function persistState() {
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  // Strip cached images before saving
  const cleanTabs = tabs.map(t => ({ id: t.id, name: t.name, params: t.params }));
  try {
    await fetch("/api/save-state", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ params, tabs: cleanTabs, figWidth: parseInt(document.getElementById("fig-width").value) }),
    });
  } catch (e) {}
}

function renderTabBar() {
  const bar = document.getElementById("tab-bar");
  const addBtn = bar.querySelector(".tab-add");
  bar.querySelectorAll(".tab").forEach(el => el.remove());

  for (const t of tabs) {
    const el = document.createElement("div");
    el.className = "tab" + (t.id === activeTabId ? " active" : "");
    el.onclick = () => switchTab(t.id);

    const nameSpan = document.createElement("span");
    nameSpan.className = "tab-name";
    nameSpan.textContent = t.name;
    el.appendChild(nameSpan);

    if (t.id === activeTabId) {
      const renameBtn = document.createElement("span");
      renameBtn.className = "tab-rename";
      renameBtn.innerHTML = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>';
      renameBtn.onclick = (e) => { e.stopPropagation(); renameTab(t.id, el); };
      el.appendChild(renameBtn);
    }

    if (tabs.length > 1) {
      const closeBtn = document.createElement("span");
      closeBtn.className = "tab-close";
      closeBtn.innerHTML = "&times;";
      closeBtn.onclick = (e) => removeTab(t.id, e);
      el.appendChild(closeBtn);
    }

    bar.insertBefore(el, addBtn);
  }
}

function renameTab(id, tabEl) {
  const tab = tabs.find(t => t.id === id);
  if (!tab) return;
  const nameSpan = tabEl.querySelector(".tab-name");
  const input = document.createElement("input");
  input.type = "text";
  input.value = tab.name;
  input.style.cssText = "width:80px;font-size:12px;border:1px solid var(--border-focus);border-radius:3px;padding:1px 4px;outline:none;font-family:var(--font);background:var(--bg)";
  nameSpan.replaceWith(input);
  input.focus();
  input.select();
  const finish = () => {
    tab.name = input.value.trim() || tab.name;
    renderTabBar();
    debouncedSaveState();
  };
  input.addEventListener("blur", finish);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); input.blur(); }
    if (e.key === "Escape") { input.value = tab.name; input.blur(); }
  });
}

// ── Controls ─────────────────────────────────────────────────
function buildControlWidget(d, val) {
  const g = document.createElement("div");
  g.className = "param-group";

  if (d.choices) {
    g.innerHTML = `<label class="param-label">${esc(d.label)}</label>
      <select class="param-input param-select" data-name="${esc(d.name)}">
        ${d.choices.map(c => `<option value="${esc(c)}" ${c==val?"selected":""}>${esc(c)}</option>`).join("")}
      </select>`;
  } else if (d.widget_hint === "color") {
    g.innerHTML = `<label class="param-label">${esc(d.label)}</label>
      <input type="color" class="param-color" data-name="${esc(d.name)}" value="${esc(val||"#000000")}">`;
  } else if (d.type_name === "bool") {
    g.innerHTML = `<label class="param-checkbox">
        <input type="checkbox" data-name="${esc(d.name)}" ${val?"checked":""}>
        <span>${esc(d.label)}</span></label>`;
  } else if ((d.type_name==="int"||d.type_name==="float") && d.min_value!==null && d.max_value!==null) {
    const step = d.step || (d.type_name==="int" ? 1 : 0.01);
    const disp = d.type_name==="float" ? Number(val).toFixed(2) : val;
    g.innerHTML = `<label class="param-label">${esc(d.label)}</label>
      <div class="range-row">
        <input type="range" data-name="${esc(d.name)}" data-type="${d.type_name}"
               min="${d.min_value}" max="${d.max_value}" step="${step}" value="${esc(val)}">
        <span class="range-value" id="rv-${esc(d.name)}">${esc(disp)}</span></div>`;
  } else if (d.type_name==="int"||d.type_name==="float") {
    g.innerHTML = `<label class="param-label">${esc(d.label)}</label>
      <input type="number" class="param-input" data-name="${esc(d.name)}" data-type="${d.type_name}"
             value="${esc(val||0)}" step="${d.step||(d.type_name==="int"?1:0.01)}"
             ${d.min_value!==null?`min="${d.min_value}"`:""}
             ${d.max_value!==null?`max="${d.max_value}"`:""}>` ;
  } else {
    g.innerHTML = `<label class="param-label">${esc(d.label)}</label>
      <input type="text" class="param-input" data-name="${esc(d.name)}" value="${esc(val||"")}">` ;
  }
  return g;
}

function buildControls(overrides) {
  const c = document.getElementById("params-container");
  c.innerHTML = "";

  // Group descriptors
  const groups = new Map(); // group name -> descriptors
  const ungrouped = [];
  for (const d of descriptors) {
    if (d.group) {
      if (!groups.has(d.group)) groups.set(d.group, []);
      groups.get(d.group).push(d);
    } else {
      ungrouped.push(d);
    }
  }

  // Render ungrouped first
  for (const d of ungrouped) {
    const val = (overrides && overrides[d.name] !== undefined) ? overrides[d.name] : d.default;
    c.appendChild(buildControlWidget(d, val));
  }

  // Render grouped sections
  for (const [groupName, items] of groups) {
    const header = document.createElement("div");
    header.className = "param-section-header";
    header.innerHTML = `<svg class="chevron" width="10" height="10" viewBox="0 0 10 10"><path d="M3 2L7 5L3 8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>${esc(groupName)}`;

    const body = document.createElement("div");
    body.className = "param-section-body";

    for (const d of items) {
      const val = (overrides && overrides[d.name] !== undefined) ? overrides[d.name] : d.default;
      body.appendChild(buildControlWidget(d, val));
    }

    header.addEventListener("click", () => {
      header.classList.toggle("collapsed");
      body.classList.toggle("collapsed");
    });

    c.appendChild(header);
    c.appendChild(body);
  }

  // Bind events
  c.querySelectorAll("[data-name]").forEach(el => {
    const evt = el.type==="checkbox" ? "change" : el.type==="range" ? "input" : "change";
    el.addEventListener(evt, () => {
      if (el.type==="range") {
        const rv = document.getElementById("rv-"+el.dataset.name);
        if (rv) rv.textContent = el.dataset.type==="float" ? Number(el.value).toFixed(2) : el.value;
      }
      saveCurrentParams();
      if (document.getElementById("auto-redraw").checked) debouncedRender();
    });
  });
}

function collectParams() {
  const p = {};
  document.querySelectorAll("#params-container [data-name]").forEach(el => {
    const n = el.dataset.name;
    if (el.type==="checkbox") p[n] = el.checked;
    else if (el.type==="range"||el.type==="number") p[n] = el.dataset.type==="int" ? parseInt(el.value) : parseFloat(el.value);
    else p[n] = el.value;
  });
  return p;
}

// ── Reset ─────────────────────────────────────────────────
async function resetDefaults() {
  try {
    const resp = await fetch("/api/defaults");
    if (!resp.ok) throw new Error(await resp.text());
    const defaults = await resp.json();
    const tab = getActiveTab();
    if (tab) tab.params = defaults;
    buildControls(defaults);
    renderFigure();
    toast("Reset to defaults", "success");
  } catch (err) { toast("Reset failed: " + err.message, "error"); }
}

// ── Render ────────────────────────────────────────────────
function debouncedRender() { clearTimeout(renderTimer); renderTimer = setTimeout(renderFigure, DEBOUNCE_MS); }

async function renderFigure() {
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  const loading = document.getElementById("loading");
  const img = document.getElementById("figure-img");
  const ph = document.getElementById("placeholder");
  const status = document.getElementById("status");

  loading.classList.add("active");
  status.textContent = "Rendering";
  status.className = "status status-rendering";

  try {
    const resp = await fetch("/api/render", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(params),
    });
    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.detail || resp.statusText);
    }
    const data = await resp.json();
    const imgSrc = "data:image/png;base64," + data.image;
    img.src = imgSrc;
    img.style.display = "block";
    ph.style.display = "none";
    status.textContent = "Ready";
    status.className = "status status-ok";
    // Cache rendered image on active tab
    const tab = getActiveTab();
    if (tab) tab._cachedImage = imgSrc;
  } catch (err) {
    status.textContent = "Error";
    status.className = "status status-error";
    toast("Render failed: " + err.message, "error");
  } finally {
    loading.classList.remove("active");
  }
}

// ── Figure size / bg ─────────────────────────────────────
function setFigureWidth(pct) {
  document.getElementById("figure-container").style.width = pct + "%";
  document.getElementById("fig-width-label").textContent = pct + "%";
  document.getElementById("fig-width").value = pct;
  debouncedSaveState();
}

function zoomFigure(delta) {
  const slider = document.getElementById("fig-width");
  const v = Math.min(100, Math.max(30, parseInt(slider.value) + delta));
  setFigureWidth(v);
}

function setFigureBg(color) {
  document.getElementById("figure-container").style.backgroundColor = color;
}

// ── Export ────────────────────────────────────────────────
async function exportFigure() {
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  const fmt = document.getElementById("export-fmt").value;
  try {
    const resp = await fetch("/api/export/" + fmt, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(params),
    });
    if (!resp.ok) throw new Error(await resp.text());
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "figure." + fmt; a.click();
    URL.revokeObjectURL(url);
    toast("Exported as " + fmt.toUpperCase(), "success");
  } catch (err) { toast("Export failed: " + err.message, "error"); }
}

// ── Server save (with filename modal) ─────────────────
let _filenameCb = null;

function showFilenameModal(title, defaultName, cb) {
  document.getElementById("filename-modal-title").textContent = title;
  const input = document.getElementById("filename-input");
  input.value = defaultName;
  _filenameCb = cb;
  document.getElementById("filename-modal").classList.add("active");
  input.focus();
  input.select();
}

function closeFilenameModal() {
  document.getElementById("filename-modal").classList.remove("active");
  _filenameCb = null;
}

function confirmFilenameModal() {
  const name = document.getElementById("filename-input").value.trim();
  const cb = _filenameCb;
  closeFilenameModal();
  if (cb) cb(name || null);
}

function showSaveImageModal() {
  const fmt = document.getElementById("export-fmt").value;
  showFilenameModal("Save Image to Server", _functionName + "." + fmt, (filename) => {
    _doSaveImageServer(filename);
  });
}

function showSaveScriptModal() {
  showFilenameModal("Save Script to Server", _functionName + ".py", (filename) => {
    _doSaveScriptServer(filename);
  });
}

async function _doSaveImageServer(filename) {
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  const fmt = document.getElementById("export-fmt").value;
  try {
    const resp = await fetch("/api/save-server/image/" + fmt, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ params, filename }),
    });
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    const paths = [data.path];
    if (data.copied_to) paths.push(...data.copied_to);
    toast("Saved:\\n" + paths.join("\\n"), "success");
  } catch (err) { toast("Server save failed: " + err.message, "error"); }
}

async function _doSaveScriptServer(filename) {
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  try {
    const resp = await fetch("/api/save-server/script", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ params, filename }),
    });
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    toast("Script saved: " + data.filename, "success");
  } catch (err) { toast("Script save failed: " + err.message, "error"); }
}

async function downloadScript() {
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  try {
    const resp = await fetch("/api/script", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(params),
    });
    if (!resp.ok) throw new Error(await resp.text());
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "generate_figure.py"; a.click();
    URL.revokeObjectURL(url);
    toast("Script downloaded", "success");
  } catch (err) { toast("Script failed: " + err.message, "error"); }
}

// ── Presets ──────────────────────────────────────────────
function showSaveModal() { document.getElementById("save-modal").classList.add("active"); document.getElementById("preset-name").focus(); }
function closeSaveModal() { document.getElementById("save-modal").classList.remove("active"); }

async function savePreset() {
  const modal = document.getElementById("save-modal");
  if (!modal.classList.contains("active")) return;
  const label = document.getElementById("preset-name").value.trim();
  if (!label) { toast("Enter a name", "error"); return; }
  modal.classList.remove("active");
  const tab = getActiveTab();
  const params = tab ? tab.params : collectParams();
  try {
    await fetch("/api/preset", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ label, params }) });
    document.getElementById("preset-name").value = "";
    toast("Saved: " + label, "success");
  } catch (err) { toast("Save failed", "error"); }
}

async function showLoadModal() {
  const list = document.getElementById("preset-list");
  list.innerHTML = '<div style="color:var(--text-muted);padding:10px;text-align:center">Loading...</div>';
  document.getElementById("load-modal").classList.add("active");
  const resp = await fetch("/api/presets");
  const presets = await resp.json();
  if (!presets.length) {
    list.innerHTML = '<div style="color:var(--text-muted);padding:16px;text-align:center">No presets</div>';
    return;
  }
  list.innerHTML = presets.map((p, i) => `
    <div class="preset-item">
      <span onclick="loadPreset(${i})" style="flex:1;cursor:pointer">
        <strong>${esc(p.label)}</strong>
        <span style="color:var(--text-muted);font-size:11px;margin-left:6px">${p.timestamp?.slice(0,19)||""}</span>
      </span>
      <button class="preset-delete" onclick="deletePreset(${i}, event)" title="Delete">&times;</button>
    </div>`).join("");
  window._presets = presets;
}
function closeLoadModal() { document.getElementById("load-modal").classList.remove("active"); }

function loadPreset(idx) {
  const p = window._presets[idx];
  if (!p) return;
  const tab = getActiveTab();
  if (tab) tab.params = p.params;
  buildControls(p.params);
  renderFigure();
  closeLoadModal();
  toast("Loaded: " + p.label, "success");
}

async function deletePreset(idx, e) {
  if (e) e.stopPropagation();
  try {
    const resp = await fetch("/api/preset/" + idx, { method: "DELETE" });
    if (!resp.ok) throw new Error(await resp.text());
    toast("Preset deleted", "success");
    showLoadModal(); // Refresh
  } catch (err) { toast("Delete failed: " + err.message, "error"); }
}

// ── Toast ────────────────────────────────────────────────
function toast(msg, type) {
  const tc = document.getElementById("toast-container");
  const t = document.createElement("div"); t.className = "toast toast-" + type; t.textContent = msg;
  tc.appendChild(t);
  setTimeout(() => t.remove(), 6000);
}

// ── Reload ───────────────────────────────────────────────
async function reloadServer() {
  toast("Reloading server...", "success");
  try {
    await fetch("/api/reload", { method: "POST" });
  } catch (e) {}
  // Poll until server is back
  const poll = setInterval(async () => {
    try {
      const r = await fetch("/api/descriptors");
      if (r.ok) {
        clearInterval(poll);
        location.reload();
      }
    } catch (e) {}
  }, 500);
}

// ── Smart tooltip ─────────────────────────────────────────
{
  const tip = document.getElementById("tooltip");
  document.addEventListener("mouseover", (e) => {
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
  });
  document.addEventListener("mouseout", (e) => {
    const el = e.target.closest("[data-tip]");
    if (el) tip.classList.remove("visible");
  });
}

// ── Heartbeat (server connection check) ─────────────────
let heartbeatInterval = null;
let isDisconnected = false;
const HEARTBEAT_NORMAL_MS = 3000;
const HEARTBEAT_RETRY_MS = 1000;

function startHeartbeat() {
  heartbeatInterval = setInterval(checkConnection, HEARTBEAT_NORMAL_MS);
}

async function checkConnection() {
  try {
    const resp = await fetch("/api/health", { signal: AbortSignal.timeout(2000) });
    if (resp.ok && isDisconnected) {
      // Reconnected
      isDisconnected = false;
      document.getElementById("disconnect-overlay").classList.remove("active");
      clearInterval(heartbeatInterval);
      heartbeatInterval = setInterval(checkConnection, HEARTBEAT_NORMAL_MS);
      toast("Reconnected to server", "success");
      renderFigure();
    }
  } catch (e) {
    if (!isDisconnected) {
      isDisconnected = true;
      document.getElementById("disconnect-overlay").classList.add("active");
      lucide.createIcons({ nodes: document.querySelectorAll("#disconnect-overlay [data-lucide]") });
      clearInterval(heartbeatInterval);
      heartbeatInterval = setInterval(checkConnection, HEARTBEAT_RETRY_MS);
    }
  }
}

// ── Help ────────────────────────────────────────────────
function toggleHelp() { document.getElementById("help-modal").classList.toggle("active"); }
function closeHelp() { document.getElementById("help-modal").classList.remove("active"); }

// ── Keyboard ─────────────────────────────────────────────
function _isModalOpen() {
  return !!document.querySelector(".modal-overlay.active");
}

document.addEventListener("keydown", (e) => {
  // Esc closes any open modal
  if (e.key === "Escape") {
    document.querySelectorAll(".modal-overlay.active").forEach(m => m.classList.remove("active"));
    return;
  }
  // ? toggles help (only when not in an input)
  if (e.key === "?" && !e.metaKey && !e.ctrlKey && e.target.tagName !== "INPUT" && e.target.tagName !== "TEXTAREA" && e.target.tagName !== "SELECT") {
    e.preventDefault(); toggleHelp(); return;
  }
  // Skip shortcuts while a modal is open (except Esc handled above)
  if (_isModalOpen()) return;
  const mod = e.metaKey || e.ctrlKey;
  if (mod && e.shiftKey && e.key === "S") { e.preventDefault(); showSaveImageModal(); return; }
  if (mod && e.shiftKey && e.key === "D") { e.preventDefault(); showSaveScriptModal(); return; }
  if (mod && e.shiftKey && e.key === "R") { e.preventDefault(); resetDefaults(); return; }
  if (mod && e.key === "Enter") { e.preventDefault(); renderFigure(); return; }
  if (mod && e.key === "s") { e.preventDefault(); showSaveModal(); return; }
  if (mod && e.key === "l") { e.preventDefault(); showLoadModal(); return; }
  if (mod && e.key === "e") { e.preventDefault(); exportFigure(); return; }
  if (mod && e.key === "d") { e.preventDefault(); downloadScript(); return; }
  if (mod && e.key === "r") { e.preventDefault(); reloadServer(); return; }
  if (mod && e.key === "t") { e.preventDefault(); addTab(); return; }
  if (mod && (e.key === "=" || e.key === "+")) { e.preventDefault(); zoomFigure(5); return; }
  if (mod && e.key === "-") { e.preventDefault(); zoomFigure(-5); return; }
});

init();
"""

"""CSS for the Dartwork interactive figure viewer.

Extracted verbatim from ``_template.py`` so the stylesheet lives as a
plain string (no f-string ``{{ }}`` escaping) and the template module
stays small. Assembled back in by :func:`_template.get_html`.
"""

CSS_BLOCK = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
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
}

html, body {
  height: 100%;
  font-family: var(--font);
  font-size: 13px;
  color: var(--text);
  background: var(--bg);
  overflow: hidden;
}

/* ── Layout ───────────────────────────────────────── */
.app { display: flex; height: 100vh; }

/* ── Sidebar ──────────────────────────────────────── */
.sidebar {
  width: var(--sidebar-w);
  min-width: var(--sidebar-w);
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 0 14px;
  min-height: 41px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.sidebar-header h2 {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: 6px;
}

.sidebar-params {
  flex: 1;
  overflow-y: auto;
  padding: 10px 14px;
}

.sidebar-params::-webkit-scrollbar { width: 3px; }
.sidebar-params::-webkit-scrollbar-track { background: transparent; }
.sidebar-params::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* ── Controls ─────────────────────────────────────── */
.param-group { margin-bottom: 14px; }

.param-section-header {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 0;
  margin-top: 8px;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid var(--border);
  margin-bottom: 8px;
}

.param-section-header:hover { color: var(--text-secondary); }

.param-section-header .chevron {
  transition: transform var(--transition);
  flex-shrink: 0;
}

.param-section-header.collapsed .chevron {
  transform: rotate(-90deg);
}

.param-section-body {
  overflow: hidden;
  transition: max-height 0.2s ease;
}

.param-section-body.collapsed {
  max-height: 0 !important;
  overflow: hidden;
}

.param-label {
  display: block;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.param-input {
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
}

.param-input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 2px var(--accent-light);
}

.param-select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23656d76' d='M3 4.5L6 7.5L9 4.5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  padding-right: 24px;
}

input[type="range"] {
  -webkit-appearance: none;
  width: 100%;
  height: 3px;
  border-radius: 2px;
  background: var(--border);
  outline: none;
  border: none;
  margin: 6px 0;
}

input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  transition: transform var(--transition);
}

input[type="range"]::-webkit-slider-thumb:hover { transform: scale(1.15); }

.range-row { display: flex; align-items: center; gap: 8px; }

.range-value {
  font-size: 11px;
  font-weight: 500;
  color: var(--accent);
  min-width: 40px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.param-color {
  width: 100%;
  height: 30px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  padding: 2px;
  background: var(--bg-input);
}

.param-color::-webkit-color-swatch-wrapper { padding: 0; }
.param-color::-webkit-color-swatch { border: none; border-radius: 4px; }

.param-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
}

.param-checkbox input { accent-color: var(--accent); width: 14px; height: 14px; }
.param-checkbox span { font-size: 13px; }

/* ── Main ─────────────────────────────────────────── */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Topbar ───────────────────────────────────────── */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  min-height: 41px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  gap: 10px;
}

.topbar-left { display: flex; align-items: center; gap: 10px; }

.topbar-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.topbar-right { display: flex; align-items: center; gap: 6px; }

/* ── Buttons ──────────────────────────────────────── */
.btn {
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
}

.btn:hover { background: var(--bg-hover); border-color: #d0d4d9; }

.btn-primary {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.btn-primary:hover { background: #0860ca; }

.toggle {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}

.toggle input { accent-color: var(--accent); width: 13px; height: 13px; }

.topbar-divider { width: 1px; height: 18px; background: var(--border); flex-shrink: 0; }

.topbar-color {
  width: 24px;
  height: 24px;
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  padding: 2px;
  background: var(--bg);
}
.topbar-color::-webkit-color-swatch-wrapper { padding: 0; }
.topbar-color::-webkit-color-swatch { border: none; border-radius: 2px; }

/* Width slider in topbar */
.width-control {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-secondary);
}

.width-control input[type="range"] {
  width: 80px;
  margin: 0;
}

.width-control span {
  font-variant-numeric: tabular-nums;
  min-width: 32px;
}

/* ── Tab bar ──────────────────────────────────────── */
.tab-bar {
  display: flex;
  align-items: center;
  padding: 0 16px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  gap: 0;
  overflow-x: auto;
}

.tab-bar::-webkit-scrollbar { height: 0; }

.tab {
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
}

.tab:hover { color: var(--text-secondary); background: var(--bg-hover); }

.tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.tab-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  font-size: 10px;
  opacity: 0;
  transition: opacity var(--transition);
}

.tab:hover .tab-close { opacity: 0.5; }
.tab-close:hover { opacity: 1 !important; background: rgba(207,34,46,0.1); color: var(--danger); }

.tab-rename {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  opacity: 0;
  cursor: pointer;
  transition: opacity var(--transition);
}

.tab:hover .tab-rename { opacity: 0.4; }
.tab-rename:hover { opacity: 1 !important; color: var(--accent); }

.tab-add {
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
}

.tab-add:hover { color: var(--accent); background: var(--accent-light); }

/* ── Figure area ──────────────────────────────────── */
.figure-area {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 24px 16px;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--bg-secondary);
}

.figure-area::-webkit-scrollbar { width: 4px; }
.figure-area::-webkit-scrollbar-track { background: transparent; }
.figure-area::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

.figure-container {
  position: relative;
  background: var(--figure-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  transition: width var(--transition);
}

.figure-container img {
  display: block;
  width: 100%;
  height: auto;
}

.figure-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 280px;
  min-width: 460px;
  color: var(--text-muted);
  font-size: 13px;
  gap: 10px;
  text-align: center;
  padding: 32px;
}

.onboarding-hints {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.6;
}

.onboarding-hints kbd {
  display: inline-block;
  padding: 1px 5px;
  font-size: 10px;
  font-family: var(--font);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 3px;
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
}

/* ── Loading ──────────────────────────────────────── */
.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255,255,255,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
}

.loading-overlay.active { opacity: 1; pointer-events: auto; }

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ── Status ───────────────────────────────────────── */
.status {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 10px;
  font-weight: 500;
}

.status-ok { background: rgba(26,127,55,0.08); color: var(--success); }
.status-rendering { background: var(--accent-light); color: var(--accent); }
.status-error { background: rgba(207,34,46,0.08); color: var(--danger); }

/* ── Toast ────────────────────────────────────────── */
.toast-container {
  position: fixed;
  bottom: 16px;
  right: 16px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.toast {
  padding: 12px 20px;
  border-radius: var(--radius);
  font-size: 12px;
  font-weight: 500;
  animation: fadeInUp 0.25s ease;
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  min-width: 200px;
  white-space: pre-line;
}

.toast-success { background: #f0fdf4; border: 1px solid #bbf7d0; color: var(--success); }
.toast-error { background: #fef2f2; border: 1px solid #fecaca; color: var(--danger); }

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Modal ────────────────────────────────────────── */
.modal-overlay {
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
}

.modal-overlay.active { opacity: 1; pointer-events: auto; }

.modal {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  min-width: 340px;
  max-width: 440px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}

.modal h3 { font-size: 14px; font-weight: 600; margin-bottom: 14px; }

.modal-actions { display: flex; gap: 6px; margin-top: 14px; justify-content: flex-end; }

.preset-list { max-height: 200px; overflow-y: auto; margin: 6px 0; }

.preset-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background var(--transition);
  font-size: 13px;
}

.preset-item:hover { background: var(--accent-light); color: var(--accent); }

.preset-delete {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 3px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 11px;
  flex-shrink: 0;
  opacity: 0;
  transition: all var(--transition);
}

.preset-item:hover .preset-delete { opacity: 0.6; }
.preset-delete:hover { opacity: 1 !important; background: rgba(207,34,46,0.1); color: var(--danger); }

/* ── Tooltip ──────────────────────────────────────── */
#tooltip {
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
}

#tooltip.visible {
  opacity: 1;
}

/* ── Disconnect overlay ──────────────────────────── */
.disconnect-overlay {
  position: fixed;
  inset: 0;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.disconnect-overlay.active {
  display: flex;
}

.disconnect-modal {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px 28px;
  text-align: center;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  min-width: 280px;
}

.disconnect-modal .disconnect-icon {
  color: var(--text-muted);
  margin-bottom: 12px;
}

.disconnect-modal h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.disconnect-modal p {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 16px;
  line-height: 1.4;
}

.disconnect-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
}

.disconnect-status .spinner {
  width: 12px;
  height: 12px;
}
"""

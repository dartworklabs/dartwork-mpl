"""HTML template for the Dartwork interactive figure viewer.

Light corporate theme with Lucide icons. No gradients, no emojis.
"""

import html

from ._scripts import JS_BLOCK
from ._styles import CSS_BLOCK


def get_html(title: str = "Dartwork Viewer") -> str:
    """Return the complete HTML page as a string.

    Parameters
    ----------
    title : str, optional
        Page title. Default is ``"Dartwork Viewer"``.

    Returns
    ----------
    str
        Full HTML document string.
    """
    # Escape the caller-supplied title before interpolating it into the
    # <title> / topbar markup (reflected-XSS guard — title is a public
    # ``run(title=...)`` argument).
    title = html.escape(title, quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<!-- Pinned (not @latest) for reproducible builds + supply-chain safety. -->
<script src="https://unpkg.com/lucide@1.17.0/dist/umd/lucide.min.js"></script>
<style>{CSS_BLOCK}</style>
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
        <button class="btn" onclick="renderFigure()" data-tip="Redraw (Cmd+Enter)"><i data-lucide="refresh-cw" style="width:12px;height:12px"></i> Redraw</button>
        <button class="btn" onclick="resetDefaults()" data-tip="Reset to defaults (Cmd+Shift+R)"><i data-lucide="undo-2" style="width:12px;height:12px"></i> Reset</button>

        <span class="topbar-divider"></span>

        <button class="btn" onclick="showSaveModal()" data-tip="Save preset (Cmd+S)"><i data-lucide="save" style="width:12px;height:12px"></i> Save</button>
        <button class="btn" onclick="showLoadModal()" data-tip="Load preset (Cmd+L)"><i data-lucide="folder-open" style="width:12px;height:12px"></i> Load</button>

        <span class="topbar-divider"></span>

        <div class="width-control" data-tip="Figure width (Cmd+Plus / Cmd+Minus)">
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
        <button class="btn" onclick="exportFigure()" data-tip="Download image (Cmd+E)"><i data-lucide="download" style="width:12px;height:12px"></i></button>
        <button class="btn" onclick="showSaveImageModal()" data-tip="Save image to server (Cmd+Shift+S)"><i data-lucide="hard-drive-download" style="width:12px;height:12px"></i></button>

        <span class="topbar-divider"></span>

        <button class="btn" onclick="downloadScript()" data-tip="Download script (Cmd+D)"><i data-lucide="file-code" style="width:12px;height:12px"></i> Script</button>
        <button class="btn" onclick="showSaveScriptModal()" data-tip="Save script to server (Cmd+Shift+D)"><i data-lucide="hard-drive-download" style="width:12px;height:12px"></i></button>

        <span class="topbar-divider"></span>

        <button class="btn" onclick="reloadServer()" data-tip="Reload server (Cmd+R)"><i data-lucide="rotate-cw" style="width:12px;height:12px"></i></button>
        <button class="btn" onclick="toggleHelp()" data-tip="Shortcuts (?)"><i data-lucide="help-circle" style="width:12px;height:12px"></i></button>
      </div>
    </header>

    <div class="tab-bar" id="tab-bar">
      <div class="tab-add" onclick="addTab()" title="New tab">+</div>
    </div>

    <div class="figure-area">
      <div class="figure-container" id="figure-container" style="width:70%">
        <div class="figure-placeholder" id="placeholder">
          <i data-lucide="image" style="width:24px;height:24px;opacity:0.4"></i>
          <div>Adjust parameters in the sidebar — the figure updates automatically.</div>
          <div class="onboarding-hints">
            <kbd>Cmd+Enter</kbd> Redraw &nbsp;&middot;&nbsp; <kbd>Cmd+S</kbd> Save preset &nbsp;&middot;&nbsp; <kbd>Cmd+E</kbd> Export
          </div>
        </div>
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

<!-- Server save filename modal -->
<div class="modal-overlay" id="filename-modal">
  <div class="modal">
    <h3 id="filename-modal-title">Save to Server</h3>
    <label class="param-label">Filename</label>
    <input type="text" class="param-input" id="filename-input" placeholder="figure"
           onkeydown="if(event.key==='Enter'){{event.preventDefault();confirmFilenameModal()}}">
    <div class="modal-actions">
      <button class="btn" onclick="closeFilenameModal()">Cancel</button>
      <button class="btn btn-primary" onclick="confirmFilenameModal()">Save</button>
    </div>
  </div>
</div>

<!-- Help overlay -->
<div class="modal-overlay" id="help-modal">
  <div class="modal" style="max-width:420px">
    <h3>Keyboard Shortcuts</h3>
    <div style="font-size:12px;line-height:2">
      <div><kbd>Cmd+Enter</kbd> &mdash; Redraw figure</div>
      <div><kbd>Cmd+S</kbd> &mdash; Save preset</div>
      <div><kbd>Cmd+L</kbd> &mdash; Load preset</div>
      <div><kbd>Cmd+E</kbd> &mdash; Export (download)</div>
      <div><kbd>Cmd+Shift+S</kbd> &mdash; Save image to server</div>
      <div><kbd>Cmd+D</kbd> &mdash; Download script</div>
      <div><kbd>Cmd+Shift+D</kbd> &mdash; Save script to server</div>
      <div><kbd>Cmd+R</kbd> &mdash; Reload server</div>
      <div><kbd>Cmd+Shift+R</kbd> &mdash; Reset to defaults</div>
      <div><kbd>Cmd+T</kbd> &mdash; New tab</div>
      <div><kbd>Cmd+Plus</kbd> &mdash; Zoom in</div>
      <div><kbd>Cmd+Minus</kbd> &mdash; Zoom out</div>
      <div><kbd>?</kbd> &mdash; Toggle this help</div>
      <div><kbd>Esc</kbd> &mdash; Close any modal</div>
    </div>
    <div class="modal-actions">
      <button class="btn btn-primary" onclick="closeHelp()">Close</button>
    </div>
  </div>
</div>

<div class="toast-container" id="toast-container"></div>
<div id="tooltip"></div>

<!-- Disconnect overlay -->
<div class="disconnect-overlay" id="disconnect-overlay">
  <div class="disconnect-modal">
    <div class="disconnect-icon">
      <i data-lucide="unplug" style="width:20px;height:20px"></i>
    </div>
    <h3>Connection lost</h3>
    <p>The server is not responding.</p>
    <div class="disconnect-status">
      <div class="spinner"></div>
      Reconnecting
    </div>
  </div>
</div>

<script>{JS_BLOCK}</script>
</body>
</html>"""

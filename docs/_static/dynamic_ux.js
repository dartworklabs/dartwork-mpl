/* ═══════════════════════════════════════════════════════════════════════
   dartwork-mpl — Dynamic UX layer
   ─────────────────────────────────────────────────────────────────────
   This file augments the static Sphinx output with:
     1. Global keyboard shortcuts (`?` overlay, `/` search focus, `g` jumps)
     2. Smart install command picker (auto-attaches above install code blocks)
     3. Troubleshooting page filter / quick-jump pills
     4. fs / fw / lw live ruler (Quickstart helpers)
     5. Save & validation lint simulator
     6. Color favorites tray (sticky, persisted in localStorage)
     7. Reading-progress bar
     8. "Copy as..." enhancement on every code block
   Each block is feature-detected — pages without the relevant DOM hooks
   simply skip that module.
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  /* ── Tiny utilities ────────────────────────────────────────────────── */
  var $ = function (sel, root) {
    return (root || document).querySelector(sel);
  };
  var $$ = function (sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  };

  // Safe localStorage wrapper — falls back to in-memory store when storage
  // throws (file://, private mode, blocked by sandbox, etc.).
  var memStore = Object.create(null);
  var safeStorage = {
    get: function (key) {
      try {
        var v = window.localStorage.getItem(key);
        return v == null ? null : v;
      } catch (e) {
        return key in memStore ? memStore[key] : null;
      }
    },
    set: function (key, value) {
      try {
        window.localStorage.setItem(key, value);
      } catch (e) {
        memStore[key] = value;
      }
    },
  };

  function copyText(text, onSuccess) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(onSuccess || function () {})
        .catch(fallback);
    } else {
      fallback();
    }
    function fallback() {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try {
        document.execCommand("copy");
        if (onSuccess) onSuccess();
      } catch (e) {}
      document.body.removeChild(ta);
    }
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === "class") {
          node.className = attrs[k];
        } else if (k === "html") {
          node.innerHTML = attrs[k];
        } else if (k === "text") {
          node.textContent = attrs[k];
        } else if (k.indexOf("on") === 0 && typeof attrs[k] === "function") {
          node.addEventListener(k.slice(2), attrs[k]);
        } else {
          node.setAttribute(k, attrs[k]);
        }
      });
    }
    if (children) {
      (Array.isArray(children) ? children : [children]).forEach(function (c) {
        if (c == null) return;
        node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
      });
    }
    return node;
  }

  function flashToast(msg) {
    var t = el("div", { class: "dm-toast", text: msg });
    document.body.appendChild(t);
    requestAnimationFrame(function () {
      t.classList.add("show");
    });
    setTimeout(function () {
      t.classList.remove("show");
      setTimeout(function () {
        t.remove();
      }, 320);
    }, 1500);
  }

  /* ═══════════════════════════════════════════════════════════════════
     1. Global keyboard shortcuts + help overlay
     ═══════════════════════════════════════════════════════════════════ */
  /* Robustly resolve a doc-root-relative URL like "/usage_guide/quickstart.html"
     using whatever Sphinx already rendered on the page. Falls back to
     <link rel="canonical"> and finally to a known-prefix slice. */
  function resolveDocUrl(target) {
    var rel = target.replace(/^\//, "");

    // 1. Reuse an existing nav link whose href ends with the same target.
    var navLinks = $$("a[href]");
    for (var i = 0; i < navLinks.length; i++) {
      var href = navLinks[i].getAttribute("href") || "";
      if (!href || href[0] === "#") continue;
      var clean = href.split("#")[0].split("?")[0];
      if (clean.endsWith(rel) || clean.endsWith("/" + rel)) {
        try {
          return new URL(href, window.location.href).toString();
        } catch (e) {
          /* keep trying */
        }
      }
    }

    // 2. Use <link rel="canonical"> as the anchor.
    var canonical = $('link[rel="canonical"]');
    if (canonical && canonical.href) {
      try {
        return new URL(rel, canonical.href).toString();
      } catch (e) {}
    }

    // 3. Slice docs root from current URL by stripping known top-level dirs.
    var knownDirs = [
      "/usage_guide/",
      "/color_system/",
      "/fonts/",
      "/examples_gallery/",
      "/api/",
      "/integrations/",
      "/philosophy/",
      "/installation/",
      "/development/",
    ];
    var here = window.location.origin + window.location.pathname;
    for (var k = 0; k < knownDirs.length; k++) {
      var idx = here.indexOf(knownDirs[k]);
      if (idx !== -1) {
        return new URL(rel, here.slice(0, idx + 1)).toString();
      }
    }

    // 4. Last resort: relative to current page (works on the index).
    try {
      return new URL(rel, window.location.href).toString();
    } catch (e) {
      return null;
    }
  }

  function initKeyboardShortcuts() {
    var SHORTCUTS = [
      { keys: "?", desc: "Toggle this help overlay" },
      { keys: "/", desc: "Focus the search box" },
      { keys: "g h", desc: "Go to home (index)" },
      { keys: "g q", desc: "Go to Quick Start" },
      { keys: "g s", desc: "Go to Styles & Presets" },
      { keys: "g c", desc: "Go to Color System" },
      { keys: "g f", desc: "Go to Fonts" },
      { keys: "g e", desc: "Go to Examples Gallery" },
      { keys: "g a", desc: "Go to API Reference" },
      { keys: "g t", desc: "Go to Troubleshooting" },
      { keys: "y", desc: "Copy current page URL" },
      { keys: "Esc", desc: "Close any open overlay" },
    ];

    var JUMPS = {
      h: "/index.html",
      q: "/usage_guide/quickstart.html",
      s: "/usage_guide/styles.html",
      c: "/color_system/index.html",
      f: "/fonts/index.html",
      e: "/examples_gallery/index.html",
      a: "/api/index.html",
      t: "/troubleshooting.html",
    };

    var overlay = el("div", {
      class: "dm-kbd-overlay",
      role: "dialog",
      "aria-modal": "true",
      "aria-hidden": "true",
    });
    var card = el("div", { class: "dm-kbd-card" });
    var head = el("div", { class: "dm-kbd-head" }, [
      el("span", { class: "dm-kbd-title", text: "Keyboard shortcuts" }),
      el("button", {
        class: "dm-kbd-close",
        "aria-label": "Close",
        text: "×",
        onclick: function () {
          hide();
        },
      }),
    ]);
    var list = el("div", { class: "dm-kbd-list" });
    SHORTCUTS.forEach(function (s) {
      var keyTokens = s.keys.split(" ").map(function (k) {
        return el("kbd", { text: k });
      });
      var keyWrap = el("span", { class: "dm-kbd-keys" });
      keyTokens.forEach(function (kt, i) {
        keyWrap.appendChild(kt);
        if (i < keyTokens.length - 1) {
          keyWrap.appendChild(
            el("span", { class: "dm-kbd-then", text: "then" }),
          );
        }
      });
      list.appendChild(
        el("div", { class: "dm-kbd-row" }, [
          keyWrap,
          el("span", { class: "dm-kbd-desc", text: s.desc }),
        ]),
      );
    });
    var foot = el("div", {
      class: "dm-kbd-foot",
      html:
        'Press <kbd>?</kbd> any time. Disable with <code>localStorage.dmKbd=0</code>.',
    });
    card.appendChild(head);
    card.appendChild(list);
    card.appendChild(foot);
    overlay.appendChild(card);
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) hide();
    });
    document.body.appendChild(overlay);

    // Floating help button
    var helpBtn = el("button", {
      class: "dm-kbd-launcher",
      "aria-label": "Show keyboard shortcuts",
      title: "Keyboard shortcuts (press ?)",
      html: "<span>?</span>",
      onclick: function () {
        show();
      },
    });
    document.body.appendChild(helpBtn);

    function show() {
      overlay.classList.add("open");
      overlay.setAttribute("aria-hidden", "false");
    }
    function hide() {
      overlay.classList.remove("open");
      overlay.setAttribute("aria-hidden", "true");
    }
    function toggle() {
      overlay.classList.contains("open") ? hide() : show();
    }

    var pendingG = false;
    var pendingTimer = null;
    function clearPending() {
      pendingG = false;
      document.body.classList.remove("dm-kbd-pending-g");
      if (pendingTimer) {
        clearTimeout(pendingTimer);
        pendingTimer = null;
      }
    }

    document.addEventListener("keydown", function (e) {
      if (safeStorage.get("dmKbd") === "0") return;

      // Skip while an IME is composing (Korean/Japanese/Chinese input).
      if (e.isComposing || e.keyCode === 229 || e.key === "Process") return;

      // Don't intercept while typing in an input/textarea/contentEditable
      var t = e.target;
      var typing =
        t &&
        (t.tagName === "INPUT" ||
          t.tagName === "TEXTAREA" ||
          t.tagName === "SELECT" ||
          t.isContentEditable);

      // Esc always closes overlay regardless
      if (e.key === "Escape") {
        if (overlay.classList.contains("open")) {
          e.preventDefault();
          hide();
        }
        clearPending();
        return;
      }

      if (typing) return;

      // Help toggle: `?` — also accept Shift+/ on layouts where `e.key` is "/"
      // because the browser hasn't decoded the shift modifier (rare).
      if (e.key === "?" || (e.key === "/" && e.shiftKey)) {
        e.preventDefault();
        toggle();
        return;
      }

      // Focus search: /
      if (e.key === "/") {
        var search =
          $('input[type="search"]') ||
          $("input[name=q]") ||
          $(".sidebar-search") ||
          $("input.search");
        if (search) {
          e.preventDefault();
          search.focus();
          search.select && search.select();
        } else {
          // Tell the reader why nothing happened instead of silently no-op'ing.
          flashToast("No search box on this page");
        }
        return;
      }

      // Copy current URL
      if (e.key === "y" && !e.metaKey && !e.ctrlKey) {
        copyText(window.location.href, function () {
          flashToast("Page URL copied");
        });
        return;
      }

      // Vim-style "g <letter>" jumps
      if (e.key === "g" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        pendingG = true;
        document.body.classList.add("dm-kbd-pending-g");
        if (pendingTimer) clearTimeout(pendingTimer);
        pendingTimer = setTimeout(clearPending, 1200);
        return;
      }
      if (pendingG && JUMPS[e.key]) {
        e.preventDefault();
        clearPending();
        var target = JUMPS[e.key];
        var url = resolveDocUrl(target);
        if (url) window.location.assign(url);
        return;
      }
    });
  }

  /* ═══════════════════════════════════════════════════════════════════
     2. Smart install command picker
     Looks for the FIRST <h1> on installation pages and injects
     an OS / package-manager toggle that rewrites a live command box.
     ═══════════════════════════════════════════════════════════════════ */
  function initInstallPicker() {
    // Only attach on the actual Installation page — i.e. a page whose H1 is
    // "Installation". Other pages (e.g. Troubleshooting) may have an
    // `#installation` H2 anchor and would otherwise pick up the widget.
    var h1 = $("article h1, main h1, .yue h1");
    if (!h1) return;
    var h1Text = (h1.textContent || "")
      .replace(/[¶#]/g, "")
      .trim()
      .toLowerCase();
    if (h1Text !== "installation" && h1Text !== "install") return;
    if ($(".dm-install-picker")) return;
    var marker =
      h1.closest("article") || h1.closest("section") || h1.parentElement;
    if (!marker) return;

    var managers = [
      {
        id: "uv",
        label: "uv",
        cmd: "uv add git+https://github.com/dartworklabs/dartwork-mpl",
        note: "Fast Rust-based resolver — recommended.",
      },
      {
        id: "pip",
        label: "pip",
        cmd: "pip install git+https://github.com/dartworklabs/dartwork-mpl",
        note: "The standard Python installer.",
      },
      {
        id: "poetry",
        label: "Poetry",
        cmd:
          "poetry add git+https://github.com/dartworklabs/dartwork-mpl.git",
        note: "Adds to <code>pyproject.toml</code> automatically.",
      },
      {
        id: "conda",
        label: "conda",
        cmd:
          "pip install git+https://github.com/dartworklabs/dartwork-mpl   # inside an active conda env",
        note: "Use <code>pip</code> inside the conda environment.",
      },
    ];

    var oses = [
      { id: "macos", label: "macOS", prereq: null },
      { id: "linux", label: "Linux", prereq: null },
      {
        id: "windows",
        label: "Windows",
        prereq: "Make sure Git is installed: <code>winget install Git.Git</code>",
      },
    ];

    // Detect platform
    var defaultOs = "linux";
    var ua = navigator.userAgent || "";
    if (/Mac/i.test(ua)) defaultOs = "macos";
    else if (/Win/i.test(ua)) defaultOs = "windows";

    var savedMgr = safeStorage.get("dmInstallMgr") || "uv";
    var savedOs = safeStorage.get("dmInstallOs") || defaultOs;

    var widget = el("div", { class: "dm-install-picker" });
    var head = el("div", { class: "dm-ip-head" }, [
      el("span", { class: "dm-ip-eyebrow", text: "Live install command" }),
      el("span", {
        class: "dm-ip-detected",
        html:
          'Detected: <strong>' +
          (defaultOs === "macos"
            ? "macOS"
            : defaultOs === "windows"
              ? "Windows"
              : "Linux") +
          "</strong>",
      }),
    ]);

    var rowMgr = el("div", { class: "dm-ip-row" });
    rowMgr.appendChild(el("span", { class: "dm-ip-row-label", text: "Tool" }));
    var mgrTabs = el("div", { class: "dm-ip-tabs" });
    managers.forEach(function (m) {
      var btn = el("button", {
        class: "dm-ip-tab" + (m.id === savedMgr ? " active" : ""),
        "data-mgr": m.id,
        text: m.label,
      });
      mgrTabs.appendChild(btn);
    });
    rowMgr.appendChild(mgrTabs);

    var rowOs = el("div", { class: "dm-ip-row" });
    rowOs.appendChild(el("span", { class: "dm-ip-row-label", text: "OS" }));
    var osTabs = el("div", { class: "dm-ip-tabs" });
    oses.forEach(function (o) {
      var btn = el("button", {
        class: "dm-ip-tab" + (o.id === savedOs ? " active" : ""),
        "data-os": o.id,
        text: o.label,
      });
      osTabs.appendChild(btn);
    });
    rowOs.appendChild(osTabs);

    var cmdBox = el("div", { class: "dm-ip-cmd" });
    var cmdPre = el("pre", {}, [el("code", { class: "dm-ip-code" })]);
    var copyBtn = el("button", {
      class: "dm-ip-copy",
      "aria-label": "Copy command",
      text: "Copy",
    });
    cmdBox.appendChild(cmdPre);
    cmdBox.appendChild(copyBtn);

    var note = el("div", { class: "dm-ip-note" });

    widget.appendChild(head);
    widget.appendChild(rowMgr);
    widget.appendChild(rowOs);
    widget.appendChild(cmdBox);
    widget.appendChild(note);

    // Insert directly after the page H1 (already located above)
    if (h1 && h1.parentNode) {
      h1.parentNode.insertBefore(widget, h1.nextSibling);
    } else {
      marker.insertBefore(widget, marker.firstChild);
    }

    function render() {
      var mgr = managers.filter(function (m) {
        return m.id === currentMgr;
      })[0];
      var os = oses.filter(function (o) {
        return o.id === currentOs;
      })[0];
      var prefix = "";
      if (os.id === "macos") prefix = "$ ";
      else if (os.id === "linux") prefix = "$ ";
      else prefix = "PS> ";
      cmdPre.querySelector("code").textContent = prefix + mgr.cmd;
      var notes = [];
      if (os.prereq) notes.push(os.prereq);
      notes.push(mgr.note);
      note.innerHTML = notes.join(" · ");
    }

    var currentMgr = savedMgr;
    var currentOs = savedOs;

    mgrTabs.addEventListener("click", function (e) {
      var b = e.target.closest("[data-mgr]");
      if (!b) return;
      currentMgr = b.getAttribute("data-mgr");
      safeStorage.set("dmInstallMgr", currentMgr);
      $$(".dm-ip-tab", mgrTabs).forEach(function (x) {
        x.classList.toggle(
          "active",
          x.getAttribute("data-mgr") === currentMgr,
        );
      });
      render();
    });
    osTabs.addEventListener("click", function (e) {
      var b = e.target.closest("[data-os]");
      if (!b) return;
      currentOs = b.getAttribute("data-os");
      safeStorage.set("dmInstallOs", currentOs);
      $$(".dm-ip-tab", osTabs).forEach(function (x) {
        x.classList.toggle("active", x.getAttribute("data-os") === currentOs);
      });
      render();
    });
    copyBtn.addEventListener("click", function () {
      // Strip a leading shell prompt — either "$ " (POSIX) or "PS> " (PowerShell).
      var text = cmdPre
        .querySelector("code")
        .textContent.replace(/^(?:\$|PS>)\s+/, "");
      copyText(text, function () {
        copyBtn.textContent = "Copied!";
        copyBtn.classList.add("copied");
        setTimeout(function () {
          copyBtn.textContent = "Copy";
          copyBtn.classList.remove("copied");
        }, 1500);
      });
    });

    render();
  }

  /* ═══════════════════════════════════════════════════════════════════
     3. Troubleshooting page filter + jump pills
     ═══════════════════════════════════════════════════════════════════ */
  function initTroubleshootingFilter() {
    // Heuristic: detect by H1 text
    var h1 = $("article h1, main h1, .yue h1");
    if (!h1) return;
    var h1Text = (h1.textContent || "").toLowerCase();
    if (
      h1Text.indexOf("troubleshoot") === -1 &&
      h1Text.indexOf("faq") === -1
    ) {
      return;
    }

    var article = h1.closest("article") || h1.parentElement;
    if (!article) return;

    // Find top-level H2 sections.
    var h2s = $$("h2", article);
    if (h2s.length < 2) return;
    if ($(".dm-faq-toolbar")) return;

    var bar = el("div", { class: "dm-faq-toolbar" });

    var searchWrap = el("div", { class: "dm-faq-search-wrap" });
    var searchIcon = el("span", { class: "dm-faq-search-icon", text: "⌕" });
    var searchInput = el("input", {
      type: "search",
      class: "dm-faq-search",
      placeholder: "Filter FAQ… (e.g. font, layout, svg)",
      "aria-label": "Filter FAQ entries",
    });
    var searchCount = el("span", { class: "dm-faq-search-count" });
    searchWrap.appendChild(searchIcon);
    searchWrap.appendChild(searchInput);
    searchWrap.appendChild(searchCount);
    bar.appendChild(searchWrap);

    var pillWrap = el("div", { class: "dm-faq-pills" });
    var pillAll = el("button", {
      class: "dm-faq-pill active",
      "data-target": "__all__",
      text: "All",
    });
    pillWrap.appendChild(pillAll);

    // Sphinx wraps each H2 in <section id="...">. The H2 itself has no id, so
    // the parent section's id is the canonical anchor.
    function sectionIdFor(h2) {
      var parent = h2.parentElement;
      if (parent && parent.tagName === "SECTION" && parent.id) return parent.id;
      return (
        h2.id ||
        (h2.textContent || "")
          .trim()
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
      );
    }

    h2s.forEach(function (h2) {
      var slug = sectionIdFor(h2);
      var label = (h2.textContent || "").replace(/¶|#/g, "").trim();
      pillWrap.appendChild(
        el("button", {
          class: "dm-faq-pill",
          "data-target": slug,
          text: label,
        }),
      );
    });
    bar.appendChild(pillWrap);

    h1.parentNode.insertBefore(bar, h1.nextSibling);

    var allEntries = [];
    h2s.forEach(function (h2) {
      var section = h2.parentElement; // Sphinx wraps each h2 in <section>
      // Sphinx wraps each h3 in its own nested <section>. Prefer that wrapper
      // when available so we hide the entry cleanly (no orphan margins).
      var h3s = $$("h3", section);
      if (!h3s.length) {
        allEntries.push({ h2: h2, h3: null, wrapper: null });
        return;
      }
      h3s.forEach(function (h3) {
        var wrapper =
          h3.closest("section") !== section ? h3.closest("section") : null;
        var nodes = [];
        if (!wrapper) {
          // Fallback: collect siblings until next h2/h3.
          var n = h3.nextSibling;
          while (n) {
            if (n.nodeType === 1) {
              var t = n.tagName;
              if (t === "H2" || t === "H3") break;
            }
            nodes.push(n);
            n = n.nextSibling;
          }
        }
        allEntries.push({ h2: h2, h3: h3, wrapper: wrapper, nodes: nodes });
      });
    });

    var activePill = "__all__";
    pillWrap.addEventListener("click", function (e) {
      var btn = e.target.closest(".dm-faq-pill");
      if (!btn) return;
      activePill = btn.getAttribute("data-target");
      $$(".dm-faq-pill", pillWrap).forEach(function (p) {
        p.classList.toggle(
          "active",
          p.getAttribute("data-target") === activePill,
        );
      });
      apply();
      if (activePill !== "__all__") {
        var anchor = document.getElementById(activePill);
        if (anchor) anchor.scrollIntoView({ behavior: "smooth", block: "start" });
      } else {
        h1.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
    searchInput.addEventListener("input", apply);

    function apply() {
      var q = (searchInput.value || "").trim().toLowerCase();
      var matched = 0;
      var total = 0;

      // First, hide/show each h2 section based on category pill
      h2s.forEach(function (h2) {
        var slug = sectionIdFor(h2);
        var section = h2.parentElement;
        if (!section) return;
        if (activePill !== "__all__" && slug !== activePill) {
          section.style.display = "none";
        } else {
          section.style.display = "";
        }
      });

      // Then, filter individual H3 entries by query
      allEntries.forEach(function (entry) {
        if (!entry.h3) return;
        total++;
        var text = "";
        if (entry.wrapper) {
          text = entry.wrapper.textContent || "";
        } else {
          text = entry.h3.textContent + " ";
          entry.nodes.forEach(function (n) {
            if (n.nodeType === 1 || n.nodeType === 3) {
              text += " " + (n.textContent || "");
            }
          });
        }
        text = text.toLowerCase();
        var hit = !q || text.indexOf(q) !== -1;
        var disp = hit ? "" : "none";
        if (entry.wrapper) {
          entry.wrapper.style.display = disp;
        } else {
          entry.h3.style.display = disp;
          entry.nodes.forEach(function (n) {
            if (n.nodeType === 1) {
              n.style.display = disp;
            }
          });
        }
        if (q && hit) matched++;
      });

      if (q) {
        searchCount.textContent =
          matched === 0 ? "no match" : matched + " of " + total;
        searchCount.classList.toggle("zero", matched === 0);
      } else {
        searchCount.textContent = "";
        searchCount.classList.remove("zero");
      }
    }
  }

  /* ═══════════════════════════════════════════════════════════════════
     4. fs / fw / lw live ruler
     Auto-injects after a heading containing "Quick Start" or "ROI"
     when the page mentions dm.fs/dm.fw/dm.lw.
     ═══════════════════════════════════════════════════════════════════ */
  function initHelperRuler() {
    var article = $("article, main .yue, main") || document.body;
    if (!article) return;
    var html = article.innerHTML || "";
    // Match the helpers in either code text or rendered prose (e.g.
    // "fs(n)", "fw(n)", "lw(n)" inside tables on the layout page).
    if (
      html.indexOf("dm.fs") === -1 &&
      html.indexOf("dm.fw") === -1 &&
      html.indexOf("dm.lw") === -1 &&
      !/[^a-zA-Z]fs\(n\)/.test(html) &&
      !/[^a-zA-Z]fw\(n\)/.test(html) &&
      !/[^a-zA-Z]lw\(n\)/.test(html)
    ) {
      return;
    }
    if ($(".dm-ruler-widget")) return;

    var presets = {
      scientific: { fs: 7.5, lw: 0.8, fw: 300 },
      report: { fs: 8.0, lw: 0.8, fw: 300 },
      minimal: { fs: 7.5, lw: 0.5, fw: 300 },
      presentation: { fs: 10.5, lw: 1.0, fw: 300 },
      poster: { fs: 12.0, lw: 1.5, fw: 300 },
      web: { fs: 11.0, lw: 0.8, fw: 400 },
      dark: { fs: 11.0, lw: 0.8, fw: 400 },
    };

    var w = el("div", { class: "dm-ruler-widget" });
    w.innerHTML =
      '<div class="dm-rw-head">' +
      '<div class="dm-rw-title">Live <code>dm.fs</code> · <code>dm.fw</code> · <code>dm.lw</code> ruler</div>' +
      '<div class="dm-rw-sub">Pick a preset, slide each helper, and read off the resolved size.</div>' +
      "</div>" +
      '<div class="dm-rw-controls">' +
      '<label class="dm-rw-ctrl">' +
      '<span>Preset</span>' +
      '<select class="dm-rw-preset">' +
      Object.keys(presets)
        .map(function (k) {
          return '<option value="' + k + '">' + k + "</option>";
        })
        .join("") +
      "</select>" +
      "</label>" +
      '<label class="dm-rw-ctrl">' +
      '<span><code>fs</code> offset <em class="dm-rw-fs-val">+0</em></span>' +
      '<input type="range" class="dm-rw-fs" min="-3" max="6" step="1" value="0">' +
      "</label>" +
      '<label class="dm-rw-ctrl">' +
      '<span><code>fw</code> offset <em class="dm-rw-fw-val">+0</em></span>' +
      '<input type="range" class="dm-rw-fw" min="-2" max="6" step="1" value="0">' +
      "</label>" +
      '<label class="dm-rw-ctrl">' +
      '<span><code>lw</code> factor <em class="dm-rw-lw-val">×1.0</em></span>' +
      '<input type="range" class="dm-rw-lw" min="0" max="6" step="1" value="0">' +
      "</label>" +
      "</div>" +
      '<div class="dm-rw-stage">' +
      '<svg class="dm-rw-svg" viewBox="0 0 320 80" preserveAspectRatio="xMidYMid meet">' +
      '<line class="dm-rw-line" x1="20" y1="40" x2="300" y2="40" stroke="currentColor" stroke-width="2"/>' +
      '<line class="dm-rw-tick" x1="20" y1="30" x2="20" y2="50" stroke="currentColor" stroke-width="1"/>' +
      '<line class="dm-rw-tick" x1="160" y1="32" x2="160" y2="48" stroke="currentColor" stroke-width="1"/>' +
      '<line class="dm-rw-tick" x1="300" y1="30" x2="300" y2="50" stroke="currentColor" stroke-width="1"/>' +
      "</svg>" +
      '<div class="dm-rw-sample">Aa Bb 한글 — Ω 1234.567</div>' +
      "</div>" +
      '<div class="dm-rw-readouts">' +
      '<div><span>fs →</span><strong class="dm-rw-fs-out">7.5 pt</strong></div>' +
      '<div><span>fw →</span><strong class="dm-rw-fw-out">300</strong></div>' +
      '<div><span>lw →</span><strong class="dm-rw-lw-out">0.80 pt</strong></div>' +
      "</div>" +
      '<pre class="dm-rw-code"><code>ax.set_xlabel("Time", fontsize=dm.fs(0), fontweight=dm.fw(0))\nax.plot(x, y, lw=dm.lw(0))</code></pre>';

    // Insert near a relevant heading
    var anchor = null;
    var headings = $$("h2, h3", article);
    for (var i = 0; i < headings.length; i++) {
      var t = (headings[i].textContent || "").toLowerCase();
      if (
        t.indexOf("at-a-glance") !== -1 ||
        t.indexOf("quick start") !== -1 ||
        t.indexOf("typography") !== -1 ||
        t.indexOf("scaling helpers") !== -1
      ) {
        anchor = headings[i];
        break;
      }
    }
    var inserted = false;
    if (anchor && anchor.parentNode) {
      // place after section containing this heading? insert just after anchor instead.
      anchor.parentNode.insertBefore(w, anchor.nextSibling);
      inserted = true;
    }
    if (!inserted) {
      // skip injection if no good anchor — avoid disrupting unrelated pages
      return;
    }

    var presetSel = $(".dm-rw-preset", w);
    var fsR = $(".dm-rw-fs", w);
    var fwR = $(".dm-rw-fw", w);
    var lwR = $(".dm-rw-lw", w);
    var fsLabel = $(".dm-rw-fs-val", w);
    var fwLabel = $(".dm-rw-fw-val", w);
    var lwLabel = $(".dm-rw-lw-val", w);
    var fsOut = $(".dm-rw-fs-out", w);
    var fwOut = $(".dm-rw-fw-out", w);
    var lwOut = $(".dm-rw-lw-out", w);
    var sample = $(".dm-rw-sample", w);
    var line = $(".dm-rw-line", w);
    var codeEl = $(".dm-rw-code code", w);

    function update() {
      var p = presets[presetSel.value];
      var fsO = parseInt(fsR.value, 10);
      var fwO = parseInt(fwR.value, 10);
      var lwF = parseInt(lwR.value, 10);
      // fs: base + offset (pt)
      var fs = Math.max(1, p.fs + fsO);
      var fw = Math.max(100, Math.min(900, p.fw + fwO * 100));
      // dm.lw: factor steps. 0 = 1.0, +1 = 1.5, +2 = 2.0, ...
      var lwMult = 1 + lwF * 0.5;
      var lw = +(p.lw * lwMult).toFixed(2);

      fsLabel.textContent = (fsO >= 0 ? "+" : "") + fsO;
      fwLabel.textContent = (fwO >= 0 ? "+" : "") + fwO;
      lwLabel.textContent = "×" + lwMult.toFixed(1);

      fsOut.textContent = fs.toFixed(1) + " pt";
      fwOut.textContent = String(fw);
      lwOut.textContent = lw.toFixed(2) + " pt";

      // Render: 1 pt ≈ 1.333 px in CSS
      sample.style.fontSize = (fs * 1.333).toFixed(2) + "px";
      sample.style.fontWeight = String(fw);
      // SVG line stroke width in user units (viewBox 320 wide ~ a sketch): 1 pt → ~2 user units
      line.setAttribute("stroke-width", (lw * 2).toFixed(2));

      codeEl.textContent =
        'dm.style.use("' +
        presetSel.value +
        '")\nax.set_xlabel("Time", fontsize=dm.fs(' +
        fsO +
        "), fontweight=dm.fw(" +
        fwO +
        "))\nax.plot(x, y, lw=dm.lw(" +
        lwF +
        "))";
    }

    [presetSel, fsR, fwR, lwR].forEach(function (n) {
      n.addEventListener("input", update);
      n.addEventListener("change", update);
    });
    update();
  }

  /* ═══════════════════════════════════════════════════════════════════
     5. Save & validation lint simulator
     Auto-injects on the Save & Validation page.
     ═══════════════════════════════════════════════════════════════════ */
  function initValidationSimulator() {
    var article = $("article, main .yue, main");
    if (!article) return;
    var heads = $$("h1, h2", article);
    var anchor = null;
    for (var i = 0; i < heads.length; i++) {
      var t = (heads[i].textContent || "").toLowerCase();
      if (
        t.indexOf("visual validation") !== -1 ||
        t.indexOf("validation") !== -1
      ) {
        anchor = heads[i];
        break;
      }
    }
    if (!anchor) return;
    if ($(".dm-lint-sim")) return;

    var w = el("div", { class: "dm-lint-sim" });
    w.innerHTML =
      '<div class="dm-ls-head">' +
      '<div class="dm-ls-title">Try the validator on a hypothetical figure</div>' +
      '<div class="dm-ls-sub">Tweak figure dimensions and content density — the same heuristics that <code>dm.validate_figure()</code> uses report what would fail.</div>' +
      "</div>" +
      '<div class="dm-ls-grid">' +
      '<label><span>Figure width (in)</span><input type="range" class="dm-ls-w" min="2.0" max="12.0" step="0.1" value="4.5"><em class="dm-ls-w-val">4.5″</em></label>' +
      '<label><span>Figure height (in)</span><input type="range" class="dm-ls-h" min="1.5" max="10.0" step="0.1" value="3.0"><em class="dm-ls-h-val">3.0″</em></label>' +
      '<label><span>Number of x-ticks</span><input type="range" class="dm-ls-xt" min="2" max="40" step="1" value="8"><em class="dm-ls-xt-val">8</em></label>' +
      '<label><span>Y-label length (chars)</span><input type="range" class="dm-ls-yl" min="0" max="60" step="1" value="14"><em class="dm-ls-yl-val">14</em></label>' +
      '<label><span>Title lines</span><input type="range" class="dm-ls-tl" min="1" max="4" step="1" value="1"><em class="dm-ls-tl-val">1</em></label>' +
      '<label><span>Legend entries</span><input type="range" class="dm-ls-le" min="0" max="20" step="1" value="3"><em class="dm-ls-le-val">3</em></label>' +
      "</div>" +
      '<div class="dm-ls-output">' +
      '<div class="dm-ls-results"></div>' +
      '<pre class="dm-ls-code"><code>dm.validate_figure(fig)</code></pre>' +
      "</div>";

    anchor.parentNode.insertBefore(w, anchor.nextSibling);

    var ws = $(".dm-ls-w", w);
    var hs = $(".dm-ls-h", w);
    var xt = $(".dm-ls-xt", w);
    var yl = $(".dm-ls-yl", w);
    var tl = $(".dm-ls-tl", w);
    var le = $(".dm-ls-le", w);
    var wsV = $(".dm-ls-w-val", w);
    var hsV = $(".dm-ls-h-val", w);
    var xtV = $(".dm-ls-xt-val", w);
    var ylV = $(".dm-ls-yl-val", w);
    var tlV = $(".dm-ls-tl-val", w);
    var leV = $(".dm-ls-le-val", w);
    var results = $(".dm-ls-results", w);
    var codeEl = $(".dm-ls-code code", w);

    function evaluate() {
      var width = parseFloat(ws.value);
      var height = parseFloat(hs.value);
      var ticks = parseInt(xt.value, 10);
      var yLen = parseInt(yl.value, 10);
      var titleLines = parseInt(tl.value, 10);
      var legend = parseInt(le.value, 10);

      wsV.textContent = width.toFixed(1) + "″";
      hsV.textContent = height.toFixed(1) + "″";
      xtV.textContent = ticks;
      ylV.textContent = yLen;
      tlV.textContent = titleLines;
      leV.textContent = legend;

      var msgs = [];

      // Tick crowding: > ~6 per inch is suspicious
      var perInch = ticks / width;
      if (perInch > 6) {
        msgs.push({
          level: "warn",
          tag: "TICK_CROWDING",
          text:
            "X-axis has " +
            ticks +
            " ticks across " +
            width.toFixed(1) +
            "″ (" +
            perInch.toFixed(1) +
            "/in > 6). Consider rotating, thinning, or formatting them.",
        });
      }

      // Y-label overflow heuristic: > 0.6 × height (rough, cumulative line-height ≈ 0.18 in per char vertical)
      // Long y-label = more horizontal space taken; if width small + ylen big, flag.
      if (yLen > 22 && width < 5.5) {
        msgs.push({
          level: "warn",
          tag: "OVERFLOW",
          text:
            "Y-label is " +
            yLen +
            " chars on a " +
            width.toFixed(1) +
            "″ figure — likely to clip without auto_layout().",
        });
      }

      // Multi-line title clip
      if (titleLines >= 3 && height < 4) {
        msgs.push({
          level: "warn",
          tag: "OVERFLOW",
          text:
            titleLines +
            "-line title on a " +
            height.toFixed(1) +
            "″ tall figure — top margin will overflow.",
        });
      }

      // Legend overflow
      if (legend > 8 && width < 6) {
        msgs.push({
          level: "warn",
          tag: "LEGEND_OVERFLOW",
          text:
            "Legend with " +
            legend +
            " entries on " +
            width.toFixed(1) +
            "″ wide axes — consider <code>ncol</code> or external placement.",
        });
      }

      // Margin asymmetry pre-check: if figure < 3 inches and no helper called, mention auto_layout
      if (width < 3 || height < 2) {
        msgs.push({
          level: "info",
          tag: "TIGHT",
          text:
            "Figure smaller than 3 × 2″ — pass <code>dm.simple_layout(fig)</code> after creating axes.",
        });
      }

      // Empty axes heuristic: legend=0 AND width small AND ticks==2
      if (legend === 0 && ticks <= 3 && width < 3.5) {
        msgs.push({
          level: "info",
          tag: "EMPTY_AXES",
          text:
            "Very few ticks and no legend — confirm the axes are not empty.",
        });
      }

      if (!msgs.length) {
        msgs.push({
          level: "ok",
          tag: "PASS",
          text:
            "No warnings — this figure shape would pass <code>dm.validate_figure()</code>.",
        });
      }

      results.innerHTML = msgs
        .map(function (m) {
          return (
            '<div class="dm-ls-line dm-ls-' +
            m.level +
            '"><span class="dm-ls-tag">' +
            m.tag +
            "</span><span class='dm-ls-text'>" +
            m.text +
            "</span></div>"
          );
        })
        .join("");

      codeEl.textContent =
        "fig, ax = plt.subplots(figsize=(" +
        width.toFixed(1) +
        ", " +
        height.toFixed(1) +
        "))\n" +
        "# … plotting …\n" +
        "warnings = dm.validate_figure(fig)\n" +
        "for w in warnings:\n    print(w)";
    }

    [ws, hs, xt, yl, tl, le].forEach(function (n) {
      n.addEventListener("input", evaluate);
      n.addEventListener("change", evaluate);
    });
    evaluate();
  }

  /* ═══════════════════════════════════════════════════════════════════
     6. Color favorites tray (sticky, persisted)
     Hooks into existing .dm-swatch elements (already on the colors page).
     A "Save" pin appears on hover; a floating tray lists collected colors.
     ═══════════════════════════════════════════════════════════════════ */
  function initFavoritesTray() {
    if (!$(".dm-swatch")) return;
    if ($(".dm-fav-tray")) return;

    var KEY = "dmFavoriteColors";

    function readFavs() {
      try {
        return JSON.parse(safeStorage.get(KEY) || "[]");
      } catch (e) {
        return [];
      }
    }
    function writeFavs(list) {
      safeStorage.set(KEY, JSON.stringify(list.slice(-30)));
    }

    var tray = el("div", { class: "dm-fav-tray", "aria-label": "Color favorites" });
    var trayHead = el("div", { class: "dm-fav-head" }, [
      el("strong", { text: "Favorites" }),
      el("button", {
        class: "dm-fav-clear",
        text: "Clear",
        title: "Remove all",
      }),
      el("button", {
        class: "dm-fav-toggle",
        "aria-label": "Toggle tray",
        text: "▾",
      }),
    ]);
    var trayList = el("div", { class: "dm-fav-list" });
    var trayHint = el("div", {
      class: "dm-fav-hint",
      text: "Click any swatch + ★ to save. Click a saved chip to copy.",
    });
    tray.appendChild(trayHead);
    tray.appendChild(trayList);
    tray.appendChild(trayHint);
    document.body.appendChild(tray);

    function render() {
      var favs = readFavs();
      tray.classList.toggle("empty", favs.length === 0);
      trayList.innerHTML = "";
      if (favs.length === 0) {
        trayHint.style.display = "";
      } else {
        trayHint.style.display = "none";
      }
      favs.forEach(function (f, idx) {
        var chip = el("button", {
          class: "dm-fav-chip",
          title: f.name + " · " + f.hex + " · click to copy hex",
          style: "background:" + f.hex,
        });
        chip.appendChild(
          el("span", { class: "dm-fav-chip-label", text: f.name || f.hex }),
        );
        var x = el("span", {
          class: "dm-fav-chip-x",
          text: "×",
          title: "Remove",
        });
        chip.appendChild(x);
        chip.addEventListener("click", function (ev) {
          if (ev.target === x) {
            var next = readFavs().filter(function (_, j) {
              return j !== idx;
            });
            writeFavs(next);
            render();
            return;
          }
          copyText(f.name || f.hex, function () {
            chip.classList.add("copied");
            setTimeout(function () {
              chip.classList.remove("copied");
            }, 900);
          });
        });
        trayList.appendChild(chip);
      });
    }

    trayHead.querySelector(".dm-fav-clear").addEventListener("click", function () {
      writeFavs([]);
      render();
    });
    trayHead.querySelector(".dm-fav-toggle").addEventListener("click", function () {
      tray.classList.toggle("collapsed");
    });

    // Inject favorite-pin hover hooks on every swatch
    $$(".dm-swatch").forEach(function (sw) {
      // Avoid breaking the existing click-to-copy behavior — overlay a dedicated
      // tiny "★" button.
      if (sw.querySelector(".dm-fav-pin")) return;
      var pin = el("button", {
        class: "dm-fav-pin",
        "aria-label": "Save to favorites",
        title: "Save to favorites",
        text: "★",
      });
      pin.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var hexEl = sw.querySelector(".dm-swatch-hex");
        var nameEl = sw.querySelector(".dm-swatch-name");
        if (!hexEl) return;
        var hex = hexEl.textContent.trim();
        var name = nameEl ? nameEl.textContent.trim() : hex;
        var favs = readFavs();
        if (
          favs.some(function (f) {
            return f.hex === hex;
          })
        ) {
          // duplicate → remove (toggle)
          favs = favs.filter(function (f) {
            return f.hex !== hex;
          });
          pin.classList.remove("on");
        } else {
          favs.push({ name: name, hex: hex });
          pin.classList.add("on");
          flashToast("Added " + name + " to favorites");
        }
        writeFavs(favs);
        render();
      });
      sw.appendChild(pin);

      // Pre-light the pin if already saved
      var hexEl = sw.querySelector(".dm-swatch-hex");
      if (
        hexEl &&
        readFavs().some(function (f) {
          return f.hex === hexEl.textContent.trim();
        })
      ) {
        pin.classList.add("on");
      }
    });

    render();
  }

  /* ═══════════════════════════════════════════════════════════════════
     7. Reading-progress bar
     ═══════════════════════════════════════════════════════════════════ */
  function initReadingProgress() {
    if ($(".dm-progress")) return;
    var bar = el("div", { class: "dm-progress" });
    var fill = el("div", { class: "dm-progress-fill" });
    bar.appendChild(fill);
    document.body.appendChild(bar);
    function tick() {
      var doc = document.documentElement;
      var top = doc.scrollTop || document.body.scrollTop;
      var max = doc.scrollHeight - doc.clientHeight;
      var p = max > 0 ? Math.min(1, Math.max(0, top / max)) : 0;
      fill.style.transform = "scaleX(" + p + ")";
    }
    document.addEventListener("scroll", tick, { passive: true });
    window.addEventListener("resize", tick);
    tick();
  }

  /* ═══════════════════════════════════════════════════════════════════
     8. Code block "Copy as…" enhancements
     Adds a small "shell ↔ python" view toggle on shell code blocks that
     contain "pip install" or "uv add", letting readers paste either form.
     ═══════════════════════════════════════════════════════════════════ */
  function initCodeBlockEnhancers() {
    var blocks = $$("div.highlight pre, pre.highlight, .highlight pre");
    blocks.forEach(function (pre) {
      var code = pre.querySelector("code") || pre;
      var text = code.textContent || "";
      if (
        text.indexOf("pip install") === -1 &&
        text.indexOf("uv add") === -1 &&
        text.indexOf("uv pip install") === -1
      )
        return;
      // Only when it references our package
      if (text.indexOf("dartwork-mpl") === -1 && text.indexOf("dartwork_mpl") === -1)
        return;
      if (pre.parentElement.querySelector(".dm-cb-toggle")) return;

      var btn = el("button", {
        class: "dm-cb-toggle",
        "aria-label": "Switch package manager",
        title: "Switch package manager",
        text: "↻ pip ↔ uv",
      });
      var original = text;
      var alt = text.replace(/^(\s*)(uv add )(\S+)/gm, function (_, s, c, pkg) {
        return s + "pip install " + pkg;
      });
      if (alt === original) {
        alt = original
          .replace(/^(\s*)pip install --upgrade (\S+)/gm, "$1uv add $2")
          .replace(/^(\s*)pip install (\S+)/gm, "$1uv add $2");
      }
      if (alt === original) return;
      var showingAlt = false;
      btn.addEventListener("click", function () {
        showingAlt = !showingAlt;
        code.textContent = showingAlt ? alt : original;
      });
      pre.parentElement.style.position = "relative";
      pre.parentElement.appendChild(btn);
    });
  }

  /* ═══════════════════════════════════════════════════════════════════
     Boot
     ═══════════════════════════════════════════════════════════════════ */
  var booted = false;
  function boot() {
    if (booted) return;
    booted = true;
    try {
      initKeyboardShortcuts();
    } catch (e) {
      console.warn("dm-ux: keyboard shortcuts init failed", e);
    }
    try {
      initInstallPicker();
    } catch (e) {
      console.warn("dm-ux: install picker init failed", e);
    }
    try {
      initTroubleshootingFilter();
    } catch (e) {
      console.warn("dm-ux: troubleshooting filter init failed", e);
    }
    try {
      initHelperRuler();
    } catch (e) {
      console.warn("dm-ux: helper ruler init failed", e);
    }
    try {
      initValidationSimulator();
    } catch (e) {
      console.warn("dm-ux: validation simulator init failed", e);
    }
    try {
      initFavoritesTray();
    } catch (e) {
      console.warn("dm-ux: favorites tray init failed", e);
    }
    try {
      initReadingProgress();
    } catch (e) {
      console.warn("dm-ux: reading progress init failed", e);
    }
    try {
      initCodeBlockEnhancers();
    } catch (e) {
      console.warn("dm-ux: code block enhancer init failed", e);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
  // bfcache restore: re-attempt boot in case static-only widgets got unmounted.
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) {
      // Defer one tick so any theme scripts re-init first.
      requestAnimationFrame(boot);
    }
  });
})();

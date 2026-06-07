/* ═══════════════════════════════════════════════════════════════════════
   Click-to-copy clipboard utility
   ═══════════════════════════════════════════════════════════════════════ */
function copyToClipboardFallback(text, onSuccess) {
  if (navigator.clipboard) {
    navigator.clipboard
      .writeText(text)
      .then(onSuccess)
      .catch(function () {
        fallbackCopy(text, onSuccess);
      });
  } else {
    fallbackCopy(text, onSuccess);
  }

  function fallbackCopy(text, cb) {
    var textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand("copy");
      if (cb) cb();
    } catch (err) {
      console.error("Fallback clipboard copy failed", err);
    }
    document.body.removeChild(textArea);
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   Click-to-copy hex code for color swatches
   ═══════════════════════════════════════════════════════════════════════ */
document.addEventListener("click", function (e) {
  var swatch = e.target.closest(".dm-swatch");
  if (!swatch) return;

  var hexEl = swatch.querySelector(".dm-swatch-hex");
  if (!hexEl) return;

  var hex = hexEl.textContent.trim();
  copyToClipboardFallback(hex, function () {
    swatch.classList.add("copied");
    setTimeout(function () {
      swatch.classList.remove("copied");
    }, 1200);
  });
});

/* ═══════════════════════════════════════════════════════════════════════
   Colormap Hover Inspector — shows color at cursor position
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  /**
   * Parse the CSS linear-gradient from a .dm-cmap-bar element.
   * Returns an array of {color: [r, g, b], pos: 0–1} stops.
   */
  function parseGradientStops(bar) {
    var bg = bar.style.background || bar.style.backgroundImage || "";
    var m = bg.match(/linear-gradient\(to right,\s*(.+)\)/);
    if (!m) return null;

    var stops = [];
    // Match patterns like: #RRGGBB XX.X%
    var re = /(#[0-9a-fA-F]{6})\s+([\d.]+)%/g;
    var match;
    while ((match = re.exec(m[1])) !== null) {
      var hex = match[1];
      var pos = parseFloat(match[2]) / 100;
      var r = parseInt(hex.slice(1, 3), 16);
      var g = parseInt(hex.slice(3, 5), 16);
      var b = parseInt(hex.slice(5, 7), 16);
      stops.push({ color: [r, g, b], pos: pos });
    }
    return stops.length > 1 ? stops : null;
  }

  /** Linearly interpolate between two color stop arrays at position t (0–1). */
  function sampleGradient(stops, t) {
    t = Math.max(0, Math.min(1, t));
    // Find the two surrounding stops
    for (var i = 0; i < stops.length - 1; i++) {
      if (t >= stops[i].pos && t <= stops[i + 1].pos) {
        var range = stops[i + 1].pos - stops[i].pos;
        var local = range > 0 ? (t - stops[i].pos) / range : 0;
        return [
          Math.round(
            stops[i].color[0] +
              local * (stops[i + 1].color[0] - stops[i].color[0]),
          ),
          Math.round(
            stops[i].color[1] +
              local * (stops[i + 1].color[1] - stops[i].color[1]),
          ),
          Math.round(
            stops[i].color[2] +
              local * (stops[i + 1].color[2] - stops[i].color[2]),
          ),
        ];
      }
    }
    return stops[stops.length - 1].color;
  }

  /** Convert RGB [0–255] to hex string. */
  function rgbToHex(rgb) {
    return (
      "#" +
      rgb
        .map(function (c) {
          return ("0" + c.toString(16)).slice(-2);
        })
        .join("")
    );
  }

  // Initialize all colormap bars
  document.addEventListener("DOMContentLoaded", function () {
    var bars = document.querySelectorAll(".dm-cmap-bar");

    bars.forEach(function (bar) {
      var stops = parseGradientStops(bar);
      if (!stops) return;
      bar._stops = stops;

      // Create inspector elements
      var inspector = document.createElement("div");
      inspector.className = "dm-cmap-inspector";

      var swatchEl = document.createElement("div");
      swatchEl.className = "dm-cmap-inspector-swatch";

      var labelEl = document.createElement("div");
      labelEl.className = "dm-cmap-inspector-label";
      labelEl.textContent = "#000000";

      inspector.appendChild(swatchEl);
      inspector.appendChild(labelEl);
      bar.appendChild(inspector);

      // Track mouse position
      bar.addEventListener("mousemove", function (e) {
        var rect = bar.getBoundingClientRect();
        var x = e.clientX - rect.left;
        var t = x / rect.width;
        var rgb = sampleGradient(bar._stops, t);
        var hex = rgbToHex(rgb);

        inspector.style.left = x + "px";
        swatchEl.style.backgroundColor = hex;
        labelEl.textContent = hex;
      });

      // Click to copy hex
      bar.addEventListener("click", function (e) {
        var rect = bar.getBoundingClientRect();
        var t = (e.clientX - rect.left) / rect.width;
        var rgb = sampleGradient(bar._stops, t);
        var hex = rgbToHex(rgb);

        copyToClipboardFallback(hex, function () {
          bar.classList.add("copied");
          setTimeout(function () {
            bar.classList.remove("copied");
          }, 1200);
        });
      });
    });
  });
})();

/* ═══════════════════════════════════════════════════════════════════════
   Font Specimen — Interactive Type Tester
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var specimens = document.querySelectorAll(".dm-font-specimen");
    if (!specimens.length) return;

    specimens.forEach(function (specimen) {
      var samples = specimen.querySelectorAll(".dm-font-grid .sample");
      if (!samples.length) return;

      // Read original text for reset
      var originalText = samples[0].textContent;

      // Create tester controls
      var tester = document.createElement("div");
      tester.className = "dm-type-tester";

      var input = document.createElement("input");
      input.type = "text";
      input.className = "dm-type-tester-input";
      input.placeholder = "Type here to preview…";
      input.setAttribute("aria-label", "Custom text preview");

      var sizeControl = document.createElement("div");
      sizeControl.className = "dm-type-tester-size";

      var sizeLabel = document.createElement("span");
      sizeLabel.className = "dm-type-tester-size-label";
      sizeLabel.textContent = "14px";

      var sizeSlider = document.createElement("input");
      sizeSlider.type = "range";
      sizeSlider.className = "dm-type-tester-slider";
      sizeSlider.min = "10";
      sizeSlider.max = "36";
      sizeSlider.value = "14";
      sizeSlider.setAttribute("aria-label", "Font size");

      sizeControl.appendChild(sizeSlider);
      sizeControl.appendChild(sizeLabel);
      tester.appendChild(input);
      tester.appendChild(sizeControl);

      // Insert controls after the description, before the grid
      var grid = specimen.querySelector(".dm-font-grid");
      if (grid) {
        specimen.insertBefore(tester, grid);
      }

      // Live text sync
      input.addEventListener("input", function () {
        var text = input.value || originalText;
        samples.forEach(function (s) {
          s.textContent = text;
        });
      });

      // Live size sync
      sizeSlider.addEventListener("input", function () {
        var size = sizeSlider.value + "px";
        sizeLabel.textContent = size;
        samples.forEach(function (s) {
          s.style.fontSize = size;
        });
      });
    });
  });
})();

/* ═══════════════════════════════════════════════════════════════════════
   Color Swatch — Detail Panel on Hover
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  /** sRGB → linear */
  function linearize(c) {
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  }

  /** linear RGB → OKLab */
  function rgbToOklab(r, g, b) {
    var lr = linearize(r),
      lg = linearize(g),
      lb = linearize(b);
    var l_ = Math.cbrt(
      0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb,
    );
    var m_ = Math.cbrt(
      0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb,
    );
    var s_ = Math.cbrt(
      0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb,
    );
    return [
      0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_,
      1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_,
      0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_,
    ];
  }

  /** OKLab → OKLCH */
  function oklabToOklch(L, a, b) {
    var C = Math.sqrt(a * a + b * b);
    var h = (Math.atan2(b, a) * 180) / Math.PI;
    if (h < 0) h += 360;
    return [L, C, h];
  }

  document.addEventListener("DOMContentLoaded", function () {
    var sheets = document.querySelectorAll(".dm-color-sheet");

    sheets.forEach(function (sheet) {
      var panel = document.createElement("div");
      panel.className = "dm-swatch-detail";
      panel.innerHTML =
        '<div class="dm-detail-name"></div>' +
        '<div class="dm-detail-row"><span class="dm-detail-key">HEX</span><span class="dm-detail-val dm-detail-hex"></span></div>' +
        '<div class="dm-detail-row"><span class="dm-detail-key">OKLCH</span><span class="dm-detail-val dm-detail-oklch"></span></div>' +
        '<div class="dm-detail-row"><span class="dm-detail-key">RGB</span><span class="dm-detail-val dm-detail-rgb"></span></div>';
      panel.style.display = "none";
      sheet.style.position = "relative";
      sheet.appendChild(panel);

      sheet.addEventListener("mousemove", function (e) {
        var swatch = e.target.closest(".dm-swatch");
        if (!swatch) {
          panel.style.display = "none";
          return;
        }

        var hexEl = swatch.querySelector(".dm-swatch-hex");
        var nameEl = swatch.querySelector(".dm-swatch-name");
        if (!hexEl) return;

        var hex = hexEl.textContent.trim();
        var name = nameEl ? nameEl.textContent.trim() : "";

        // Parse hex to RGB
        var rr = parseInt(hex.slice(1, 3), 16);
        var gg = parseInt(hex.slice(3, 5), 16);
        var bb = parseInt(hex.slice(5, 7), 16);

        // Compute OKLCH
        var lab = rgbToOklab(rr / 255, gg / 255, bb / 255);
        var lch = oklabToOklch(lab[0], lab[1], lab[2]);

        panel.querySelector(".dm-detail-name").textContent = name;
        panel.querySelector(".dm-detail-hex").textContent = hex;
        panel.querySelector(".dm-detail-oklch").textContent =
          lch[0].toFixed(2) +
          ", " +
          lch[1].toFixed(3) +
          ", " +
          lch[2].toFixed(0) +
          "°";
        panel.querySelector(".dm-detail-rgb").textContent =
          rr + ", " + gg + ", " + bb;

        // Position panel near cursor (fixed positioning)
        var offsetX = 16,
          offsetY = 16;
        var panelW = panel.offsetWidth || 180;
        var panelH = panel.offsetHeight || 100;
        var cx = e.clientX,
          cy = e.clientY;

        // Flip to left/above if near viewport edge
        var left =
          cx + offsetX + panelW > window.innerWidth
            ? cx - offsetX - panelW
            : cx + offsetX;
        var top =
          cy + offsetY + panelH > window.innerHeight
            ? cy - offsetY - panelH
            : cy + offsetY;

        panel.style.left = left + "px";
        panel.style.top = top + "px";
        panel.style.transform = "none";
        panel.style.display = "";
      });

      sheet.addEventListener("mouseleave", function () {
        panel.style.display = "none";
      });
    });
  });
})();

/* ═══════════════════════════════════════════════════════════════════════
   ⑨ Named Color Search — live filter for color swatches
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var sheets = document.querySelectorAll(".dm-color-sheet");
    if (!sheets.length) return;

    // Only add search if there are multiple sheets (colors page)
    var container = sheets[0].parentElement;
    if (!container) return;

    // Insert SVG filters for colorblindness simulation
    var svgFilters = document.createElement("div");
    svgFilters.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" style="position:absolute;width:0;height:0">' +
      '<filter id="dm-protanopia"><feColorMatrix type="matrix" values="0.567,0.433,0,0,0 0.558,0.442,0,0,0 0,0.242,0.758,0,0 0,0,0,1,0"/></filter>' +
      '<filter id="dm-deuteranopia"><feColorMatrix type="matrix" values="0.625,0.375,0,0,0 0.7,0.3,0,0,0 0,0.3,0.7,0,0 0,0,0,1,0"/></filter>' +
      '<filter id="dm-tritanopia"><feColorMatrix type="matrix" values="0.95,0.05,0,0,0 0,0.433,0.567,0,0 0,0.475,0.525,0,0 0,0,0,1,0"/></filter>' +
      "</svg>";
    document.body.appendChild(svgFilters);

    // Build combined toolbar
    var toolbar = document.createElement("div");
    toolbar.className = "dm-color-toolbar";

    // Search input
    var searchWrap = document.createElement("div");
    searchWrap.className = "dm-color-search-wrap";
    var searchIcon = document.createElement("span");
    searchIcon.className = "dm-color-search-icon";
    searchIcon.textContent = "⌕";
    var searchInput = document.createElement("input");
    searchInput.type = "text";
    searchInput.className = "dm-color-search";
    searchInput.placeholder = "Search colors… (e.g. oc.blue, tw.red, #FF)";
    searchInput.setAttribute("aria-label", "Search named colors");
    var searchCount = document.createElement("span");
    searchCount.className = "dm-color-search-count";
    searchWrap.appendChild(searchIcon);
    searchWrap.appendChild(searchInput);
    searchWrap.appendChild(searchCount);

    // Colorblind buttons
    var cbWrap = document.createElement("div");
    cbWrap.className = "dm-cvd-buttons";
    var cbLabel = document.createElement("span");
    cbLabel.className = "dm-cvd-label";
    cbLabel.textContent = "CVD";
    cbWrap.appendChild(cbLabel);

    var modes = [
      { id: "none", label: "Normal" },
      { id: "protanopia", label: "Protan" },
      { id: "deuteranopia", label: "Deutan" },
      { id: "tritanopia", label: "Tritan" },
    ];
    var activeCVD = "none";

    modes.forEach(function (mode) {
      var btn = document.createElement("button");
      btn.className = "dm-cvd-btn" + (mode.id === "none" ? " active" : "");
      btn.textContent = mode.label;
      btn.setAttribute("data-cvd", mode.id);
      btn.addEventListener("click", function () {
        activeCVD = mode.id;
        cbWrap.querySelectorAll(".dm-cvd-btn").forEach(function (b) {
          b.classList.toggle("active", b.getAttribute("data-cvd") === mode.id);
        });
        sheets.forEach(function (sheet) {
          if (mode.id === "none") {
            sheet.style.filter = "";
          } else {
            sheet.style.filter = "url(#dm-" + mode.id + ")";
          }
        });
        // Also apply to colormap bars
        document.querySelectorAll(".dm-cmap-bar").forEach(function (bar) {
          if (mode.id === "none") {
            bar.style.filter = "";
          } else {
            bar.style.filter = "url(#dm-" + mode.id + ")";
          }
        });
      });
      cbWrap.appendChild(btn);
    });

    toolbar.appendChild(searchWrap);
    toolbar.appendChild(cbWrap);

    // Insert toolbar before first sheet
    container.insertBefore(toolbar, sheets[0]);

    // Collect all groups for filtering
    var groups = container.querySelectorAll(".dm-color-group");

    // Search logic
    searchInput.addEventListener("input", function () {
      var query = searchInput.value.trim().toLowerCase();
      var matchCount = 0;
      var totalCount = 0;

      groups.forEach(function (group) {
        var swatches = group.querySelectorAll(".dm-swatch");
        var groupMatch = false;

        swatches.forEach(function (swatch) {
          totalCount++;
          var title = (swatch.getAttribute("title") || "").toLowerCase();
          var hex =
            (swatch.querySelector(".dm-swatch-hex") || {}).textContent || "";
          hex = hex.toLowerCase();

          if (
            !query ||
            title.indexOf(query) !== -1 ||
            hex.indexOf(query) !== -1
          ) {
            swatch.style.opacity = "";
            swatch.style.transform = "";
            groupMatch = true;
            if (query) matchCount++;
          } else {
            swatch.style.opacity = "0.1";
            swatch.style.transform = "scale(0.92)";
          }
        });

        // Also check group label
        var label = group.querySelector(".dm-group-label");
        if (label) {
          var labelText = label.textContent.toLowerCase();
          if (!query || labelText.indexOf(query) !== -1) {
            groupMatch = true;
          }
        }

        group.style.opacity = groupMatch || !query ? "" : "0.3";
      });

      if (query) {
        if (matchCount === 0) {
          searchCount.textContent = "no match";
          searchCount.style.color = "#e53935";
        } else {
          searchCount.textContent = matchCount + " found";
          searchCount.style.color = "";
        }
      } else {
        searchCount.textContent = "";
      }
    });
  });
})();

/* ═══════════════════════════════════════════════════════════════════════
   ⑪ Gallery Metadata Filter — search + category pills on gallery index
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    // Only activate on the gallery index page
    var heading = document.getElementById("examples-gallery");
    if (!heading) return;

    var article = heading.closest("article") || heading.parentElement;
    if (!article) return;

    // Collect all category sections
    var sections = article.querySelectorAll(
      "section[id]:not(#examples-gallery)",
    );
    if (!sections.length) return;

    // Build toolbar
    var toolbar = document.createElement("div");
    toolbar.className = "dm-gallery-toolbar";

    // Search input
    var searchWrap = document.createElement("div");
    searchWrap.className = "dm-gallery-search-wrap";
    var searchInput = document.createElement("input");
    searchInput.type = "text";
    searchInput.className = "dm-gallery-search";
    searchInput.placeholder = "Filter examples… (e.g. bar, scatter, legend)";
    searchInput.setAttribute("aria-label", "Filter gallery examples");
    var searchCount = document.createElement("span");
    searchCount.className = "dm-gallery-search-count";
    searchWrap.appendChild(searchInput);
    searchWrap.appendChild(searchCount);

    // Category pills
    var pillWrap = document.createElement("div");
    pillWrap.className = "dm-gallery-pills";

    var pillAll = document.createElement("button");
    pillAll.className = "dm-gallery-pill active";
    pillAll.textContent = "All";
    pillAll.setAttribute("data-category", "all");
    pillWrap.appendChild(pillAll);

    var activeCategory = "all";
    var categoryMap = {};

    sections.forEach(function (sec) {
      var h2 = sec.querySelector("h2");
      if (!h2) return;
      var name = h2.textContent.replace("¶", "").trim();
      var id = sec.id;
      categoryMap[id] = { name: name, section: sec };

      var pill = document.createElement("button");
      pill.className = "dm-gallery-pill";
      pill.textContent = name;
      pill.setAttribute("data-category", id);
      pillWrap.appendChild(pill);
    });

    toolbar.appendChild(searchWrap);
    toolbar.appendChild(pillWrap);

    // Insert toolbar after the h1 (and its description)
    var firstSection = sections[0];
    firstSection.parentElement.insertBefore(toolbar, firstSection);

    // Total count
    var allCards = article.querySelectorAll(".sphx-glr-thumbcontainer");
    var totalExamples = allCards.length;

    // Pill click handler
    pillWrap.addEventListener("click", function (e) {
      var btn = e.target.closest(".dm-gallery-pill");
      if (!btn) return;

      activeCategory = btn.getAttribute("data-category");
      pillWrap.querySelectorAll(".dm-gallery-pill").forEach(function (p) {
        p.classList.toggle(
          "active",
          p.getAttribute("data-category") === activeCategory,
        );
      });
      applyFilter();
    });

    // Search handler
    searchInput.addEventListener("input", function () {
      applyFilter();
    });

    function applyFilter() {
      var query = searchInput.value.trim().toLowerCase();
      var matched = 0;

      sections.forEach(function (sec) {
        var sectionId = sec.id;
        var categoryHidden =
          activeCategory !== "all" && sectionId !== activeCategory;

        if (categoryHidden) {
          sec.style.display = "none";
          return;
        }

        sec.style.display = "";
        var cards = sec.querySelectorAll(".sphx-glr-thumbcontainer");
        var sectionMatch = false;

        cards.forEach(function (card) {
          var title =
            (card.querySelector(".sphx-glr-thumbnail-title") || {})
              .textContent || "";
          var tooltip = card.getAttribute("tooltip") || "";
          var searchText = (title + " " + tooltip).toLowerCase();

          if (!query || searchText.indexOf(query) !== -1) {
            card.style.display = "";
            card.style.opacity = "";
            card.style.transform = "";
            sectionMatch = true;
            matched++;
          } else {
            card.style.opacity = "0.08";
            card.style.transform = "scale(0.92)";
          }
        });

        // Hide empty sections
        if (!sectionMatch && query) {
          sec.style.display = "none";
        }
      });

      // Update count
      if (query || activeCategory !== "all") {
        searchCount.textContent = matched + " / " + totalExamples;
        searchCount.style.color = matched === 0 ? "#e53935" : "";
      } else {
        searchCount.textContent = "";
      }
    }
  });
})();

/* ═══════════════════════════════════════════════════════════════════════
   ⑬ Code Output Preview — toggle between code/output on example pages
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    // Only activate on sphinx-gallery example pages
    var exTitle = document.querySelector(".sphx-glr-example-title");
    if (!exTitle) return;

    var article = exTitle.closest("article") || exTitle.parentElement;
    if (!article) return;

    // Find all code blocks and output images
    var codeBlocks = article.querySelectorAll(".highlight-Python");
    var outputImgs = article.querySelectorAll(".sphx-glr-single-img");
    var multiImgLists = article.querySelectorAll("ul.sphx-glr-horizontal");
    var scriptOuts = article.querySelectorAll(".sphx-glr-script-out");
    if (!codeBlocks.length && !outputImgs.length && !multiImgLists.length)
      return;

    // Build control bar
    var ctrlBar = document.createElement("div");
    ctrlBar.className = "dm-example-controls";

    var modes = [
      { id: "full", label: "Full", icon: "📄" },
      { id: "code-only", label: "Code", icon: "⌨" },
      { id: "output-only", label: "Output", icon: "🖼" },
    ];

    var activeMode = "full";

    modes.forEach(function (mode) {
      var btn = document.createElement("button");
      btn.className =
        "dm-example-mode-btn" + (mode.id === "full" ? " active" : "");
      btn.innerHTML = mode.icon + " " + mode.label;
      btn.setAttribute("data-mode", mode.id);
      btn.addEventListener("click", function () {
        activeMode = mode.id;
        ctrlBar.querySelectorAll(".dm-example-mode-btn").forEach(function (b) {
          b.classList.toggle("active", b.getAttribute("data-mode") === mode.id);
        });
        applyMode();
      });
      ctrlBar.appendChild(btn);
    });

    // Insert controls after the h1
    var h1 = exTitle.querySelector("h1");
    var desc = h1 ? h1.nextElementSibling : null;
    // Insert after description paragraph
    if (desc && desc.tagName === "P") {
      desc.parentElement.insertBefore(ctrlBar, desc.nextSibling);
    } else if (h1) {
      h1.parentElement.insertBefore(ctrlBar, h1.nextSibling);
    }

    function applyMode() {
      // Code blocks: hide in output-only
      codeBlocks.forEach(function (block) {
        block.style.display = activeMode === "output-only" ? "none" : "";
      });

      // Output images (single): hide in code-only
      outputImgs.forEach(function (img) {
        img.style.display = activeMode === "code-only" ? "none" : "";
      });

      // Output images (multi): hide in code-only
      multiImgLists.forEach(function (ul) {
        ul.style.display = activeMode === "code-only" ? "none" : "";
      });

      // Stdout outputs: hide in output-only (they're code output, not visual)
      scriptOuts.forEach(function (out) {
        out.style.display = activeMode === "output-only" ? "none" : "";
      });

      // Timing footer: hide in output-only
      var timing = article.querySelector(".sphx-glr-timing");
      if (timing) {
        timing.style.display = activeMode === "output-only" ? "none" : "";
      }

      // Download footer: hide in output-only
      // Target the footer div directly — do NOT use .closest("section")
      // which would climb up and hide the entire page content section.
      var downloadFooter = article.querySelector(".sphx-glr-footer");
      if (downloadFooter) {
        downloadFooter.style.display =
          activeMode === "output-only" ? "none" : "";
      }
    }
  });
})();

/* ═══════════════════════════════════════════════════════════════════════
   Color Interpolation Widget — interactive cspace() demo
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  // ── Color math utilities ──────────────────────────────────────────
  function srgbLinearize(c) {
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  }

  function srgbDelinearize(c) {
    return c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1.0 / 2.4) - 0.055;
  }

  function hexToLinearRgb(hex) {
    var r = parseInt(hex.slice(1, 3), 16) / 255;
    var g = parseInt(hex.slice(3, 5), 16) / 255;
    var b = parseInt(hex.slice(5, 7), 16) / 255;
    return [srgbLinearize(r), srgbLinearize(g), srgbLinearize(b)];
  }

  function linearRgbToOklab(lr, lg, lb) {
    var l_ = Math.cbrt(
      0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb,
    );
    var m_ = Math.cbrt(
      0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb,
    );
    var s_ = Math.cbrt(
      0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb,
    );
    return [
      0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_,
      1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_,
      0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_,
    ];
  }

  function oklabToLinearRgb(L, a, b) {
    var l_ = L + 0.3963377774 * a + 0.2158037573 * b;
    var m_ = L - 0.1055613458 * a - 0.0638541728 * b;
    var s_ = L - 0.0894841775 * a - 1.291485548 * b;
    var l = l_ * l_ * l_;
    var m = m_ * m_ * m_;
    var s = s_ * s_ * s_;
    return [
      +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
      -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
      -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
    ];
  }

  function oklabToOklch(L, a, b) {
    var C = Math.sqrt(a * a + b * b);
    var h = (Math.atan2(b, a) * 180) / Math.PI;
    if (h < 0) h += 360;
    return [L, C, h];
  }

  function oklchToOklab(L, C, h) {
    var rad = (h * Math.PI) / 180;
    return [L, C * Math.cos(rad), C * Math.sin(rad)];
  }

  function clamp01(x) {
    return Math.max(0, Math.min(1, x));
  }

  function linearRgbToHex(lr, lg, lb) {
    var r = Math.round(clamp01(srgbDelinearize(lr)) * 255);
    var g = Math.round(clamp01(srgbDelinearize(lg)) * 255);
    var b = Math.round(clamp01(srgbDelinearize(lb)) * 255);
    return (
      "#" +
      ("0" + r.toString(16)).slice(-2) +
      ("0" + g.toString(16)).slice(-2) +
      ("0" + b.toString(16)).slice(-2)
    );
  }

  // ── Interpolation functions ───────────────────────────────────────
  function interpolateOklch(hex1, hex2, n) {
    var rgb1 = hexToLinearRgb(hex1);
    var rgb2 = hexToLinearRgb(hex2);
    var lab1 = linearRgbToOklab(rgb1[0], rgb1[1], rgb1[2]);
    var lab2 = linearRgbToOklab(rgb2[0], rgb2[1], rgb2[2]);
    var lch1 = oklabToOklch(lab1[0], lab1[1], lab1[2]);
    var lch2 = oklabToOklch(lab2[0], lab2[1], lab2[2]);

    // Handle hue wrapping (shortest path)
    var h1 = lch1[2],
      h2 = lch2[2];
    var dh = h2 - h1;
    if (dh > 180) h2 -= 360;
    else if (dh < -180) h2 += 360;

    var colors = [];
    for (var i = 0; i < n; i++) {
      var t = n === 1 ? 0 : i / (n - 1);
      var L = lch1[0] + t * (lch2[0] - lch1[0]);
      var C = lch1[1] + t * (lch2[1] - lch1[1]);
      var h = h1 + t * (h2 - h1);
      if (h < 0) h += 360;
      if (h >= 360) h -= 360;
      var lab = oklchToOklab(L, C, h);
      var rgb = oklabToLinearRgb(lab[0], lab[1], lab[2]);
      colors.push(linearRgbToHex(rgb[0], rgb[1], rgb[2]));
    }
    return colors;
  }

  function interpolateRgb(hex1, hex2, n) {
    var r1 = parseInt(hex1.slice(1, 3), 16);
    var g1 = parseInt(hex1.slice(3, 5), 16);
    var b1 = parseInt(hex1.slice(5, 7), 16);
    var r2 = parseInt(hex2.slice(1, 3), 16);
    var g2 = parseInt(hex2.slice(3, 5), 16);
    var b2 = parseInt(hex2.slice(5, 7), 16);

    var colors = [];
    for (var i = 0; i < n; i++) {
      var t = n === 1 ? 0 : i / (n - 1);
      var r = Math.round(r1 + t * (r2 - r1));
      var g = Math.round(g1 + t * (g2 - g1));
      var b = Math.round(b1 + t * (b2 - b1));
      colors.push(
        "#" +
          ("0" + r.toString(16)).slice(-2) +
          ("0" + g.toString(16)).slice(-2) +
          ("0" + b.toString(16)).slice(-2),
      );
    }
    return colors;
  }

  // Determine text color for readability
  function textColorFor(hex) {
    var r = parseInt(hex.slice(1, 3), 16) / 255;
    var g = parseInt(hex.slice(3, 5), 16) / 255;
    var b = parseInt(hex.slice(5, 7), 16) / 255;
    var lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    return lum < 0.45 ? "#fff" : "#333";
  }

  // ── Widget 0: Color Space Converter ─────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    var widget = document.querySelector(".dm-conv-widget");
    if (!widget) return;

    var picker = widget.querySelector(".dm-conv-picker");
    var hexInput = widget.querySelector(".dm-conv-hex-input");
    var valOklab = widget.querySelector(".dm-conv-val-oklab");
    var valOklch = widget.querySelector(".dm-conv-val-oklch");
    var valRgb = widget.querySelector(".dm-conv-val-rgb");
    var valHex = widget.querySelector(".dm-conv-val-hex");

    function render(hex) {
      // Basic hex validation
      if (!/^#[0-9a-fA-F]{6}$/i.test(hex)) return;

      var hexUpper = hex.toUpperCase();
      picker.value = hex;
      if (document.activeElement !== hexInput) {
        hexInput.value = hexUpper;
      }
      valHex.textContent = hexUpper;

      var rgb = hexToLinearRgb(hex);
      valRgb.textContent =
        rgb[0].toFixed(3) + ", " + rgb[1].toFixed(3) + ", " + rgb[2].toFixed(3);

      var lab = linearRgbToOklab(rgb[0], rgb[1], rgb[2]);
      valOklab.textContent =
        lab[0].toFixed(3) + ", " + lab[1].toFixed(3) + ", " + lab[2].toFixed(3);

      var lch = oklabToOklch(lab[0], lab[1], lab[2]);
      valOklch.textContent =
        lch[0].toFixed(3) +
        ", " +
        lch[1].toFixed(3) +
        ", " +
        lch[2].toFixed(1) +
        "°";
    }

    picker.addEventListener("input", function (e) {
      render(e.target.value);
    });

    hexInput.addEventListener("input", function (e) {
      var val = e.target.value.trim();
      if (!val.startsWith("#")) val = "#" + val;
      if (val.length === 7) {
        render(val);
      }
    });

    // Initial render
    render(picker.value);
  });

  // ── Widget 0.5: Colormap Builder ────────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    var widget = document.querySelector(".dm-cmap-builder");
    if (!widget) return;

    var tabs = widget.querySelectorAll(".dm-cb-tab");
    var startInput = widget.querySelector(".dm-cb-start");
    var midInput = widget.querySelector(".dm-cb-mid");
    var endInput = widget.querySelector(".dm-cb-end");
    var midGroup = widget.querySelector(".dm-cb-mid-group");
    var bar = widget.querySelector(".dm-cb-bar");
    var codeLabel = widget.querySelector(".dm-cb-code code");

    var activeMode = "sequential"; // or "diverging"

    function renderLabel(input) {
      var wrap = input.closest(".dm-cb-input-wrap");
      if (wrap) {
        var hexSpan = wrap.querySelector(".dm-cb-hex");
        if (hexSpan) hexSpan.textContent = input.value.toUpperCase();
      }
    }

    function render() {
      renderLabel(startInput);
      renderLabel(midInput);
      renderLabel(endInput);

      var c1 = startInput.value;
      var c2 = midInput.value;
      var c3 = endInput.value;

      if (activeMode === "sequential") {
        var hexes = interpolateOklch(c1, c3, 100);
        var stops = hexes
          .map(function (h, i) {
            return h + " " + i + "%";
          })
          .join(", ");
        bar.style.background = "linear-gradient(to right, " + stops + ")";
        codeLabel.textContent =
          'colors = dm.cspace("' +
          c1.toUpperCase() +
          '", "' +
          c3.toUpperCase() +
          '", n=256, space="oklch")';
      } else {
        var hexes1 = interpolateOklch(c1, c2, 50);
        var hexes2 = interpolateOklch(c2, c3, 50);
        var hexes = hexes1.concat(hexes2);
        var stops = hexes
          .map(function (h, i) {
            return h + " " + i + "%";
          })
          .join(", ");
        bar.style.background = "linear-gradient(to right, " + stops + ")";
        codeLabel.textContent =
          'colors1 = dm.cspace("' +
          c1.toUpperCase() +
          '", "' +
          c2.toUpperCase() +
          '", n=128)\ncolors2 = dm.cspace("' +
          c2.toUpperCase() +
          '", "' +
          c3.toUpperCase() +
          '", n=128)\ncolors = colors1[:-1] + colors2';
      }
    }

    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        activeMode = tab.getAttribute("data-type");
        tabs.forEach(function (t) {
          t.classList.remove("active");
        });
        tab.classList.add("active");
        midGroup.style.display = activeMode === "diverging" ? "flex" : "none";
        render();
      });
    });

    [startInput, midInput, endInput].forEach(function (input) {
      input.addEventListener("input", render);
    });

    render();
  });

  // ── Widget 0.7: Font Specimen Tester ────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    var testers = document.querySelectorAll(".dm-font-tester");
    if (!testers.length) return;

    testers.forEach(function (widget) {
      var familySelect = widget.querySelector(".dm-ft-family");
      var weightSelect = widget.querySelector(".dm-ft-weight");
      var sizeInput = widget.querySelector(".dm-ft-size");
      var textarea = widget.querySelector(".dm-ft-textarea");

      var weightMap = {
        100: "Thin",
        200: "ExtraLight",
        300: "Light",
        400: "Regular",
        500: "Medium",
        600: "SemiBold",
        700: "Bold",
        800: "ExtraBold",
        900: "Black",
      };

      function update() {
        var family = familySelect.value; // e.g., dm-Roboto
        var weight = weightSelect.value;
        var weightSuffix = weightMap[weight] || "Regular";
        var fullFamily = family + "-" + weightSuffix;
        var size = sizeInput.value + "px";

        textarea.style.fontFamily =
          "'" + fullFamily + "', '" + family + "', sans-serif";
        textarea.style.fontWeight = weight;
        textarea.style.fontSize = size;
      }

      [familySelect, weightSelect, sizeInput].forEach(function (input) {
        input.addEventListener("input", update);
        input.addEventListener("change", update);
      });

      update();
    });
  });

  // ── Widget 0.8: Font Utilities Playground ───────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    var playgrounds = document.querySelectorAll(".dm-util-playground");
    if (!playgrounds.length) return;

    var presets = {
      scientific: { baseSize: 7.5, baseWeight: 300, isPx: false },
      report: { baseSize: 9, baseWeight: 300, isPx: false },
      presentation: { baseSize: 10.5, baseWeight: 300, isPx: false },
      minimal: { baseSize: 10, baseWeight: 300, isPx: false },
      web: { baseSize: 16, baseWeight: 400, isPx: true },
    };

    playgrounds.forEach(function (widget) {
      var baseSelect = widget.querySelector(".dm-up-base");
      var fsRange = widget.querySelector(".dm-up-fs");
      var fwRange = widget.querySelector(".dm-up-fw");

      var fsValDisplay = widget.querySelector(".dm-up-fs-val");
      var fwValDisplay = widget.querySelector(".dm-up-fw-val");

      var sampleText = widget.querySelector(".dm-up-sample");
      var calcSizeDisplay = widget.querySelector(".dm-up-calc-size");
      var calcWeightDisplay = widget.querySelector(".dm-up-calc-weight");
      var codeDisplay = widget.querySelector(".dm-up-code");

      function update() {
        var presetKey = baseSelect.value;
        var preset = presets[presetKey];
        var fsOffset = parseInt(fsRange.value);
        var fwOffset = parseInt(fwRange.value);

        fsValDisplay.textContent = fsOffset > 0 ? "+" + fsOffset : fsOffset;
        fwValDisplay.textContent = fwOffset > 0 ? "+" + fwOffset : fwOffset;

        var finalSize = Math.max(
          1,
          preset.baseSize + (preset.isPx ? fsOffset * 2 : fsOffset),
        ); // approximate pt to px for visualization if needed, but here we just map 1 unit to 1pt or 2px
        var unit = preset.isPx ? "px" : "pt";
        var renderSize = preset.isPx
          ? finalSize + "px"
          : finalSize * 1.333 + "px"; // CSS uses px, 1pt approx 1.333px

        var finalWeight = Math.max(
          100,
          Math.min(900, preset.baseWeight + fwOffset * 100),
        );

        sampleText.style.fontSize = renderSize;
        sampleText.style.fontWeight = finalWeight;

        calcSizeDisplay.textContent = finalSize + unit;
        calcWeightDisplay.textContent = finalWeight;

        codeDisplay.textContent =
          'ax.set_title("Sample Text", fontsize=dm.fs(' +
          fsOffset +
          "), fontweight=dm.fw(" +
          fwOffset +
          "))";
      }

      [baseSelect, fsRange, fwRange].forEach(function (el) {
        el.addEventListener("input", update);
        el.addEventListener("change", update);
      });

      update();
    });
  });

  // ── Widget 1: Interpolation ───────────────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    var widget = document.querySelector(".dm-interp-widget");
    if (!widget) return;

    var picker1 = widget.querySelector(".dm-interp-picker-from");
    var picker2 = widget.querySelector(".dm-interp-picker-to");
    var hex1Input = widget.querySelector(".dm-interp-hex-from");
    var hex2Input = widget.querySelector(".dm-interp-hex-to");
    var slider = widget.querySelector(".dm-interp-slider");
    var stepsLabel = widget.querySelector(".dm-interp-steps-label");
    var bar = widget.querySelector(".dm-interp-bar");
    var codeEl = widget.querySelector(".dm-interp-code");

    function render() {
      var c1 = picker1.value;
      var c2 = picker2.value;
      var n = parseInt(slider.value, 10);

      hex1Input.value = c1;
      hex2Input.value = c2;
      stepsLabel.textContent = "n=" + n;

      var colors = interpolateOklch(c1, c2, n);
      bar.innerHTML = "";
      colors.forEach(function (hex) {
        var cell = document.createElement("div");
        cell.className = "dm-interp-cell";
        cell.style.backgroundColor = hex;
        var label = document.createElement("span");
        label.className = "dm-interp-cell-hex";
        label.style.color = textColorFor(hex);
        label.textContent = hex;
        cell.appendChild(label);
        cell.addEventListener("click", function () {
          copyToClipboardFallback(hex, function () {
            cell.classList.add("copied");
            setTimeout(function () {
              cell.classList.remove("copied");
            }, 1200);
          });
        });
        bar.appendChild(cell);
      });

      if (codeEl) {
        codeEl.textContent =
          "dm.cspace('" + c1 + "', '" + c2 + "', n=" + n + ", space='oklch')";
      }
    }

    picker1.addEventListener("input", render);
    picker2.addEventListener("input", render);
    slider.addEventListener("input", render);

    hex1Input.addEventListener("change", function () {
      if (/^#[0-9a-fA-F]{6}$/.test(hex1Input.value)) {
        picker1.value = hex1Input.value;
        render();
      }
    });
    hex2Input.addEventListener("change", function () {
      if (/^#[0-9a-fA-F]{6}$/.test(hex2Input.value)) {
        picker2.value = hex2Input.value;
        render();
      }
    });

    render();
  });

  // ── Widget 2: OKLCH vs RGB comparison ─────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    var widget = document.querySelector(".dm-compare-widget");
    if (!widget) return;

    var slider = widget.querySelector(".dm-compare-slider");
    var stepsLabel = widget.querySelector(".dm-compare-steps-label");
    var oklchBar = widget.querySelector(".dm-compare-bar-oklch");
    var rgbBar = widget.querySelector(".dm-compare-bar-rgb");
    var toggleBtns = widget.querySelectorAll(".dm-compare-toggle-btn");
    var verdictEl = widget.querySelector(".dm-compare-verdict");

    var activeMode = "both";
    var color1 = "#FF6B6B";
    var color2 = "#4ECDC4";

    function renderBar(barEl, colors) {
      barEl.innerHTML = "";
      colors.forEach(function (hex) {
        var cell = document.createElement("div");
        cell.className = "dm-compare-cell";
        cell.style.backgroundColor = hex;
        cell.setAttribute("data-hex", hex);
        cell.addEventListener("click", function () {
          copyToClipboardFallback(hex, function () {
            cell.classList.add("copied");
            setTimeout(function () {
              cell.classList.remove("copied");
            }, 1200);
          });
        });
        barEl.appendChild(cell);
      });
    }

    function render() {
      var n = parseInt(slider.value, 10);
      stepsLabel.textContent = "n=" + n;

      var oklchColors = interpolateOklch(color1, color2, n);
      var rgbColors = interpolateRgb(color1, color2, n);

      renderBar(oklchBar, oklchColors);
      renderBar(rgbBar, rgbColors);

      // Visibility based on mode
      var oklchRow = oklchBar.closest(".dm-compare-row");
      var rgbRow = rgbBar.closest(".dm-compare-row");
      if (activeMode === "oklch") {
        oklchRow.style.display = "";
        rgbRow.style.display = "none";
      } else if (activeMode === "rgb") {
        oklchRow.style.display = "none";
        rgbRow.style.display = "";
      } else {
        oklchRow.style.display = "";
        rgbRow.style.display = "";
      }

      // Update verdict text
      if (verdictEl) {
        if (activeMode === "both") {
          verdictEl.innerHTML =
            "↑ <strong>OKLCH</strong> maintains vivid hues through the transition. " +
            "↓ <strong>RGB</strong> produces muddy, desaturated midtones — " +
            "notice the grey-brown colors in the middle.";
        } else if (activeMode === "oklch") {
          verdictEl.innerHTML =
            "<strong>OKLCH</strong> — every step looks equally spaced to the human eye. " +
            "Brightness, saturation, and hue all shift uniformly.";
        } else {
          verdictEl.innerHTML =
            "<strong>RGB</strong> — linear component mixing produces uneven " +
            "perceptual steps and desaturated midtones.";
        }
      }
    }

    // Toggle buttons
    toggleBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        activeMode = btn.getAttribute("data-mode");
        toggleBtns.forEach(function (b) {
          b.classList.toggle(
            "active",
            b.getAttribute("data-mode") === activeMode,
          );
        });
        render();
      });
    });

    slider.addEventListener("input", render);
    render();
  });
})();

/* ═══════════════════════════════════════════════════════════════════════
   Live Color Constructor Widget
   ═══════════════════════════════════════════════════════════════════════ */
document.addEventListener("DOMContentLoaded", function () {
  var cwWidget = document.querySelector(".dm-constructor-widget");
  if (!cwWidget) return;

  var stage = cwWidget.querySelector(".dm-cw-master-stage");
  var picker = cwWidget.querySelector(".dm-cw-master-picker");
  var hexLabel = cwWidget.querySelector(".dm-cw-master-hex");
  var codeOklab = cwWidget.querySelector('.dm-cw-card[data-format="oklab"] .dm-cw-code');
  var codeOklch = cwWidget.querySelector('.dm-cw-card[data-format="oklch"] .dm-cw-code');
  var codeRgb = cwWidget.querySelector('.dm-cw-card[data-format="rgb"] .dm-cw-code');
  var codeRgb255 = cwWidget.querySelector('.dm-cw-card[data-format="rgb255"] .dm-cw-code');
  var codeHex = cwWidget.querySelector('.dm-cw-card[data-format="hex"] .dm-cw-code');

  function srgbLinearize(x) {
    return x >= 0.04045 ? Math.pow((x + 0.055) / 1.055, 2.4) : x / 12.92;
  }
  function hexToLinearRgb(hex) {
    var r = parseInt(hex.slice(1, 3), 16) / 255;
    var g = parseInt(hex.slice(3, 5), 16) / 255;
    var b = parseInt(hex.slice(5, 7), 16) / 255;
    return [srgbLinearize(r), srgbLinearize(g), srgbLinearize(b)];
  }
  function linearRgbToOklab(lr, lg, lb) {
    var l_ = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
    var m_ = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
    var s_ = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);
    return [
      0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_,
      1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_,
      0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_,
    ];
  }
  function oklabToOklch(L, a, b) {
    var C = Math.sqrt(a * a + b * b);
    var h = (Math.atan2(b, a) * 180) / Math.PI;
    if (h < 0) h += 360;
    return [L, C, h];
  }

  function formatF(v, d) { return v.toFixed(d); }

  function updateCodes(hex) {
    stage.style.backgroundColor = hex;
    hexLabel.textContent = hex.toUpperCase();

    var match = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    var r255 = 0, g255 = 0, b255 = 0;
    if (match) {
      r255 = parseInt(match[1], 16);
      g255 = parseInt(match[2], 16);
      b255 = parseInt(match[3], 16);
    }

    codeHex.textContent = "dm.hex('" + hex + "')";
    codeRgb255.textContent = "dm.rgb(" + r255 + ", " + g255 + ", " + b255 + ")";
    codeRgb.textContent = "dm.rgb(" + formatF(r255/255, 3) + ", " + formatF(g255/255, 3) + ", " + formatF(b255/255, 3) + ")";

    var lrgb = hexToLinearRgb(hex);
    var lab = linearRgbToOklab(lrgb[0], lrgb[1], lrgb[2]);
    var lch = oklabToOklch(lab[0], lab[1], lab[2]);

    codeOklab.textContent = "dm.oklab(" + formatF(lab[0], 3) + ", " + formatF(lab[1], 3) + ", " + formatF(lab[2], 3) + ")";
    codeOklch.textContent = "dm.oklch(" + formatF(lch[0], 3) + ", " + formatF(lch[1], 3) + ", " + formatF(lch[2], 1) + ")";
  }

  picker.addEventListener("input", function (e) {
    updateCodes(e.target.value);
  });

  var cards = cwWidget.querySelectorAll(".dm-cw-card");
  cards.forEach(function(card) {
    card.addEventListener("click", function() {
      var snippet = card.querySelector(".dm-cw-code").textContent;
      if (typeof copyToClipboardFallback === "function") {
        copyToClipboardFallback(snippet, function() {
          card.classList.add("copied");
          setTimeout(function(){ card.classList.remove("copied"); }, 1200);
        });
      } else {
        if (navigator.clipboard) {
          navigator.clipboard.writeText(snippet).then(function() {
            card.classList.add("copied");
            setTimeout(function(){ card.classList.remove("copied"); }, 1200);
          });
        }
      }
    });
  });

  // Init
  updateCodes(picker.value);
});

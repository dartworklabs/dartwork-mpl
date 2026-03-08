/* ═══════════════════════════════════════════════════════════════════════
   Click-to-copy hex code for color swatches
   ═══════════════════════════════════════════════════════════════════════ */
document.addEventListener("click", function (e) {
  var swatch = e.target.closest(".dm-swatch");
  if (!swatch) return;

  var hexEl = swatch.querySelector(".dm-swatch-hex");
  if (!hexEl) return;

  var hex = hexEl.textContent.trim();
  navigator.clipboard.writeText(hex).then(function () {
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

        navigator.clipboard.writeText(hex).then(function () {
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
    if (!codeBlocks.length && !outputImgs.length) return;

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
      codeBlocks.forEach(function (block) {
        if (activeMode === "output-only") {
          block.style.display = "none";
        } else {
          block.style.display = "";
        }
      });

      outputImgs.forEach(function (img) {
        if (activeMode === "code-only") {
          img.style.display = "none";
        } else {
          img.style.display = "";
        }
      });

      // Hide timing and footnote text in output-only mode
      var timing = article.querySelector(".sphx-glr-timing");
      if (timing) {
        timing.style.display = activeMode === "output-only" ? "none" : "";
      }

      // Also hide text between code blocks in code-only mode
      // (descriptive paragraphs from sphinx-gallery sections)
    }
  });
})();

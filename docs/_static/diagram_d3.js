/* D3.js interactive module dependency graph for the diagrams PoC page.
 *
 * Loaded only on docs/internals/diagrams_poc.html via the {raw} html
 * <script> block at the bottom of §A. The data is the same set of edges
 * the Graphviz extractor produced — embedded inline here so the page is
 * fully self-contained without an extra fetch.
 *
 * Renders a force-directed graph with drag, hover tooltip, and a
 * cluster-tinted palette matching the rest of the page.
 */
(function () {
  "use strict";

  // Wait for both the DOM and d3 (loaded from a CDN <script> tag above).
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    var host = document.getElementById("dm-d3-modgraph");
    if (!host || typeof window.d3 === "undefined") return;
    if (host.dataset.dmRendered === "1") return;
    host.dataset.dmRendered = "1";

    // -- Data (mirrors the Graphviz extractor's clusters) -------------
    var clusters = {
      api:     "#0d8ee8",
      data:    "#0090a8",
      support: "#9750c1",
    };
    var nodes = [
      { id: "style",      group: "api" },
      { id: "layout",     group: "api" },
      { id: "io",         group: "api" },
      { id: "annotation", group: "api" },
      { id: "scale",      group: "api" },
      { id: "icon",       group: "api" },
      { id: "units",      group: "api" },
      { id: "colors",     group: "data" },
      { id: "cmap",       group: "data" },
      { id: "font",       group: "data" },
      { id: "asset",      group: "data" },
      { id: "asset_viz",  group: "data" },
      { id: "agent",      group: "support" },
      { id: "mcp",        group: "support" },
      { id: "ui",         group: "support" },
      { id: "lint",       group: "support" },
      { id: "validate",   group: "support" },
      { id: "diagnostics",group: "support" },
      { id: "helpers",    group: "support" },
      { id: "config",     group: "support" },
    ];
    var links = [
      { source: "style",      target: "colors"   },
      { source: "style",      target: "font"     },
      { source: "style",      target: "asset"    },
      { source: "layout",     target: "style"    },
      { source: "layout",     target: "config"   },
      { source: "layout",     target: "scale"    },
      { source: "io",         target: "config"   },
      { source: "io",         target: "diagnostics"},
      { source: "annotation", target: "scale"    },
      { source: "annotation", target: "colors"   },
      { source: "icon",       target: "asset"    },
      { source: "icon",       target: "scale"    },
      { source: "asset_viz",  target: "asset"    },
      { source: "cmap",       target: "colors"   },
      { source: "validate",   target: "diagnostics"},
      { source: "validate",   target: "config"   },
      { source: "lint",       target: "config"   },
      { source: "mcp",        target: "lint"     },
      { source: "mcp",        target: "validate" },
      { source: "mcp",        target: "asset"    },
      { source: "agent",      target: "asset"    },
      { source: "agent",      target: "lint"     },
      { source: "ui",         target: "mcp"      },
      { source: "ui",         target: "asset"    },
      { source: "helpers",    target: "config"   },
    ];

    // -- Layout setup -------------------------------------------------
    var d3 = window.d3;
    var width  = host.clientWidth  || 720;
    var height = 380;
    host.style.height = height + "px";

    var svg = d3.select(host).append("svg")
                .attr("viewBox", "0 0 " + width + " " + height)
                .attr("preserveAspectRatio", "xMidYMid meet");

    // Tooltip — absolute-positioned, follows the cursor on hover.
    var tooltip = d3.select(host).append("div")
                    .attr("class", "dm-d3-tooltip");

    // Degree = number of edges touching a node. Drives radius so hub
    // modules (config, asset, lint) read as bigger at a glance — the same
    // "importance by connectivity" signal the static Graphviz weights
    // edges by, but here it's encoded in node size.
    var degree = {};
    nodes.forEach(function (n) { degree[n.id] = 0; });
    links.forEach(function (l) {
      degree[l.source] = (degree[l.source] || 0) + 1;
      degree[l.target] = (degree[l.target] || 0) + 1;
    });
    var maxDeg = Math.max.apply(null, nodes.map(function (n) {
      return degree[n.id];
    }));
    function radius(d) { return 9 + 9 * Math.sqrt(degree[d.id] / maxDeg); }

    var groupLabel = {
      api:     "Plotting API",
      data:    "Design tokens",
      support: "Tooling / agent",
    };

    // Force simulation — gentle so it settles within ~3s.
    var simulation = d3.forceSimulation(nodes)
      .force("link",   d3.forceLink(links).id(function (d) { return d.id; })
                                         .distance(90).strength(0.5))
      .force("charge", d3.forceManyBody().strength(-260))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide(function (d) {
        return radius(d) + 16;
      }));

    var link = svg.append("g")
      .attr("class", "dm-d3-links")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("class", "dm-d3-link")
      .attr("stroke-width", 1.1);

    var node = svg.append("g")
      .attr("class", "dm-d3-nodes")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("class", "dm-d3-node")
      .call(d3.drag()
              .on("start", dragstarted)
              .on("drag",  dragged)
              .on("end",   dragended));

    node.append("circle")
      .attr("r", radius)
      .attr("fill", function (d) { return clusters[d.group] || "#1c2024"; })
      .attr("fill-opacity", 0.18)
      .attr("stroke", function (d) { return clusters[d.group] || "#1c2024"; })
      .attr("stroke-width", 1.4)
      .on("mouseover", function (event, d) {
        var rect = host.getBoundingClientRect();
        tooltip.classed("is-visible", true)
               .html(
                 "<b>" + d.id + "</b><br>" +
                 (groupLabel[d.group] || d.group) +
                 " · " + degree[d.id] + " edges")
               .style("left",
                      (event.clientX - rect.left + 12) + "px")
               .style("top",
                      (event.clientY - rect.top  - 12) + "px");
      })
      .on("mousemove", function (event) {
        var rect = host.getBoundingClientRect();
        tooltip.style("left",
                      (event.clientX - rect.left + 12) + "px")
               .style("top",
                      (event.clientY - rect.top  - 12) + "px");
      })
      .on("mouseout", function () {
        tooltip.classed("is-visible", false);
      });

    node.append("text")
      .attr("dy", 4)
      .attr("x", function (d) { return radius(d) + 5; })
      .text(function (d) { return d.id; });

    // Cluster legend (top-left) — three color chips so the hover tooltip
    // isn't the only way to learn what a color means.
    var legend = svg.append("g")
      .attr("class", "dm-d3-legend")
      .attr("transform", "translate(14, 16)");
    var legendKeys = Object.keys(groupLabel);
    legendKeys.forEach(function (g, i) {
      var row = legend.append("g")
        .attr("transform", "translate(0," + (i * 20) + ")");
      row.append("circle")
        .attr("r", 6).attr("cx", 6).attr("cy", 0)
        .attr("fill", clusters[g]).attr("fill-opacity", 0.22)
        .attr("stroke", clusters[g]).attr("stroke-width", 1.4);
      row.append("text")
        .attr("x", 18).attr("dy", 4)
        .attr("font-size", "11.5px").attr("fill", "#60646c")
        .text(groupLabel[g]);
    });

    simulation.on("tick", function () {
      link
        .attr("x1", function (d) { return d.source.x; })
        .attr("y1", function (d) { return d.source.y; })
        .attr("x2", function (d) { return d.target.x; })
        .attr("y2", function (d) { return d.target.y; });

      node.attr("transform", function (d) {
        // Soft-clamp inside the viewbox so dragged nodes can't escape.
        d.x = Math.max(20, Math.min(width  - 20, d.x));
        d.y = Math.max(20, Math.min(height - 20, d.y));
        return "translate(" + d.x + "," + d.y + ")";
      });
    });

    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;  d.fy = d.y;
    }
    function dragged(event, d) {
      d.fx = event.x;  d.fy = event.y;
    }
    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;  d.fy = null;
    }

    // Stop the simulation after 8s so it doesn't burn battery on a
    // tab the visitor left open.
    setTimeout(function () { simulation.stop(); }, 8000);
  });
})();

/* Pin every Mermaid SVG to its NATURAL viewBox width.
 *
 * Mermaid (+ the Shibuya/sphinxcontrib-mermaid injected <style>) stamps
 * `width="100%"` on the <svg> and a `max-width:100%` rule that beats the
 * element's own inline `max-width:<viewBox>px`. The net effect is a small
 * diagram scaled UP to the full container, which blurs the foreignObject
 * HTML labels (the user's "강제 확대만 한 느낌").
 *
 * CSS alone can't fix this because the cap we want is the per-diagram
 * viewBox width — a value only the SVG knows. So after Mermaid renders we
 * read each viewBox and set `max-width:<w>px !important` + `width:100%`:
 *   - a diagram narrower than the container renders at its natural size
 *     (crisp, no upscaling),
 *   - a diagram wider than the container shrinks to fit (vector, stays
 *     sharp).
 *
 * A MutationObserver catches the async CDN render; it self-disconnects
 * after 8s so it never lingers.
 */
(function () {
  "use strict";

  function fit(svg) {
    var vb = svg.getAttribute("viewBox");
    if (!vb) return;
    var parts = vb.split(/\s+/);
    var w = parseFloat(parts[2]);
    if (!w || !isFinite(w)) return;
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    svg.style.setProperty("max-width", Math.ceil(w) + "px", "important");
    svg.style.setProperty("width", "100%", "important");
    svg.style.setProperty("height", "auto", "important");
    svg.dataset.dmFit = "1";
  }

  function scan() {
    var svgs = document.querySelectorAll(".mermaid svg:not([data-dm-fit])");
    for (var i = 0; i < svgs.length; i++) fit(svgs[i]);
  }

  if (document.readyState !== "loading") scan();
  document.addEventListener("DOMContentLoaded", scan);

  // Mermaid renders asynchronously after the CDN script loads, so watch
  // for the injected <svg> nodes.
  if (typeof MutationObserver !== "undefined") {
    var obs = new MutationObserver(scan);
    obs.observe(document.documentElement, { childList: true, subtree: true });
    setTimeout(function () { obs.disconnect(); }, 8000);
  }
})();

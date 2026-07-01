const PALETTES = {
    // ── SEQUENTIAL — single-hue lightness ramps (very narrow) ──
    teal:    { name:"Teal", fam:"Sequential", band:"very-narrow · single hue",
      cols:["#2a524c","#166c61","#008577","#129e8e","#21b8a5","#5dcebd","#94e3d5","#caf7ee"],
      intent:"Categories with a natural ORDER — quality tiers, time periods, confidence buckets — where rank should read straight off the lightness. A single house-teal hue stepped light to dark, which also makes it the most black-and-white-perfect palette in the set.",
      design:"One hue (house teal, CIELAB h≈182) held constant; 8 steps on a monotonic L* ramp 32→94, chroma peaking mid.",
      application:"Stacked area (weight top→bottom), ordered bars, confidence ribbons. Avoid for UNordered categories.",
      bw:"min ΔL* 8.6", cvd:"d8.6 / p7.2 / t9.0" },
    indigo:  { name:"Indigo", fam:"Sequential", band:"very-narrow · single hue",
      cols:["#414b64","#4d6089","#5b76ae","#6d8ccd","#86a4e6","#a3bcf8","#c5d4ff","#e8edff"],
      intent:"Ordered categories in a cooler, more corporate register than teal — magnitude buckets, tiers, time periods. One indigo hue on an even lightness ramp, so rank reads instantly and every step survives grayscale printing intact.",
      design:"Single indigo hue (CIELAB h≈280) on a monotonic L* ramp 32→94. Pairs as the cool member of the sequential set.",
      application:"Heatmap rows, ordered bars, area, ribbons. Reads as rank.",
      bw:"min ΔL* 8.6", cvd:"d8.9 / p8.6 / t8.9" },
    coral:   { name:"Coral", fam:"Sequential", band:"very-narrow · single hue",
      cols:["#6c4a45","#93564e","#b86259","#d87368","#f1897d","#fea69a","#ffc6be","#ffe5e1"],
      intent:"Ordered categories in a warm, human register — intensity, recency, heat or severity scales. A single coral hue stepped light to dark; the warm counterpart to the teal and indigo sequential ramps, and still safe in black and white.",
      design:"Single coral hue (CIELAB h≈32) on a monotonic L* ramp 35→93. Warm counterpart to teal/indigo sequential.",
      application:"Heat/intensity encodings, ordered bars, area. The warm sequential.",
      bw:"min ΔL* 8.1", cvd:"d7.7 / p7.3 / t8.3" },
    // ── ANALOGOUS — one-mood hue arcs (narrow) ──
    teal_indigo: { name:"Teal → Indigo", fam:"Analogous", band:"narrow · cool arc",
      cols:["#056463","#4cb3c3","#2b88aa","#a1d3ff","#486d9d","#aeb6ed","#958bbf","#f3daff"],
      intent:"A few related series that should feel like ONE cool mood rather than a rainbow — cohesion over maximum distinctness. A teal-to-indigo arc separated by lightness, best for thin multi-line ensembles with an editorial, institutional tone.",
      design:"A ~120° cool arc (teal→blue→indigo) on a staggered even L* ladder 38→90, so adjacent series contrast by lightness while sharing a family. Anchored on house teal.",
      application:"Multi-series LINE ensembles (3–6 thin lines), area fills, refined scatter. Editorial / institutional tone.",
      bw:"min ΔL* 7.4", cvd:"d6.3 / p5.5 / t9.6" },
    forest:      { name:"Forest", fam:"Analogous", band:"narrow · green arc",
      cols:["#475b26","#8cac74","#5b8554","#a4daa8","#37734d","#80c6a0","#619b70","#c7eeb4"],
      intent:"A few related series in a natural, organic register — ESG, agriculture, environment, growth themes. A green arc held to one hue family and separated by lightness, so the lines read as cohesive and calm rather than scattered or noisy.",
      design:"A ~40° green arc (yellow-green→teal-green) on a staggered even L* ladder 36→90 — one hue family, lightness-separated.",
      application:"Multi-series line / area for environmental or organic topics. Calm, cohesive.",
      bw:"min ΔL* 7.7", cvd:"d7.8 / p6.8 / t8.7" },
    // ── DUO — warm vs cool split (medium) ──
    warm_cool:   { name:"Warm / Cool", fam:"Duo", band:"medium · 180° split",
      cols:["#91422f","#b36d44","#ed8987","#ffc18d","#06768f","#389ad1","#32cae0","#d3e4ff"],
      intent:"TWO opposed groups — put the warm family on one side and the cool on the other for A/B, before/after, or sentiment splits. The temperature contrast groups the sides while internal lightness steps keep the members within each side distinct.",
      design:"4 warm + 4 cool hues (≈180° apart), each an internal L* ramp; even ladder 38→90.",
      application:"Grouped bars, two-cluster scatter, paired lines. Excellent CVD — the temperature split is the most colorblind-robust structure.",
      bw:"min ΔL* 7.3", cvd:"d14.4 / p11.4 / t14.3" },
    blue_orange: { name:"Blue / Orange", fam:"Duo", band:"medium · 180° split",
      cols:["#036085","#2485c2","#17b2e3","#b1cfff","#a9532c","#cb8043","#fea18a","#ffddba"],
      intent:"Two opposed groups using the single most colorblind-robust opposition, blue versus orange — A/B, gain/loss, before/after. The widest temperature split available, so the two sides stay clearly distinct even in grayscale or for CVD viewers.",
      design:"4 blue + 4 orange hues (~180° apart), each an internal L* ramp; even ladder 38→90.",
      application:"Grouped bars, two-cluster scatter, paired lines. Best-in-class CVD across all three types.",
      bw:"min ΔL* 7.3", cvd:"d12.6 / p12.2 / t14.8" },
    teal_coral:  { name:"Teal / Coral", fam:"Duo", band:"medium · 180° split",
      cols:["#01655c","#0d8d8a","#2ab9a1","#3ae3e7","#ae5029","#d07d3e","#ffa183","#ffdcbe"],
      intent:"Two opposed groups in the house-teal brand voice — teal against warm coral for A/B, before/after, or sentiment splits. The on-brand alternative to blue/orange, pairing the same temperature contrast with the dartwork identity color.",
      design:"4 teal + 4 coral hues; even ladder 38→90. The warm side is pushed toward ORANGE (h≈44–68, not pure red) so the teal↔warm split lands on the blue-yellow axis and survives protanopia.",
      application:"Brand-forward duos, grouped bars, paired lines. CVD-safe after the orange re-tune (still the softest of the three duos; for maximum accessibility, Blue/Orange or Warm/Cool lead).",
      bw:"min ΔL* 7.2", cvd:"d13.3 / p8.4 / t14.6" },
    // ── BALANCED — everyday default (medium-wide) ──
    trustworthy: { name:"Trustworthy", fam:"Balanced", band:"medium-wide · teal + neutrals",
      cols:["#06655a","#72a6db","#8076a9","#ffb8a5","#467647","#ef9dc2","#83919c","#d0dfeb"],
      intent:"The everyday DEFAULT — reach for this first for 4 to 8 unrelated categories. Six evenly-spaced hues anchored on house teal plus two neutrals, muted enough to stay report-grade yet distinct enough that the series never tangle or shout.",
      design:"6 evenly-spaced hues anchored on house teal + 2 neutrals, muted chroma (no neon), staggered even L* ladder 38→88.",
      application:"Everything — line, bar, scatter; works on white pages and in tables. The general-purpose cycle.",
      bw:"min ΔL* 7.1", cvd:"d11.7 / p9.9 / t6.8" },
    // ── MUTED — soft editorial (medium-wide, low chroma) ──
    pastel:       { name:"Pastel", fam:"Muted", band:"medium-wide · low chroma",
      cols:["#56857c","#96bad4","#9b94b4","#f6c9c0","#799075","#e4b9c7","#bba387","#b6ecf3"],
      intent:"A soft, editorial categorical set for dense dashboards or backgrounds where vivid color would shout. High-key pastels carry 4 to 8 categories quietly, keeping the data readable without competing for attention on an already busy page.",
      design:"Same 8-hue spread as the default but low chroma (~18) and a higher L* band 52→90. Calm, magazine-like. (B&W is softer by design.)",
      application:"Dashboards, small multiples, annotation-heavy figures. Pair with one vivid accent for emphasis.",
      bw:"min ΔL* 5.3 (soft by design)", cvd:"d8.9 / p7.9 / t5.3" },
    // ── SPECTRUM — full hue wheel (widest) ──
    spectrum:    { name:"Vivid", fam:"Spectrum", band:"widest · full wheel",
      cols:["#026a5f","#01b3d5","#0784d9","#e9b8ff","#c6376e","#ff9e7a","#aa911a","#9ff18c"],
      intent:"MANY unrelated categories — up to eight — where color alone must separate everything and maximum distinctness matters more than restraint. An even, vivid rainbow spread for legends, maps, and crowded categorical charts that need every series apart.",
      design:"8 hues evenly spaced 45° around the full wheel (teal-anchored), high chroma, staggered even L* ladder 40→88 so it still survives B&W.",
      application:"8-category scatter, side-by-side bars, editorial infographics. Vivid, confident tone.",
      bw:"min ΔL* 6.6", cvd:"d9.1 / p9.7 / t13.8" },
    // ── ACCESSIBLE — fixed Okabe-Ito CUD (CVD gold standard) ──
    accessible:  { name:"Okabe-Ito", fam:"Accessible", band:"widest · CVD gold standard",
      cols:["#000000","#E69F00","#56B4E9","#009E73","#F0E442","#0072B2","#D55E00","#CC79A7"],
      intent:"When colorblind-safety is mandatory — journals, public-sector, clinical work. The proven Okabe-Ito CUD eight-color set shipped verbatim, so every pair stays distinguishable under all of the common forms of color-vision deficiency.",
      design:"Fixed Okabe & Ito (2008) palette — NOT regenerated. Tuned for deuter/protan/tritan separation (the strongest in the family).",
      application:"Any figure where CVD accessibility is a hard requirement. Not built for B&W (near-equal lightness) — don't lean on grayscale for this one.",
      bw:"n/a (CVD-optimised, not B&W)", cvd:"d14.8 / p14.0 / t11.0" },
    // ── INTENT-based families (organised by purpose, not spectral width) ──
    gray:    { name:"Neutral Gray", fam:"Neutral", band:"neutral · hue-free L* ramp",
      cols:["#353535","#4b4b4b","#636363","#7c7c7c","#969696","#b0b0b0","#cccccc","#e8e8e8"],
      intent:"Ordered AMOUNT with no hue meaning — magnitude, density, or rank where color should not imply a separate category. A pure neutral lightness ramp, the most print-safe and colorblind-bulletproof option for encoding pure quantity.",
      design:"8-step TRUE neutral L* ramp 22→92, chroma 0 (R=G=B, no cast). Pure lightness ⇒ perfect B&W and CVD. The cast-free anchor beside Warm Gray and Cool Gray.",
      application:"Heat tables, ordered bars/area where hue is noise, backgrounds. Pair with one accent for emphasis.",
      bw:"min ΔL* 9.7", cvd:"d8.9 / p8.9 / t8.9" },
    // DIVERGING — two-ended, pale center (ordered ± data). B&W-exempt by design.
    coolwarm:    { name:"Cool ↔ Warm", fam:"Diverging", band:"two-ended · pale center",
      cols:["#055f8b","#3b8bba","#81b7db","#bcdcf1","#f5cec9","#dfa19c","#bb6f6e","#943d45"],
      intent:"Ordered data with a meaningful MIDPOINT at zero — change, delta, correlation, z-scores, above or below average. Blue marks negative and red positive through a pale center, so both direction and magnitude read at a single glance.",
      design:"Symmetric L* tent (dark ends → pale center), blue (h≈250) ↔ red (h≈25). Excellent CVD. NOT a categorical set — the order IS the meaning.",
      application:"Correlation matrices, change heatmaps, anomaly/sentiment scales, Likert. ⚠ B&W not separable (ends share lightness — inherent to diverging).",
      bw:"n/a (diverging — ends share L)", cvd:"d12.6 / p13.6 / t14.2" },
    teal_amber: { name:"Teal ↔ Amber", fam:"Diverging", band:"two-ended · pale center",
      cols:["#06655c","#209389","#74bdb6","#b4e0db","#ebd3bc","#d0a987","#aa7951","#844c21"],
      intent:"The diverging intent in the house voice — teal for negative and amber for positive through a pale neutral center. An on-brand alternative to blue-red for deltas, correlations, and above-or-below-average encodings on branded material.",
      design:"Symmetric L* tent, teal (h≈186) ↔ amber (h≈66). The blue-yellow axis is CVD-robust.",
      application:"Brand-forward change/delta heatmaps, ± scales. ⚠ B&W not separable by design.",
      bw:"n/a (diverging)", cvd:"d13.1 / p8.8 / t13.9" },
    // TONE — frequently-reached aesthetic families
    earth:       { name:"Earth", fam:"Tone", band:"warm · earthy",
      cols:["#80443a","#cb9375","#94744b","#d6c898","#666a3d","#e5a48e","#a0895f","#d1e3b7"],
      intent:"Categorical series in a warm, organic register — ESG and sustainability, geography, agriculture, or premium-natural brands. Earthy, grounded hues that feel editorial and separate a handful of categories without ever looking corporate.",
      design:"Terracotta, ochre, olive, sand, sage, clay (h 35→125, muted chroma ~26-30), staggered even L* ladder 36→88.",
      application:"Multi-series line/bar/area for environmental or earthy topics. Calm, grounded, magazine-like.",
      bw:"min ΔL* 7.2", cvd:"d6.1 / p6.3 / t7.5" },
    jewel:       { name:"Jewel", fam:"Tone", band:"deep · rich saturation",
      cols:["#02504f","#25a88a","#0375a0","#b3bdfe","#963c3e","#caa65e","#a26eb0","#42ecfb"],
      intent:"Rich, deep, saturated variety for premium or luxury editorial. Distinct from Vivid by going darker and deeper rather than brighter, so many categories stay separable while the whole set keeps an upscale, high-contrast mood.",
      design:"Emerald, sapphire, indigo, vermilion, topaz, amethyst, deep teal/cyan (high chroma 42), even L* ladder 30→86. Retuned to clear the protanopia collapse.",
      application:"Up to 8 categories where you want depth + luxury. ⚠ Softest CVD of the set (protan ~4) — for strict accessibility use Accessible or a Duo.",
      bw:"min ΔL* 7.8", cvd:"d7.6 / p4.2 (softest) / t16.3" },
    // ── singleton families expanded to 2-3 siblings ──
    corporate:   { name:"Corporate", fam:"Balanced", band:"cool · formal / professional",
      cols:["#056058","#4caab5","#487da2","#fab1a7","#446f50","#a4aeda","#7e8c97","#cad9e5"],
      intent:"The DEFAULT for formal, institutional material — finance, board decks, policy print. Cooler and more restrained than Trustworthy, with the same even-lightness construction so it stays legible in tables and holds up in grayscale.",
      design:"Opens on house teal, then steel-blue → slate → muted brick → sage + 2 neutrals, low-moderate chroma, staggered even L* ladder 36→86.",
      application:"Everyday categorical for serious documents. Conservative, print-safe, never shouts.",
      bw:"min ΔL* 6.8", cvd:"d8.1 / p9.3 / t10.6" },
    dusty:       { name:"Dusty", fam:"Muted", band:"deep · vintage muted",
      cols:["#3d665f","#7a99af","#7b7691","#d0a9a2","#5d715a","#bf9aa6","#98846c","#9ac9cf"],
      intent:"A deeper, more vintage muted set — lower lightness than the high-key Pastel. Built for moody editorial, dark-on-cream layouts, and retro themes where soft-but-saturated tones suit the page better than bright, high-key color.",
      design:"Same 8-hue spread as Muted but a mid L* band 40→78 and low chroma ~16. Calm but with more body than pastel.",
      application:"Dense editorial, atmospheric dashboards, retro / vintage themes. (B&W softer by design.)",
      bw:"min ΔL* 5.3 (soft by design)", cvd:"d8.4 / p7.8 / t5.5" },
    bold:        { name:"Bold", fam:"Spectrum", band:"punchy · curated high-contrast",
      cols:["#035f5a","#e77a6f","#358645","#c3b5ff","#8f5915","#e290d8","#0892c4","#d8d678"],
      intent:"MANY categories with maximum punch — a curated, high-contrast set rather than Vivid's even rainbow. For presentations, posters, and dashboards that must pop, where each category should grab attention from across the room.",
      design:"Opens on house teal, then 7 vivid deliberately UNeven hues (high chroma 48), staggered even L* ladder 36→84. Retuned so no two collapse under color-blindness.",
      application:"8-category bars / scatter on slides and posters. Confident, energetic, attention-grabbing.",
      bw:"min ΔL* 6.7", cvd:"d8.1 / p7.7 / t13.3" },
    warm_gray:   { name:"Warm Gray", fam:"Neutral", band:"neutral · warm taupe ramp",
      cols:["#3a342e","#514a44","#69625b","#827b74","#9d958e","#b7afa8","#d3cbc3","#efe7df"],
      intent:"A hue-free ordered ramp with a WARM taupe or greige cast — for cream paper, editorial warmth, or warm brand systems. Encodes magnitude or rank without implying any category, staying soft and print-friendly from light to dark.",
      design:"8-step L* ramp 22→92 at a warm hue (h≈70), chroma ≈ 5. Pure lightness ⇒ perfect B&W + CVD.",
      application:"Warm-toned heat tables, ordered bars / area, backgrounds on cream stock.",
      bw:"min ΔL* 9.7", cvd:"d8.9 / p9.0 / t8.9" },
    cool_gray:   { name:"Cool Gray", fam:"Neutral", band:"neutral · cool slate ramp",
      cols:["#2d363d","#434d54","#5b656c","#737d85","#8d97a0","#a7b2bb","#c2ced6","#deeaf3"],
      intent:"A hue-free ordered ramp with a COOL slate or blue cast — for tech, clinical, or cool brand systems. Encodes magnitude or rank without implying any category, holding a crisp, neutral tone the whole way from light to dark.",
      design:"8-step L* ramp 22→92 at a cool hue (h≈250), chroma ≈ 6. Perfect B&W + CVD.",
      application:"Cool-toned heat tables, ordered encodings, UI backgrounds.",
      bw:"min ΔL* 9.7", cvd:"d9.0 / p8.9 / t9.0" },
    teal_accent:       { name:"Teal Accent", fam:"Emphasis", band:"1 teal accent + 7 neutrals",
      cols:["#0a7b6e","#767e85","#868f96","#97a0a7","#a8b1b8","#b9c3ca","#cbd4dc","#dde7ee"],
      intent:"Highlight ONE series while everything else recedes to gray — the storytelling staple, color the one thing. House teal marks the salient series and graded neutrals carry the rest, keeping attention exactly where you point it.",
      design:"Slot 0 = house teal (salient), slots 1-7 = graded neutrals on an even L* ladder 46→91. Pair with Coral Accent for the warm-highlight version, or combine the two accent colors to highlight a second series.",
      application:"Single-series emphasis in line / bar charts, explanatory figures, slide builds.",
      bw:"min ΔL* 6.2", cvd:"d5.8 / p5.7 / t5.8" },
    coral_accent:  { name:"Coral Accent", fam:"Emphasis", band:"1 warm accent + 7 neutrals",
      cols:["#b54b43","#767e85","#868f96","#97a0a7","#a8b1b8","#b9c3ca","#cbd4dc","#dde7ee"],
      intent:"Highlight one series with a WARM coral accent instead of teal — for warmth, alerts, or when teal clashes with the content. Coral marks the salient line and graded neutrals mute everything else quietly into the background.",
      design:"Slot 0 = coral (h≈32, salient), slots 1-7 = graded neutrals, even L* ladder 46→91.",
      application:"Single-series emphasis where a warm highlight reads better (e.g., risk / attention).",
      bw:"min ΔL* 6.2", cvd:"d5.8 / p5.7 / t5.8" },
  };
const ORDER = ["teal","indigo","coral","teal_indigo","forest","warm_cool","blue_orange","teal_coral","trustworthy","corporate","pastel","dusty","spectrum","bold","accessible","gray","warm_gray","cool_gray","teal_accent","coral_accent","coolwarm","teal_amber","earth","jewel"];
const VB='0 0 100 56';
  const P = {
    line(c){ const n=c.length; let s=`<svg viewBox="${VB}" preserveAspectRatio="none">`;
      for(let i=0;i<n;i++){ const yc=n>1?9+i*(38/(n-1)):28; let d='';
        for(let x=0;x<=100;x+=1.25){ const t=x/100; const y=yc+Math.sin(t*4.6+i*0.9)*3.5-(t-0.5)*(i-n/2)*1.8; d+=(x===0?'M':'L')+x.toFixed(2)+' '+y.toFixed(2)+' '; }
        s+=`<path d="${d}" fill="none" stroke="${c[i]}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>`; }
      return s+'</svg>'; },
    scatter(c){ const n=c.length; let s=`<svg viewBox="${VB}">`;
      for(let i=0;i<n;i++){ const cx=12+(i/(n-1||1))*76, cy=15+((i*37)%28);
        for(let k=0;k<11;k++){ const a=i*2.3+k*1.7; s+=`<circle cx="${(cx+Math.cos(a)*9+Math.sin(k*3.1)*2.6).toFixed(1)}" cy="${(cy+Math.sin(a)*9+Math.cos(k*2.2)*2.6).toFixed(1)}" r="2" fill="${c[i]}" opacity="0.82"/>`; } }
      return s+'</svg>'; },
    area(c){ const n=c.length, S=48, acc=new Array(S+1).fill(54); let s=`<svg viewBox="${VB}" preserveAspectRatio="none">`;
      for(let i=0;i<n;i++){ let top='',bot='';
        for(let xi=0;xi<=S;xi++){ const x=xi*(100/S), v=(46/n)*(0.85+0.34*Math.sin(xi*0.22+i*0.95)), y0=acc[xi], y1=acc[xi]-v; acc[xi]=y1; top+=(xi===0?'M':'L')+x.toFixed(2)+' '+y1.toFixed(2)+' '; bot=x.toFixed(2)+' '+y0.toFixed(2)+' '+bot; }
        s+=`<path d="${top}L${bot}Z" fill="${c[i]}" opacity="0.96"/>`; }
      return s+'</svg>'; },
    bar(c){ const n=c.length, g=2.2, bw=100/n, h=[40,28,48,34,44,30,38,46]; let s=`<svg viewBox="${VB}" preserveAspectRatio="none">`;
      for(let i=0;i<n;i++){ const x=i*bw+g/2, bh=h[i%8]; s+=`<rect x="${x.toFixed(1)}" y="${(52-bh).toFixed(1)}" width="${(bw-g).toFixed(1)}" height="${bh}" rx="0.8" fill="${c[i]}"/>`; }
      return s+'</svg>'; },
    heatmap(c){ const n=c.length, cw=100/n, rows=5, rh=56/rows; let s=`<svg viewBox="${VB}">`;
      for(let i=0;i<n;i++){ for(let r=0;r<rows;r++){ s+=`<rect x="${(i*cw).toFixed(1)}" y="${(r*rh).toFixed(1)}" width="${cw.toFixed(1)}" height="${rh.toFixed(1)}" fill="${c[i]}" opacity="${(0.4+r*0.14).toFixed(2)}"/>`; } } return s+'</svg>'; },
    bubble(c){ const n=c.length; let s=`<svg viewBox="${VB}">`;
      for(let i=0;i<n;i++){ const cx=12+(i/(n-1||1))*76, cy=16+((i*29)%26);
        for(let k=0;k<5;k++){ const a=i*1.7+k*2.2, rr=1.6+((i+k*3)%4)*1.4; s+=`<circle cx="${(cx+Math.cos(a)*8).toFixed(1)}" cy="${(cy+Math.sin(a)*8).toFixed(1)}" r="${rr.toFixed(1)}" fill="${c[i]}" opacity="0.68"/>`; } }
      return s+'</svg>'; },
    lollipop(c){ const n=c.length, g=100/(n+1); let s=`<svg viewBox="${VB}">`;
      for(let i=0;i<n;i++){ const x=g*(i+1), y=52-(14+Math.abs(Math.sin(i*1.5+0.4))*32); s+=`<line x1="${x.toFixed(1)}" y1="52" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="${c[i]}" stroke-width="1.4"/><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" fill="${c[i]}"/>`; }
      return s+'</svg>'; },
    waffle(c){ const n=c.length, cols=12, rows=5, cell=56/rows, cw=100/cols, total=cols*rows; const raw=[]; let t=0; for(let i=0;i<n;i++){ const v=0.6+Math.abs(Math.sin(i*1.7+0.2)); raw.push(v); t+=v; }
      const cnt=raw.map(v=>Math.max(1,Math.round(total*v/t)));
      let s=`<svg viewBox="${VB}">`, idx=0;
      for(let ci=0;ci<n;ci++){ for(let k=0;k<cnt[ci]&&idx<total;k++,idx++){ const r=Math.floor(idx/cols), col=idx%cols; s+=`<rect x="${(col*cw+0.6).toFixed(2)}" y="${(r*cell+0.6).toFixed(2)}" width="${(cw-1.2).toFixed(2)}" height="${(cell-1.2).toFixed(2)}" rx="1" fill="${c[ci]}"/>`; } }
      return s+'</svg>'; },
  };
const PLABEL={line:"line",area:"stacked area",scatter:"scatter",bubble:"bubble",bar:"bar",lollipop:"lollipop",waffle:"waffle",heatmap:"heatmap"};
const FAM_NOTE={Sequential:"ordered amount",Analogous:"one-mood arc",Duo:"two opposed groups",Balanced:"everyday default",Muted:"soft / editorial",Spectrum:"many categories",Accessible:"CVD-mandatory",Neutral:"hue-free ramp",Emphasis:"highlight one",Diverging:"around a midpoint",Tone:"a specific mood"};

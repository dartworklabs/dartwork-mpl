const PALETTES = {
    // ── SEQUENTIAL — single-hue lightness ramps (very narrow) ──
    teal:    { name:"Teal", fam:"Sequential", band:"very-narrow · single hue",
      cols:["#2A524C","#166C61","#008577","#129E8E","#21B8A5","#5DCEBD","#94E3D5","#CAF7EE"],
      intent:"Categories with a natural ORDER — quality tiers, time periods, confidence buckets — where rank should read straight off the lightness. A single house-teal hue stepped light to dark, which also makes it the most black-and-white-perfect palette in the set.",
      design:"One hue (house teal, CIELAB h≈182) held constant; 8 steps on a monotonic L* ramp 32→94, chroma peaking mid.",
      application:"Stacked area (weight top→bottom), ordered bars, confidence ribbons. Avoid for UNordered categories.",
      bw:"min ΔL* 8.6", cvd:"d8.6 / p7.2 / t9.0" },
    indigo:  { name:"Indigo", fam:"Sequential", band:"very-narrow · single hue",
      cols:["#414B64","#4D6089","#5B76AE","#6D8CCD","#86A4E6","#A3BCF8","#C5D4FF","#E8EDFF"],
      intent:"Ordered categories in a cooler, more corporate register than teal — magnitude buckets, tiers, time periods. One indigo hue on an even lightness ramp, so rank reads instantly and every step survives grayscale printing intact.",
      design:"Single indigo hue (CIELAB h≈280) on a monotonic L* ramp 32→94. Pairs as the cool member of the sequential set.",
      application:"Heatmap rows, ordered bars, area, ribbons. Reads as rank.",
      bw:"min ΔL* 8.6", cvd:"d8.9 / p8.6 / t8.9" },
    coral:   { name:"Coral", fam:"Sequential", band:"very-narrow · single hue",
      cols:["#6C4A45","#93564E","#B86259","#D87368","#F1897D","#FEA69A","#FFC6BE","#FFE5E1"],
      intent:"Ordered categories in a warm, human register — intensity, recency, heat or severity scales. A single coral hue stepped light to dark; the warm counterpart to the teal and indigo sequential ramps, and still safe in black and white.",
      design:"Single coral hue (CIELAB h≈32) on a monotonic L* ramp 35→93. Warm counterpart to teal/indigo sequential.",
      application:"Heat/intensity encodings, ordered bars, area. The warm sequential.",
      bw:"min ΔL* 8.1", cvd:"d7.7 / p7.3 / t8.3" },
    // ── ANALOGOUS — one-mood hue arcs (narrow) ──
    teal_indigo: { name:"Teal → Indigo", fam:"Analogous", band:"narrow · cool arc",
      cols:["#056463","#4CB3C3","#2B88AA","#A1D3FF","#486D9D","#AEB6ED","#958BBF","#F3DAFF"],
      intent:"A few related series that should feel like ONE cool mood rather than a rainbow — cohesion over maximum distinctness. A teal-to-indigo arc separated by lightness, best for thin multi-line ensembles with an editorial, institutional tone.",
      design:"A ~120° cool arc (teal→blue→indigo) on a staggered even L* ladder 38→90, so adjacent series contrast by lightness while sharing a family. Anchored on house teal.",
      application:"Multi-series LINE ensembles (3–6 thin lines), area fills, refined scatter. Editorial / institutional tone.",
      bw:"min ΔL* 7.4", cvd:"d6.3 / p5.5 / t9.6" },
    forest:      { name:"Forest", fam:"Analogous", band:"narrow · green arc",
      cols:["#475B26","#8CAC74","#5B8554","#A4DAA8","#37734D","#80C6A0","#619B70","#C7EEB4"],
      intent:"A few related series in a natural, organic register — ESG, agriculture, environment, growth themes. A green arc held to one hue family and separated by lightness, so the lines read as cohesive and calm rather than scattered or noisy.",
      design:"A ~40° green arc (yellow-green→teal-green) on a staggered even L* ladder 36→90 — one hue family, lightness-separated.",
      application:"Multi-series line / area for environmental or organic topics. Calm, cohesive.",
      bw:"min ΔL* 7.7", cvd:"d7.8 / p6.8 / t8.7" },
    // ── DUO — warm vs cool split (medium) ──
    blue_orange: { name:"Blue / Orange", fam:"Duo", band:"medium · 180° split",
      cols:["#036085","#2485C2","#17B2E3","#B1CFFF","#A9532C","#CB8043","#FEA18A","#FFDDBA"],
      intent:"Two opposed groups using the single most colorblind-robust opposition, blue versus orange — A/B, gain/loss, before/after. The widest temperature split available, so the two sides stay clearly distinct even in grayscale or for CVD viewers.",
      design:"4 blue + 4 orange hues (~180° apart), each an internal L* ramp; even ladder 38→90.",
      application:"Grouped bars, two-cluster scatter, paired lines. Best-in-class CVD across all three types.",
      bw:"min ΔL* 7.3", cvd:"d12.6 / p12.2 / t14.8" },
    teal_coral:  { name:"Teal / Coral", fam:"Duo", band:"medium · 180° split",
      cols:["#01655C","#0D8D8A","#2AB9A1","#3AE3E7","#AE5029","#D07D3E","#FFA183","#FFDCBE"],
      intent:"Two opposed groups in the house-teal brand voice — teal against warm coral for A/B, before/after, or sentiment splits. The on-brand alternative to blue/orange, pairing the same temperature contrast with the dartwork identity color.",
      design:"4 teal + 4 coral hues; even ladder 38→90. The warm side is pushed toward ORANGE (h≈44–68, not pure red) so the teal↔warm split lands on the blue-yellow axis and survives protanopia.",
      application:"Brand-forward duos, grouped bars, paired lines. CVD-safe after the orange re-tune (still the softest of the three duos; for maximum accessibility, Blue/Orange or Warm/Cool lead).",
      bw:"min ΔL* 7.2", cvd:"d13.3 / p8.4 / t14.6" },
    // ── BALANCED — everyday default (medium-wide) ──
    trustworthy: { name:"Trustworthy", fam:"Balanced", band:"medium-wide · teal + neutrals",
      cols:["#06655A","#72A6DB","#8076A9","#FFB8A5","#467647","#EF9DC2","#83919C","#D0DFEB"],
      intent:"The everyday DEFAULT — reach for this first for 4 to 8 unrelated categories. Six evenly-spaced hues anchored on house teal plus two neutrals, muted enough to stay report-grade yet distinct enough that the series never tangle or shout.",
      design:"6 evenly-spaced hues anchored on house teal + 2 neutrals, muted chroma (no neon), staggered even L* ladder 38→88.",
      application:"Everything — line, bar, scatter; works on white pages and in tables. The general-purpose cycle.",
      bw:"min ΔL* 7.1", cvd:"d11.7 / p9.9 / t6.8" },
    // ── MUTED — soft editorial (medium-wide, low chroma) ──
    pastel:       { name:"Pastel", fam:"Muted", band:"medium-wide · low chroma",
      cols:["#538789","#AEB9DA","#BC918B","#C0E0C7","#A68398","#D3C8A7","#8BAFC8","#DBEAF6"],
      intent:"A soft, editorial categorical set for dense dashboards or backgrounds where vivid color would shout. High-key pastels carry 4 to 8 categories quietly, keeping the data readable without competing for attention on an already busy page.",
      design:"Same 8-hue spread as the default but low chroma (~18) and a higher L* band 52→90. Calm, magazine-like. (B&W is softer by design.)",
      application:"Dashboards, small multiples, annotation-heavy figures. Pair with one vivid accent for emphasis.",
      bw:"min ΔL* 5.4", cvd:"d5.9 / p4.8 / t6.3" },
    // ── SPECTRUM — full hue wheel (widest) ──
    vivid:    { name:"Vivid", fam:"Spectrum", band:"widest · full wheel",
      cols:["#04696F","#05A7F7","#CB5A51","#81D383","#9455A6","#CBAC4D","#8F82DD","#51EABB"],
      intent:"MANY unrelated categories — up to eight — where color alone must separate everything and maximum distinctness matters more than restraint. An even, vivid rainbow spread for legends, maps, and crowded categorical charts that need every series apart.",
      design:"8 hues evenly spaced 45° around the full wheel (teal-anchored), high chroma, staggered even L* ladder 40→88 so it still survives B&W.",
      application:"8-category scatter, side-by-side bars, editorial infographics. Vivid, confident tone.",
      bw:"min ΔL* 6.1", cvd:"d4.9 / p9.5 / t10.9" },
    // ── ACCESSIBLE — fixed Okabe-Ito CUD (CVD gold standard) ──
    accessible:  { name:"Okabe-Ito", fam:"Accessible", band:"widest · CVD gold standard",
      cols:["#000000","#E69F00","#56B4E9","#009E73","#F0E442","#0072B2","#D55E00","#CC79A7"],
      intent:"When colorblind-safety is mandatory — journals, public-sector, clinical work. The proven Okabe-Ito CUD eight-color set shipped verbatim, so every pair stays distinguishable under all of the common forms of color-vision deficiency.",
      design:"Fixed Okabe & Ito (2008) palette — NOT regenerated. Tuned for deuter/protan/tritan separation (the strongest in the family).",
      application:"Any figure where CVD accessibility is a hard requirement. Not built for B&W (near-equal lightness) — don't lean on grayscale for this one.",
      bw:"min ΔL* 0.8", cvd:"d14.8 / p14.0 / t11.0" },
    // ── INTENT-based families (organised by purpose, not spectral width) ──
    gray:    { name:"Neutral Gray", fam:"Neutral", band:"neutral · hue-free L* ramp",
      cols:["#353535","#4B4B4B","#636363","#7C7C7C","#969696","#B0B0B0","#CCCCCC","#E8E8E8"],
      intent:"Ordered AMOUNT with no hue meaning — magnitude, density, or rank where color should not imply a separate category. A pure neutral lightness ramp, the most print-safe and colorblind-bulletproof option for encoding pure quantity.",
      design:"8-step TRUE neutral L* ramp 22→92, chroma 0 (R=G=B, no cast). Pure lightness ⇒ perfect B&W and CVD. The cast-free anchor beside Warm Gray and Cool Gray.",
      application:"Heat tables, ordered bars/area where hue is noise, backgrounds. Pair with one accent for emphasis.",
      bw:"min ΔL* 9.7", cvd:"d8.9 / p8.9 / t8.9" },
    // DIVERGING — two-ended, pale center (ordered ± data). B&W-exempt by design.
    cool_warm:    { name:"Cool ↔ Warm", fam:"Diverging", band:"two-ended · pale center",
      cols:["#055F8B","#3B8BBA","#81B7DB","#BCDCF1","#F5CEC9","#DFA19C","#BB6F6E","#943D45"],
      intent:"Ordered data with a meaningful MIDPOINT at zero — change, delta, correlation, z-scores, above or below average. Blue marks negative and red positive through a pale center, so both direction and magnitude read at a single glance.",
      design:"Symmetric L* tent (dark ends → pale center), blue (h≈250) ↔ red (h≈25). Excellent CVD. NOT a categorical set — the order IS the meaning.",
      application:"Correlation matrices, change heatmaps, anomaly/sentiment scales, Likert. ⚠ B&W not separable (ends share lightness — inherent to diverging).",
      bw:"min ΔL* 0.0", cvd:"d12.6 / p13.6 / t14.2" },
    teal_amber: { name:"Teal ↔ Amber", fam:"Diverging", band:"two-ended · pale center",
      cols:["#06655C","#209389","#74BDB6","#B4E0DB","#EBD3BC","#D0A987","#AA7951","#844C21"],
      intent:"The diverging intent in the house voice — teal for negative and amber for positive through a pale neutral center. An on-brand alternative to blue-red for deltas, correlations, and above-or-below-average encodings on branded material.",
      design:"Symmetric L* tent, teal (h≈186) ↔ amber (h≈66). The blue-yellow axis is CVD-robust.",
      application:"Brand-forward change/delta heatmaps, ± scales. ⚠ B&W not separable by design.",
      bw:"min ΔL* 0.0", cvd:"d13.1 / p8.8 / t13.9" },
    // TONE — frequently-reached aesthetic families
    earth:       { name:"Earth", fam:"Tone", band:"warm · earthy",
      cols:["#80443A","#CB9375","#94744B","#D6C898","#666A3D","#E5A48E","#A0895F","#D1E3B7"],
      intent:"Categorical series in a warm, organic register — ESG and sustainability, geography, agriculture, or premium-natural brands. Earthy, grounded hues that feel editorial and separate a handful of categories without ever looking corporate.",
      design:"Terracotta, ochre, olive, sand, sage, clay (h 35→125, muted chroma ~26-30), staggered even L* ladder 36→88.",
      application:"Multi-series line/bar/area for environmental or earthy topics. Calm, grounded, magazine-like.",
      bw:"min ΔL* 7.2", cvd:"d6.1 / p6.3 / t7.5" },
    jewel:       { name:"Jewel", fam:"Tone", band:"deep · rich saturation",
      cols:["#02504F","#25A88A","#0375A0","#B3BDFE","#963C3E","#CAA65E","#A26EB0","#42ECFB"],
      intent:"Rich, deep, saturated variety for premium or luxury editorial. Distinct from Vivid by going darker and deeper rather than brighter, so many categories stay separable while the whole set keeps an upscale, high-contrast mood.",
      design:"Emerald, sapphire, indigo, vermilion, topaz, amethyst, deep teal/cyan (high chroma 42), even L* ladder 30→86. Retuned to clear the protanopia collapse.",
      application:"Up to 8 categories where you want depth + luxury. ⚠ Softest CVD of the set (protan ~4) — for strict accessibility use Accessible or a Duo.",
      bw:"min ΔL* 7.8", cvd:"d7.6 / p4.2 / t16.3" },
    // ── singleton families expanded to 2-3 siblings ──
    dusty:       { name:"Dusty", fam:"Muted", band:"deep · vintage muted",
      cols:["#346162","#8992AE","#916D68","#9CB8A2","#7C5F71","#ABA285","#69889E","#B4C3CF"],
      intent:"A deeper, more vintage muted set — lower lightness than the high-key Pastel. Built for moody editorial, dark-on-cream layouts, and retro themes where soft-but-saturated tones suit the page better than bright, high-key color.",
      design:"Same 8-hue spread as Muted but a mid L* band 40→78 and low chroma ~16. Calm but with more body than pastel.",
      application:"Dense editorial, atmospheric dashboards, retro / vintage themes. (B&W softer by design.)",
      bw:"min ΔL* 5.5", cvd:"d6.2 / p5.1 / t6.5" },
    warm_gray:   { name:"Warm Gray", fam:"Neutral", band:"neutral · warm taupe ramp",
      cols:["#3A342E","#514A44","#69625B","#827B74","#9D958E","#B7AFA8","#D3CBC3","#EFE7DF"],
      intent:"A hue-free ordered ramp with a WARM taupe or greige cast — for cream paper, editorial warmth, or warm brand systems. Encodes magnitude or rank without implying any category, staying soft and print-friendly from light to dark.",
      design:"8-step L* ramp 22→92 at a warm hue (h≈70), chroma ≈ 5. Pure lightness ⇒ perfect B&W + CVD.",
      application:"Warm-toned heat tables, ordered bars / area, backgrounds on cream stock.",
      bw:"min ΔL* 9.7", cvd:"d8.9 / p9.0 / t8.9" },
    cool_gray:   { name:"Cool Gray", fam:"Neutral", band:"neutral · cool slate ramp",
      cols:["#2D363D","#434D54","#5B656C","#737D85","#8D97A0","#A7B2BB","#C2CED6","#DEEAF3"],
      intent:"A hue-free ordered ramp with a COOL slate or blue cast — for tech, clinical, or cool brand systems. Encodes magnitude or rank without implying any category, holding a crisp, neutral tone the whole way from light to dark.",
      design:"8-step L* ramp 22→92 at a cool hue (h≈250), chroma ≈ 6. Perfect B&W + CVD.",
      application:"Cool-toned heat tables, ordered encodings, UI backgrounds.",
      bw:"min ΔL* 9.7", cvd:"d9.0 / p8.9 / t9.0" },
    teal_accent:       { name:"Teal Accent", fam:"Emphasis", band:"1 teal accent + 7 neutrals",
      cols:["#0A7B6E","#767E85","#868F96","#97A0A7","#A8B1B8","#B9C3CA","#CBD4DC","#DDE7EE"],
      intent:"Highlight ONE series while everything else recedes to gray — the storytelling staple, color the one thing. House teal marks the salient series and graded neutrals carry the rest, keeping attention exactly where you point it.",
      design:"Slot 0 = house teal (salient), slots 1-7 = graded neutrals on an even L* ladder 46→91. Pair with Coral Accent for the warm-highlight version, or combine the two accent colors to highlight a second series.",
      application:"Single-series emphasis in line / bar charts, explanatory figures, slide builds.",
      bw:"min ΔL* 6.2", cvd:"d5.8 / p5.7 / t5.8" },
    coral_accent:  { name:"Coral Accent", fam:"Emphasis", band:"1 warm accent + 7 neutrals",
      cols:["#B54B43","#767E85","#868F96","#97A0A7","#A8B1B8","#B9C3CA","#CBD4DC","#DDE7EE"],
      intent:"Highlight one series with a WARM coral accent instead of teal — for warmth, alerts, or when teal clashes with the content. Coral marks the salient line and graded neutrals mute everything else quietly into the background.",
      design:"Slot 0 = coral (h≈32, salient), slots 1-7 = graded neutrals, even L* ladder 46→91.",
      application:"Single-series emphasis where a warm highlight reads better (e.g., risk / attention).",
      bw:"min ΔL* 6.2", cvd:"d5.8 / p5.7 / t5.8" },

    neon: { name:"Neon", fam:"Spectrum", band:"max chroma · electric",
      cols:["#045F5E","#02A5F5","#A357C4","#FFA9DB","#5F6C02","#E4A431","#5584F8","#08F2CC"],
      intent:"MAXIMUM chroma — the loudest legal categorical, at the sRGB gamut edge. Up to 6 vivid categories on dark UI or hero moments.",
      design:"Electric hues at the per-rung gamut ceiling; CVD-confusable pairs thrown far apart in L* so loudness never costs separability.",
      application:"Dark-mode dashboards, brand hero charts, few-category small multiples.",
      bw:"min ΔL* 7.0", cvd:"d8.3 / p10.4 / t8.9" },
    ember: { name:"Ember", fam:"Tone", band:"warm · vibrant",
      cols:["#942732","#E6835F","#9E6B29","#D9C778","#536A26","#FF91AB","#C17746","#D0DFEB"],
      intent:"The saturated WARM categorical — brick, coral, orange, amber, gold, olive plus a cool-neutral anchor. Golden-hour energy without earth's muteness.",
      design:"All-warm hues carry little CVD margin, so the even L* stagger + a cool anchor + one green do the separating.",
      application:"Warmth-themed dashboards, seasonal / energy / hospitality decks.",
      bw:"min ΔL* 7.6", cvd:"d5.3 / p4.9 / t8.1" },
    purple_green: { name:"Purple / Green", fam:"Diverging", band:"two-ended · pale center",
      cols:["#523F87","#8573AA","#B9ABCC","#E8DFEE","#D8E6DA","#99B89E","#56875A","#09581B"],
      intent:"Diverging purple to green around a pale centre (PRGn lineage) — the TRITAN-robust axis that blue-orange and teal-amber lack.",
      design:"Symmetric even-L* tent: dark saturated ends, pale low-chroma centre; both arms separable under all three CVD types.",
      application:"Signed quantities where blue-yellow deficiency must be covered.",
      bw:"min ΔL* 0.0", cvd:"d8.6 / p10.4 / t8.1" },
};
const ORDER = ["teal","indigo","coral","gray","warm_gray","cool_gray","forest","teal_indigo","blue_orange","teal_coral","trustworthy","pastel","dusty","vivid","neon","ember","earth","jewel","cool_warm","teal_amber","purple_green","teal_accent","coral_accent","accessible"];
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

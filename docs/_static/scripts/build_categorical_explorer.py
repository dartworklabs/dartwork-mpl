#!/usr/bin/env python3
"""Build the interactive *categorical palette explorer* (``categorical_explorer.html``).

A self-contained MyST ``{raw} html :file:`` fragment (no doctype/html/body) —
the de-nested widget embedded by ``docs/color_system/categorical-palettes.md``.

Layers, from the ground up:
  · DATA SSOT  — ``categorical_explorer_data.js`` (24 palettes + SVG renderers).
                 Edit palettes / intents / chart renderers THERE, not in the
                 generated HTML.
  · SHARED_CSS / SHARED_JS — swatches, 9-chart grid, copy-to-clipboard, toast.
  · COMMON_JS / EXTRA_CSS  — glossary tooltips, plain-language B&W + CVD readout,
                 Pygments-class syntax highlighting, and the palette-shaping
                 controls (Charts / Colors sliders + Gradient / Reverse / Shuffle
                 / B&W toggles) that mirror ``dm.get_palette(order=, reverse=,
                 seed=)`` exactly.
  · g_css      — the "Guided" master-detail layout.
  · assembly   — scope every rule under ``#dm-exp``, pin the left rail (left-only
                 self-scroll), drop the right TOC / widen the column, emit.

The output is byte-identical and deterministic (no timestamps / randomness), so
it is committed to git and CI-safe. Regenerate after editing the data or this
script — same convention as ``build_showcase.py``:

    python3 build_categorical_explorer.py
"""

from __future__ import annotations

import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUT = SCRIPT_DIR.parent / "categorical_explorer.html"
ROOT = "dm-exp"

# Provenance banner baked into the output so nobody hand-edits the 50 KB blob.
BANNER = (
    "<!-- GENERATED FILE - do not edit by hand.\n"
    "     Source: docs/_static/scripts/build_categorical_explorer.py\n"
    "             + docs/_static/scripts/categorical_explorer_data.js (palette data SSOT).\n"
    "     Regenerate: python3 build_categorical_explorer.py -->\n"
)

# ── data SSOT (palettes + SVG chart renderers) ──
DATA = (
    (SCRIPT_DIR / "categorical_explorer_data.js")
    .read_text(encoding="utf-8")
    .rstrip()
)


# ----------------------------------------------------------------------
# shared widget layer (swatches, 9-chart grid, copy-to-clipboard, toast)
# ----------------------------------------------------------------------
HELPERS = r"""
// ── 9th chart: squarified treemap (variable-size rects show all colors) ──
P.treemap=function(c){
  var W=100,H=56;
  var vals=c.map(function(_,i){return 1+Math.abs(Math.sin(i*1.7+0.3))*1.7;});
  var tot=vals.reduce(function(a,b){return a+b;},0);
  var items=c.map(function(col,i){return {col:col,area:vals[i]/tot*(W*H)};});
  var x=0,y=0,w=W,h=H,rects=[];
  function worst(row,len){var s=0,mn=Infinity,mx=0;row.forEach(function(r){s+=r.area;if(r.area<mn)mn=r.area;if(r.area>mx)mx=r.area;});
    return Math.max(len*len*mx/(s*s),s*s/(len*len*mn));}
  function lay(row,horiz){var sum=0;row.forEach(function(r){sum+=r.area;});
    if(horiz){var rh=sum/w,cx=x;row.forEach(function(r){var rw=r.area/rh;rects.push({x:cx,y:y,w:rw,h:rh,col:r.col});cx+=rw;});y+=rh;h-=rh;}
    else{var rw=sum/h,cy=y;row.forEach(function(r){var rh=r.area/rw;rects.push({x:x,y:cy,w:rw,h:rh,col:r.col});cy+=rh;});x+=rw;w-=rw;}}
  var q=items.slice(),row=[];
  while(q.length){var horiz=(w<=h),len=horiz?w:h,nx=q[0];
    if(row.length===0||worst(row,len)>=worst(row.concat([nx]),len)){row.push(q.shift());}
    else{lay(row,horiz);row=[];}}
  if(row.length)lay(row,(w<=h));
  var s='<svg viewBox="'+VB+'">';
  rects.forEach(function(r){s+='<rect x="'+r.x.toFixed(2)+'" y="'+r.y.toFixed(2)+'" width="'+Math.max(0,r.w-0.5).toFixed(2)+'" height="'+Math.max(0,r.h-0.5).toFixed(2)+'" rx="1" fill="'+r.col+'"/>';});
  return s+'</svg>';};
PLABEL.treemap="treemap";
// ── waffle: cumulative assignment fills ALL cells (no blank at small n) ──
P.waffle=function(c){var n=c.length,cols=12,rows=5,cell=56/rows,cw=100/cols,total=cols*rows;
  var raw=c.map(function(_,i){return 0.6+Math.abs(Math.sin(i*1.7+0.2));});
  var t=raw.reduce(function(a,b){return a+b;},0),cum=0;
  var bounds=raw.map(function(v){cum+=v;return Math.round(cum/t*total);});
  var s='<svg viewBox="'+VB+'">',idx=0;
  for(var ci=0;ci<n;ci++){var end=(ci===n-1)?total:bounds[ci];
    for(;idx<end;idx++){var r=Math.floor(idx/cols),col=idx%cols;
      s+='<rect x="'+(col*cw+0.6).toFixed(2)+'" y="'+(r*cell+0.6).toFixed(2)+'" width="'+(cw-1.2).toFixed(2)+'" height="'+(cell-1.2).toFixed(2)+'" rx="1" fill="'+c[ci]+'"/>';}}
  return s+'</svg>';};

const SHOWORDER=["line","bar","scatter","area","lollipop","bubble","heatmap","waffle","treemap"];
const state={pal:"trustworthy",n:8,gs:false,show:9};
function active(){var p=PALETTES[state.pal];return p.cols.slice(0,state.n);}
function pySnip(){var p=PALETTES[state.pal];return "import dartwork_mpl as dm\n# "+p.name+"  ("+state.n+" colors)\ndm.set_cycle(dm.get_palette('"+state.pal+"', n="+state.n+"))";}
function dmToast(msg){var el=document.getElementById('dm-toast');if(!el){el=document.createElement('div');el.id='dm-toast';el.className='dm-toast';document.body.appendChild(el);}el.textContent=msg;el.classList.add('show');clearTimeout(window._dmtt);window._dmtt=setTimeout(function(){el.classList.remove('show');},1100);}
function hexRgb(h){var m=h.replace('#','');return 'rgb('+parseInt(m.substr(0,2),16)+', '+parseInt(m.substr(2,2),16)+', '+parseInt(m.substr(4,2),16)+')';}
function swStrip(cs){return cs.map(function(c){return '<button class="sw" data-hex="'+c+'" title="click: copy '+c+'   ·   shift-click: copy rgb"><span class="chip" style="background:'+c+'"></span><span class="hx">'+c+'</span></button>';}).join('');}
function wireSwatches(root){root.querySelectorAll('.sw[data-hex]').forEach(function(b){b.onclick=function(e){var hex=b.dataset.hex,txt=e.shiftKey?hexRgb(hex):hex;if(navigator.clipboard)navigator.clipboard.writeText(txt);dmToast(txt+' copied');b.classList.add('copied');setTimeout(function(){b.classList.remove('copied');},800);};});}
function plots(cs){return SHOWORDER.slice(0,state.show).map(function(pt){return '<div class="pcell"><div class="pl">'+PLABEL[pt]+'</div>'+P[pt](cs)+'</div>';}).join('');}
function metaBlock(p){return '<div class="meta"><div><b>Intent:</b> '+p.intent+'</div><div><b>Design:</b> '+p.design+'</div><div><b>Application:</b> '+p.application+'</div><div><b>B&amp;W:</b> '+p.bw+' · <b>CVD:</b> '+p.cvd+'</div></div>';}
function controlsHTML(){
  return '<span class="cwrap">colors <input type="range" min="2" max="8" value="'+state.n+'" id="cnt"><b id="cv">'+state.n+'</b></span>'
    +'<span class="seg"><span class="sl">show</span>'+[3,6,9].map(function(s){return '<button class="segbtn'+(state.show===s?' on':'')+'" data-show="'+s+'">'+s+'</button>';}).join('')+'</span>'
    +'<span class="seg" title="preview in grayscale — checks black-&-white separability"><button class="segbtn'+(!state.gs?' on':'')+'" data-gs="0">Color</button><button class="segbtn'+(state.gs?' on':'')+'" data-gs="1">B&amp;W</button></span>';
}
function wireControls(root,paint){
  var cnt=root.querySelector('#cnt');if(cnt)cnt.oninput=function(e){state.n=+e.target.value;var cv=root.querySelector('#cv');if(cv)cv.textContent=state.n;paint();};
  root.querySelectorAll('[data-show]').forEach(function(b){b.onclick=function(){state.show=+b.dataset.show;root.querySelectorAll('[data-show]').forEach(function(x){x.classList.toggle('on',+x.dataset.show===state.show);});paint();};});
  root.querySelectorAll('[data-gs]').forEach(function(b){b.onclick=function(){state.gs=(b.dataset.gs==='1');root.querySelectorAll('[data-gs]').forEach(function(x){x.classList.toggle('on',(x.dataset.gs==='1')===state.gs);});paint();};});
}
function famGroups(){var fams={};ORDER.forEach(function(k){var f=PALETTES[k].fam;(fams[f]=fams[f]||[]).push(k);});return fams;}
function mini(k,w){return '<span class="mini" style="width:'+(w||'auto')+'">'+PALETTES[k].cols.map(function(c){return '<i style="background:'+c+'"></i>';}).join('')+'</span>';}
"""
TOAST_CSS = (
    ".dm-toast{position:fixed;bottom:26px;left:50%;transform:translateX(-50%);"
    "background:var(--dm-gray-12);color:var(--dm-bg-page);padding:8px 16px;border-radius:999px;"
    "font-size:12.5px;opacity:0;transition:opacity .18s;pointer-events:none;z-index:99999;}"
    ".dm-toast.show{opacity:1;}\n"
)
SHARED_CSS = (
    """
*{box-sizing:border-box;}
body{margin:0;background:var(--dm-bg-page);color:var(--dm-gray-12);
  font-family:var(--dm-f-sys,"Inter",system-ui,sans-serif);letter-spacing:-.003em;}
.poc-wrap{max-width:1180px;margin:0 auto;padding:26px 24px 90px;}
.poc-h{font-size:13px;color:var(--dm-text-muted);margin:0 0 18px;line-height:1.5;}
.poc-h b{color:var(--dm-gray-12);font-weight:650;}
.mini{display:inline-flex;height:13px;border-radius:3px;overflow:hidden;}
.mini i{flex:1;min-width:3px;}
.strip{display:flex;gap:6px;margin:0 0 4px;}
.sw{appearance:none;background:transparent;border:0;padding:0;font:inherit;flex:1;min-width:0;
  cursor:pointer;display:block;text-align:center;}
.sw .chip{display:block;height:34px;border-radius:6px;transition:transform .1s,box-shadow .1s;}
.sw:hover .chip{transform:translateY(-2px);box-shadow:0 2px 6px rgba(0,0,0,.12);}
.sw .hx{font-family:var(--dm-f-mono,monospace);font-size:9px;color:var(--dm-text-muted);margin-top:4px;overflow:hidden;}
.sw.copied .hx{color:var(--dm-accent-11);font-weight:700;}
.sw.copied .hx::after{content:" ✓";}
.plots{display:grid;grid-template-columns:repeat(3,1fr);gap:11px;margin-top:12px;}
.pcell{border:1px solid var(--dm-border-faint);border-radius:10px;padding:9px 11px;background:var(--dm-bg-page);}
.pcell .pl{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--dm-text-muted);margin-bottom:7px;}
.plots.gs svg,.strip.gs .chip{filter:grayscale(1);}
svg{display:block;width:100%;height:auto;}
.meta{font-size:12px;color:var(--dm-text-muted);line-height:1.6;display:grid;gap:3px;margin-top:13px;}
.meta b{color:var(--dm-gray-12);font-weight:600;}
.code{margin-top:13px;background:var(--dm-i-code-surface);border-radius:8px;padding:11px 14px;
  font-family:var(--dm-f-mono,monospace);font-size:11.5px;color:var(--dm-gray-12);white-space:pre;overflow-x:auto;}
.cwrap{display:inline-flex;align-items:center;gap:7px;font-size:11.5px;color:var(--dm-text-muted);}
.cwrap input[type=range]{width:96px;accent-color:var(--dm-accent-9);}
.seg{display:inline-flex;align-items:center;gap:1px;border:1px solid var(--dm-border-faint);
  border-radius:8px;padding:2px;background:var(--dm-bg-page);}
.seg .sl{font-size:9.5px;color:var(--dm-text-muted);text-transform:uppercase;letter-spacing:.05em;padding:0 6px 0 4px;}
.segbtn{appearance:none;background:transparent;border:0;border-radius:6px;padding:4px 11px;font:inherit;
  font-size:11.5px;font-weight:500;color:var(--dm-text-muted);cursor:pointer;transition:background .12s,color .12s;}
.segbtn:hover{color:var(--dm-gray-12);}
.segbtn.on{background:var(--dm-accent-3);color:var(--dm-accent-11);font-weight:600;}
.dh{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;}
.dh h3{margin:0;font-size:16px;font-weight:700;}
.dh .band{font-size:11px;color:var(--dm-text-muted);font-family:var(--dm-f-mono,monospace);}
.dctrl{margin-left:auto;display:flex;gap:8px;align-items:center;flex-wrap:wrap;}
"""
    + TOAST_CSS
    + """
.poc-switch{position:fixed;top:0;left:0;right:0;z-index:99;display:flex;gap:8px;justify-content:center;
  background:#111;color:#fff;padding:7px;font:600 12px Inter,system-ui,sans-serif;}
.poc-switch a{color:#fff;text-decoration:none;padding:4px 13px;border-radius:999px;border:1px solid #444;opacity:.72;}
.poc-switch a.on{background:#12a594;border-color:#12a594;opacity:1;}
"""
)

# ----------------------------------------------------------------------
# glossary tooltips + plain-language readout + syntax highlight + controls
# ----------------------------------------------------------------------
COMMON_JS = r"""
var GLOSSARY={
 dl:"ΔL* — the smallest lightness gap between any two colors (CIE L*, a 0–100 brightness scale). Bigger means they stay distinct in grayscale or black-and-white print.",
 ls:"L* — CIE lightness, 0 (black) to 100 (white): how bright a color looks to the eye.",
 cvd:"Color-vision check — the smallest difference between colors as seen with simulated color-blindness. Bigger is safer.",
 d:"Deuteranopia — the most common red–green color-blindness (missing green cone), about 6% of men.",
 p:"Protanopia — red–green color-blindness (missing red cone).",
 t:"Tritanopia — blue–yellow color-blindness (rare)."
};
function term(txt,key,cls){return '<span class="term'+(cls?' '+cls:'')+'" tabindex="0" role="note" data-tip="'+GLOSSARY[key].replace(/"/g,'&quot;')+'">'+txt+'</span>';}
function lstar(hex){var m=hex.replace('#','');function L(v){v/=255;return v<=0.04045?v/12.92:Math.pow((v+0.055)/1.055,2.4);}
  var Y=0.2126*L(parseInt(m.substr(0,2),16))+0.7152*L(parseInt(m.substr(2,2),16))+0.0722*L(parseInt(m.substr(4,2),16));
  var f=Y>0.008856?Math.pow(Y,1/3):(7.787*Y+16/116);return Math.round(116*f-16);}
function bwNum(p){var m=p.bw.match(/([\d.]+)/);return m?+m[1]:0;}
function cvdNums(p){var m=p.cvd.match(/d([\d.]+).*?p([\d.]+).*?t([\d.]+)/);return m?{d:+m[1],p:+m[2],t:+m[3]}:{d:0,p:0,t:0};}
function bwVerdict(p){var v=bwNum(p);return v>=6?'Stays clear in black & white':(v>=4?'Mostly clear in black & white':'Some colors merge in black & white');}
function cvdVerdict(p){var c=cvdNums(p),m=Math.min(c.d,c.p,c.t);return m>=6?'Color-blind safe':(m>=4?'Mostly color-blind safe':'Take care for color-blind viewers');}
function readoutHTML(p){var c=cvdNums(p),bwok=bwNum(p)>=6,cvok=Math.min(c.d,c.p,c.t)>=6;
  return '<div class="ro">'
   +'<div class="ro-i"><span class="ro-ic'+(bwok?' ok':'')+'">'+(bwok?'✓':'◑')+'</span>'
     +'<span class="ro-tx">'+term('Black & white','dl')+' — <b>'+bwVerdict(p)+'</b></span>'
     +'<span class="ro-n">ΔL* '+bwNum(p)+'</span></div>'
   +'<div class="ro-i"><span class="ro-ic'+(cvok?' ok':'')+'">'+(cvok?'✓':'◔')+'</span>'
     +'<span class="ro-tx">'+term('Color-vision','cvd')+' — <b>'+cvdVerdict(p)+'</b></span>'
     +'<span class="ro-n">'+term('d','d')+' '+c.d+' · '+term('p','p')+' '+c.p+' · '+term('t','t','r')+' '+c.t+'</span></div>'
   +'</div>';}
function railHTML(){var fg=famGroups(),h='';Object.keys(fg).forEach(function(f){
  h+='<div class="fh">'+f+'</div>';
  fg[f].forEach(function(k){h+='<div class="ri'+(k===state.pal?' on':'')+'" data-k="'+k+'">'+mini(k,'44px')+'<span class="nm">'+PALETTES[k].name+'</span></div>';});});
  return h;}
// ── palette-manipulation options — drive the widget AND the code example ──
// these candidates are proposed get_palette() params: order / start / reverse
state.order='default';state.rev=false;state.shuffleSeed=1;
function shuffleSeeded(arr,seed){var s=(0x6d2b79f5^seed)>>>0;function rnd(){s=s+0x6d2b79f5>>>0;var t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;}
  for(var i=arr.length-1;i>0;i--){var j=Math.floor(rnd()*(i+1)),tmp=arr[i];arr[i]=arr[j];arr[j]=tmp;}return arr;}
function active(){var sel=PALETTES[state.pal].cols.slice(0,state.n);
  if(state.order==='lightness')sel=sel.slice().sort(function(a,b){return lstar(b)-lstar(a);});
  else if(state.order==='shuffle')sel=shuffleSeeded(sel.slice(),state.shuffleSeed);
  if(state.rev)sel=sel.slice().reverse();
  return sel;}
function pySnip(){var p=PALETTES[state.pal];
  var parts=["'"+state.pal+"'","n="+state.n];
  if(state.order==='lightness')parts.push("order='lightness'");
  else if(state.order==='shuffle'){parts.push("order='shuffle'");parts.push('seed='+state.shuffleSeed);}
  if(state.rev)parts.push("reverse=True");
  var note=[state.n+' colors'];
  if(state.order==='lightness')note.push('gradient');
  else if(state.order==='shuffle')note.push('shuffled');
  if(state.rev)note.push('reversed');
  return "import dartwork_mpl as dm\n# "+p.name+"  ("+note.join(', ')+")\ndm.set_cycle(dm.get_palette("+parts.join(', ')+"))";}
function wireRail(after){document.querySelectorAll('.ri').forEach(function(e){e.onclick=function(){state.pal=e.dataset.k;state.n=8;document.getElementById('rail').innerHTML=railHTML();wireRail(after);renderDetail();if(after)after();};});}
function flash(){var d=document.getElementById('detail');d.classList.remove('flash');void d.offsetWidth;d.classList.add('flash');}
// ── Python syntax highlight using the docs' own Pygments token classes ──
var PYKW={'import':'kn','from':'kn','as':'k','def':'k','return':'k','for':'k','in':'k','if':'k','None':'kc','True':'kc','False':'kc'};
function _esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function pyHighlight(code){return code.split('\n').map(function(line){
  if(/^\s*#/.test(line))return '<span class="c1">'+_esc(line)+'</span>';
  var imp=/^\s*(import|from)\b/.test(line),nameCls=imp?'nn':'n',out='';
  var re=/(\s+)|('[^']*'|"[^"]*")|(\b\d+\b)|([A-Za-z_]\w*)|(.)/g,m;
  while((m=re.exec(line))){
    if(m[1])out+='<span class="w">'+m[1]+'</span>';
    else if(m[2])out+='<span class="'+(m[2][0]==="'"?'s1':'s2')+'">'+_esc(m[2])+'</span>';
    else if(m[3])out+='<span class="mi">'+m[3]+'</span>';
    else if(m[4]){var w=m[4];out+='<span class="'+(PYKW[w]||nameCls)+'">'+w+'</span>';}
    else{var ch=m[5],c=(ch==='('||ch===')'||ch===',')?'p':((ch==='.'||ch==='=')?'o':'');
      out+=c?'<span class="'+c+'">'+_esc(ch)+'</span>':_esc(ch);}
  }
  return out;}).join('\n');}
function paintInto(d,strip){var cs=active();
  var sh=d.querySelector('.swhost');sh.className='swhost strip'+(state.gs?' gs':'');sh.innerHTML=strip(cs);
  var pl=d.querySelector('.plots');pl.className='plots'+(state.gs?' gs':'');pl.innerHTML=plots(cs);
  d.querySelector('.code').innerHTML='<pre>'+pyHighlight(pySnip())+'</pre>';wireSwatches(d);}
// ── control styles (overrides the shared segmented controls) ──
var CTRL='tabs';
function _field(label,ctrl){return '<span class="field"><span class="cl">'+label+'</span>'+ctrl+'</span>';}
function _tgl(key,label,on){return '<button class="tgl'+(on?' on':'')+'" data-tgl="'+key+'"><span class="tgl-l">'+label+'</span><span class="tgl-tr"><span class="tgl-kn"></span></span></button>';}
function controlsHTML(){
  var colors=_field('Colors','<input type="range" min="2" max="8" value="'+state.n+'" id="cnt" class="crng"><b id="cv" class="cval">'+state.n+'</b>');
  if(CTRL==='slider'){
    var idx={3:0,6:1,9:2}[state.show];
    var charts=_field('Charts','<input type="range" min="0" max="2" value="'+idx+'" id="shrng" class="crng"><b id="shv" class="cval">'+state.show+'</b>');
    return charts+colors+_tgl('light','Gradient',state.order==='lightness')+_tgl('rev','Reverse',state.rev)
          +_tgl('shuffle','Shuffle',state.order==='shuffle')+_tgl('bw','B&amp;W',state.gs);
  }
  if(CTRL==='chips'){
    return colors
      +_field('Charts','<span class="cchips">'+[3,6,9].map(function(s){return '<button class="copt'+(state.show===s?' on':'')+'" data-show="'+s+'">'+s+'</button>';}).join('')+'</span>')
      +_field('View','<span class="cchips"><button class="copt'+(!state.gs?' on':'')+'" data-gs="0">Color</button><button class="copt'+(state.gs?' on':'')+'" data-gs="1">B&amp;W</button></span>');
  }
  return colors
    +_field('Charts','<span class="optset">'+[3,6,9].map(function(s){return '<button class="topt'+(state.show===s?' on':'')+'" data-show="'+s+'">'+s+'</button>';}).join('')+'</span>')
    +_field('View','<span class="optset"><button class="topt'+(!state.gs?' on':'')+'" data-gs="0">Color</button><button class="topt'+(state.gs?' on':'')+'" data-gs="1">B&amp;W</button></span>');
}
function wireControls(root,paint){
  var cnt=root.querySelector('#cnt');if(cnt)cnt.oninput=function(e){state.n=+e.target.value;var cv=root.querySelector('#cv');if(cv)cv.textContent=state.n;paint();};
  root.querySelectorAll('[data-show]').forEach(function(b){b.onclick=function(){state.show=+b.dataset.show;root.querySelectorAll('[data-show]').forEach(function(x){x.classList.toggle('on',+x.dataset.show===state.show);});paint();};});
  root.querySelectorAll('[data-gs]').forEach(function(b){b.onclick=function(){state.gs=(b.dataset.gs==='1');root.querySelectorAll('[data-gs]').forEach(function(x){x.classList.toggle('on',(x.dataset.gs==='1')===state.gs);});paint();};});
  var sh=root.querySelector('#shrng');if(sh)sh.oninput=function(){state.show=[3,6,9][+sh.value];var v=root.querySelector('#shv');if(v)v.textContent=state.show;paint();};
  root.querySelectorAll('.tgl[data-tgl]').forEach(function(b){b.onclick=function(){var k=b.dataset.tgl;
    if(k==='bw')state.gs=!state.gs;
    else if(k==='rev')state.rev=!state.rev;
    else if(k==='light')state.order=(state.order==='lightness')?'default':'lightness';
    else if(k==='shuffle'){state.order=(state.order==='shuffle')?'default':'shuffle';if(state.order==='shuffle')state.shuffleSeed=Math.floor(Math.random()*100000);}
    root.querySelectorAll('.tgl[data-tgl]').forEach(function(x){var kk=x.dataset.tgl,on=false;
      if(kk==='bw')on=state.gs;else if(kk==='rev')on=state.rev;
      else if(kk==='light')on=(state.order==='lightness');else if(kk==='shuffle')on=(state.order==='shuffle');
      x.classList.toggle('on',on);});
    paint();};});
}
"""
EXTRA_CSS = """
.term{position:relative;display:inline-block;border-bottom:1px dotted var(--dm-gray-7);cursor:help;outline:none;}
.term:focus{border-bottom-color:var(--dm-accent-9);}
.term::after{content:attr(data-tip);position:absolute;left:0;top:calc(100% + 8px);width:max-content;max-width:250px;
  background:var(--dm-gray-12);color:var(--dm-bg-page);padding:9px 12px;border-radius:9px;
  font:400 11px/1.55 var(--dm-f-sys,"Inter",system-ui,sans-serif);letter-spacing:0;text-transform:none;
  opacity:0;visibility:hidden;transform:translateY(-3px);transition:opacity .14s ease,transform .14s ease;
  z-index:60;pointer-events:none;box-shadow:0 5px 16px rgba(0,0,0,.17);white-space:normal;}
.term:hover::after,.term:focus::after{opacity:1;visibility:visible;transform:translateY(0);}
.term.r::after{left:auto;right:0;}
@media(prefers-reduced-motion:reduce){.term::after{transition:none;}}
.ro{display:flex;flex-direction:column;gap:8px;margin:15px 0 19px;}
.ro-i{display:flex;align-items:baseline;gap:9px;font-size:14.5px;flex-wrap:wrap;}
.ro-ic{font-size:13px;line-height:1.2;color:var(--dm-gray-7);font-weight:700;}
.ro-ic.ok{color:var(--dm-accent-10);}
.ro-tx{color:var(--dm-text-muted);}
.ro-tx b{color:var(--dm-gray-12);font-weight:600;}
.ro-n{font-family:var(--dm-f-mono,monospace);font-size:11.5px;color:var(--dm-gray-8);}
.swcap{font-size:11px;color:var(--dm-gray-8);margin-bottom:9px;}
/* descriptions match docs body size — never tiny */
.poc-h{font-size:14.5px;line-height:1.65;}
.meta{font-size:14.5px;line-height:1.72;}
.meta b{font-weight:650;}
/* syntax-highlighted code: inner <pre> inherits Pygments token colors */
.code pre{margin:0;padding:0;background:transparent;font:inherit;color:inherit;white-space:pre;overflow-x:auto;}
/* ── controls: one consistent field/label/value system (no eyebrows) ──
   every field = <label> + <control>; label and options share a size class,
   the label is set apart by color (muted) not by being tiny. */
.field{display:inline-flex;align-items:center;gap:8px;flex:0 0 auto;}
.cl{font-size:13px;font-weight:500;color:var(--dm-gray-9);letter-spacing:normal;text-transform:none;white-space:nowrap;}
.crng{accent-color:var(--dm-accent-9);width:70px;}
.cval{font-size:14px;font-weight:700;color:var(--dm-accent-11);min-width:1ch;}
.optset{display:inline-flex;align-items:center;gap:15px;}
.topt{appearance:none;border:0;background:transparent;padding:1px 1px 5px;font:inherit;font-size:14px;color:var(--dm-text-muted);cursor:pointer;border-bottom:2px solid transparent;transition:color .12s,border-color .12s;}
.topt:hover{color:var(--dm-gray-12);}
.topt.on{color:var(--dm-gray-12);font-weight:650;border-bottom-color:var(--dm-accent-9);}
.cchips{display:inline-flex;gap:6px;}
.copt{appearance:none;background:var(--dm-bg-page);border:1px solid var(--dm-border);border-radius:999px;padding:4px 13px;font:inherit;font-size:13.5px;color:var(--dm-gray-11);cursor:pointer;transition:all .12s;}
.copt:hover{border-color:var(--dm-border-strong);}
.copt.on{background:var(--dm-accent-9);border-color:var(--dm-accent-9);color:#fff;font-weight:600;}
.cchk{display:inline-flex;align-items:center;gap:7px;font-size:14px;color:var(--dm-gray-12);cursor:pointer;}
.cchk input{accent-color:var(--dm-accent-9);width:15px;height:15px;}
/* grouped controls + toggle switch (final slider variant) */
.cgrp{display:inline-flex;align-items:center;gap:20px;flex-wrap:wrap;}
.tgl{appearance:none;border:0;background:transparent;padding:0;cursor:pointer;display:inline-flex;align-items:center;gap:6px;font:inherit;flex:0 0 auto;white-space:nowrap;}
.tgl .tgl-l{font-size:13px;font-weight:500;color:var(--dm-gray-9);transition:color .12s;}
.tgl.on .tgl-l{color:var(--dm-gray-12);}
.tgl-tr{width:32px;height:18px;border-radius:999px;background:var(--dm-gray-5);position:relative;transition:background .15s;flex:0 0 auto;}
.tgl-kn{position:absolute;top:2px;left:2px;width:14px;height:14px;border-radius:50%;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.28);transition:left .15s;}
.tgl.on .tgl-tr{background:var(--dm-accent-9);}
.tgl.on .tgl-kn{left:16px;}
.step{display:inline-flex;align-items:center;gap:8px;}
.stepb{appearance:none;border:1px solid var(--dm-border);background:var(--dm-bg-page);border-radius:7px;
  width:24px;height:24px;font:inherit;font-size:15px;line-height:1;color:var(--dm-gray-11);cursor:pointer;
  display:inline-flex;align-items:center;justify-content:center;}
.stepb:hover{border-color:var(--dm-border-strong);color:var(--dm-gray-12);}
.stepv{font-size:14px;font-weight:700;color:var(--dm-accent-11);min-width:1ch;text-align:center;}
"""

# ── Guided master-detail layout ──
g_css = """
.md{display:grid;grid-template-columns:198px 1fr;gap:28px;align-items:start;}
@media(max-width:760px){.md{grid-template-columns:1fr;gap:18px;}.detail{position:static!important;}}
.rail{display:flex;flex-direction:column;gap:1px;}
.rail .fh{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;
  color:var(--dm-gray-10);margin:16px 0 5px;}
.rail .fh:first-child{margin-top:0;}
.ri{display:flex;align-items:center;gap:10px;padding:4px 9px;border-radius:9px;cursor:pointer;min-width:0;}
.ri:hover{background:var(--dm-gray-a2);}
.ri.on{background:var(--dm-accent-2);}
.ri .mini{flex:0 0 36px;height:12px;border-radius:4px;}
.ri .nm{font-size:12px;font-weight:400;color:var(--dm-gray-12);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;}
.ri.on .nm{color:var(--dm-accent-11);font-weight:500;}
.detail{position:sticky;top:48px;background:var(--dm-bg-subtle);border-radius:18px;padding:24px 26px;}
.d-ey{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--dm-accent-11);margin-bottom:7px;}
.d-title{display:flex;align-items:baseline;gap:11px;flex-wrap:wrap;}
.d-title h3{margin:0;font-size:25px;font-weight:700;letter-spacing:-.02em;}
.d-key{font-family:var(--dm-f-mono,monospace);font-size:13px;color:var(--dm-accent-11);background:var(--dm-accent-2);
  padding:2px 9px;border-radius:6px;font-weight:500;cursor:pointer;transition:background .12s;align-self:center;}
.d-key:hover{background:var(--dm-accent-3);}
.d-key.copied{background:var(--dm-accent-9);color:#fff;}
.d-key.copied::after{content:" ✓";}
/* fixed height (3 lines) so switching palettes never shifts the layout */
.d-use{font-size:15.5px;color:var(--dm-gray-11);line-height:1.62;margin:11px 0 8px;min-height:4.86em;}
/* readout uses the Reading style (borderless inline) — inherits EXTRA_CSS .ro base */
/* controls: parallel fields; slider variant groups palette-shaping vs preview */
.d-bar{display:flex;align-items:center;gap:13px;flex-wrap:nowrap;margin-bottom:16px;}
.swhost{display:flex;gap:7px;margin-bottom:18px;}
.swhost .sw{flex:1;}
.swhost .chip{height:46px;border-radius:11px;}
.swhost .hx{font-size:9px;}
.plots{gap:13px;}
.pcell{border:0;background:var(--dm-bg-page);border-radius:13px;padding:10px 12px;}
.meta{margin-top:8px;}
"""
g_js = r"""
function renderDetail(){var p=PALETTES[state.pal],d=document.getElementById('detail');
  d.innerHTML='<div class="d-ey">'+p.fam+' palette</div>'
    +'<div class="d-title"><h3>'+p.name+'</h3><code class="d-key" title="copy the name to use in code">'+state.pal+'</code></div>'
    +'<p class="d-use">'+p.intent+'</p>'
    +readoutHTML(p)
    +'<div class="d-bar">'+controlsHTML()+'</div>'
    +'<div class="swhost"></div><div class="plots"></div>'
    +'<div class="meta"><div><b>How it’s built</b> '+p.design+'</div><div><b>Good for</b> '+p.application+'</div></div>'
    +'<div class="code highlight"></div>';
  var dk=d.querySelector('.d-key');if(dk)dk.onclick=function(){if(navigator.clipboard)navigator.clipboard.writeText(state.pal);dmToast(state.pal+' copied');dk.classList.add('copied');setTimeout(function(){dk.classList.remove('copied');},900);};
  function paint(){paintInto(d,swStrip);}wireControls(d,paint);paint();}
document.getElementById('rail').innerHTML=railHTML();wireRail();renderDetail();
"""


def gjs(ctrl):
    return f"CTRL={ctrl!r};\n" + g_js


# ── scope every CSS rule under the widget root (page-safe embedding) ──
def scope_css(css, root):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, i, n = [], 0, len(css)
    while i < n:
        if css[i].isspace():
            i += 1
            continue
        j = i
        while j < n and css[j] not in "{;":
            j += 1
        if j >= n:
            break
        pre = css[i:j].strip()
        if css[j] == ";":
            out.append(pre + ";\n")
            i = j + 1
            continue
        d, k = 1, j + 1
        while k < n and d:
            d += 1 if css[k] == "{" else (-1 if css[k] == "}" else 0)
            k += 1
        body = css[j + 1 : k - 1]
        if pre.startswith("@keyframes") or pre.startswith("@font-face"):
            out.append(f"{pre} {{{body}}}\n")
        elif pre.startswith("@media") or pre.startswith("@supports"):
            out.append(f"{pre} {{\n{scope_css(body, root)}}}\n")
        else:
            sels = []
            for s in (x.strip() for x in pre.split(",") if x.strip()):
                if s in ("body", "html"):
                    sels.append(root)
                elif s.startswith(":root"):
                    sels.append(root + s[5:])
                elif s.startswith(("html", "body")) and (
                    len(s) == 4 or s[4] in " .[:>~+"
                ):
                    sels.append(root + s[4:])
                else:
                    sels.append(f"{root} {s}")
            out.append(f"{', '.join(sels)} {{{body}}}\n")
        i = k
    return "".join(out)


# ── SHARED_JS = data blocks + shared helpers (treemap/waffle/swatch/copy) ──
SHARED_JS = DATA + "\n" + HELPERS


def build() -> str:
    """Return the self-contained ``#dm-exp`` fragment."""
    scoped = scope_css(SHARED_CSS + EXTRA_CSS + g_css, f"#{ROOT}")
    pane = "max-height:calc(100vh - 120px);overflow-y:auto;"
    thin = (
        f"#{ROOT} .rail{{scrollbar-width:thin;}}\n"
        f"#{ROOT} .rail::-webkit-scrollbar{{width:9px;}}\n"
        f"#{ROOT} .rail::-webkit-scrollbar-thumb{{background:var(--dm-gray-a4);border-radius:9px;"
        f"border:2px solid transparent;background-clip:content-box;}}\n"
    )
    # widget overrides: inherit docs font, left-only self-scroll (rail pinned, detail flows)
    ov = (
        f"#{ROOT}{{width:100%;font-family:inherit;letter-spacing:normal;}}\n"
        f"#{ROOT} .rail{{position:sticky;top:96px;{pane}padding-right:8px;}}\n"
        f"#{ROOT} .detail{{position:static;top:auto;}}\n" + thin
    )
    # column-fill: drop the right TOC and let the main column use the full width
    colfill = (
        "#rside,.sy-rside{display:none!important;}\n"
        "@media(min-width:1280px){.sy-main{width:calc(100% - 18rem)!important;max-width:none!important;}}\n"
        ".yue,.yue.bd-article,.bd-article,.bd-content,.bd-article-container,.bd-main{max-width:none!important;}\n"
    )
    return (
        BANNER + f'<div id="{ROOT}" class="yue">\n'
        f"<style>\n{scoped}{ov}{colfill}</style>\n"
        f'<div class="md"><div class="rail" id="rail"></div>'
        f'<div class="detail" id="detail"></div></div>\n'
        f"<script>(function(){{{SHARED_JS}\n{COMMON_JS}\n{gjs('slider')}}})();</script>\n"
        f"</div>\n"
    )


if __name__ == "__main__":
    frag = build()
    OUT.write_text(frag, encoding="utf-8")
    print(f"OK - wrote {OUT} ({len(frag):,} B)")

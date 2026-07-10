---
orphan: true
---

# Fonts · 현재 B — 결과 1칼럼

현재 faceted browser(왼쪽 rail 필터 + 카드 결과)를 **동작·카드 디자인 그대로 유지**하고,
결과 그리드만 **2칼럼 → 1칼럼**으로 바꾼 버전입니다. 실제 docs 폭(~800px)에 임베드된 모습입니다.

```{raw} html
<div style="border:1px solid var(--dm-accent-6);background:var(--dm-accent-2);border-radius:12px;padding:13px 16px;margin:6px 0 22px;">
  <div style="font-size:15px;font-weight:700;color:var(--dm-gray-12);">현재 B · 왼쪽 rail 필터 + <b style="color:var(--dm-accent-11);">1칼럼</b> 결과</div>
  <div style="font-size:13px;color:var(--dm-gray-11);line-height:1.55;margin-top:3px;">변경점은 결과 그리드 <code>repeat(2, …)</code> → <code>1fr</code> 한 곳뿐. 필터·상세·복사·반응형은 그대로.</div>
</div>
```

```{raw} html
:file: _static/poc_fonts_facets.frag.html
```

---
orphan: true
---

# Fonts · 1칼럼 faceted browser — 디자인 리파인

1칼럼 faceted browser의 디테일을 다듬은 3안입니다. 세 가지 요구를 각각 다르게 풉니다 —
필터를 콤팩트하게(현재 유지 vs 슬림), 1칼럼 카드 내부 요소·배치 개선, main의 color/palettes 메뉴 디자인 차용.
모두 실제 docs 폭(~800px)에 임베드된 모습이고, 상단 사이트 테마 토글로 라이트/다크가 따라옵니다.

```{raw} html
<style>
  .rf-banner{border:1px solid var(--dm-accent-6);background:var(--dm-accent-2);border-radius:14px;
    padding:14px 18px;margin:6px 0 22px;}
  .rf-banner .t{font-size:16px;font-weight:750;color:var(--dm-gray-12);}
  .rf-banner .d{font-size:13.5px;color:var(--dm-gray-11);line-height:1.55;margin-top:3px;}
  .rf-banner .d b{color:var(--dm-gray-12);}
</style>
```

---

## R1 — 콤팩트 rail + 웨이트 스트립 카드

```{raw} html
<div class="rf-banner">
  <div class="t">R1 · Compact rail + weight-strip cards</div>
  <div class="d">왼쪽 rail을 <b>슬림하게</b>. 카드마다 웨이트 래더를 <b>팔레트 스와치 스트립</b>처럼(클릭 복사) + 상단 "내 텍스트 입력"으로 전 카드 라이브 재조판.</div>
</div>
```

```{raw} html
:file: _static/poc_fonts_r1.frag.html
```

---

## R2 — 상단 툴바 + 전체폭 가로 카드

```{raw} html
<div class="rf-banner">
  <div class="t">R2 · Top toolbar + full-width horizontal cards</div>
  <div class="d">필터를 <b>상단 툴바</b>로 옮겨 폭을 확보하고, 카드를 <b>전체폭 가로형</b>으로. 강한 호버 모션 + 웨이트 스와치 스트립.</div>
</div>
```

```{raw} html
:file: _static/poc_fonts_r2.frag.html
```

---

## R3 — Palettes 페이지 쌍둥이 (현재 rail 유지 + 스타일 일치)

```{raw} html
<div class="rf-banner">
  <div class="t">R3 · Palettes-twin (현재 rail 유지)</div>
  <div class="d">rail 구조는 <b>현재처럼 유지</b>하되 categorical/colors 페이지와 <b>토큰·간격·스와치 스트립을 동일</b>하게. Fonts가 Palettes의 픽셀 형제처럼.</div>
</div>
```

```{raw} html
:file: _static/poc_fonts_r3.frag.html
```

---

## 참고 — 현재 1칼럼 (리파인 전)

```{raw} html
<div class="rf-banner">
  <div class="t">현재 1칼럼 (baseline)</div>
  <div class="d">방금 커밋한 버전. 위 3안이 이걸 어떻게 다듬는지 대조.</div>
</div>
```

```{raw} html
:file: _static/poc_fonts_facets.frag.html
```

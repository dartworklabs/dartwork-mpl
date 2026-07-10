---
orphan: true
---

# Fonts browser — UX 개선 A/B

공통 개선(문구·복사 편의·키보드·role 배지·tnum 증명·drawer 이동)은 이미
`/fonts/`에 적용되어 있습니다. 아래 두 변형은 그 위에 얹는 상호작용 방향입니다.

```{raw} html
<style>
  .poc-banner{border:1px solid var(--dm-accent-6);background:var(--dm-accent-2);
    border-radius:14px;padding:15px 18px;margin:6px 0 24px;display:flex;flex-wrap:wrap;
    gap:7px 16px;align-items:baseline;}
</style>
```

## A — Preview workbench (내 문장 + 차트 롤 크기)

```{raw} html
<div class="poc-banner">시그니처 = 타이핑한 문장을 tick/label/title 실측 크기로 전 패밀리 오디션</div>
```

```{raw} html
:file: _static/pocs/fonts_ux_a.frag.html
```

## B — Pin & compare (후보 고정 + 나란히 비교)

```{raw} html
<div class="poc-banner">시그니처 = 최대 3개 패밀리를 고정해 같은 문장·같은 크기로 비교</div>
```

```{raw} html
:file: _static/pocs/fonts_ux_b.frag.html
```

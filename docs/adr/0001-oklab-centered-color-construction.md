---
orphan: true
---

# ADR 0001: OKLab 중심 색 생성과 모델 기반 상대 Y 계약의 분리

Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 sRGB; it
is not a measurement of a particular display, perceived brightness, or OKLab
`L`.

- 상태: Accepted
- 날짜: 2026-07-14
- 결정자: dartwork-mpl maintainers
- 대체하는 설계: `2026-07-03-color-system-v5-design.md`의 CIELAB L\* + OKLCH 혼합 생성 규칙

## 맥락

현재 공개 `Color` 객체는 이미 OKLab을 정규 저장 공간으로 쓰고, hue·chroma 조작은
OKLCH, 경로 등화는 OKLab ΔE로 수행한다. 그러나 팔레트와 컬러맵 컴파일러는
OKLCH `L`을 이진 탐색해 렌더된 sRGB가 목표 CIELAB L\*에 도달하도록 만든다.
따라서 한 색을 만들기 위해 두 지각 모델을 오가며, 문서의 “OKLCH가 L/h를
보존한다”는 설명과 실제 “CIELAB L\*를 맞춘다”는 구현이 충돌한다.

고정된 기준 백색과 CIELAB 기준 조건에서 L\*는 `Y`의 단조 변환이다. 따라서
카탈로그가 보존하려는 명목상 sRGB 순서는 CIELAB을 생성 경로에 다시 넣지 않고
계산된 상대 CIE Y로 검사할 수 있다. 이 계산만으로 특정 디스플레이, 인쇄 공정,
지각 밝기, 또는 흑백 변환의 안전성을 보장할 수는 없다. CIEDE2000과 명명된 CVD
시뮬레이션은 서로 다른 한계를 가진 모델 기반 회귀 진단이므로, OKLab을 쓴다는
이유만으로 검증 계층에서 제거하지 않는다.

또한 기존 200개 팔레트 색, 두 기본 cycle, 43×256 컬러맵, curated 색과
discrete 선택은 이미 공개 결과다. 좌표계를 정리한다는 이유로 이 결과를 바꾸는
것은 허용하지 않는다.

## 결정

1. 색의 **생성 좌표계**는 OKLab/OKLCH 하나로 통일한다.
   - lightness와 거리: OKLab `L`, OKLab ΔE
   - chroma와 hue: OKLCH `C`, `h`
   - gamut mapping: OKLCH `L`과 `h`를 유지하며 `C`를 줄이는 하나의 정책

2. 레시피의 밝기 파라미터는 0–1 범위의 `neutral_tone`으로 저장한다.
   `neutral_tone := cbrt(relative_Y)`인 출력 계약 좌표다. 따라서
   `Y = neutral_tone³`으로 CIELAB을 경유하지 않고 모델 기반 상대 Y 목표를 정의한다.
   이것은 chromatic swatch 자체의 OKLCH `L`도, 유한 정밀도 OKLab 행렬로 다시
   계산한 중립 회색의 `L`도 아니다. 상대 Y 커널은 v5 행렬의 Y row를 white=1이
   되도록 정규화한 `(0.21267287873271212, 0.7151521284847872,
   0.07217499278250072)`를 쓴다.

3. 모델 기반 상대 Y는 지각 좌표가 아니라 **선택적 출력 계약**으로 취급한다.
   - 기존 shipped 팔레트와 ordered 컬러맵은 호환성과 명목상 Y topology를
     위해 `Y = neutral_tone³` 잠금을 적용한다.
   - 상대 Y solver는 요청된 `C`와 `h`에서 OKLCH `L`을 탐색한다. 그 뒤 공통
     gamut mapper는 solver가 얻은 `L`과 `h`를 유지하면서 필요한 경우 `C`를
     줄일 수 있다. 따라서 전체 파이프라인이 chroma를 절대 바꾸지 않는다고
     주장하지 않는다.
   - 새 알고리즘을 시험할 때는 잠금 없는 direct-OKLCH 경로도 제공하되, 공개
     catalog는 검증된 잠금 정책을 명시적으로 선택한다.
   - sequential은 `Y` 단조, diverging은 중심 기준 `Y` 대칭, isoluminant
     cyclic은 `Y` 일정성을 출력 계약으로 갖는다. categorical/qualitative은
     L\* trajectory를 갖지 않는다.

4. CIELAB/CIEDE2000은 **검증 전용 격리 계층**에 남긴다.
   - CIEDE2000과 CVD 결과는 기존 품질 하한과 호환성을 확인한다.
   - recipe/compiler는 CIELAB 또는 CIEDE2000을 import할 수 없다.
   - multi-hue discrete의 기존 선택은 index manifest로 고정하고,
     CIEDE2000은 선택기가 아니라 사후 gate로만 사용한다.

5. 현행 산출물은 exact compatibility contract로 고정한다.
   - 기존 palette, cycle, curated/manual 색, 43×256 LUT, 공개 이름·kind·reverse
     등록, 기존 discrete 결과는 byte-for-byte 동일해야 한다.
   - v5 L\* 목표가 모두 L\*>8 구간에 있으므로 raw legacy row의 white 합을
     `S=1.0000001`이라 할 때
     `neutral_tone = (L\* + 16) / (116 × cbrt(S))`로 한 번 변환한다.
     그러면 `Y_normalized = neutral_tone³ = Y_legacy / S`라서 기존 solver의
     float RGB와 모델 기반 상대 Y 목표를 함께 보존한다. 실험 재컴파일에서 palette 200개와
     43×256 LUT의 hex mismatch가 모두 0임을 확인했다.
   - 위 변환은 v5 마이그레이션 범위에만 쓴다. L\*≤8 호환 입력은 CIE의
     piecewise inverse로 legacy `Y`를 구하고 `S`로 정규화한 뒤
     `neutral_tone = cbrt(Y_normalized)`로 바꾼다.
   - 기존 XYZ Y row `(0.2126729, 0.7151522, 0.0721750)`는 반올림 때문에 합이
     `1.0000001`이라 그대로는 흰색의 relative Y가 1을 넘는다. white-normalized
     row는 이 모순을 제거하면서 실험 재컴파일에서 palette와 43×256 LUT의 hex를
     하나도 바꾸지 않았다. CSS Color 4 rational row는 이 레시피에 그대로 대입했을
     때 palette 1개와 LUT 59개 hex를 바꾸므로 이번 호환 마이그레이션에서는
     채택하지 않는다.

6. build gate를 현행 CI 불변식 이상으로 강화하고, 변경 전후 HTML/JSON 비교
   리포트를 항상 생성할 수 있게 한다. 임계값만 통과하는 열화는 허용하지 않고,
   현행 실측 품질을 하한으로 사용한다.

## 결과

장점:

- 생성 규칙의 지각 모델이 하나가 되고 `L`의 의미가 명확해진다.
- 명목상 sRGB 출력 순서 요구는 계산된 상대 Y로 명확히 설명하고 검증한다.
- 기존 외관과 모델 기반 상대 Y를 바꾸지 않은 채 내부 결합을 제거할 수 있다.
- CIEDE2000을 별도 모델 기반 진단으로 유지해 단일 지표에만 의존하지 않는다.

비용:

- `neutral_tone`과 실제 chromatic OKLCH `L`의 차이를 문서에서 분명히 설명해야
  한다.
- 상대 Y 잠금에는 결정론적 root solve가 계속 필요하다. 다만 이는 다른 지각
  공간을 맞추는 우회가 아니라 명시적인 호환성 계약이다.
- v5 JSON은 호환성 fixture로 보존하고, v6 recipe SSOT와 역할을 분리해야 한다.

## 기각한 대안

### CIELAB L\*를 계속 생성 좌표로 사용

출력을 보존하기는 쉽지만 혼합 모델과 문서 모순을 그대로 남긴다. L\* 단조성으로
보장하려던 것은 결국 `Y` 단조성이므로 불필요한 간접 계층이다.

### 모든 곳에서 direct OKLCH L만 사용

개념은 가장 단순하지만 hue/chroma에 따라 `Y`가 달라져 기존 색과 명목상 상대-Y
topology가 변한다. 현행 파라미터의 단순 치환 실험은 팔레트에서 최대 ΔE00 10.42,
컬러맵에서 단조·대칭 위반을 만들었다. 호환성 및 출력 계약 없이 적용하지 않는다.

### CIEDE2000도 OKLab ΔE로 전부 교체

모델 기반 회귀 진단의 다양성을 잃고 기존 CVD 임계값의 의미를 바꾼다.
생성에서는 제거하되 검증에서는 두 지표를 함께 유지한다.

## 부록: ADR 0002에서 흡수한 계약 (2026-08-02)

[ADR 0002](0002-separate-shipped-color-compatibility-from-oklab-authoring.md)는
기각했다. 그 설계문서에서 **코드나 테스트로 복원할 수 없는** 계약만 아래로
옮긴다. 나머지는 커밋 `8ce8b852`의 git 이력에 남아 있다.

### A1. 동결의 정본은 문서가 아니라 테스트다

- 런타임 색 표면의 판정기: `tests/test_shipped_colors_hash.py`. named 1,272 ·
  colormaps 99×256 · presets 588 · discrete 1,344 · curated 15의 sha256을
  각각 고정한다. 색이 바뀌면 어느 표면이 바뀌었는지까지 알려준다.
- 18개 exact surface의 목록은 `tests/test_color_v6_comparison.py::EXACT_FIELDS`가
  정본이다. **문서는 이 목록을 복제하지 않는다** — 복제본은 반드시 어긋난다.
- v5 비교 baseline은 커밋 `6be8cb56`이다. 이 커밋은 main `12d16bac`의
  문서 전용 자식이므로 `src/` 트리는 둘이 동일하다.

### A2. 2단계 gamut 경계는 교체하지 않는다 (가장 중요)

`_generate.gamut_max_chroma`는 이름이 말하는 값을 계산하지 않는다. 고정 chroma
`0.04`에서 OKLCH `L`을 먼저 풀고 그 `L`을 얼린 뒤 최대 chroma를 탐색하므로,
**고정 상대 Y에서의 진짜 최대 chroma가 아니다.** 실측 오차는 참값 대비
−21.5% ~ +13.2%다. 마찬가지로 `_cmaps.diverging_pair`만 gamut 캡을 적용하지
않아 diverging 계열 어두운 팔의 chroma가 `to_rgb`에서 조용히 깎인다.

**두 곳 모두 알고 있는 결함이며, 그럼에도 shipped 콜그래프에서 교체를
금지한다.** 고치면 diverging 11종의 어두운 팔이 최대 6 ΔEok 진해지는 등 승인된
색이 실제로 바뀌기 때문이다. 오차의 크기와 무관하게 금지다.

이 근사를 대체하려면 (a) 별도 제안으로 바뀌는 색을 렌더해 비교하고,
(b) 승인을 받은 뒤, (c) `tests/test_shipped_colors_hash.py`의 digest를 의도적으로
재생성해야 한다. 테스트를 통과시키려고 digest를 고치는 것은 이 계약의 위반이다.

향후 authoring 레인이 분리되면 이 근사는 `..._shipped_compat` 접미사를 붙여
의미를 이름으로 봉인한다. 해당 진입점은 아직 구현되어 있지 않다.

### A3. 좌표와 레이어의 역할 구분

| 좌표 | 역할 |
|---|---|
| OKLab `L`·ΔEOK, OKLCH `C`·`h` | 생성(construction) |
| modeled relative Y, `neutral_tone` | 출력 계약(output contract) |
| CIELAB L\*, CIEDE2000, CVD 시뮬레이션 | 검증(validation) 전용 |
| WCAG contrast | 보고(reporting) 전용, 지정된 전경/배경 쌍에 한정 |

modeled relative Y는 휘도 측정값도, 지각 밝기도, OKLab `L`도, 접근성 인증도
아니다.

### A4. authoring 레인의 규칙 (신규 패밀리에만 적용)

- 좌표는 `luminance_lock: bool`이 아니라 discriminated union으로 표현한다 —
  direct-OKLCH 점과 fixed-relative-Y 점은 서로 다른 타입이다.
- 신규 패밀리의 **기본값은 direct OKLCH**다. fixed-Y는 사유를 명시한 좁은
  opt-in으로만 쓴다.
- selector는 `_metrics`/`_gates`를 import하지 않는다. CIEDE2000과 CVD는 선택이
  끝난 뒤의 admission gate로만 쓴다.

### A5. frozen index는 fail-closed다

multi-hue discrete 선택은 `MULTI_HUE_DISCRETE_INDICES` replay다. 매니페스트에
행이 없으면 **실패시킨다.** 런타임 재최적화로 되돌아가면 빌드 데이터 손상이
가려지고 출력이 알고리즘 리비전에 의존하게 된다.

### A6. 미해결로 남기는 것

고정 상대 Y에서의 엄밀한 최대 chroma solver(다항식 근 격리 + 독립 오라클 교차
검증)는 A2의 금지 때문에 shipped 경로에 들어갈 수 없다. authoring 레인이 생길
때 그 레인 전용으로 도입한다.

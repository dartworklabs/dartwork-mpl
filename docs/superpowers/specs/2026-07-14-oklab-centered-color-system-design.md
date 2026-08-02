# OKLab-centered color system redesign

- **Date:** 2026-07-14
- **Status:** Accepted
- **Decision:** [ADR 0001](../../adr/0001-oklab-centered-color-construction.md)

## 1. 목표

dartwork-mpl 색 생성기를 OKLab/OKLCH 중심으로 재구성하되, 사용자가 이미 쓰는
색과 컬러맵은 바꾸지 않는다. “OKLab만 고집해서 더 나빠지는” 전환을 막기 위해
기존 결과, 모델 기반 상대 CIE Y, CVD, 균일성의 전후 차이를 같은 리포트에서
검증한다.

여기서 상대 CIE Y는 nominal D65 sRGB에서 계산한 모델 좌표다. 특정 디스플레이의
측정값, 지각 밝기, 또는 OKLab `L`이 아니다.

완료 조건은 다음과 같다.

- recipe/compiler의 CIELAB L\*·CIEDE2000 의존 0개
- 공개 palette 200색, cycle, curated/manual 색 exact 일치
- 43×256 연속 LUT와 모든 기존 multi-hue discrete 선택 exact 일치
- 이름, kind, reverse 등록, semantic token, MCP/typing surface 변화 0개
- 현행보다 약하지 않은 OKLab·모델 기반 상대 Y·CVD·gamut gate
- deterministic side-by-side HTML과 machine-readable JSON 리포트
- 전체 테스트, docs asset determinism, visual regression 통과

## 2. 범위와 비범위

범위:

- `_colors` conversion, gamut, tone, metrics, recipe, compiler, gates, build,
  discrete selection
- v6 SSOT와 v5 compatibility fixture
- color-system 문서, theory figure, explorer metric, prompt/MCP 설명
- 테스트·CI·비교 리포트

비범위:

- 공개 `Color` API나 토큰 이름 변경
- vendored OpenColor/Ant/Chakra/Material/Primer/Tailwind 원본 수정
- 이번 결정과 독립적인 mutable-hash, writable-view API 재설계
- 색의 미적 retuning. 별도 제안과 비교 승인 없이는 shipped hex를 바꾸지 않는다.

## 3. 현행 구조의 문제

현행 `Color`의 canonical store는 OKLab이다. 그러나 compiler는 다음 경로를 쓴다.

```text
CIELAB L* target
  -> OKLCH L binary search
  -> gamut-map to sRGB
  -> rendered CIELAB L* measurement
  -> OKLab ΔE arc-length equalization
```

이 구조는 다음 문제를 만든다.

1. `L`이 CIELAB L\*인지 OKLCH L인지 호출부마다 다르다.
2. 문서는 gamut mapping이 “L\*와 h를 유지”한다고 쓰지만 실제 `Color.to_rgb()`는
   OKLCH `L`과 `h`를 유지한다.
3. 명목상 출력 순서를 보존하려는 요구가 특정 지각 모델의 생성 제약으로 잘못
   표현돼 있다.
4. build gate가 full-LUT CI보다 약해, 새 구현이 기존 품질보다 나빠져도 통과할 수
   있다.
5. multi-hue discrete는 CIEDE2000으로 색을 직접 선택해 construction과 validation이
   다시 결합된다.

## 4. 새 색 모델

### 4.1 좌표와 책임

| 책임 | 좌표/지표 | 역할 |
|---|---|---|
| canonical color | OKLab | 저장, 변환 기준 |
| authoring | OKLCH | `L`, `C`, `h` 경로 |
| 경로 등화 | OKLab ΔE ×100 | 인접 스텝 균일성 |
| 모델 기반 출력 좌표 | nominal linear-sRGB relative CIE `Y` | 단조·대칭·등 Y 호환성 |
| 모델 진단 | CIEDE2000 + CVD | 사후 회귀 검증만 |
| gamut | sRGB | OKLCH L/h 유지, C 축소 |

### 4.2 `neutral_tone`

`neutral_tone`은 `cbrt(relative_Y)`로 정의한 출력 계약 좌표다. chromatic
OKLCH L이나 유한 정밀도 OKLab 행렬로 재계산한 중립 회색 L과 동일하다고
주장하지 않는다.

```text
Y_target = neutral_tone ** 3
```

shipped catalog의 기존 목표는 모두 CIELAB toe 위에 있으므로 마이그레이션 때만
다음 동치를 사용해 v6 값을 산출한다.

```text
legacy_Y_white = 1.0000001
neutral_tone = (legacy_Lstar + 16) / (116 * cbrt(legacy_Y_white))
```

이 식은 v5 fixture를 v6로 변환하는 provenance이지, production compiler의
CIELAB 연산이 아니다. v6 코드와 SSOT에는 변환된 0–1 tone 값만 저장한다. 새
레시피는 L\* 숫자를 입력으로 받지 않는다. 일반적인 legacy 변환기는 L\*≤8에서
CIE piecewise inverse로 raw `Y`를 구하고 legacy white 합으로 나눈 뒤
`cbrt(Y_normalized)`를 취해야 하며, 위 식을 검정까지 외삽하면 안 된다.

### 4.3 렌더 정책

compiler의 단일 primitive는 target `Y`와 실제 chromatic OKLCH `L`을 이름부터
분리한다. 편의 wrapper만 `tone`을 받아 `target_y=tone³`으로 넘긴다.

```python
render_oklch_at_tone(
    *,
    tone: float,
    chroma: float,
    hue: float,
    luminance_lock: bool,
) -> Rgb
```

- `luminance_lock=False`: `OKLCH(L=tone, C=chroma, h=hue)`를 gamut-map한다.
- `luminance_lock=True`: 상대 Y solver는 요청된 `C`와 `h`에서 실제 OKLCH
  `L`을 탐색한다. 이어지는 공통 gamut mapper는 그 결과의 `L`과 `h`를
  유지하면서 필요하면 `C`를 줄일 수 있다.
- 탐색 tolerance와 iteration 수는 하나의 named gamut/tone policy에 둔다.
- low-level solver 이름은 `solve_oklch_l_for_relative_y`이며, actual OKLab L,
  mapped chroma, achieved Y, residual을 결과에 담는다.
- shipped palette와 ordered/cyclic catalog는 명시적으로 lock policy를 선택한다.
- root solve는 `Y`만 읽으며 validation 계층을 import하지 않는다.
- `RelativeY`와 `NeutralTone`은 finite `0..1` 경계를 갖는 내부 value type으로
  구분한다.

이 설계에서 `tone`은 경로를 쓰는 좌표이고 실제 chromatic `L`은 결과 좌표다.
둘을 같은 이름으로 노출하지 않는다.

## 5. 생성과 검증의 경계

### construction이 사용할 수 있는 것

- OKLab/OKLCH 변환
- OKLab ΔE
- sRGB gamut 판정과 mapping
- `Y` output contract

### construction이 사용할 수 없는 것

- CIELAB L\*, a\*, b\*
- CIEDE2000
- CVD simulation 결과를 objective로 삼는 선택

architecture test가 `_recipe.py`, `_tone.py`, `_generate.py`, `_cmaps.py`,
`_discrete.py`에서 validation-only symbol import를 금지한다.

### validation에 남기는 것

CIEDE2000과 Machado/BVM CVD는 기존 품질의 모델 기반 회귀 진단으로 유지한다. CIELAB
변환은 CIEDE2000 구현 내부와 v5 compatibility report에만 존재할 수 있다.

## 6. 호환성 계약

### exact 대상

exact contract은 다음 18개 surface를 이름, 순서, 값까지 재귀적으로
비교한다.

1. `palette`: 20×10 = 200 hex;
2. `cycles`: octave와 octave_print;
3. `cmaps_256`: 43×256 = 11,008 hex;
4. `curated_rows`;
5. `diverging_canonicals`;
6. `semantic_coordinates`;
7. `semantic_colors`;
8. `dark_cycle_coordinates`;
9. `dark_cycle`;
10. `taxonomy`: 56 family;
11. `registrations`: forward/reverse를 포함한 99 matplotlib cmap 이름;
12. `typing_literals`;
13. `mcp_discovery`;
14. `public_inventory`;
15. `discrete_hex`;
16. `reverse_discrete_hex`;
17. `multi_hue_discrete_indices`: family별 `n=1..8` LUT index; 그리고
18. `vendor_colors`: all 892 vendor token name → lowercase `#rrggbb` values.

`vendor_colors` provenance는 원본 asset과 namespace prefix를 함께 고정한다:
`opencolor.txt` → `oc.*`, `tailwind_colors.json` → `tw.*`,
`material_colors.json` → `md.*`, `ant_colors.json` → `ad.*`,
`chakra_colors.json` → `cu.*`, `primer_colors.json` → `pr.*`.
baseline extractor는 accepted commit의 이 원본을 읽고 candidate compiler는
현재 bundled 원본을 별도로 parse한다. 두 경로 모두 duplicate token,
prefix, six-digit RGB schema를 검증하며 `vendor_colors` canonical hash를
독립 exact surface로 비교한다.

v5 JSON은 immutable visual/golden fixture로 남긴다. v6 JSON은
`src/dartwork_mpl/asset/color/color_v6_ssot.json`에 패키징하며 recipe와 현재 gate
report의 운영 SSOT가 된다. production은 단일 검증 accessor로 이 asset을 읽고,
`_recipe.py`나 `_build.py`에 같은 recipe/index literal을 복제하지 않는다.
palette/direct-32/full-256/cycle/curated/dark/forward-discrete 각 행의 hash,
count, unique count, adjacent-duplicate count, max-run 계약도 pinned v5 입력에서
생성해 저장한다. 기존 quantized LUT의 자산별 의도된 중복을 보존하므로 전역
all-unique 규칙은 두지 않는다.
`_generated.py`는 v6에서 파생된다.

감사 시점(`12d16bac`)의 frozen 식별자는 다음과 같다.

| 대상 | SHA-256 |
|---|---|
| `_generated.py` | `999950452b2f2d8e2d58449af7c7fa043d918c922719be68939f765f5f762d54` |
| `_curated.py` | `ee570b840323015db427e1bb36f500eb4f12d67027aa3894f9b7ba02caa295f5` |
| v5 JSON | `a75bd08f2ae5606ec3076a01877ba813b9f2899a96b95739a44e5d3493b68518` |
| canonical palette JSON | `4431b8d1accbeca9527e6097a62c048a51fd6fd699588998c202c359b98b458e` |
| canonical cycles JSON | `cda50ebd800a44dbb3b8d58a4fe53924ecaf914f7dbadbc2ac196e77cf6595cd` |
| canonical 43×256 cmap JSON | `e026ce047dd8a186299b2857e3d8c81f2b2bc4b7249df37f35b7c0093c5240c1` |
| canonical 892-entry `vendor_colors` JSON | `6dc6053c4f8c66adb9d7deb746c3e7eee0295c27cc107b37c872b46f83f79a72` |

### exact 확인

- 항목별 mismatch count가 0이어야 한다.
- `_generated.py`, `_curated.py`, v5 fixture SHA-256을 baseline manifest에 기록한다.
- float solver equivalence는 최대 RGB channel drift `<= 5e-12`, frozen v5
  solver와의 achieved-Y drift `<= 5e-13`을 요구한다. 절대 target-Y residual은
  현행 24-step gamut boundary의 미세 불연속 때문에 전 점에서 `5e-13` 이내일 수
  없으므로 asset별 frozen residual보다 악화되지 않아야 하며 raw 값으로 보고한다.
  `Y=0`, `Y=1` endpoint는 각각 exact black/white와 residual 0으로 처리한다.
- 플랫폼 차이가 8-bit 경계를 넘으면 build를 실패시키고 JSON에 최대 OKLab ΔE,
  ΔE00, `ΔY`를 함께 기록한다. 임의 tolerance로 hex 변화를 숨기지 않는다.
- baseline은 candidate compiler를 다시 실행해 만들지 않는다. 위 release fixture의
  literal 배열과 frozen discrete index manifest를 읽는다. generator와 golden을
  같은 변경에서 함께 고쳐 호환성 검사를 우회할 수 없어야 한다.

## 7. 강제 gate

모든 gate는 32-stop 미리보기만이 아니라 export된 256 LUT에도 적용한다.

현행 실측 하한은 최소 다음을 manifest에 고정한다.

| surface | 현행 실측 |
|---|---|
| palette family OKLab-step CV | `0.0107 .. 0.0225` |
| direct-32 seq/multi OKLab-step CV | `0.03098 .. 0.05393` |
| full-256 seq/multi worst signed ΔY | `-0.0005864` |
| full-256 CVD worst signed ΔY | `-0.0042956` |
| diverging max OKLab arm-arc ratio | `1.075` |
| cyclic seam ΔEOK (`hue/halo/corona`) | `0.3388 / 0.5570 / 0.6196` |
| octave raw CVD floor (common/tritan) | `10.312044 / 8.291186` |
| octave_print raw CVD floor | `10.374645 / 9.761556` |
| dark cycle raw CVD floor | `11.513135 / 11.010756` |

이 값은 반올림 display가 아니라 raw double로 판정한다. exact migration에서는
candidate가 동일해야 하고, 향후 의도적 색 변경 모드에서도 각 asset별 baseline보다
나빠질 수 없다. qualitative에는 cycle의 10/8 floor를 일괄 적용하지 않는다. 현행
curated set 중 일부의 최솟값이 약 4이므로 palette별 실측 하한을 쓴다.

### palette

- actual OKLab L과 `Y` 모두 엄격 단조
- 인접 OKLab ΔE cv는 현행 family별 baseline 이하 또는 전역 0.08 중 더 강한 값
- gamut-map 이후 finite, channel range, hue identity 검사

### sequential / multi-hue

- 256-stop `Y` 단조 허용오차는 8-bit quantization에서 유도하고 현행 `.2 L*`
  같은 다른 공간 단위를 쓰지 않는다.
- OKLab L 단조
- gray 변환은 `Y`로 직접 생성하고 같은 순서를 유지
- OKLab ΔE cv와 Y-span은 보고만 하지 않고 현행 baseline보다 악화되면 실패

### diverging

- 중심이 최대 `Y`
- 양 arm 각각 단조
- mirrored `Y` 오차와 OKLab step balance가 현행 baseline보다 악화되면 실패
- center와 endpoint 정체성 유지

### cyclic

- seam OKLab ΔE와 seam/mean ratio 모두 현행 이하
- isoluminant hue map은 `Y` spread가 현행 이하
- twilight형은 두 arm topology와 midpoint symmetry 검사

### qualitative / cycle / discrete

- 기존 hex/index exact
- normal/protan/deutan/tritan ΔE00 하한은 현행 실측값보다 낮아질 수 없음
- OKLab ΔE도 병렬 보고해 단일 oracle 의존을 피함

## 8. conversion과 metric 정리

1. `_conversion.py`를 gamma, linear-sRGB, OKLab/OKLCH의 유일한 수학 커널로 만든다.
2. 모델 기반 nominal-D65-sRGB `Y`는 parity와 white=1 불변식을 함께 지키기 위해 기존 Y row를
   정규화한 `SRGB_D65_Y=(0.21267287873271212, 0.7151521284847872,
   0.07217499278250072)`를 단일 SSOT로 쓴다. 기존 raw row는 합이
   `1.0000001`이므로 CIEDE2000 내부의 legacy XYZ 변환에만 남긴다. WCAG
   contrast의 반올림 계수와 이름도 명시적으로 분리한다.
3. `_metrics.py`의 중복 gamma/OKLab 구현을 제거하고 conversion kernel을 사용한다.
4. gray simulation은 `L* -> Y` 왕복 대신 입력 `Y`를 neutral sRGB로 직접 변환한다.
5. published OKLab, sRGB, CIEDE2000 reference vectors와 conversion parity test를
   추가한다.
6. gamut search iteration/tolerance/chroma fraction literal을 named policy로 모은다.
   shipped catalog는 현재의 fixed-L/h chroma 축소, tolerance `1e-6`, 24회 탐색,
   최종 clamp를 그대로 고정한다. 신규 family용 `max_chroma_at_tone()` 개선은
   compatibility policy와 분리해 grid property test를 먼저 통과해야 한다.

## 9. discrete migration

현행 multi-hue optimizer는 CIELAB band·chroma와 CIEDE2000 maximin으로 출력을
선택한다. migration 시 모든 `(family, n=1..8)` 결과의 256-LUT index를 v6 SSOT에
고정한다. runtime은 이 index를 읽을 뿐 CIEDE2000으로 재선택하지 않는다.

새 family용 후보 선택기는 OKLab/OKLCH로 작성한다. 결과는 별도 CIEDE2000/CVD
gate를 통과해야 하며, 기존 family의 frozen index를 자동 교체하지 않는다.

## 10. side-by-side 검증 공간

`scripts/compare_color_systems.py`가 다음을 결정론적으로 만든다.

```text
build/color-system-comparison/
├── index.html
└── report.json
```

HTML은 외부 네트워크나 JavaScript framework 없이 다음을 한 화면에 보여준다.

- palette: v5 / v6 / difference chip
- 43 cmap: v5 32-stop / v6 32-stop / grayscale / CVD strips
- OKLab L, modeled relative Y, neighbor ΔE profile overlay
- mismatch와 worst-case metric을 색으로 표시한 summary
- 설명용 direct-OKLCH(unlocked) 결과와 shipped luminance-locked 결과 비교

JSON은 schema version, source digests, exact mismatch counts, max/p95 OKLab ΔE,
ΔE00, ΔY, gate before/after, discrete indices를 담는다. HTML은 사람
검수용이다.

The comparator process exit code is the authority for the current invocation.
`report.json` is a completed-run gate record and last-write evidence, not proof
of the current invocation from file presence alone. Exit `0`과 `1`은 각각
신뢰할 수 있는 pass/fail report를 작성하고, exit `2`는 새 trustworthy
report를 완성하지 못한 run을 뜻한다. CI는 현재 process exit code로
step을 판정하고 JSON은 완료된 run의 검사 가능한 증거로 upload한다.

비교 metric은 candidate 코드에만 의존하지 않는다. frozen reference case와
kernel hash를 가진 비교 모듈을 사용하며, CIEDE2000은 published Sharma reference
pair를, CVD는 source-pinned Machado matrices, project-adapted BVM matrices, 그리고
project-derived regression cases를 먼저 통과해야 한다. JSON은
`allow_nan=False`, 정렬된 key, 고정 소수 표시를 쓰되 판정은 반올림 전 double로
수행한다.

## 11. SSOT와 파생물

```text
v5 fixture (immutable) ───────────────┐
                                      ├─> compatibility report
v6 recipe SSOT -> compiler -> gates ──┤
                         ├─> _generated.py
                         ├─> typing / registry metadata
                         ├─> explorers / theory figures
                         └─> comparison HTML + JSON
```

- historical v5 design/plan은 수정 이력으로 보존하되 상단에 superseded 표기를 넣는다.
- current `docs/color_system/design-rationale.md`는 본 결정을 기준으로 다시 쓴다.
- stale `gen_palettes.py`와 `dm_palettes_gen.json`은 migration fixture로 격리하거나
  제거하고, 더 이상 필요하지 않으면 `colorspacious` dev dependency도 제거한다.
- generated asset에는 generator와 regeneration command를 명시한다.

## 12. 구현 순서

1. v5 exact manifest, 256-LUT digest, discrete index golden을 먼저 고정한다.
2. 실패하는 compatibility/tone/Y/architecture tests를 작성한다.
3. conversion·luminance kernel과 named gamut policy를 통합한다.
4. v6 neutral-tone recipe와 luminance-locked OKLCH renderer를 구현한다.
5. palette/cmap compiler를 옮기고 exact parity를 확인한다.
6. multi-hue discrete를 frozen index + independent validation으로 분리한다.
7. full-LUT build gates를 승격한다.
8. side-by-side report를 구현하고 golden/CI를 연결한다.
9. docs, explorers, theory assets, prompts/MCP 설명을 동기화한다.
10. 전체 test/docs/visual/format/type 검증 후 diff와 리포트를 검수한다.

## 13. 검증 명령

최종 검증은 최소 다음을 포함한다.

```bash
uv run pytest tests/test_color_* tests/test_family_invariants.py \
  tests/test_discrete_forms.py -q
uv run python -m dartwork_mpl._colors._build
uv run python scripts/compare_color_systems.py --check
uv run pytest tests/ -q --no-cov
```

build 전후 `git diff --exit-code -- src/dartwork_mpl/_colors/_generated.py`가
성공해야 한다. docs asset generator를 실행한 뒤에도 두 번째 실행은 byte-identical
해야 한다.

## 14. 감사에서 발견했으나 별도 후속인 항목

다음은 실제 문제지만 본 좌표계 전환과 결합하면 위험이 커 별도 이슈로 남긴다.

- mutable `Color`의 hash 안정성
- writable view의 NaN 검증
- family taxonomy의 이름 heuristic 제거와 typed catalog 통합
- 일반 `dartwork_mpl` import의 eager registration 계약을 재설계하는 구조

이 항목들은 본 작업의 exact output contract를 만족한 뒤 독립적으로 다룬다.
단, comparison CLI는 검증 독립성을 위해 `_colors/` source tree를 고유한 private
namespace alias로만 로드한다. 이는 public package import/registration 동작을
바꾸는 구조 개편이 아니라 감사 프로세스에 한정된 격리 경계이며, committed
`_generated.py`와 runtime registry를 읽거나 변경해서는 안 된다.

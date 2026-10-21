---
orphan: true
---

# 구조 감사: `_colors/` · `diagnostics/` · `_luminance.py` · `_build_entry.py`

기준: `code-implement` SKILL(+structure/modeling/python), limn `tools/check_boundaries.py`. 대상 `0e88b810`(main), 수치는 실측.

## 1. 현재 구조 요약
총 16,014줄, 33개 모듈. `import dartwork_mpl` 시 실제 로드되는 것은 14개(≈3,940줄, **런타임**)이고
나머지 13개(≈10,630줄, `_typing.py` 1,389줄 생성물 포함)는 빌드·검증 전용인데 같은 평면 폴더에 있다.

- 런타임: `_color` 876, `_views` 428, `_conversion` 387, `_gamut` 425, `_contrast` 177, `_luminance` 46, `_generated` 172(생성),
  `_curated` 465, `_families` 85, `_discrete` 193, `_semantic` 55, `_loader` 224, `_register` 118, `_api` 279, `__init__` 59
- 빌드: `_build` 177, `_ssot` 818, `_recipe` 194, `_tone` 527, `_generate` 160, `_cmaps` 516, `_cycles` 43, `_catalog` 1,476, `_typing` 1,389(생성)
- 검증: `_gates` 1,184, `_comparison` 1,699, `_metrics` 230, `_compatibility_metrics` 2,220
- diagnostics: `_colors` 535, `_colormaps` 419, `_fonts` 313, `__init__` 37; 부트스트랩 `_build_entry` 88

내부 import 그래프(요지):
- `__init__` → `_api, _color, _contrast, _loader, _register, _semantic, _views`
- `_color` ↔ `_views` (TYPE_CHECKING 순환; `_views.py:167-380`이 `Color._L/_a/_b`를 직접 씀), `_color` → `_conversion, _gamut`
- `_contrast` → `_luminance` → (지연 import) `_colors._conversion` — **최상위 모듈과 패키지 간 순환** (`_luminance.py:16-19` 주석이 순환 회피라고 명시)
- `_api` → `_discrete, _families, _register`; `_loader/_register/_semantic/_families/_discrete` → `_curated, _generated`
- 빌드: `_build` → `_catalog, _comparison, _gates, _ssot`; `_catalog` → `_cmaps, _curated, _cycles, _generate, _ssot`;
  `_recipe` → `_ssot, _tone`; `_cmaps/_generate` → `_recipe, _tone, _conversion`; `_tone` → `_gamut`
- 검증: `_gates` → `_compatibility_metrics, _ssot`; `_comparison` → `_compatibility_metrics, _gates`
- `diagnostics._colormaps` → `_colors._families`(private), `diagnostics._colors` → `_colors._loader`(private)

밖에서 들어오는 import (private 이름 횡단 표시 ★):
- `dartwork_mpl/__init__` → `_colors` surface 13개, `_build_entry`, `diagnostics.plot_fonts`; `explore`·`util` → surface만
- ★ `helpers/labels.py:45` → `_loader.ensure_loaded`; ★ `mcp/resources.py:137`, `mcp/tools.py:402` → `_loader.COLOR_LIBRARIES`
- ★ `style.py:385,530` → `_colors._semantic.apply_semantic, SEMANTIC_TOKEN_NAMES`
- ★ `validate/_checks/grayscale_safety.py:98` → `_conversion._srgb_to_oklab, relative_y_srgb_d65`;
  ★ `validate/_checks/_luminance.py:5`, `text_contrast.py:11` → `_luminance._contrast_ratio/_linearized/_rel_lum`

밖으로 나가는 import: ★ `_api.py:162` → `style._style_lock` (style → `_colors._semantic`과 합쳐 **colors↔style 순환**),
`_api.py:237` → `units`, ★ `diagnostics/_fonts.py:110` → `font._FONT_DIR`.
파일 경로 결합: `_catalog.py:49-51,1050-1068`이 `mcp/tools.py·resources.py·prompts.py·artifacts/transport.py`와
`_semantic.py`를 **AST로 읽고**, `theme-dark.mplstyle`을 읽는다. `_gates.py:38`, `_catalog.py:47`은 `parents[3]`로
레포 루트의 `docs/superpowers/specs/assets/...json`을 읽는다 — 휠 설치본에서는 존재하지 않는 경로다.

레포 밖 소비자: tests 54파일, `scripts/` 4, `docs/color_system/*.py` 2, `docs/_static/scripts/` 2가 `_colors._xxx`를 직접 import한다.

## 2. 파일트리 결함

1. **런타임과 빌드·검증이 한 폴더.** 변경 이유가 셋(런타임 API / 카탈로그 생성 / 호환성 검증)인데 평면 `_*.py` 27개로
   섞였다. `_build_entry.py:72-84`가 `_colors/__init__`을 실행하지 않는 빈 패키지를 만들어야 하는 것도 이 혼재 탓이다.
2. **god 파일 4개.** `_catalog.py` 1,476줄: 모듈 docstring은 "Pure immutable snapshots"인데 JSON 벤더 색 로딩(`:875-942`),
     MCP 소스 AST 스캔(`_McpDecoratorVisitor :947`, `scan_mcp_discovery :1050`), 소스 해시(`:1348`),
     typing payload 생성(`:1263`), discrete 파생(`:1181-1260`, `_discrete.py`와 같은 kind 분기 복제)을 함께 가진다.
     MCP 도구 이름이 바뀌면 색 카탈로그 파일이 바뀌는 구조다.
   - `_comparison.py` 1,699줄: 순수 비교(`:1-1170`)와 HTML 렌더러(`:1171-1699`; 소비자는 `scripts/compare_color_systems.py`뿐).
   - `_gates.py` 1,184줄: 순수 gate 판정과 레포 경로 fixture 로딩(`load_quality_baseline`, `:38-47`)이 섞임.
   - `_compatibility_metrics.py` 2,220줄: 독립 오라클이라 단일 파일 자체는 의도적. **다만 경로와 바이트 SHA가
     `asset/color/color_v6_ssot.json:29`, `ACCEPTED_ORACLE_PATH`(`:31`), quality fixture에 고정**되어 있어(§4 참조)
     옮기거나 한 글자라도 고치면 `:1539`, `:2033` 검사가 실패한다.
3. **중복 정의.** `CatalogSnapshot`이 3곳(`_catalog.py:340` dataclass, `_comparison.py:54`·`_gates.py:64` 동일 Protocol),
   `_catalog_for_oracle`·`_as_mapping`·`_freeze` 가 `_gates`/`_comparison`에 각각, `_freeze`/`_thaw`가 `_ssot`·`_catalog`·
   `_comparison`·`_gates`에 4벌, `de_ok_rgb/hex_from_rgb`가 `_generate`·`_metrics`·`_cmaps`(`_de_ok_rgb`)에 3벌.
   `_gates`와 `_comparison`은 같은 검증 슬라이스로 같이 바뀌므로(git co-change 2회) 하나로 합칠 대상이다.
   반대로 `_compatibility_metrics`의 sRGB/OKLab 재구현은 "독립 오라클"이 존재 이유라 중복이 아니다.
4. **diagnostics는 기술 계층 묶음.** "asset을 시각화한다"는 이유로 colormap·색·폰트를 묶었다. 이력상
   `diagnostics/_colormaps.py`(11커밋)는 `colors/_loader.py`와 6회, `test_color_v5_register.py`와 6회 함께 바뀌었고,
   `_fonts.py`(2커밋)는 색과 같이 바뀐 적이 없다. `_colors.py:138 _text_brightness`는 의도적 휴리스틱(docstring)이라 합치지 않는다.
5. **테스트가 코드에서 멀다.** 이 영역 테스트는 `tests/` 평면에 ≈40파일 ≈17,000줄(`test_color_v6_comparison.py` 2,072,
   `test_color_v6_architecture.py` 1,310 등), 이름은 기능이 아니라 `v5_`/`v6_` **버전 접두사**로 묶였다. `testpaths = ["tests"]`,
   휠 `packages = ["src/dartwork_mpl"]`(제외 규칙 없음)라 지금은 슬라이스 내부 `tests/`가 수집되지도, 휠에서 빠지지도 않는다.
6. **경계 검사 없음.** limn `tools/check_boundaries.py` 상당물이 없고 `test_color_v6_architecture.py:612`가 빌더 경계 하나만 본다.
   (git 이력은 squash PR 위주라 co-change 증거가 약해, import 그래프와 `sys.modules` 실측을 1차 근거로 했다.)

## 3. 타입 결함
`mypy --strict`(+`exhaustive-match`)와 ruff `D100-D107`은 이미 이 영역에서 0건이다. 결함은 표현 수준에 있다.

| 항목 | 건수 / 위치 |
|---|---|
| `cast(` | 92: `_catalog` 45, `_compatibility_metrics` 19, `_comparison` 14, `_gates` 5, `_ssot` 4, `_recipe` 3, `_build` 1, `_build_entry` 1 |
| `Mapping/dict[str, object]`·`JsonMapping` | 123줄: `_comparison` 39, `_compatibility_metrics` 27, `_gates` 21, `_ssot` 17, `_catalog` 16 |
| `Any` | 43줄, 대부분 `np.ndarray[Any, Any]`(허용). 실결함: `_contrast.py:20,25,41,86` 색 입력이 `Any`; `diagnostics/_colors.py:233,245`, `_fonts.py:129` `list[dict[str, Any]]` |
| `type: ignore` | 5: `_api.py:53,74`, `_metrics.py:223,230`, `diagnostics/_colors.py:506` |
| `__all__` 없음 | `_luminance`, `_build_entry`, `_compatibility_metrics`(고정이라 추가 불가), `_typing`, `_generated`. `_conversion.py:9`는 `__all__ = []`인데 `relative_y_srgb_d65`를 validate가 씀 |
| 예외로 흐름 제어 | `diagnostics/_colors.py:96,240,419,439,466` `except (ValueError, TypeError): pass` / `(0,0,0)` 대체 |

핵심 결함(규칙 위반 순):
1. **validate만 하고 parse하지 않는 권위 데이터.** `_ssot.load_color_v6_ssot()`(`_ssot.py:816`)이 81개 `raise`로 검증한 뒤
   `Mapping[str, object]`를 돌려준다. 그래서 소비자가 다시 `_mapping`/`_sequence`+`cast`로 꺼낸다
   (`_recipe.py:74-110`, `_catalog.py:135-142`, `_gates.py:192`). 같은 `_require_mapping` 류 헬퍼가 `_ssot`·`_catalog`·
   `_recipe`에 따로 있다. → 타입화된 `ColorAuthority`(recipe·coordinates·policies·row_contracts·multi_hue_indices)로 한 번 parse.
2. **status 문자열 + 의미 없는 채움값.** `GateViolation`(`_gates.py:110`)은 `rule: str`에 `"=="`, `">="`, `"valid"` 등을
   넣고, 잘못된 metric은 `observed=0.0, allowed=1.0, rule="valid"`로 표현한다(`_gate_invalid :262-274`). 이를
   `_comparison._adapt_gate_violation`(`:758-770`)이 `metric == "/candidate"`·`rule == "valid"` 문자열 분기로
   `Violation.code: str`(`"candidate_quality_invalid"`/`"quality_metric_invalid"`/`"quality_regression"`/`"exact_mismatch"`)로
   다시 바꾼다. → `ThresholdViolation | InvalidMetric | InvalidCandidate`, 비교 쪽은 variant별 dataclass + `TypeAlias`.
3. **variant 전용 필드.** `ExactMismatch`(`_comparison.py:150`)는 `baseline_present: bool` + `baseline: object` —
   present=False일 때 값은 의미가 없다 → `Added | Removed | Changed`. `HexRowComparison`의 `MaybeSummary`(= `NumericSummary | None`)
   6필드(`:244-249`)는 RGB 파싱 실패 시 일괄 None — 계산 불가 행을 별도 타입으로. `ComparisonReport.passed: bool`은
   `violations`에서 유도되는 값이라 모순 상태가 가능하다.
4. **Family의 kind 문자열 + 선택 필드.** `Family(kind: Literal[...5], has_continuous: bool, discrete_size: int | None)`
   (`_families.py`)에서 `discrete_size`는 multi-hue·cyclic일 때만 None, `has_continuous`는 qualitative일 때만 False —
   kind로 결정되는 중복 상태다. 소비처가 `family.kind == "..."` 분기 13곳(`_api.py:124-232`, `_discrete.py:51-53`,
   `_catalog.py:1223-1242`). → kind별 frozen dataclass union + `match`. 공개 `show_colors(kind=...)`의 문자열은 경계에서 parse.
5. **무명 튜플이 슬라이스를 넘음.** 가변 `COLOR_LIBRARIES: list[tuple[str, str, str, str]]`(`_loader.py:104`)을 mcp 두 곳
   (`resources.py:139`, `tools.py:405`)이 위치 언패킹해 prefix만 쓴다 → surface는 `ColorLibrary` tuple 또는 prefix 목록.
6. **가변 공개 상수.** `_generated.PALETTE/CYCLES/CMAPS_256/MULTI_HUE_DISCRETE_INDICES`, `_curated.CURATED/CURATED_META`
   (`dict[str, dict[str, str]]` — `family`/`band` 문자열 메타), `_semantic._MAPS`가 모두 가변 dict. 동결 해시 대상이라
   **값은 그대로 두고** `Mapping` 타입 + `MappingProxyType`으로만 바꾼다. `_generated.py`는 `_build.py:51`이 문자열로
   찍어내므로 생성기와 같은 PR에서.
7. **absent를 None으로.** `_comparison._as_mapping/_number/_strict_rgb -> X | None` — 슬라이스 내부라 우선순위 낮음.
8. `Color`의 view setter 가변성(`_views.py:169-414`), `classify_cmap -> str`은 **공개 계약이라 유지**.

## 4. 제안 목표 구조
고정점(움직이면 인터페이스·동결을 건드림):
- `dartwork_mpl._colors` 패키지 경로와 re-export — `docs/migration.md:29,332`가 공개 import 경로로 안내한다.
- `python -m dartwork_mpl._colors._build` — CI 3곳(`ci.yml:342`, `docs.yml:68`, `release.yml:69`), `docs/color_system/validation.md:31`,
  `_build_entry._COLOR_BUILD_MODULE`. `_build.py`는 이 경로에 CLI 진입점으로 남는다(배선만).
- `_colors/_compatibility_metrics.py` — 경로+SHA가 출하 자산 `color_v6_ssot.json`에 고정. **이동·수정 금지, `__all__` 추가도 금지**;
  바꾸려면 별도 사람 승인(CLAUDE.md의 동결 규칙과 같은 성격).
- `_generated.py`/`_typing.py` 경로 — 생성기(`_build.py`, `scripts/generate_typing.py`)와 ruff exclude가 경로를 안다.
- `dartwork_mpl.diagnostics`의 4개 이름, `dm.*` 13개 색 이름, `tests/test_shipped_colors_hash.py`.
- `_build_entry.py`는 `_colors/__init__` 실행 전에 돌아야 하므로 패키지 밖 최상위에 남는다(진입점, `__all__` 추가만).

```text
src/dartwork_mpl/_colors/
  __init__.py            진입점: 아래 surface re-export + 등록 3회 호출만
  _build.py              진입점: python -m CLI → build.main
  _compatibility_metrics.py  동결(verify 소유, 위치 고정)
  model/     Color, color, cspace, hex, oklab, oklch, rgb, *View/*ViewIterator,
             srgb_to_linear, srgb_to_oklab, relative_y_srgb_d65        (_color,_views,_conversion,_gamut)
  contrast/  readable_text_color, ensure_contrast, wcag_relative_luminance, contrast_ratio (_contrast + _luminance)
  catalog/   Family(union), FAMILIES, discrete_colors, PALETTE, CYCLES, CMAPS_256, CURATED,
             SEMANTIC_TOKEN_NAMES                                      (_generated,_curated,_families,_discrete,_typing)
  registry/  ensure_loaded, ensure_registered, apply_semantic, COLOR_LIBRARIES (_loader,_register,_semantic)
  families_api.py  colors, set_colors, list_colors, show_colors        (_api; 한 파일 슬라이스)
  diagnostics/     classify_cmap, render_cmap_catalog, render_color_catalog
  build/     main, compile_candidate_snapshot, CatalogSnapshot (_ssot,_recipe,_tone,_generate,_cmaps,_cycles,_catalog→snapshot+sources)
  verify/    evaluate_catalog, compare_catalog, render_comparison_html, GateReport (_gates,_comparison→compare+report_html)
  _metrics.py  src 내 소비자 0 (tests 4·docs 스크립트 2만 import) → docs 도구 쪽 이전 또는 제거를 별도 결정
  각 슬라이스/tests/   해당 테스트
src/dartwork_mpl/diagnostics/__init__.py  공개 경로 유지: 위 3개 + font 쪽 plot_fonts re-export(진입점)
```

테스트 배치: model ← `test_color_conversion, _parser, _view, _eq_gamut, _v6_gamut, _api`; catalog ← `test_discrete_forms,
test_palette_family_taxonomy, test_family_invariants, test_color_v5_presets, test_typing_parity`; registry ← `test_loader,
test_color_v5_loader/_register/_semantic`; families_api ← `test_color_model_b_api`; diagnostics ← `test_diagnostics(색 부분),
test_diagnostics_color_brightness, test_colormap_explorer_taxonomy`; build ← `test_color_v5_build/_generate/_recipe/_cmaps_*/_cycles,
test_color_v6_tone/_ssot_validation/_atomic_writes/_architecture, test_color_build_entrypoint`; verify ← `test_color_v5_gates,
test_color_v6_comparison/_quality_oracle/_compatibility`. 슬라이스를 가로지르는 외부 판정기(`test_shipped_colors_hash`, `test_drift`,
`test_docs_*`)는 `tests/`에 남긴다.

허용 슬라이스 의존(한 방향, 사업 이유):
- `contrast → model`: WCAG 휘도는 sRGB 선형화를 model의 정의로 계산해야 한 값이 된다.
- `catalog → model`: multi-hue discrete 선택이 relative Y(`_discrete.py`)를 쓴다.
- `registry → catalog`: matplotlib에 등록하는 값이 곧 출하 카탈로그다.
- `families_api → catalog, registry`: 이름→패밀리 해석과, cmap 조회 전 등록 보장.
- `diagnostics → catalog, registry`: 패밀리 분류 목록과 색 라이브러리 목록을 그린다.
- `build → model, catalog`: 생성은 model의 변환·gamut, `_curated`·`_cycles` 명세를 입력으로 한다. 출력은 파일(`_generated.py`).
- `verify → build`(`CatalogSnapshot`·authority만), `verify → _compatibility_metrics`. **verify는 model을 import하지 않는다**(현재도
  그렇다) — 오라클 독립성이 존재 이유. 역방향 금지는 ADR 0001 A4("selector는 `_metrics`/`_gates`를 import하지 않는다").
- 패키지 밖: `validate → model, contrast`; `mcp, helpers.labels → registry`; `style → registry`; `util/explore → model, families_api`.
- 끊을 것: `families_api → style._style_lock` (rcParams 락을 플랫폼 모듈로 내려 style과 colors가 함께 import), `build.sources →
  mcp 소스 AST` (MCP 인벤토리는 mcp 쪽 테스트가 소유하도록 이전 — 색 카탈로그의 변경 이유에서 MCP 제거), `_luminance ↔ _colors` 순환.

## 5. 분할 PR 제안 (순서대로, 각각 독립 머지 가능)
공통 검증: `pytest tests/test_shipped_colors_hash.py tests/test_drift.py`, `python -m dartwork_mpl._colors._build --check`, `mypy src`.

1. **PR1 경계 검사 + 수집 설정** (~350줄, 이동 없음). `tests/architecture/test_color_boundaries.py`(limn 방식 AST import 그래프:
   private 횡단, shared→slice, 순환, 미등록 의존, decision 모듈의 타 기능 import)와 현재 위반 목록을 ratchet allowlist로.
   `testpaths`에 `src/dartwork_mpl` 추가, 휠에서 `**/tests/**` 제외. 위험: 낮음 — `uv build` 후 휠 목록 비교, 주입 위반 5종
   실패 확인. 충돌: `chore/skm-antipattern-ratchet`(pyproject·tests 신규 파일).
2. **PR2 순환 2개 절단** (~150줄). `_style_lock`을 플랫폼 모듈로, `_luminance` 내용을 `_colors` 안 contrast 쪽으로 옮기고
   `dartwork_mpl._luminance`는 삭제(private; validate 2곳·테스트 import 수정). 검증: `test_validate_accessibility, test_style,
   test_color_api, test_concurrency`. 충돌: `origin/fix/grayscale-safety-per-axes-2026-08-02`(validate/_checks).
3. **PR3 빌드·검증 순수 이동** (`git mv` + import 수정 ~250줄). `build/`, `verify/` 생성, `_build.py`는 진입점으로 축소,
   `_compatibility_metrics.py`는 그대로. 갱신: `scripts/*.py` 4개, `docs/color_system/*.py`, `docs/_static/scripts/*`,
   테스트 import, `test_color_v6_architecture.py:958`의 경로 목록, `_catalog._candidate_source_hashes` 경로 키(리포트 전용,
   고정 해시 없음 확인됨). 위험: 중 — 경로 문자열 결합. 검증: 빌드 `--check` 바이트 동일, `test_color_v6_*`, `test_color_v5_build`,
   `test_color_build_entrypoint`. 충돌: 안티패턴 ratchet baseline(파일 경로 키) — docs 스크립트 경로는 안 바뀌므로 낮음.
4. **PR4 런타임 슬라이스 이동 A: model + contrast** (~300줄). `__all__` 선언, `_colors/__init__` re-export 불변,
   `validate`의 `_conversion` private import를 surface로. 검증: `test_color_conversion/_parser/_view/_api`, `test_api_stability`.
5. **PR5 런타임 슬라이스 이동 B: catalog + registry + families_api** (~350줄). `_generated.py`/`_typing.py`는 경로 고정이므로
   catalog surface가 re-export만 하거나 생성기 출력 경로를 같은 PR에서 바꾼다(택일, 후자는 `_build.py`·`generate_typing.py`·ruff
   exclude 동시 수정). mcp·helpers·style import를 surface로. 검증: `test_loader, test_color_v5_register/_semantic, test_style,
   test_typing_parity, tests/mcp`. 충돌: mcp 쪽 진행 작업(최근 #511/#514/#517이 `mcp/tools.py` 반복 수정).
6. **PR6 diagnostics 재배치** (~200줄). `_colormaps`/`_colors` → `_colors/diagnostics/`, `_fonts` → font 소유(폰트 감사와 조율),
   `dartwork_mpl.diagnostics`는 re-export 진입점, private `_plot_single_library` re-export 제거. 검증: `test_diagnostics*, test_docs_snippets`.
7. **PR7~9 테스트 동거 이동** (슬라이스별 1 PR, 순수 `git mv`; `v5_`/`v6_` 접두사 개명은 별도 커밋). 검증: 수집 테스트 수 동일.
8. **PR10 Family variant 타입** (~250줄). kind별 frozen dataclass + `TypeAlias`, `match`로 13곳 분기 교체. 공개 `show_colors(kind=)`,
   `dm.colors` 동작·메시지 불변. 검증: `test_color_model_b_api, test_palette_family_taxonomy, test_discrete_forms`, 해시 테스트.
9. **PR11 gate/비교 결과 variant 타입** (~400줄). `GateViolation`·`Violation`·`ExactMismatch` → union, `passed` → property.
   `to_payload()` JSON 키 불변. 검증: `test_color_v5_gates, test_color_v6_comparison(EXACT_FIELDS), test_color_v6_quality_oracle`.
10. **PR12~13 권위 데이터 parse** (각 ~400줄). `load_color_v6_ssot` → `ColorAuthority`; recipe/policies 먼저, 다음 row_contracts/
    coordinates. 출하 JSON·해시 불변. 검증: `test_color_v6_ssot_validation, test_color_v6_architecture`, 빌드 `--check`, cast 수.
11. **PR14 build/verify 내부 분할** (~300줄). `_catalog` → `snapshot`+`sources`(I/O), `_comparison` → `compare`+`report_html`,
    `CatalogSnapshot` Protocol 1개, `_freeze/_thaw` 슬라이스당 1벌. MCP AST 스캔 이전은 mcp 담당과 합의 후 별도 PR.
12. **PR15 가변 상수 동결** (~150줄). `Mapping` + `MappingProxyType`, `COLOR_LIBRARIES` → `ColorLibrary`; `_generated.py`는
    생성기로만. 검증: 해시 테스트, `test_color_v5_build`.

하지 않을 것: `_compatibility_metrics.py` 이동·수정, `test_shipped_colors_hash.py` digest 재생성, 공개 `Color` 불변화,
ADR 0001 A2의 두 gamut 근사(`_generate`, `_cmaps.diverging_pair`) 로직 변경. 참고로 ADR 0001 A2가 가리키는
`_generate.gamut_max_chroma`는 현재 코드에 그 이름이 없다 — PR3 이동 시 ADR의 이름 참조를 실제 위치로 함께 맞출 것.

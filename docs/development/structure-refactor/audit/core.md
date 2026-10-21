---
orphan: true
---
# 구조 감사 — core (layout·annotation·units·font·style·formatting·io·scale·util·tokens·icon·helpers·templates·`__init__`)
기준: code-implement 스킬(SKILL·python·structure·modeling), limn(`src/limn/<기능>/tests/`, `tools/check_boundaries.py`,
ADR-0009/0010/0012). 대상 `0e88b810`(main), 읽기 전용.

## 1. 현재 구조 요약

| 모듈 | 줄 | `__all__` | 역할 |
|---|---|---|---|
| `annotation.py` | 1028 | O | label_axes, annotate_value/corner, label_hline, place_legend, wrap_axis_label(s), arrow_axis + bbox 장애물 계산 |
| `layout.py` | 921 | O | simple_layout, tight_crop, get_bounding_box, adopt_axis_label_font + 측정·해법·margin 파싱 |
| `units.py` | 723 | O | Length, cm/mm/pt/inch, figsize(_grid), aspect 토큰 |
| `font.py` | 692 | O | 번들 폰트 등록·메타데이터 보정·측정(FontMeasurement)·FONTS 레지스트리 |
| `__init__.py` | 591 | O | 재노출 + twinx 몽키패치 + `_REMOVED_NAMES` 레지스트리(~200줄) + `col1/col2` 정의 + import 시 폰트 등록 |
| `style.py` | 575 | O | Style(stack/use/context), preset/mplstyle 읽기, rcParams 소유권 상태 |
| `io.py` | 509 | O | save_formats, show, save_and_show |
| `formatting.py` | 501 | **X** | format_axis_*, recommend_tick_decimals, rotate/avoid_tick_* |
| `tokens.py` | 274 | O | `dm.tokens.*` 의미 토큰 |
| `util.py` | 186 | O | set_decimal, mix_colors, pseudo_alpha, make_offset + 5개 모듈 재노출 허브 |
| `icon.py` / `scale.py` | 161 / 151 | O | 아이콘 폰트 등록 / fs·fw·lw·dpi |
| `_helpers.py` | 144 | X | BBOX_ERRORS, get_renderer, iter_figure_level_extents, create_parent_path |
| `helpers/` 5 / `templates/` 2파일 | 487 / 372 | `__init__`만 | make_palette, validate_data, optimize_legend, check_figure_quality, suggest_chart_type / plot_diverging_bar |

합계 7,315줄. `asset/`: font 276파일 130MB, mplstyle 15(+presets.json), color 7, icon 4, prompt 41, tokens 1.

**영역 내부 import 그래프** (L = 함수 안 지연 import)
- `layout` → `_helpers`, `units`, `config`(L)
- `annotation` → `_helpers`, `scale`
- `io` → `_helpers`, `config`(L), `layout.adopt_axis_label_font`(L, io.py:261,444), `validate.validate_figure`(L, io.py:266)
- `util` → `annotation`, `io`, `layout`, `prompt`, `scale`, `_colors.Color` (util.py:14-18,47) — 재노출 허브
- `style` → `font`(L, style.py:354), `_colors._semantic`(L, **private**, style.py:385,530)
- `icon` → `style._did_you_mean`(L, **private**, icon.py:69)
- `helpers/labels` → `scale`, `_colors._loader`(L, **private**, labels.py:45)
- `templates/diverging_bar` → `import dartwork_mpl as dm`(diverging_bar.py:18) — 루트 패키지 전체

**영역 밖 → 영역** (private 굵게)
- `validate/_types.py:17`, `_orchestrator.py:9`, `_checks/overflow.py:7` → `_helpers`; `_checks/tick_decimal.py:8` → `formatting`
- `validate_fixes.py:13` → **`helpers.quality._MIN_RECOMMENDED_DPI`**; `diagnostics/_fonts.py:110` → **`font._FONT_DIR`**
- `_colors/_api.py:162` → **`style._style_lock`**; `_colors/_api.py:237` → `units`
- `ui/ui.py:50,978` → `util.save_formats`; `mcp/tools.py:383` → `util.mix_colors`; `mcp/resources.py:16` → `util.get_prompt`
  (모두 소유자가 아닌 호환 허브를 경유)
- `prompt.py:22` → `_helpers.create_parent_path`

**저장 형식 누출**: `presets.json`을 `style.py:305`·`lint.py:1297`·`mcp/tools.py:1315`가 각자 읽음; `theme-dark.mplstyle`을
`_colors/_catalog.py:50`이 읽음; `mcp/_assets.py:12`·`tools.py:56`·`resources.py:22,26`이 `asset/` 경로를 직접 앎.

**순환**(지연 import로 숨김): ① `style` ⇄ `_colors`(→`_colors._semantic` / ←`style._style_lock`) ② `dartwork_mpl` ⇄
`templates`(`__init__`→`templates`→`import dartwork_mpl`). 우회: `ui`→`util`→`io`→`validate`.

**`__init__.py`는 wiring만이 아니다**: twinx 몽키패치(`__init__.py:300-323`, 동작 정책), 제거 이름 레지스트리
(`:347-555`), `col1/col2` 값 정의(`:151-152`, units 소유 지식), `font.ensure_loaded()`(자원 생성 — wiring으로 허용).

## 2. 파일트리 결함
**능력(capability)과 흩어짐**
- **Sizing**: `units.py` + `__init__.col1/col2` + `scale.dpi` + `templates`의 raw `figsize: tuple` 인자. **Layout/측정**: `layout.py` + `_helpers.py`(측정 기계) + `validate/_checks/overflow`가 같은 extent 반복자 공유.
  `_measure_overflow`(layout.py:719)는 docstring 스스로 "tests/test_layout.py 전용"이라 명시한 테스트용 프로덕션 코드.
- **Typography**: `font.py`(등록·측정) + `icon.py`(같은 font_manager 등록 패턴, `_loaded/_lock` 복제) + `scale.fs/fw/lw` +
  `tokens.fs_*`(둘 다 rcParams 기준 상대값) + `layout.adopt_axis_label_font`(폰트 정책인데 layout에 있음, io가 호출).
- **Style preset**: `style.py` + presets.json을 3곳이 읽음 + KR 판정이 이름 부분문자열(`"lang-kr" in nm`, style.py:389).
- **Annotation/legend**: `annotation.place_legend` 와 `helpers/labels.optimize_legend`가 같은 결정(범례 배치)을 두 집에서.
  `util.make_offset`(텍스트 오프셋 변환)도 annotation 지식.
- **Ticks**: `formatting.py` + `util.set_decimal`(10-21 "keep decimal labels on dynamic ticks"는 tick 포맷 수정).
- **Export**: `io.py` — 저장 시 typography 확정+validate 조합 workflow(소유 적절). **색**: `util.mix_colors/pseudo_alpha`,
  `helpers/colors.make_palette`는 `_colors` 능력인데 밖에 있음.
- **품질 검사**: `helpers/quality.check_figure_quality`(문자열 리스트)와 `validate.validate_figure`(VisualWarning) 두 모델,
  DPI 임계값 200을 validate_fixes가 private import로 공유.

**god/잡동사니 파일**: `util.py`(4개 무관 함수 + 재노출, 모듈 docstring "do not warrant their own module"),
`_helpers.py`(소유자 다른 4항목), `helpers/`(5개 기능을 "helpers"로 묶음 — 각 항목이 다른 소유자를 가짐),
`annotation.py`(1028줄: 장애물 수집·충돌 점수·배치 규칙·matplotlib 적용이 한 파일), `__init__.py`.

**co-change 증거** (`git log --since=2025-10-01`, 영역 200커밋): `__init__`가 94회로 모든 변경에 끌려감
(layout 18, util 16, units 12, style 11, formatting 10). `annotation`↔`layout` 10, `io`↔`layout` 9, `font`↔`icon` 8,
`icon`↔`style` 8, `formatting`↔`layout` 7, `layout`↔`helpers/formatting`(현재 삭제) 8. → `__init__` 동반 변경은 재노출
목록 때문이며, font+icon은 한 능력, layout·annotation·io는 측정 기계(_helpers)를 매개로 함께 바뀜.

**테스트가 코드와 멂**: 전부 `tests/` 평면(135개 항목). `test_util.py`(432줄, 32 tests)는 util 허브를 그대로 거울
(fs/fw/lw는 `test_scale.py`와 중복). `test_helpers.py`는 `_helpers` 테스트. private 이름 직접 사용: `font._measure`(18회), `_family_codepoints`(3), `_add_fonts`,
`_EXPECTED_MIN_FONTS`, `_FONT_DIR`, `layout._measure_overflow`, `_adopt_axis_label_font_core`,
`_figure_artist_reservations`, `io._resolve_saved_path`, `style._dm_preset_values`, `helpers.quality._MIN_RECOMMENDED_DPI`,
`monkeypatch "dartwork_mpl.io.show"`(6). 경계 import-graph 검사는 **없다**(limn의 `tests/architecture/test_boundaries.py` 부재).

## 3. 타입 결함

| 항목 | 수 | 근거 |
|---|---|---|
| `Any` | 58 | annotation 16, font 9, io 8, helpers/data 7, layout 4, formatting 4, diverging_bar 3, _helpers 3, util 2, `__init__` 2 |
| `dict[str, Any]` 함수 경계 통과 | 9 | annotation.py:669,688,886,942; io.py:83-84,106,119,472 |
| `cast` (파싱 대용) | 4 | tokens.py:103,105,111,118 |
| `type: ignore` | 13 | layout:272, annotation:778-779, font:605,623, style:82,368, io:339,349,501, _helpers:67, `__init__`:322-323 |
| `raise` | 58 | units 18, annotation 10, style 7, io 5, formatting 5 … (대부분 호출자 전제조건 위반 = defect, 허용) |
| 가변 모듈 전역 | 7 | `style._dm_preset_values`/`_style_lock`(_colors와 공유), `font._loaded/_lock`, `icon._loaded/_lock`, `tokens._TOKENS`(import 시 로드), twinx 패치 |
| `__all__` 없음 | 8 | formatting.py, _helpers.py, helpers/{colors,data,labels,quality}.py, templates/diverging_bar.py, (validate_fixes 영역 밖) |

**stringly-typed kind/mode** (Literal도 아닌 `str`, 런타임 집합 검사):
annotation `side: str`(312, 592; `_annotation_side_spec` dict lookup :274), `loc: str`(438, 668, 697),
`direction: str`(875); `wrap_axis_label(axis: str)`(818); formatting은 같은 파일 안에서도 불일치 —
`format_axis_myriad(axis: str, locale: str)`(105-107) vs 나머지 `Literal["x","y","both"]`; `io.show(unit: str)`(308);
`save_formats(formats: tuple[str, ...])`(160, 문자열 검증); `style.stack`이 locale을 이름 부분문자열로 추론해 `apply_semantic("kr"|"default")` 문자열 모드 전달(style.py:389-391);
`FontFaceMeasurement.license: str`, `stretch: str`(font.py:58-77); `suggest_chart_type -> str`(열린 문자열 집합,
MCP가 다시 해석: mcp/tools.py:72); `check_figure_quality -> list[str]`(결과가 메시지 문자열).

**숨은 결과 채널**: `place_legend`가 반환 Legend에 `_dm_collision_free/_score` 속성을 붙임(annotation.py:778-779,
docstring이 안내 → 사실상 공개 계약). **파싱 부재**: `tokens._load_tokens`는 JSON 오류·누락 키를 삼키고 `_FALLBACK_TOKENS`로 조용히 대체
(tokens.py:115-128) — 같은 지식이 json과 코드 두 집. `layout._parse_margin`(:106)은 매 호출 문자열→float 변환하고
`"5%"`·Length·fraction 세 변이를 `float|None` 하나로 뭉갬. `simple_layout`의 `ml/mr/mt/mb: ...|None` + `margin`은
"개별 지정 vs 공통" 두 상태를 Optional로 표현.

**예상 결과를 예외로**: `helpers/data.validate_data`가 데이터 불일치를 `ValueError`·warnings로(data.py:62-107) —
"검증기"의 기대 결과. `font._entries_for_family` `KeyError`(font.py:387,521, 내부). 공개 함수의 예외 계약
(`Style.use` KeyError, `icon_font_path` FileNotFoundError)은 **공개 인터페이스라 이번 범위에서 바꾸지 않는다**.
**양호 사례**: `units.Length`(`__slots__`, 정규 저장, 파싱 생성자), font의 frozen dataclass 3종.

## 4. 제안 목표 구조
원칙: 공개 경로 = 모듈 이름이면 **같은 이름 패키지로 변환**(shim 불필요), 이름이 바뀌는 것만 재노출 shim.
`dm.style`은 `__init__`가 Style 인스턴스로 재바인딩하므로 `style/` 패키지화 후에도 동일.

```text
src/dartwork_mpl/
  __init__.py            # wiring만: 재노출, font.ensure_loaded(), style.install_twinx_patch()
  _compat.py             # _Deprecation/_DEPRECATED_NAMES/_REMOVED_NAMES (+ __getattr__ 본체); __init__가 재노출
  _figure_geometry.py    # platform: get_renderer, iter_figure_level_extents, BBOX_ERRORS (슬라이스 import 금지)
  _rc.py                 # platform: rcParams mutation lock (style·_colors 공용), did_you_mean
  units/   __all__ = Length, cm, mm, pt, inch, length, figsize, figsize_grid, list_aspect_tokens, parse_width, col1, col2
           _length.py _aspect.py _figsize.py tests/
  scale.py, tokens.py    # one-file 슬라이스 유지(작고 co-change 낮음). tokens는 파서 교체만
  font/    __all__ = 기존 font.__all__ + icon_font, icon_font_path, list_icon_fonts
           _registry.py(FONTS) _register.py(shell) _measure.py _icon.py tests/      # icon.py = shim
  style/   __all__ = Style, style, list_styles, load_style_dict, style_path, preset_names, preset_chain,
                     install_twinx_patch
           _presets.py(presets.json 유일 리더) _rcparams.py(소유권 상태) _locale.py tests/
  layout/  __all__ = simple_layout, tight_crop, get_bounding_box, adopt_axis_label_font
           _margins.py(Margin 파싱) _measure.py(shell) _solve.py(순수) _typography.py tests/
  annotation/ __all__ = 기존 8개 + optimize_legend, make_offset
           _obstacles.py(shell) _placement.py(순수 점수) _legend.py _axis_arrow.py tests/   # helpers/labels = shim
  formatting/ __all__ = format_axis_*, recommend_tick_decimals, rotate_tick_labels, avoid_tick_overlap, set_decimal
  io/      __all__ = save_formats, show, save_and_show   # export workflow
  templates/ (경로 유지, 루트 import 제거 → 슬라이스 surface import)
  util.py  # shim만: 각 소유자에서 재노출(호환 경로)
  helpers/ # shim 패키지: colors→_colors, data→validate, labels→annotation, quality→validate
```

**허용 슬라이스 의존(한 방향, 이유)**
| from → to | 업무 이유 | 아는 것 |
|---|---|---|
| layout → units | margin을 물리 길이로 받는다 | `Length` |
| annotation → scale | 라벨 기본 크기가 preset 상대값 | `fs` |
| style → font | preset 적용 전 번들 폰트 등록 필요 | `ensure_loaded` |
| style → _colors | preset 로케일이 semantic 색을 고른다 | `apply_semantic` (surface로 승격) |
| io → layout, io → validate | 저장이 typography 확정·검증을 수행(사용자 의도 = 저장) | `adopt_axis_label_font`, `validate_figure` |
| validate → formatting | tick-decimal 검사가 포맷터와 같은 권장값 | `recommend_tick_decimals` |
| templates → units/scale/layout | 템플릿은 공개 API의 소비자 | 각 surface |
| layout/annotation/validate → `_figure_geometry`, style/_colors → `_rc` | platform, 업무 없음 | — |
금지: `_colors`→style, icon→style, style 밖의 presets.json 직접 읽기(lint·mcp는 `style.preset_chain`).

**테스트 배치**: 현재 `testpaths = ["tests"]`(pyproject.toml), `tests/__init__.py` 존재, autouse rcParams 리셋은
`tests/conftest.py`. 슬라이스 동거에는 (1) `testpaths = ["tests", "src/dartwork_mpl"]` + `--import-mode=importlib`,
(2) autouse 픽스처를 루트 `conftest.py`로 승격(안 하면 동거 테스트가 격리를 잃음), (3) wheel/sdist에서
`**/tests/**` exclude(`packages = ["src/dartwork_mpl"]`라 그대로면 배포됨), (4) mypy `exclude`에 동거 테스트 추가.
`tests/robustness/`, `tests/visual/`, `test_api_stability`, `test_deprecation_*`, `test_docs_*`, `test_shipped_colors_hash`,
`test_antipattern_ratchet`, `test_preset_matrix`, `test_concurrency`는 여러 기능 계약이라 루트 유지(limn ADR-0012 동형).
기존 테스트 이동은 스킬상 **승인 필요** — 결정 기록(ADR) 선행.

**인터페이스 영향 플래그**: 모든 `dm.*` 이름 불변. 경로 보존 방식 — 패키지 변환: units, font, style, layout,
annotation, formatting, io, templates. shim(재노출): `util`, `icon`, `helpers.{colors,data,labels,quality}`,
`templates.diverging_bar`(automodule 대상, docs/api/templates.rst). `dm.style.presets_dict` 등 메서드 불변.
`place_legend`의 `_dm_collision_*` 속성은 docstring 공개 계약이라 유지(내부 결과 타입에서 채움).
Literal 축소(side/loc/axis)는 런타임 동일하나 **정적 타입 계약 변경** — 사용자가 `str` 변수로 넘기면 mypy 경고. 별도 승인.
깨지는 것: 테스트의 private import/`monkeypatch("dartwork_mpl.io.show")` 경로 — 해당 PR에서 함께 갱신.

## 5. 분할 PR 제안 (이동과 타입 변경 분리, 각 ≤~800줄)

| # | 범위 | 파일 | 위험 | 검증 |
|---|---|---|---|---|
| 0 | ADR: 슬라이스·테스트 동거 결정(≤200줄) | docs/adr | 낮음 | 승인 |
| 1 | 경계 검사(AST import graph, 현 위반은 ratchet 허용목록) | tests/architecture/test_boundaries.py | 낮음 | 주입 위반 5종 fail, 슬라이스 내부 pass |
| 2 | 동거 테스트 인프라: testpaths, importlib 모드, 루트 conftest, wheel/sdist/mypy exclude | pyproject.toml, conftest.py | 중(수집 변화) | `pytest --collect-only` 수 동일, `uv build` 후 wheel에 tests 없음 |
| 3 | `_helpers` 해체 → `_figure_geometry`(이동) + create_parent_path 인라인(io, prompt) | _helpers, layout, annotation, validate/*, io, prompt, test_helpers | 낮음 | 전체 pytest, visual |
| 4 | `_rc.py`(lock, did_you_mean): style⇄_colors, icon→style 순환 제거 | style, _colors/_api, icon | 중(스레드 테스트) | test_concurrency, test_style |
| 5 | style surface `preset_names/preset_chain`; lint·mcp·_colors가 presets.json 직접 읽기 중단 | style, lint.py:1297, mcp/tools.py:1315, mcp/resources | 중 | test_lint, test_mcp, test_preset_matrix |
| 6 | font 패키지화 + icon 흡수(icon.py shim) + `get_font_dir`로 diagnostics 누출 제거; test_font*/test_icon 이동 | font, icon, diagnostics/_fonts | 중 | test_font_invariants, glyph, docs fonts generator parity |
| 7 | units 패키지화 + col1/col2 이동; test_units/test_figsize_grid 이동 | units, `__init__` | 낮음 | test_api_stability |
| 8 | layout 패키지화(이동만); `_measure_overflow` → 테스트 지원 코드; test_layout/orphan_tick/figure_level_extents 이동 | layout | 중 | visual 픽셀, robustness |
| 9 | annotation 패키지화 + optimize_legend, make_offset 흡수(helpers/labels shim) | annotation, helpers/labels, util | 중 | test_annotation, test_helpers_labels |
| 10 | formatting 패키지화 + set_decimal 흡수 + `__all__` | formatting, util | 낮음 | test_formatting*, test_util 분할 |
| 11 | io 패키지화; ui/mcp가 util 대신 소유자 import | io, ui/ui.py, mcp/tools.py, mcp/resources.py | 중(mcp 활발) | test_io, test_ui_*, test_mcp |
| 12 | util → shim 전용; mix_colors/pseudo_alpha → `_colors`(색 감사와 조율) | util, _colors | 중 | test_util, color hash |
| 13 | helpers → shim; make_palette→_colors, validate_data·check_figure_quality·suggest_chart_type→validate; DPI 상수 surface화 | helpers/*, validate, validate_fixes | 중 | test_helpers_*, test_validate_fixes |
| 14 | templates 루트 import 제거; `__init__` wiring화(`_compat.py`, twinx 패치 → style) | templates, `__init__`, _compat | 중 | test_init_patch, test_api_stability, test_deprecation_* |
| T1 | tokens 파서: cast 제거, 손상 JSON은 명시 오류 또는 이름 붙은 fallback, fallback 이중 정의 제거 | tokens | 낮음 | test_tokens, test_mplstyle_tokens |
| T2 | annotation 내부 Literal(side/loc/direction) + `LegendPlacement` 결과 타입(공개 속성 유지) | annotation | 중(정적 계약) | test_annotation, figure_legend_hardening |
| T3 | style `Locale` 파싱(이름 부분문자열 → 타입), `apply_semantic` Literal | style, _colors/_semantic | 중 | test_color_v5_semantic, test_style |
| T4 | layout `Margin` 값 타입 + `_solve` 순수 코어 분리 | layout | 중 | visual 픽셀 동일 |
| T5 | io `SaveFormat` 파싱, `show(unit)` Literal; formatting myriad Literal 통일 | io, formatting | 낮음 | test_io, test_formatting_myriad |

**충돌 가능성** (`git log --since=2026-08-01`): style.py 2커밋(최근 10-21 "preserve caller edits"), io.py 2(#514, 10-21),
util.py 2(10-21 set_decimal), formatting 1(#479), layout 1(#473), mcp/tools.py는 #517까지 매우 활발 — PR 5·11은 mcp 작업과
조율. annotation·units·icon·tokens·templates·_helpers는 8월 이후 무변경 → 3·7·9 먼저. 이동과 내용 변경은 커밋 분리.

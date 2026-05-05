# Public API Audit (live)

이 문서는 [#141](https://github.com/dartworklabs/dartwork-mpl/issues/141)에서
시작된 public API 정리 작업의 살아있는 기록이다. 운영 룰·컬럼 정의·분류
원칙은 [`docs/superpowers/specs/2026-05-05-prune-low-value-utils-design.md`](../superpowers/specs/2026-05-05-prune-low-value-utils-design.md)
참조.

## How to read

| 컬럼 | 의미 |
|---|---|
| `name` | `dm.<name>` 또는 `dm.<module>.<name>` 노출 이름 |
| `module` | `src/dartwork_mpl/<module>` |
| `kind` | `func` / `class` |
| `loc` | 함수 본문 LOC (def·docstring·빈 줄 제외) |
| `mpl_canonical_1to1` | matplotlib에 1:1 매핑되는 canonical 호출이 존재 (`Y` / `N`). 빈 셀 = 미평가 |
| `repo_callsites` | 리포 내 `docs/`·`tests/`의 `.py`·`.md`에서 발견된 호출처 수 (제거 시 함께 인라인할 사이트). 상한값으로 해석. |
| `inline_difficulty` | AI 에이전트 인라인 난이도 (`1` = matplotlib 1줄 / `2` = 2~3줄 + default kwargs / `3` = 데이터 변환·복잡 분기). 빈 셀 = 미평가 |
| `classification` | spec §3 3-bucket: `keep` / `borderline` / `remove` |
| `notes` | borderline 사유, 마이그레이션 한 줄, 관련 이슈 |
| `status` | `pending` (분류 전) / `audited` (분류 완료) / `removed` (실제 제거 완료) |

## How to update

1. 자동 컬럼(`name`, `module`, `kind`, `loc`, `repo_callsites`)은
   `python scripts/api_audit.py`로 재생성한다.
2. 수동 컬럼은 spec §2(decision principles)·§3(classification) 적용으로 채운다.
3. 후속 라운드 PR이 `remove` 항목을 처리하면 `status`를 `removed`로 갱신한다.

## Audit table

<!-- 모듈·이름 사전순 정렬. 자동 컬럼은 scripts/api_audit.py 출력. 빈 행으로 그룹 구분 금지(재생성 시 깨짐). -->

| name | module | kind | loc | mpl_canonical_1to1 | repo_callsites | inline_difficulty | classification | notes | status |
|---|---|---|---|---|---|---|---|---|---|
| `arrow_axis` | `dartwork_mpl.annotation` | func | 103 | N | 28 | 3 | keep | renderer-aware bidirectional Low-High arrow axis; text extent measurement + annotate calls — annotation 본질 | audited |
| `label_axes` | `dartwork_mpl.annotation` | func | 28 | N | 58 | 3 | keep | auto x-position (ylabel 존재 여부 분기) + 다중 axes 순회 — 58 callsites; 다중 axes 자동 라벨링 | audited |
| `ensure_loaded` | `dartwork_mpl.cmap` | func | 13 |  | 47 |  |  |  | pending |
| `Color` | `dartwork_mpl.color._color` | class | 0 | N | 174 | 3 | keep | OKLCH-native color object; stores internally in OKLab, exposes oklab/oklch/rgb views — dartwork-mpl 색 시스템 핵심 | audited |
| `cspace` | `dartwork_mpl.color._color` | func | 105 | N | 92 | 3 | keep | OKLCH 인터폴레이션 + 최단 hue 경로 처리; oklch/oklab/rgb 3-space 지원 — no matplotlib equivalent | audited |
| `hex` | `dartwork_mpl.color._color` | func | 1 | N | 67 | 2 | keep | hex 문자열 → Color 진입점; 1-line body지만 OKLCH 타입 시스템 시맨틱 entry-point | audited |
| `named` | `dartwork_mpl.color._color` | func | 10 | N | 72 | 2 | keep | named color → Color; dm. prefix deprecation 경고 포함 — 의미 있는 진입점 | audited |
| `oklab` | `dartwork_mpl.color._color` | func | 1 | N | 76 | 2 | keep | OKLab → Color 진입점; 1-line body지만 OKLCH 타입 시스템 시맨틱 entry-point | audited |
| `oklch` | `dartwork_mpl.color._color` | func | 1 | N | 113 | 2 | keep | OKLCH → Color 진입점; 1-line body지만 OKLCH 타입 시스템 시맨틱 entry-point | audited |
| `rgb` | `dartwork_mpl.color._color` | func | 1 | N | 62 | 2 | keep | RGB → Color 진입점; auto 0-1/0-255 range detection — OKLCH 타입 시스템 시맨틱 entry-point | audited |
| `ensure_loaded` | `dartwork_mpl.color._loader` | func | 5 |  | 47 |  |  |  | pending |
| `OklabView` | `dartwork_mpl.color._views` | class | 0 |  | 4 |  |  |  | pending |
| `OklchView` | `dartwork_mpl.color._views` | class | 0 |  | 4 |  |  |  | pending |
| `RgbView` | `dartwork_mpl.color._views` | class | 0 |  | 4 |  |  |  | pending |
| `classify_colormap` | `dartwork_mpl.diagnostics` | func | 120 | N | 21 | 3 | keep | HSV 분석 기반 다분기 분류 (Categorical/Single-Hue/Multi-Hue/Diverging/Cyclical) — non-trivial classifier | audited |
| `plot_colormaps` | `dartwork_mpl.diagnostics` | func | 48 | N | 26 | 3 | keep | colormap 시각화 + classify_colormap 기반 그룹화 — diagnostic asset visualizer | audited |
| `plot_colors` | `dartwork_mpl.diagnostics` | func | 32 | N | 35 | 3 | keep | 팔레트 색상 배열 시각화 — diagnostic asset visualizer | audited |
| `plot_fonts` | `dartwork_mpl.diagnostics` | func | 203 | N | 29 | 3 | keep | 폰트 specimen 패널 생성 (203 LOC) — diagnostic asset visualizer | audited |
| `list_colormaps` | `dartwork_mpl.explore` | func | 7 | N | 5 | 2 | keep | ensure_loaded + dc.* prefix filter + _r 제거 — resource discovery; no matplotlib equivalent | audited |
| `list_palettes` | `dartwork_mpl.explore` | func | 11 | N | 6 | 2 | keep | regex 기반 named-color map 순회 → prefix.name 집합 추출 — resource discovery | audited |
| `show_palette` | `dartwork_mpl.explore` | func | 52 | N | 6 | 3 | keep | 색상 swatch 렌더러 (52 LOC) + contrast 휴리스틱 + 라벨 배치 — palette visualizer | audited |
| `figure` | `dartwork_mpl.figure` | func | 62 | N | 401 | 3 | keep | 물리 단위 width API + aspect 토큰 + legacy figsize=/dpi= 명시 거부 — 핵심 abstraction | audited |
| `subplots` | `dartwork_mpl.figure` | func | 82 | N | 645 | 3 | keep | 동상 — width/aspect → figsize 변환, gridspec/ratios 통합, legacy 인자 거부 | audited |
| `ensure_loaded` | `dartwork_mpl.font` | func | 11 | N | 47 | 1 | keep | thread-safe double-checked locking + _add_fonts() 등록 — 폰트 시스템 bootstrap; 47 내부 callsites | audited |
| `format_axis_billions` | `dartwork_mpl.formatting` | func | 25 | N | 18 | 3 | keep | zero-tick special case + `x/1e9` scaling in formatter body | audited |
| `format_axis_currency` | `dartwork_mpl.formatting` | func | 34 | N | 11 | 3 | keep | sign-outside-symbol placement, zero-rounding sign suppression, prefix/suffix position logic | audited |
| `format_axis_millions` | `dartwork_mpl.formatting` | func | 25 | N | 20 | 3 | keep | zero-tick special case + `x/1e6` scaling in formatter body | audited |
| `format_axis_percent` | `dartwork_mpl.formatting` | func | 6 | N | 4 | 2 | borderline | wraps `ticker.PercentFormatter` directly — no custom formatter logic; x/y/both dispatch adds minor value — 토론 | audited |
| `format_axis_si` | `dartwork_mpl.formatting` | func | 37 | N | 26 | 3 | keep | multi-level prefix selection (k/M/G/T), negative sign handling, zero-tick special case | audited |
| `format_axis_thousands` | `dartwork_mpl.formatting` | func | 6 | N | 2 | 2 | borderline | single FuncFormatter lambda with configurable sep — minimal transformation, no scaling logic — 토론 | audited |
| `rotate_tick_labels` | `dartwork_mpl.formatting` | func | 26 | N | 25 | 2 | borderline | auto-ha inference (rotation sign → left/center/right) + FixedLocator-safe iteration — more than a 1-line setp call — 토론 | audited |
| `auto_select_colors` | `dartwork_mpl.helpers.colors` | func | 63 | N | 33 | 3 | keep | categorical/sequential/diverging 3-way 분기 + highlight 인덱스 처리 — 카테고리 → 팔레트 매핑 | audited |
| `validate_data` | `dartwork_mpl.helpers.data` | func | 43 | N | 26 | 2 | keep | NaN 제거·길이 검증·min_points 체크 — 데이터 shape 검증 | audited |
| `create_figure_with_style` | `dartwork_mpl.helpers.io` | func | 9 | N | 22 | 2 | borderline | `dm.style.use(style)` + `plt.figure(figsize=..., dpi=...)` 2줄 shortcut; `figsize=` 안티패턴 직접 호출 — strong remove candidate | audited |
| `save_figure` | `dartwork_mpl.helpers.io` | func | 11 | N | 24 | 2 | borderline | 내부적으로 `dm.save_formats` 1-line passthrough + mkdir + verbose print — double-wrapper, strong remove candidate | audited |
| `add_value_labels` | `dartwork_mpl.helpers.labels` | func | 18 | N | 17 | 3 | borderline | 데이터 순회 + y-range 기반 offset 계산 + ax.text 배치 — bar/line value annotation | audited |
| `format_axis_labels` | `dartwork_mpl.helpers.labels` | func | 12 | N | 22 | 2 | borderline | unit 접미사 붙이기 + fs() fontsize 적용 — composition (set_xlabel/ylabel/title 3줄 묶음) — 토론 | audited |
| `optimize_legend` | `dartwork_mpl.helpers.labels` | func | 31 | N | 15 | 3 | borderline | ncol 휴리스틱 (n_items 기반) + inside/outside 배치 분기 — legend 자동 위치 composition | audited |
| `check_figure_quality` | `dartwork_mpl.helpers.quality` | func | 39 | N | 18 | 3 | keep | DPI·style·축라벨·틱·여백 다중 검사 루프 — publication-quality 검증 | audited |
| `suggest_chart_type` | `dartwork_mpl.helpers.quality` | func | 31 | N | 24 | 3 | keep | x_type/y_type/n_points/n_series 기반 다분기 결정 트리 — 자연어 인터페이스 | audited |
| `ensure_loaded` | `dartwork_mpl.icon` | func | 4 | N | 47 | 1 | keep | icon font 등록 bootstrap — font 시스템과 대칭; 47 내부 callsites | audited |
| `icon_font` | `dartwork_mpl.icon` | func | 2 | N | 13 | 2 | keep | icon_font_path → FontProperties(fname=) 변환; icon font 시스템 핵심 진입점 | audited |
| `icon_font_path` | `dartwork_mpl.icon` | func | 12 | N | 7 | 2 | keep | registry 룩업 + FileNotFoundError — path helper with validation | audited |
| `list_icon_fonts` | `dartwork_mpl.icon` | func | 1 | N | 9 | 1 | keep | sorted(_REGISTRY.keys()) — 1줄이지만 icon font discovery API | audited |
| `install_llm_txt` | `dartwork_mpl.install` | func | 42 | N | 24 | 3 | keep | CLI 도구 — SSOT bundle 합성 + .claude/commands/.cursor 양방향 설치 로직 | audited |
| `uninstall_llm_txt` | `dartwork_mpl.install` | func | 19 | N | 7 | 3 | keep | CLI 도구 — 파일 제거 + 오류 처리 | audited |
| `save_and_show` | `dartwork_mpl.io` | func | 14 | N | 34 | 3 | keep | tmp 파일 생성·정리 + 경로 분기 + custom show() 호출 — 2줄 이상 실질 로직 | audited |
| `save_formats` | `dartwork_mpl.io` | func | 8 | N | 77 | 2 | keep | `savefig` 다중 포맷 확장 + bbox/validate kwargs 모호성 해소 | audited |
| `show` | `dartwork_mpl.io` | func | 48 | N | 238 | 3 | keep | SVG DOM 파싱 + aspect-ratio 보존 width/height 치환 + IPython display — plt.show() 아님 | audited |
| `auto_layout` | `dartwork_mpl.layout` | func | 322 | N | 293 | 3 | keep | dartwork-mpl 고유 content-aware 측정 | audited |
| `get_bounding_box` | `dartwork_mpl.layout` | func | 15 | N | 6 | 2 | keep | 측정 helper | audited |
| `set_xmargin` | `dartwork_mpl.layout` | func | 7 | N | 8 | 2 | borderline | x-margin + xlim 동시 조정 — 토론 | audited |
| `set_ymargin` | `dartwork_mpl.layout` | func | 7 | N | 7 | 2 | borderline | y-margin + ylim 동시 조정 — 토론 | audited |
| `simple_layout` | `dartwork_mpl.layout` | func | 82 | N | 275 | 2 | keep | tight_layout/constrained_layout 모호성 해소 | audited |
| `tight_crop` | `dartwork_mpl.layout` | func | 128 | N | 3 | 2 | keep | artist-bbox 측정 후 fig 리사이즈 | audited |
| `Issue` | `dartwork_mpl.lint` | class | 0 |  | 19 |  |  |  | pending |
| `Rule` | `dartwork_mpl.lint` | class | 0 |  | 17 |  |  |  | pending |
| `format_report` | `dartwork_mpl.lint` | func | 19 |  | 17 |  |  |  | pending |
| `lint` | `dartwork_mpl.lint` | func | 16 |  | 191 |  |  |  | pending |
| `load_rules` | `dartwork_mpl.lint` | func | 28 |  | 20 |  |  |  | pending |
| `migrate_legacy_code` | `dartwork_mpl.lint` | func | 20 |  | 34 |  |  |  | pending |
| `copy_prompt` | `dartwork_mpl.prompt` | func | 10 |  | 9 |  |  |  | pending |
| `find_template` | `dartwork_mpl.prompt` | func | 27 |  | 22 |  |  |  | pending |
| `get_prompt` | `dartwork_mpl.prompt` | func | 2 |  | 32 |  |  |  | pending |
| `list_prompts` | `dartwork_mpl.prompt` | func | 15 |  | 16 |  |  |  | pending |
| `prompt_path` | `dartwork_mpl.prompt` | func | 4 |  | 9 |  |  |  | pending |
| `fs` | `dartwork_mpl.scale` | func | 1 | N | 1256 | 1 | keep | relative font-size token (`rcParams['font.size'] + n`) — no matplotlib equivalent | audited |
| `fw` | `dartwork_mpl.scale` | func | 4 | N | 83 | 2 | keep | string weight name → numeric conversion via `_WEIGHT_MAP` + offset — no matplotlib equivalent | audited |
| `lw` | `dartwork_mpl.scale` | func | 1 | N | 417 | 1 | keep | relative linewidth token (`rcParams['lines.linewidth'] + n`) — no matplotlib equivalent | audited |
| `add_frame` | `dartwork_mpl.spines` | func | 4 | N | 10 | 2 | borderline | composition (visible+color+linewidth on all spines) — 토론 | audited |
| `add_grid` | `dartwork_mpl.spines` | func | 11 | N | 15 | 2 | borderline | dm.* default kwargs(color, alpha 등) 가치 — 토론 | audited |
| `hide_all_spines` | `dartwork_mpl.spines` | func | 2 | Y | 28 | 1 | remove | `for s in ax.spines.values(): s.set_visible(False)` | audited |
| `hide_spines` | `dartwork_mpl.spines` | func | 6 | Y | 10 | 1 | remove | `for s in ['top','right']: ax.spines[s].set_visible(False)` | audited |
| `minimal_axes` | `dartwork_mpl.spines` | func | 7 | N | 27 | 3 | borderline | 4 함수 묶음 composition — 토론 | audited |
| `remove_grid` | `dartwork_mpl.spines` | func | 1 | Y | 3 | 1 | remove | `ax.grid(False)` | audited |
| `show_only_spines` | `dartwork_mpl.spines` | func | 4 | Y | 4 | 2 | remove | `for s in ['top','right','bottom','left']: ax.spines[s].set_visible(s in which)` | audited |
| `style_spines` | `dartwork_mpl.spines` | func | 14 | N | 9 | 2 | borderline | composition (color+linewidth+visible filter) — 토론 | audited |
| `Style` | `dartwork_mpl.style` | class | 0 | N | 61 | 3 | keep | presets 로딩 + thread-safe rcParams 갱신 + use/stack/context/context_manager — 'One Right Way' 스타일 시스템 핵심 | audited |
| `list_styles` | `dartwork_mpl.style` | func | 2 | N | 11 | 2 | keep | asset/mplstyle glob → stem 목록 — style discovery | audited |
| `load_style_dict` | `dartwork_mpl.style` | func | 26 | N | 10 | 2 | keep | mplstyle 커스텀 파서 (inline comment 제거 + colon-split + float 변환) — no matplotlib equivalent | audited |
| `style_path` | `dartwork_mpl.style` | func | 5 | N | 7 | 1 | keep | asset 경로 해석 + ValueError — style 파일 path helper | audited |
| `get_source_code` | `dartwork_mpl.templates.diverging_bar` | func | 13 |  | 0 |  |  |  | pending |
| `plot_diverging_bar` | `dartwork_mpl.templates.diverging_bar` | func | 206 |  | 28 |  |  |  | pending |
| `Inches` | `dartwork_mpl.units` | class | 0 | N | 27 | 2 | keep | 단위 태그 클래스 — `__array_ufunc__=None` + 산술 연산자 오버라이드로 numpy 경계에서 단위 손실 방지 | audited |
| `cm` | `dartwork_mpl.units` | func | 1 | N | 200 | 1 | keep | 물리 단위 토큰 — cm → Inches 변환; parse_width 진입점 | audited |
| `inch` | `dartwork_mpl.units` | func | 1 | N | 35 | 1 | keep | 물리 단위 토큰 — Inches 태그 부여 identity | audited |
| `mm` | `dartwork_mpl.units` | func | 1 | N | 43 | 1 | keep | 물리 단위 토큰 — mm → Inches 변환 | audited |
| `parse_aspect` | `dartwork_mpl.units` | func | 27 | N | 28 | 2 | keep | 토큰 룩업 + bool 거부 + 수치 검증 + 오타 제안 — 핵심 내부 파서 | audited |
| `parse_width` | `dartwork_mpl.units` | func | 44 | N | 37 | 2 | keep | Inches pass-through + bool 거부 + 단위 파싱 + 검증 + 오타 제안 — 핵심 내부 파서 | audited |
| `make_offset` | `dartwork_mpl.util` | func | 2 | N | 21 | 2 | borderline | ScaledTranslation 2-line wrapper (x/72, y/72 + fig.dpi_scale_trans) — Task 11에서 keep/remove 결정 | audited |
| `mix_colors` | `dartwork_mpl.util` | func | 8 | N | 28 | 2 | borderline | 단순 RGB linspace (mcolors.to_rgb 경유) — OKLCH 인터폴레이션 없음; 토론 | audited |
| `pseudo_alpha` | `dartwork_mpl.util` | func | 1 | N | 34 | 2 | borderline | mix_colors 1-line delegate; 백색 블렌딩 의미 있으나 구현이 RGB — 토론 | audited |
| `set_decimal` | `dartwork_mpl.util` | func | 9 | N | 40 | 2 | borderline | get_ticks + set_ticks + set_ticklabels 3-step pattern per axis; no rcParams/locale logic — 토론 | audited |
| `Severity` | `dartwork_mpl.validate` | class | 0 |  | 26 |  |  |  | pending |
| `VisualWarning` | `dartwork_mpl.validate` | class | 0 |  | 24 |  |  |  | pending |
| `validate_figure` | `dartwork_mpl.validate` | func | 39 | N | 103 | 3 | keep | 8개 check lambda 등록·선택 실행 + canvas.draw() 렌더 → VisualWarning 수집 — 종합 visual 검증 엔진 | audited |
| `check_agent_requirements` | `dartwork_mpl.validate_fixes` | func | 41 |  | 1 |  |  |  | pending |
| `generate_validation_report` | `dartwork_mpl.validate_fixes` | func | 47 |  | 1 |  |  |  | pending |
| `get_fix_suggestions` | `dartwork_mpl.validate_fixes` | func | 90 |  | 20 |  |  |  | pending |
| `validate_with_fixes` | `dartwork_mpl.validate_fixes` | func | 48 |  | 16 |  |  |  | pending |

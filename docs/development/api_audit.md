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
| `ensure_loaded` | `dartwork_mpl.cmap` | func | 13 | N | 47 | 1 | keep | thread-safe double-checked locking + _load_colormaps() 등록 — colormap 시스템 bootstrap; 47 내부 callsites | audited |
| `Color` | `dartwork_mpl.color._color` | class | 0 | N | 174 | 3 | keep | OKLCH-native color object; stores internally in OKLab, exposes oklab/oklch/rgb views — dartwork-mpl 색 시스템 핵심 | audited |
| `cspace` | `dartwork_mpl.color._color` | func | 105 | N | 92 | 3 | keep | OKLCH 인터폴레이션 + 최단 hue 경로 처리; oklch/oklab/rgb 3-space 지원 — no matplotlib equivalent | audited |
| `hex` | `dartwork_mpl.color._color` | func | 1 | N | 67 | 2 | keep | hex 문자열 → Color 진입점; 1-line body지만 OKLCH 타입 시스템 시맨틱 entry-point | audited |
| `named` | `dartwork_mpl.color._color` | func | 10 | N | 72 | 2 | keep | named color → Color; dm. prefix deprecation 경고 포함 — 의미 있는 진입점 | audited |
| `oklab` | `dartwork_mpl.color._color` | func | 1 | N | 76 | 2 | keep | OKLab → Color 진입점; 1-line body지만 OKLCH 타입 시스템 시맨틱 entry-point | audited |
| `oklch` | `dartwork_mpl.color._color` | func | 1 | N | 113 | 2 | keep | OKLCH → Color 진입점; 1-line body지만 OKLCH 타입 시스템 시맨틱 entry-point | audited |
| `rgb` | `dartwork_mpl.color._color` | func | 1 | N | 62 | 2 | keep | RGB → Color 진입점; auto 0-1/0-255 range detection — OKLCH 타입 시스템 시맨틱 entry-point | audited |
| `ensure_loaded` | `dartwork_mpl.color._loader` | func | 5 | N | 47 | 1 | keep | 색 정의 idempotent 로딩 — _loaded 플래그 guard; 47 내부 callsites | audited |
| `OklabView` | `dartwork_mpl.color._views` | class | 0 | N | 4 | 2 | keep | OKLab 좌표 뷰 — sequence 프로토콜 + __iter__/__len__/__repr__; OKLCH 색 시스템 구성 요소 | audited |
| `OklchView` | `dartwork_mpl.color._views` | class | 0 | N | 4 | 2 | keep | OKLCH 좌표 뷰 — 동상; OKLCH 색 시스템 구성 요소 | audited |
| `RgbView` | `dartwork_mpl.color._views` | class | 0 | N | 4 | 2 | keep | RGB 좌표 뷰 — 동상; OKLCH 색 시스템 구성 요소 | audited |
| `classify_cmap` | `dartwork_mpl.diagnostics` | func | 120 | N | 21 | 3 | keep | HSV 분석 기반 다분기 분류 (Categorical/Single-Hue/Multi-Hue/Diverging/Cyclical) — non-trivial classifier | audited |
| `render_cmap_catalog` | `dartwork_mpl.diagnostics` | func | 48 | N | 26 | 3 | keep | colormap 시각화 + classify_cmap 기반 그룹화 — diagnostic asset visualizer | audited |
| `render_color_catalog` | `dartwork_mpl.diagnostics` | func | 32 | N | 35 | 3 | keep | 팔레트 색상 배열 시각화 — diagnostic asset visualizer | audited |
| `plot_fonts` | `dartwork_mpl.diagnostics` | func | 203 | N | 29 | 3 | keep | 폰트 specimen 패널 생성 (203 LOC) — diagnostic asset visualizer | audited |
| `list_colors` | `dartwork_mpl.explore` | func | 7 | N | 5 | 2 | keep | ensure_loaded + dc.* prefix filter + _r 제거 — resource discovery; no matplotlib equivalent | audited |
| `list_colors` | `dartwork_mpl.explore` | func | 11 | N | 6 | 2 | keep | regex 기반 named-color map 순회 → prefix.name 집합 추출 — resource discovery | audited |
| `show_colors` | `dartwork_mpl.explore` | func | 52 | N | 6 | 3 | keep | 색상 swatch 렌더러 (52 LOC) + contrast 휴리스틱 + 라벨 배치 — palette visualizer | audited |
| `figure` | `dartwork_mpl.figure` | func | 62 | N | 403 | 3 | keep | 물리 단위 width API + aspect 토큰 + legacy figsize=/dpi= 명시 거부 — 핵심 abstraction | audited |
| `subplots` | `dartwork_mpl.figure` | func | 82 | N | 657 | 3 | keep | 동상 — width/aspect → figsize 변환, gridspec/ratios 통합, legacy 인자 거부 | audited |
| `ensure_loaded` | `dartwork_mpl.font` | func | 11 | N | 47 | 1 | keep | thread-safe double-checked locking + _add_fonts() 등록 — 폰트 시스템 bootstrap; 47 내부 callsites | audited |
| `format_axis_billions` | `dartwork_mpl.formatting` | func | 25 | N | 18 | 3 | keep | zero-tick special case + `x/1e9` scaling in formatter body | audited |
| `format_axis_currency` | `dartwork_mpl.formatting` | func | 34 | N | 11 | 3 | keep | sign-outside-symbol placement, zero-rounding sign suppression, prefix/suffix position logic | audited |
| `format_axis_millions` | `dartwork_mpl.formatting` | func | 25 | N | 23 | 3 | keep | zero-tick special case + `x/1e6` scaling in formatter body | audited |
| `format_axis_percent` | `dartwork_mpl.formatting` | func | 6 | N | 7 | 2 | borderline | wraps `ticker.PercentFormatter` directly — no custom formatter logic; x/y/both dispatch adds minor value — 토론 | removed |
| `format_axis_si` | `dartwork_mpl.formatting` | func | 37 | N | 29 | 3 | keep | multi-level prefix selection (k/M/G/T), negative sign handling, zero-tick special case | audited |
| `format_axis_thousands` | `dartwork_mpl.formatting` | func | 6 | N | 2 | 2 | borderline | single FuncFormatter lambda with configurable sep — minimal transformation, no scaling logic — 토론 | removed |
| `rotate_tick_labels` | `dartwork_mpl.formatting` | func | 26 | N | 25 | 2 | borderline | auto-ha inference (rotation sign → left/center/right) + FixedLocator-safe iteration — more than a 1-line setp call — 토론 | audited |
| `auto_select_colors` | `dartwork_mpl.helpers.colors` | func | 63 | N | 33 | 3 | keep | categorical/sequential/diverging 3-way 분기 + highlight 인덱스 처리 — 카테고리 → 팔레트 매핑; renamed to `make_palette` in Round 5 (#156) with arg cleanup (n_series→n, color_type→kind, highlight_index→highlight) | renamed |
| `validate_data` | `dartwork_mpl.helpers.data` | func | 43 | N | 26 | 2 | keep | NaN 제거·길이 검증·min_points 체크 — 데이터 shape 검증 | audited |
| `create_figure_with_style` | `dartwork_mpl.helpers.io` | func | 9 | N | 22 | 2 | borderline | `dm.style.use(style)` + `plt.figure(figsize=..., dpi=...)` 2줄 shortcut; `figsize=` 안티패턴 직접 호출 — strong remove candidate | removed |
| `save_figure` | `dartwork_mpl.helpers.io` | func | 11 | N | 24 | 2 | borderline | 내부적으로 `dm.save_formats` 1-line passthrough + mkdir + verbose print — double-wrapper, strong remove candidate | removed |
| `add_value_labels` | `dartwork_mpl.helpers.labels` | func | 18 | N | 17 | 3 | borderline | 데이터 순회 + y-range 기반 offset 계산 + ax.text 배치 — bar/line value annotation | removed |
| `format_axis_labels` | `dartwork_mpl.helpers.labels` | func | 12 | N | 22 | 2 | borderline | unit 접미사 붙이기 + fs() fontsize 적용 — composition (set_xlabel/ylabel/title 3줄 묶음) — 토론 | removed |
| `optimize_legend` | `dartwork_mpl.helpers.labels` | func | 31 | N | 15 | 3 | borderline | ncol 휴리스틱 (n_items 기반) + inside/outside 배치 분기 — legend 자동 위치 composition | audited |
| `check_figure_quality` | `dartwork_mpl.helpers.quality` | func | 39 | N | 18 | 3 | keep | DPI·style·축라벨·틱·여백 다중 검사 루프 — publication-quality 검증 | audited |
| `suggest_chart_type` | `dartwork_mpl.helpers.quality` | func | 31 | N | 24 | 3 | keep | x_type/y_type/n_points/n_series 기반 다분기 결정 트리 — 자연어 인터페이스 | audited |
| `ensure_loaded` | `dartwork_mpl.icon` | func | 4 | N | 47 | 1 | keep | icon font 등록 bootstrap — font 시스템과 대칭; 47 내부 callsites | audited |
| `icon_font` | `dartwork_mpl.icon` | func | 2 | N | 13 | 2 | keep | icon_font_path → FontProperties(fname=) 변환; icon font 시스템 핵심 진입점 | audited |
| `icon_font_path` | `dartwork_mpl.icon` | func | 12 | N | 7 | 2 | keep | registry 룩업 + FileNotFoundError — path helper with validation | audited |
| `list_icon_fonts` | `dartwork_mpl.icon` | func | 1 | N | 9 | 1 | keep | sorted(_REGISTRY.keys()) — 1줄이지만 icon font discovery API | audited |
| `install_llm_txt` | `dartwork_mpl.install` | func | 42 | N | 24 | 3 | remove | removed in #170 — superseded by MCP + repo-root AGENTS.md / llms-full.txt (use `dm.agent_doc_path`) | removed |
| `uninstall_llm_txt` | `dartwork_mpl.install` | func | 19 | N | 7 | 3 | remove | removed in #170 — superseded by MCP + repo-root AGENTS.md / llms-full.txt | removed |
| `save_and_show` | `dartwork_mpl.io` | func | 14 | N | 34 | 3 | keep | tmp 파일 생성·정리 + 경로 분기 + custom show() 호출 — 2줄 이상 실질 로직 | audited |
| `save_formats` | `dartwork_mpl.io` | func | 8 | N | 88 | 2 | keep | `savefig` 다중 포맷 확장 + bbox/validate kwargs 모호성 해소 | audited |
| `show` | `dartwork_mpl.io` | func | 48 | N | 238 | 3 | keep | SVG DOM 파싱 + aspect-ratio 보존 width/height 치환 + IPython display — plt.show() 아님 | audited |
| `auto_layout` | `dartwork_mpl.layout` | func | 322 | N | 304 | 3 | keep | dartwork-mpl 고유 content-aware 측정 | audited |
| `get_bounding_box` | `dartwork_mpl.layout` | func | 15 | N | 6 | 2 | keep | 측정 helper | audited |
| `set_xmargin` | `dartwork_mpl.layout` | func | 7 | N | 8 | 2 | borderline | x-margin + xlim 동시 조정 — 토론 | removed |
| `set_ymargin` | `dartwork_mpl.layout` | func | 7 | N | 7 | 2 | borderline | y-margin + ylim 동시 조정 — 토론 | removed |
| `simple_layout` | `dartwork_mpl.layout` | func | 82 | N | 275 | 2 | keep | tight_layout/constrained_layout 모호성 해소 | audited |
| `tight_crop` | `dartwork_mpl.layout` | func | 128 | N | 3 | 2 | keep | artist-bbox 측정 후 fig 리사이즈 | audited |
| `Issue` | `dartwork_mpl.lint` | class | 0 | N | 19 | 3 | keep | frozen dataclass — rule_id·severity·line·snippet·column·fix_suggestion; lint engine 핵심 결과 타입 | audited |
| `Rule` | `dartwork_mpl.lint` | class | 0 | N | 17 | 3 | keep | frozen dataclass — id·severity·detector_kind/value·message·why·fix_suggestion; YAML 카탈로그 단위 | audited |
| `format_report` | `dartwork_mpl.lint` | func | 19 | N | 17 | 3 | keep | 19 LOC — severity 그룹화 + fix_suggestion 인라인 출력; MCP 도구 + CLI 공유 포맷터 | audited |
| `lint` | `dartwork_mpl.lint` | func | 16 | N | 191 | 3 | keep | 191 callsites — regex/substring 검출 루프; MCP lint_dartwork_mpl_code + CLI 진입점 | audited |
| `load_rules` | `dartwork_mpl.lint` | func | 28 | N | 20 | 3 | keep | 28 LOC YAML 카탈로그 파서 — detector kind 분기 + Rule 객체 생성; SSOT 로더 | audited |
| `migrate_legacy_code` | `dartwork_mpl.lint` | func | 20 | N | 34 | 3 | keep | 0.3→0.4 마이그레이션 도구 — load_rules 기반 auto-fix 치환; 34 callsites | audited |
| `copy_prompt` | `dartwork_mpl.prompt` | func | 10 | N | 9 | 2 | keep | 번들 prompt → 지정 경로 복사; dir/file 분기 + create_parent_path; 프롬프트 추출 CLI | audited |
| `find_template` | `dartwork_mpl.prompt` | func | 27 | N | 22 | 3 | keep | 27 LOC 토큰 매칭 scorer — _index.json 기반 template 랭킹; MCP find_template Python 동등체 | audited |
| `get_prompt` | `dartwork_mpl.prompt` | func | 2 | N | 32 | 2 | keep | prompt_path + read_text 2줄; 의미 있는 진입점 — 32 callsites | audited |
| `list_prompts` | `dartwork_mpl.prompt` | func | 15 | N | 16 | 2 | keep | glob + canonical set 비교 + drift warning; 번들 knowledge-base 디스커버리 | audited |
| `prompt_path` | `dartwork_mpl.prompt` | func | 4 | N | 9 | 2 | keep | 번들 경로 해석 + ValueError; path helper with validation | audited |
| `fs` | `dartwork_mpl.scale` | func | 1 | N | 1256 | 1 | keep | relative font-size token (`rcParams['font.size'] + n`) — no matplotlib equivalent | audited |
| `fw` | `dartwork_mpl.scale` | func | 4 | N | 83 | 2 | keep | string weight name → numeric conversion via `_WEIGHT_MAP` + offset — no matplotlib equivalent | audited |
| `lw` | `dartwork_mpl.scale` | func | 1 | N | 417 | 1 | keep | relative linewidth token (`rcParams['lines.linewidth'] + n`) — no matplotlib equivalent | audited |
| `add_frame` | `dartwork_mpl.spines` | func | 4 | N | 10 | 2 | borderline | composition (visible+color+linewidth on all spines) — 토론 | removed |
| `add_grid` | `dartwork_mpl.spines` | func | 11 | N | 21 | 2 | remove | dm.* default kwargs(color, alpha 등) 가치 — round 4 of #141 / #156: removed; recipe at docs/usage_guide/recipes.md#publication-grid | removed |
| `hide_all_spines` | `dartwork_mpl.spines` | func | 2 | Y | 28 | 1 | remove | `for s in ax.spines.values(): s.set_visible(False)` | removed |
| `hide_spines` | `dartwork_mpl.spines` | func | 6 | Y | 13 | 1 | remove | `for s in ['top','right']: ax.spines[s].set_visible(False)` | removed |
| `minimal_axes` | `dartwork_mpl.spines` | func | 7 | N | 30 | 3 | remove | 4 함수 묶음 composition — round 4 of #141 / #156: removed; recipe at docs/usage_guide/recipes.md#minimal-axes-tufte-style | removed |
| `remove_grid` | `dartwork_mpl.spines` | func | 1 | Y | 3 | 1 | remove | `ax.grid(False)` | removed |
| `show_only_spines` | `dartwork_mpl.spines` | func | 4 | Y | 4 | 2 | remove | `for s in ['top','right','bottom','left']: ax.spines[s].set_visible(s in which)` | removed |
| `style_spines` | `dartwork_mpl.spines` | func | 14 | N | 9 | 2 | remove | composition (color+linewidth+visible filter) — round 4 of #141 / #156: removed; recipe at docs/usage_guide/recipes.md#thin-gray-spines | removed |
| `Style` | `dartwork_mpl.style` | class | 0 | N | 61 | 3 | keep | presets 로딩 + thread-safe rcParams 갱신 + use/stack/context/context_manager — 'One Right Way' 스타일 시스템 핵심 | audited |
| `list_styles` | `dartwork_mpl.style` | func | 2 | N | 11 | 2 | keep | asset/mplstyle glob → stem 목록 — style discovery | audited |
| `load_style_dict` | `dartwork_mpl.style` | func | 26 | N | 10 | 2 | keep | mplstyle 커스텀 파서 (inline comment 제거 + colon-split + float 변환) — no matplotlib equivalent | audited |
| `style_path` | `dartwork_mpl.style` | func | 5 | N | 7 | 1 | keep | asset 경로 해석 + ValueError — style 파일 path helper | audited |
| `get_source_code` | `dartwork_mpl.templates.diverging_bar` | func | 13 | N | 0 | 2 | borderline | importlib+inspect 경유 모듈 소스 반환 — 외부 callsite 0; AI agent용 코드 노출 의도이나 단순 inspect wrapper — 토론 | removed |
| `plot_diverging_bar` | `dartwork_mpl.templates.diverging_bar` | func | 206 | N | 28 | 3 | keep | 206 LOC 완전한 chart template — blended transform + cascading layout + 값 라벨 배치; 28 callsites | audited |
| `Length` | `dartwork_mpl.units` | class | 0 | N | 27 | 2 | keep | 물리 길이 wrapper (Color 패턴) — 멀티 유닛 view (.cm/.mm/.inch/.pt), str init 파싱, 산술 보존; 0.4 in-flight `Inches(float)` 마커를 #152에서 리네임 | audited |
| `cm` | `dartwork_mpl.units` | func | 1 | N | 200 | 1 | keep | 물리 단위 토큰 — cm → Length 변환; parse_width 진입점 | audited |
| `inch` | `dartwork_mpl.units` | func | 1 | N | 35 | 1 | keep | 물리 단위 토큰 — Length 태그 부여 identity | audited |
| `mm` | `dartwork_mpl.units` | func | 1 | N | 43 | 1 | keep | 물리 단위 토큰 — mm → Length 변환 | audited |
| `pt` | `dartwork_mpl.units` | func | 1 | N | 0 | 1 | keep | 물리 단위 토큰 — pt → Length 변환 (1 pt = 1/72 in); #152에서 추가 | audited |
| `length` | `dartwork_mpl.units` | func | 1 | N | 0 | 1 | keep | 단위 문자열 파서 — `dm.length("13cm")`; `dm.hex(...)`의 길이 버전 | audited |
| `parse_aspect` | `dartwork_mpl.units` | func | 27 | N | 28 | 2 | keep | 토큰 룩업 + bool 거부 + 수치 검증 + 오타 제안 — 핵심 내부 파서 | audited |
| `parse_width` | `dartwork_mpl.units` | func | 44 | N | 37 | 2 | keep | Length pass-through + bool 거부 + 단위 파싱 + 검증 + 오타 제안 — 핵심 내부 파서 | audited |
| `make_offset` | `dartwork_mpl.util` | func | 2 | N | 21 | 2 | borderline | ScaledTranslation 2-line wrapper (x/72, y/72 + fig.dpi_scale_trans) — Task 11에서 keep/remove 결정 | audited |
| `mix_colors` | `dartwork_mpl.util` | func | 8 | N | 28 | 2 | borderline | 단순 RGB linspace (mcolors.to_rgb 경유) — OKLCH 인터폴레이션 없음; 토론 | audited |
| `pseudo_alpha` | `dartwork_mpl.util` | func | 1 | N | 34 | 2 | borderline | mix_colors 1-line delegate; 백색 블렌딩 의미 있으나 구현이 RGB — 토론 | audited |
| `set_decimal` | `dartwork_mpl.util` | func | 9 | N | 40 | 2 | borderline | get_ticks + set_ticks + set_ticklabels 3-step pattern per axis; no rcParams/locale logic — 토론 | audited |
| `Severity` | `dartwork_mpl.validate` | class | 0 | N | 26 | 2 | keep | WARNING/INFO Enum; 26 callsites — validate 시스템 severity 타입 | audited |
| `VisualWarning` | `dartwork_mpl.validate` | class | 0 | N | 24 | 2 | keep | dataclass — severity·check_id·message·detail + _ICONS + __str__; 24 callsites — visual 검증 결과 타입 | audited |
| `validate_figure` | `dartwork_mpl.validate` | func | 39 | N | 103 | 3 | keep | 8개 check lambda 등록·선택 실행 + canvas.draw() 렌더 → VisualWarning 수집 — 종합 visual 검증 엔진 | audited |
| `check_agent_requirements` | `dartwork_mpl.validate_fixes` | func | 41 | N | 1 | 3 | keep | 41 LOC — DPI·style·axis labels·data·color 다중 검사 dict 반환; agent-oriented 요구사항 점검 | audited |
| `generate_validation_report` | `dartwork_mpl.validate_fixes` | func | 47 | N | 1 | 3 | keep | 47 LOC — requirements + visual warnings + score + status 종합 리포트; agent 출력용 구조화 텍스트 | audited |
| `get_fix_suggestions` | `dartwork_mpl.validate_fixes` | func | 90 | N | 20 | 3 | keep | 90 LOC — check_id별 5분기 코드 스니펫 생성; 20 callsites; auto-fix agent 핵심 | audited |
| `validate_with_fixes` | `dartwork_mpl.validate_fixes` | func | 48 | N | 16 | 3 | keep | validate_figure + get_fix_suggestions 결합 — 검증·수정 제안 원스톱 API; 16 callsites | audited |

## Borderline cases (토론 대상)

분류가 `borderline`인 항목을 별도 정리. 각 항목은 PR 리뷰 또는 후속 코멘트에서
keep / remove로 재분류한다. `잠정 권고`는 본 spec §3 기준의 중간 판단이며, 메인테이너
합의로 확정한다.

| name | module | loc | callsites | 핵심 사유 (notes 요약) | 잠정 권고 |
|---|---|---|---|---|---|
| `format_axis_percent` | `dartwork_mpl.formatting` | 6 | 4 | PercentFormatter 래핑 + x/y/both 분기 dispatch 제공 | **removed** (#141 round 3) |
| `format_axis_thousands` | `dartwork_mpl.formatting` | 6 | 2 | 단순 FuncFormatter 람다, sep 파라미터만 추가 | remove |
| `rotate_tick_labels` | `dartwork_mpl.formatting` | 26 | 25 | auto-ha 추론 + FixedLocator-safe 순회 — 실질 로직 | keep |
| `create_figure_with_style` | `dartwork_mpl.helpers.io` | 9 | 22 | figsize= 안티패턴 직접 사용하는 2줄 shortcut | remove |
| `save_figure` | `dartwork_mpl.helpers.io` | 11 | 24 | save_formats 1-line passthrough + mkdir + print — double-wrapper | remove |
| `add_value_labels` | `dartwork_mpl.helpers.labels` | 18 | 17 | 데이터 순회·offset 계산·ax.text 배치 — bar/line annotation | **removed** (#141 round 3) |
| `format_axis_labels` | `dartwork_mpl.helpers.labels` | 12 | 22 | xlabel/ylabel/title + fontsize 3-call composition | **removed** (#141 round 3) |
| `optimize_legend` | `dartwork_mpl.helpers.labels` | 31 | 15 | ncol 휴리스틱 + inside/outside 배치 분기 composition | keep |
| `set_xmargin` | `dartwork_mpl.layout` | 7 | 8 | margin + 선택적 edge pinning composition (4-step) | **removed** (#141 round 3) |
| `set_ymargin` | `dartwork_mpl.layout` | 7 | 7 | margin + 선택적 edge pinning composition (4-step) | **removed** (#141 round 3) |
| `add_frame` | `dartwork_mpl.spines` | 4 | 10 | 전체 spine에 visible·color·linewidth 적용 composition | **removed** (#141 round 3) |
| `add_grid` | `dartwork_mpl.spines` | 11 | 15 | dm.* 기본값(color, alpha 등) 적용 grid 헬퍼 | **removed** (#156 round 4) |
| `minimal_axes` | `dartwork_mpl.spines` | 7 | 27 | 4개 함수 묶음 composition, 27 callsites | **removed** (#156 round 4) |
| `style_spines` | `dartwork_mpl.spines` | 14 | 9 | color·linewidth·visible 필터 composition | **removed** (#156 round 4) |
| `get_source_code` | `dartwork_mpl.templates.diverging_bar` | 13 | 0 | importlib+inspect 경유 소스 반환 — 외부 callsite 0 | remove |
| `make_offset` | `dartwork_mpl.util` | 2 | 21 | ScaledTranslation 2-line wrapper — LOC≤3 단순 래핑 | remove |
| `mix_colors` | `dartwork_mpl.util` | 8 | 28 | RGB linspace 블렌딩 — OKLCH 미지원, 28 callsites | ? |
| `pseudo_alpha` | `dartwork_mpl.util` | 1 | 34 | mix_colors 1-line delegate (LOC=1) — 의미는 있으나 인라인 trivial | remove |
| `set_decimal` | `dartwork_mpl.util` | 9 | 40 | get/set ticks + ticklabels 3-step per axis, 40 callsites | keep |

## Round 4: keep-survivor remove (#156)

[#156](https://github.com/dartworklabs/dartwork-mpl/issues/156) reviewed
the four `keep`-audited borderline survivors below (kept on callsite
count + composition value). An earlier draft proposed segregating them
under a new `dm.defaults` submodule; the proposal was rejected on
naming-as-signal grounds (no candidate name read cleanly — `defaults`,
`preset`, `recipes` all carried defects). See
[`docs/superpowers/specs/2026-05-07-keep-survivor-remove-design.md`](../superpowers/specs/2026-05-07-keep-survivor-remove-design.md)
§2 / §7 for the full reasoning.

Three items are reclassified `keep` → `remove`. The fourth
(`auto_select_colors`) stays `keep` because its body is a curated
palette **lookup**, not a kwarg recipe — but is renamed to
`make_palette` in Round 5 for vocabulary alignment with `make_offset`
/ `list_colors` / `show_colors`. The audit framework stays
3-bucket; no new value. Round 5 implements.

| name | module | LOC | from | to | preservation vehicle |
|---|---|---|---|---|---|
| `style_spines` | `dartwork_mpl.spines` | 14 | keep | **remove** | docs recipe (thin gray spines snippet) |
| `add_grid` | `dartwork_mpl.spines` | 11 | keep | **remove** | docs recipe (publication grid snippet) + optional lint rule for `set_axisbelow` (§4.2 of spec) |
| `minimal_axes` | `dartwork_mpl.spines` | 7 | keep | **remove** | docs recipe (minimal axes snippet) |

`auto_select_colors` (`dartwork_mpl.helpers.colors`, LOC 63, 33
callsites) stays **keep**, renamed to `make_palette` in Round 5.
Argument cleanup at rename: `n_series → n`, `color_type → kind`,
`highlight_index → highlight`. Final signature:
`dm.make_palette(n, kind="categorical", highlight=None)`. See spec §3.1.

Items audited as `keep` that **stay** at top-level under the existing
3-bucket framework: `rotate_tick_labels`, `optimize_legend`,
`set_decimal`, all `format_axis_*`. Each carries non-default control
flow (FixedLocator-safe iteration, ncol heuristic, multi-step
tick-rewrite pattern, sign-outside-symbol formatting, SI tier
selection). See spec §3 for per-item reasoning.

`make_offset` / `mix_colors` / `pseudo_alpha` are out of scope of this
round and remain on the existing prune track.

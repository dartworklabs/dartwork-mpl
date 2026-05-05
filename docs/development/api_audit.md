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
| `arrow_axis` | `dartwork_mpl.annotation` | func | 103 |  | 28 |  |  |  | pending |
| `label_axes` | `dartwork_mpl.annotation` | func | 28 |  | 58 |  |  |  | pending |
| `ensure_loaded` | `dartwork_mpl.cmap` | func | 13 |  | 47 |  |  |  | pending |
| `Color` | `dartwork_mpl.color._color` | class | 0 |  | 174 |  |  |  | pending |
| `cspace` | `dartwork_mpl.color._color` | func | 105 |  | 92 |  |  |  | pending |
| `hex` | `dartwork_mpl.color._color` | func | 1 |  | 67 |  |  |  | pending |
| `named` | `dartwork_mpl.color._color` | func | 10 |  | 72 |  |  |  | pending |
| `oklab` | `dartwork_mpl.color._color` | func | 1 |  | 76 |  |  |  | pending |
| `oklch` | `dartwork_mpl.color._color` | func | 1 |  | 113 |  |  |  | pending |
| `rgb` | `dartwork_mpl.color._color` | func | 1 |  | 62 |  |  |  | pending |
| `ensure_loaded` | `dartwork_mpl.color._loader` | func | 5 |  | 47 |  |  |  | pending |
| `OklabView` | `dartwork_mpl.color._views` | class | 0 |  | 4 |  |  |  | pending |
| `OklchView` | `dartwork_mpl.color._views` | class | 0 |  | 4 |  |  |  | pending |
| `RgbView` | `dartwork_mpl.color._views` | class | 0 |  | 4 |  |  |  | pending |
| `classify_colormap` | `dartwork_mpl.diagnostics` | func | 120 |  | 21 |  |  |  | pending |
| `plot_colormaps` | `dartwork_mpl.diagnostics` | func | 48 |  | 26 |  |  |  | pending |
| `plot_colors` | `dartwork_mpl.diagnostics` | func | 32 |  | 35 |  |  |  | pending |
| `plot_fonts` | `dartwork_mpl.diagnostics` | func | 203 |  | 29 |  |  |  | pending |
| `list_colormaps` | `dartwork_mpl.explore` | func | 7 |  | 5 |  |  |  | pending |
| `list_palettes` | `dartwork_mpl.explore` | func | 11 |  | 6 |  |  |  | pending |
| `show_palette` | `dartwork_mpl.explore` | func | 52 |  | 6 |  |  |  | pending |
| `figure` | `dartwork_mpl.figure` | func | 62 |  | 401 |  |  |  | pending |
| `subplots` | `dartwork_mpl.figure` | func | 82 |  | 645 |  |  |  | pending |
| `ensure_loaded` | `dartwork_mpl.font` | func | 11 |  | 47 |  |  |  | pending |
| `format_axis_billions` | `dartwork_mpl.formatting` | func | 25 |  | 18 |  |  |  | pending |
| `format_axis_currency` | `dartwork_mpl.formatting` | func | 34 |  | 11 |  |  |  | pending |
| `format_axis_millions` | `dartwork_mpl.formatting` | func | 25 |  | 20 |  |  |  | pending |
| `format_axis_percent` | `dartwork_mpl.formatting` | func | 6 |  | 4 |  |  |  | pending |
| `format_axis_si` | `dartwork_mpl.formatting` | func | 37 |  | 26 |  |  |  | pending |
| `format_axis_thousands` | `dartwork_mpl.formatting` | func | 6 |  | 2 |  |  |  | pending |
| `rotate_tick_labels` | `dartwork_mpl.formatting` | func | 26 |  | 25 |  |  |  | pending |
| `auto_select_colors` | `dartwork_mpl.helpers.colors` | func | 63 |  | 33 |  |  |  | pending |
| `validate_data` | `dartwork_mpl.helpers.data` | func | 43 |  | 26 |  |  |  | pending |
| `create_figure_with_style` | `dartwork_mpl.helpers.io` | func | 9 |  | 22 |  |  |  | pending |
| `save_figure` | `dartwork_mpl.helpers.io` | func | 11 |  | 24 |  |  |  | pending |
| `add_value_labels` | `dartwork_mpl.helpers.labels` | func | 18 |  | 17 |  |  |  | pending |
| `format_axis_labels` | `dartwork_mpl.helpers.labels` | func | 12 |  | 22 |  |  |  | pending |
| `optimize_legend` | `dartwork_mpl.helpers.labels` | func | 31 |  | 15 |  |  |  | pending |
| `check_figure_quality` | `dartwork_mpl.helpers.quality` | func | 39 |  | 18 |  |  |  | pending |
| `suggest_chart_type` | `dartwork_mpl.helpers.quality` | func | 31 |  | 24 |  |  |  | pending |
| `ensure_loaded` | `dartwork_mpl.icon` | func | 4 |  | 47 |  |  |  | pending |
| `icon_font` | `dartwork_mpl.icon` | func | 2 |  | 13 |  |  |  | pending |
| `icon_font_path` | `dartwork_mpl.icon` | func | 12 |  | 7 |  |  |  | pending |
| `list_icon_fonts` | `dartwork_mpl.icon` | func | 1 |  | 9 |  |  |  | pending |
| `install_llm_txt` | `dartwork_mpl.install` | func | 42 |  | 24 |  |  |  | pending |
| `uninstall_llm_txt` | `dartwork_mpl.install` | func | 19 |  | 7 |  |  |  | pending |
| `save_and_show` | `dartwork_mpl.io` | func | 14 |  | 34 |  |  |  | pending |
| `save_formats` | `dartwork_mpl.io` | func | 8 |  | 77 |  |  |  | pending |
| `show` | `dartwork_mpl.io` | func | 48 |  | 238 |  |  |  | pending |
| `auto_layout` | `dartwork_mpl.layout` | func | 322 | N | 293 | 3 | keep | dartwork-mpl 고유 content-aware 측정 | audited |
| `get_bounding_box` | `dartwork_mpl.layout` | func | 15 | N | 6 | 2 | keep | 측정 helper | audited |
| `set_xmargin` | `dartwork_mpl.layout` | func | 7 | N | 8 | 2 | borderline | x-margin + xlim 동시 조정 | audited |
| `set_ymargin` | `dartwork_mpl.layout` | func | 7 | N | 7 | 2 | borderline | y-margin + ylim 동시 조정 | audited |
| `simple_layout` | `dartwork_mpl.layout` | func | 82 | N | 275 | 2 | keep | tight_layout/constrained_layout 모호성 해소 | audited |
| `tight_crop` | `dartwork_mpl.layout` | func | 128 | N | 3 | 2 | keep | 고유 alpha-cropping | audited |
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
| `fs` | `dartwork_mpl.scale` | func | 1 |  | 1256 |  |  |  | pending |
| `fw` | `dartwork_mpl.scale` | func | 4 |  | 83 |  |  |  | pending |
| `lw` | `dartwork_mpl.scale` | func | 1 |  | 417 |  |  |  | pending |
| `add_frame` | `dartwork_mpl.spines` | func | 4 | N | 10 | 2 | borderline | composition — 토론 | audited |
| `add_grid` | `dartwork_mpl.spines` | func | 11 | N | 15 | 2 | borderline | dm.* default kwargs(color, alpha 등) 가치 — 토론 | audited |
| `hide_all_spines` | `dartwork_mpl.spines` | func | 2 | Y | 28 | 1 | remove | `for s in ax.spines.values(): s.set_visible(False)` | audited |
| `hide_spines` | `dartwork_mpl.spines` | func | 6 | Y | 10 | 1 | remove | `for s in ['top','right']: ax.spines[s].set_visible(False)` | audited |
| `minimal_axes` | `dartwork_mpl.spines` | func | 7 | N | 27 | 3 | borderline | 4 함수 묶음 composition — 토론 | audited |
| `remove_grid` | `dartwork_mpl.spines` | func | 1 | Y | 3 | 1 | remove | `ax.grid(False)` | audited |
| `show_only_spines` | `dartwork_mpl.spines` | func | 4 | Y | 4 | 2 | remove | spec §2.1 — 4-element loop | audited |
| `style_spines` | `dartwork_mpl.spines` | func | 14 | N | 9 | 2 | borderline | composition (color+linewidth+visible filter) — 토론 | audited |
| `Style` | `dartwork_mpl.style` | class | 0 |  | 61 |  |  |  | pending |
| `list_styles` | `dartwork_mpl.style` | func | 2 |  | 11 |  |  |  | pending |
| `load_style_dict` | `dartwork_mpl.style` | func | 26 |  | 10 |  |  |  | pending |
| `style_path` | `dartwork_mpl.style` | func | 5 |  | 7 |  |  |  | pending |
| `get_source_code` | `dartwork_mpl.templates.diverging_bar` | func | 13 |  | 0 |  |  |  | pending |
| `plot_diverging_bar` | `dartwork_mpl.templates.diverging_bar` | func | 206 |  | 28 |  |  |  | pending |
| `Inches` | `dartwork_mpl.units` | class | 0 |  | 27 |  |  |  | pending |
| `cm` | `dartwork_mpl.units` | func | 1 |  | 200 |  |  |  | pending |
| `inch` | `dartwork_mpl.units` | func | 1 |  | 35 |  |  |  | pending |
| `mm` | `dartwork_mpl.units` | func | 1 |  | 43 |  |  |  | pending |
| `parse_aspect` | `dartwork_mpl.units` | func | 27 |  | 28 |  |  |  | pending |
| `parse_width` | `dartwork_mpl.units` | func | 44 |  | 37 |  |  |  | pending |
| `make_offset` | `dartwork_mpl.util` | func | 2 |  | 21 |  |  |  | pending |
| `mix_colors` | `dartwork_mpl.util` | func | 8 |  | 28 |  |  |  | pending |
| `pseudo_alpha` | `dartwork_mpl.util` | func | 1 |  | 34 |  |  |  | pending |
| `set_decimal` | `dartwork_mpl.util` | func | 9 |  | 40 |  |  |  | pending |
| `Severity` | `dartwork_mpl.validate` | class | 0 |  | 26 |  |  |  | pending |
| `VisualWarning` | `dartwork_mpl.validate` | class | 0 |  | 24 |  |  |  | pending |
| `validate_figure` | `dartwork_mpl.validate` | func | 39 |  | 103 |  |  |  | pending |
| `check_agent_requirements` | `dartwork_mpl.validate_fixes` | func | 41 |  | 1 |  |  |  | pending |
| `generate_validation_report` | `dartwork_mpl.validate_fixes` | func | 47 |  | 1 |  |  |  | pending |
| `get_fix_suggestions` | `dartwork_mpl.validate_fixes` | func | 90 |  | 20 |  |  |  | pending |
| `validate_with_fixes` | `dartwork_mpl.validate_fixes` | func | 48 |  | 16 |  |  |  | pending |

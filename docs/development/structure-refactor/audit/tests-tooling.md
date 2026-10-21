---
orphan: true
---

# 구조 감사: `tests/`와 품질 도구

기준: `code-implement`(SKILL.md, references/structure·python·format)·`code-testing` 스킬, limn(`pyproject.toml`, `tools/check_boundaries.py`, `tests/architecture/`, ADR 0010/0012, `verification.md`). 대상 커밋 `0e88b810`(main). 읽기 전용 감사. 측정은 `git archive` 사본(`/tmp/dmpl-copy`)과 `uv sync --frozen --all-extras --dev` 환경에서 했다.

## 1. 현재 상태

### 1.1 테스트 트리 분류

루트 `tests/`에는 `test_*.py` 129개, `conftest.py`, `__init__.py`, `_docs_color_oracles.py`, 하위 디렉터리 `mcp/`(22개 파일), `robustness/`(3개), `visual/`(2개)가 있다. 수집 수는 6887개다. "관찰 대상"은 그 파일이 import하는 `dartwork_mpl` 하위 단위와 읽는 경로로 판정했다. 목적지 열의 `<unit>/tests/`는 현재 모듈 이름 기준이다. 슬라이스 경계가 확정되면 그 경계를 따른다.

| 목적지 | 파일 (관찰 대상) | 수 |
|---|---|---|
| `_colors/tests/` | `test_color_api`, `color_build_entrypoint`, `color_conversion`, `color_eq_gamut`, `color_model_b_api`, `color_parser`, `color_v5_*` 13개, `color_v6_{architecture,gamut,ssot_validation,tone}`, `color_view`, `discrete_forms`, `family_invariants`, `loader`, `palette_sources_consistency`, `theme_dark_cycle`, `typing_parity` (모두 `_colors.*`만 관찰. `color_v6_architecture`는 이 슬라이스 안의 AST 규칙이다) | 30 |
| `mcp/tests/` | `test_mcp`, `test_mcp_{asset_boundary,data_repair_contract,heavy_tools,render_smoke,tool_hardening,validation_contract,validators_complete}`, `test_docstring_catalogs`, 그리고 `tests/mcp/{agent_loop,artifacts,data_repair}/` 전체(22개 + `artifacts/conftest.py` + fixtures) | 9+22 |
| `ui/tests/` | `test_ui_{boundary,files,hardening,http_security,init,main,param,scaffold,security,template,widget}` | 11 |
| `validate/tests/` | `test_validate`, `validate_accessibility`, `check_registry`, `grayscale_safety_metrics`, `figure_legend_hardening` | 5 |
| 단일 모듈 단위 | style: `test_style`, `mplstyle_fonts`, `mplstyle_tokens`, `tokens` (4) / font: `test_font`, `font_glyph_coverage`, `font_invariants`, `font_licenses` (4) / formatting: 3 / units: `test_units`, `figsize_grid`, `docs_assets`(실제로는 `dm.figsize` 불변식) (3) / layout: `test_layout`, `figure_level_extents` (2) / helpers: `test_helpers_*` 5 / lint: `test_lint`, `migrate_legacy` / prompt: `test_prompt`, `find_template` / diagnostics: 2 / 1개씩: icon, scale, annotation, io, util, `_helpers`, validate_fixes, templates, explore | 36 |
| 루트 `tests/contracts/` | `test_shipped_colors_hash`(CLAUDE.md가 경로를 명시한 색 동결), `api_stability`, `deprecation_aliases`, `deprecation_registry_parity`, `init_patch`, `version`, `concurrency`(style·font·_colors·icon 동시 관찰), `integration`(mcp+agent 문서), `cli`, `examples_smoke`, `orphan_tick_font`(io+layout+style 종단), `preset_matrix`(validate×preset), `robustness/`, `visual/`(CI·baseline 경로 고정) | 12+2 디렉터리 |
| 루트 `tests/docs/` | `test_docs_*` 12개(`docs_assets` 제외), `drift`, `colormap_explorer_taxonomy`, `palette_family_taxonomy`, `fonts_browser_consistency`, `fonts_generator_parity`, `style_chain_parity`, `template_body_parity` (docs/·scripts/·llms 산출물 대조) | 19 |
| 루트 `tests/tools/` | `test_color_v6_{atomic_writes,comparison,quality_oracle,compatibility}`(scripts/ 실행·소스 텍스트 대조), `check_integration_junit`, `extract_release_notes` | 6 |
| 루트 `tests/architecture/` | `test_domain_neutrality`(저장소 전역 어휘 검사, limn `test_naming.py`와 같은 성격) + 신규 경계 검사 | 1 |

합계: 슬라이스로 갈 파일 91개 + `tests/mcp/**` 22개, 루트에 남을 파일 38개 + `robustness/`·`visual/`.

공용 도우미와 fixture:
- `tests/conftest.py` — autouse `_matplotlib_state_isolation`(rcParams·`dm.config`·`_dm_preset_values` 초기화)은 모든 테스트가 의존한다. 모듈 import 시점에 `src`와 가짜 dist-info를 `sys.path`·`PYTHONPATH`에 넣는다(`test_version`, 하위 프로세스 테스트가 의존). 루트 `tests/conftest.py`는 `src/` 아래 테스트에 적용되지 않으므로, 동거하려면 저장소 루트 `conftest.py`로 올려야 한다.
- 같은 파일의 `v5_ssot`(9개 파일), `candidate_catalog`(3개 파일)는 color 테스트만 쓴다. `_colors/tests/conftest.py`로 옮긴다.
- `tests/_docs_color_oracles.py` — `test_docs_float_claims`, `test_docs_theory_figures`가 `from tests._docs_color_oracles import`로 쓴다.
- `tests/robustness/{scenarios,pixel_assertions}.py`(`from tests.robustness import`), `tests/visual/scenarios.py`(상대 import), `tests/mcp/artifacts/conftest.py`(`owned_input_root`).
- `test_input_delivery.py`, `test_input_recovery.py`는 다른 테스트 모듈을 `from test_input_store import ...`처럼 맨 이름으로 import한다. prepend 모드에서만 동작한다.

### 1.2 도구 설정 요약 (`pyproject.toml`)

- pytest: `testpaths=["tests"]`, `pythonpath=["src"]`, import-mode는 기본값(prepend). marker는 `mpl_image_compare` 하나.
- ruff: `line-length=80`, select는 `E W F I B C4 UP BLE RET SIM PERF RUF`이고 **D 규칙이 없다**. `tests/**` per-file-ignore 8개.
- mypy: `strict=true`, `ignore_missing_imports=true`, `exclude=asset/prompt/05-templates`, `mcp.*`·`ui.*`에 `disallow_untyped_decorators/subclassing_any=false`, `files` 없음, `exhaustive-match` 없음. `type: ignore`는 21개.
- coverage: `source=src/dartwork_mpl`, `omit=*/ui/*`, `fail_under=80`.
- 빌드: hatchling. wheel은 `packages=["src/dartwork_mpl"]`이고 **exclude가 없다**. sdist는 `only-include`(src/dartwork_mpl 포함, tests/ 미포함).
- Makefile·justfile·nox·tox 없음.

### 1.3 CI 명령 (`.github/workflows/`)

| 검사 | 명령 | 위치 |
|---|---|---|
| ruff lint·format | pre-commit hook `ruff --fix`, `ruff-format` (rev v0.15.16, uv.lock과 같은 버전이지만 수동 고정) | `pre-commit.yml`(`pre-commit/action` 기본 `--all-files`. job 이름은 "changed files"라 실제와 다르다) |
| mypy | `uv run mypy src/dartwork_mpl/` | `ci.yml` lint job과 pre-commit 로컬 hook(`--frozen`, CI에서는 `SKIP: mypy`) |
| pytest | `uv run pytest tests/ ...`(3.12만 `--cov`), `pytest tests/mcp/artifacts`(fastmcp 2/3 행렬), `pytest tests/visual/test_visual_pixels.py --mpl` | `ci.yml`, `release.yml`, `visual-baselines.yml` |
| 실행 증명 | `scripts/check_integration_junit.py`. 보호 모듈 37개를 `tests.test_mcp` 같은 junit 이름으로 하드코딩했다 | `ci.yml`, `release.yml` |
| 색·문서 산출물 | `build_color_v6_ssot.py`+`cmp`, `_build --check`, `compare_color_systems.py --check`, explorer `--check`, `sphinx-build -W` | `ci.yml` docs job, `docs.yml`, `release.yml`(세 곳에 중복) |

- **mypy 6개 오류는 CI에서 재현되지 않는다.** 로컬 `.venv`에 extras(pydantic, fastapi, fastmcp)가 없어서 생긴다(`ui/_boundary.py` 4개, `mcp/artifacts/transport.py` unused-ignore 2개). `--all-extras` 환경에서는 `Success: no issues found in 116 source files`가 나온다. 따라서 "로컬과 CI가 같은 명령" 규칙은 명령 문자열만 같고 환경이 다르다.
- main CI는 최근 3회 모두 실패다(`test (3.13)`·`test-mcp-artifacts (3.4.2)`에서 `tests/mcp/artifacts/test_input_access.py` ERROR, push=self-hosted runner). 테스트 이동 전후를 대조하려면 기준선이 녹색이어야 한다.
- pre-commit exclude의 `src/dartwork_mpl/colors/_generated\.py$`는 존재하지 않는 경로다(실제는 `_colors/`).

### 1.4 기존 구조 검사

패키지 전역 import 그래프 검사는 **없다**. 국소 AST 검사만 셋 있다.
- `test_color_v6_architecture.py` — color builder·recipe·discrete가 legacy solver와 CIE 모듈을 import하지 않는지 본다.
- `tests/mcp/artifacts/test_artifact_boundaries.py`·`test_artifact_entry_policies.py` — artifacts 하위 모듈 사이의 import 제한.
- `test_ui_boundary.py` 883–902행 — ui 경계 AST 검사.
- `test_api_stability.py` — `dm.__all__`에 deprecated 이름이 없는지, 모든 이름을 import할 수 있는지.

`__all__`이 있는 하위 패키지는 7개(`_colors`, `diagnostics`, `helpers`, `mcp`, `templates`, `validate`, `ui`)다. 단일 파일 모듈 22개는 표면을 선언하지 않는다.

## 2. limn 대비 격차

1. **동거 테스트 수집**: limn은 `testpaths=["tests","src/limn"]`, `--import-mode=importlib`, `pythonpath=["tests/support"]`를 쓴다. dartwork-mpl은 `tests`만 수집하고 prepend 모드를 쓴다. CI가 `pytest tests/`로 경로를 명시하므로 testpaths를 바꿔도 CI는 src 아래를 수집하지 않는다(`ci.yml` 91·101행, `release.yml` 92행).
2. **wheel에서 테스트 제외**: limn은 `exclude=["**/tests/**","**/test_*.py"]`를 둔다. dartwork-mpl에는 없다. 사본에 `src/dartwork_mpl/x/tests/test_probe.py`를 넣고 빌드하면 wheel에 포함됐다. exclude를 추가하면 0이 된다(검증함).
3. **경계 검사기**: limn은 `tools/check_boundaries.py`(AST 기반, ENTRY_POINTS·CAPABILITIES·BOUNDARIES, `__all__` 표면, 공유 경로 추적, 승인 목록과 사용처 대조)와 `tests/architecture/test_boundaries.py`(주입 위반 20여 개)를 두고, CI `Feature boundaries` 단계에서 실행한다. dartwork-mpl에는 대응물이 없다.
4. **docstring 규칙**: limn은 D100–D107(테스트는 D100–D101)을 쓴다. dartwork-mpl에는 없다. 현재 위반은 src 26개(D105 16, D102 9, D107 1), tests 75개(D101 64, D100 11)다.
5. **mypy**: limn은 `files=["src/limn"]`, 동거 테스트 exclude 정규식, `enable_error_code=["exhaustive-match"]`, `strict_equality`를 명시하고 CI에서 `uv run mypy`(인자 없음)를 실행한다. dartwork-mpl은 경로를 명령에 쓰고, `ignore_missing_imports=true`, mcp/ui 완화 override를 둔다.
6. **이동 대조 도구**: limn에는 `tools/test_id_map.py`(collect-only id를 ref와 비교해 lost·duplicated·new를 보고)가 있다. dartwork-mpl에는 없다. 테스트 120여 개를 옮기려면 필요하다.
7. **루트 `tests/`의 끝 상태 결정**: limn ADR-0012는 `contracts/`·`architecture/`·`tools/`·`support/`·`data/`를 정한다. dartwork-mpl에는 대응 ADR이 없다(`docs/adr/` 0001–0004는 색·MCP 결정).
8. **Handbook 참조 검사**(`test_handbook_refs.py`)와 **CI 고정 검사**(`test_ci_pins.py`): dartwork-mpl에는 Handbook이 없고, 액션 SHA 고정은 지켜지지만 그것을 검사하는 테스트가 없다. 이 둘은 이번 범위 밖으로 둔다.

## 3. 제안 게이트

### 3.1 pytest·conftest (동거 허용)
```toml
[tool.pytest.ini_options]
testpaths = ["tests", "src/dartwork_mpl"]
pythonpath = ["src", "tests/support"]
addopts = ["-v", "--strict-markers", "--tb=short", "--import-mode=importlib"]
```
- `tests/conftest.py`의 sys.path·metadata 부트스트랩과 autouse 격리 fixture는 루트 `conftest.py`로 올린다. color fixture 2개는 `_colors/tests/conftest.py`로 옮긴다.
- 영향: importlib 모드만 켜면 collection error 2개가 나고 6702개만 수집된다(`test_input_delivery`, `test_input_recovery`의 맨 이름 import). 공유 부분(`STATES`, `seed`, `NOW`, `fixture`, `identity`, `selection`, `manifest`)을 `tests/support/helpers_mcp_input.py`로 빼면 해결된다. 사본에서 `-o pythonpath="src tests/mcp/artifacts"`로 6887개를 그대로 수집하는 것을 확인했다. `_docs_color_oracles.py`, `robustness/{scenarios,pixel_assertions}.py`도 `tests/support/`로 옮긴다.
- CI·release의 `pytest tests/`를 `pytest`(경로 없음)로 바꾼다. visual 단일 파일 실행은 그대로 둔다.
- coverage: `omit = ["*/ui/*", "*/tests/*", "*/test_*.py"]`.

### 3.2 패키징
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/dartwork_mpl"]
exclude = ["**/tests/**", "**/test_*.py", "**/conftest.py"]
```
- sdist `only-include`에 `src/dartwork_mpl`이 있으므로 동거 테스트는 sdist에 자동으로 들어간다. 루트 `tests/`는 지금처럼 빠진다. `asset/` 안에 `test_*` 파일이 없음을 확인했으므로, 현재 wheel의 파일 수 변화는 0이다.
- 검증: `uv build --wheel` 후 `unzip -l ... | grep -c /tests/`가 0이어야 한다. 이 확인을 `tests/architecture/test_packaging.py`로 고정한다.

### 3.3 ruff D 규칙
```toml
select = [..., "D100","D101","D102","D103","D104","D105","D106","D107"]
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [...기존, "D102","D103","D104","D105","D106","D107"]
"src/dartwork_mpl/**/tests/**/*.py" = [기존 tests 목록과 동일]
```
- 영향: src 26개, tests 75개, 합계 101개다. ratchet을 둘 만한 규모가 아니므로 한 PR에서 직접 고친다. 도입 PR에서 docstring을 일괄로 쓰는 것은 "untouched code 일괄 문서화 금지" 규칙과 충돌하므로, 사용자 승인을 받은 별도 단계로 명시한다. 승인이 없으면 ruff의 `extend-per-file-ignores`로 현재 위반 파일만 목록에 올리고 그 목록이 줄어들기만 하게 한다.
- 소유자: docstring 존재는 ruff 하나가 맡는다. `test_docstring_catalogs.py`는 카탈로그 파싱 계약이라 겹치지 않는다.

### 3.4 mypy 강화 (all-extras 환경 측정)
```toml
files = ["src/dartwork_mpl"]
exclude = ['asset/prompt/05-templates/.*\.py$', '^src/dartwork_mpl/(?:.*/)?(?:tests/|test_[^/]*\.py$|conftest\.py$)']
strict_equality = true
enable_error_code = ["exhaustive-match"]
```
- `exhaustive-match` 영향은 0개다. 바로 켠다.
- `ignore_missing_imports=false`로 바꾸면 3개가 나온다(`fontTools` untyped, `fastmcp.tools.tool` 미발견, `importlib.resources.abc`가 3.10 타깃에서 없음). 모듈별 override 3줄로 바꿔 범위를 좁힌다.
- mcp/ui override를 제거하면 1개가 나온다(`mcp/artifacts/transport.py:191` `ToolResult`가 Any). override를 그 모듈 하나로 좁힌다.
- `warn_unreachable`은 26개(15파일)다. limn에도 없으므로 보류한다.
- 명령 통일: CI·pre-commit 모두 `uv run mypy`(인자 없음). 로컬 환경 차이(6개 오류)를 없애려면 dev 그룹에 `"dartwork-mpl[mcp,ui,notebook]"` 자기 참조를 넣어 `uv sync`만으로 extras가 깔리게 한다. 도입 전에 uv 지원과 `test-no-extras` job(`uv sync --no-dev`)이 영향받지 않는지 검증한다.
- tests는 mypy 대상이 아니다(`mypy tests`는 2137개). limn과 같다.

### 3.5 경계 검사기 `tools/check_boundaries.py` + `tests/architecture/`
- 구조: limn과 같은 AST 전용 검사(앱 코드를 import하지 않음)로 만든다. 상수는 `ENTRY_POINTS`(`dartwork_mpl/__init__`, `cli`, `ui.__main__`, `mcp.server`), `SLICES`, `SHARED`(`_helpers`, `_luminance`, `units`, `config` 후보), `ALLOWED_DEPENDENCIES`(`{(src,dst): "업무상 이유"}`), `DECISION_MODULES`(source 감사 결과로 채움), 이관 기간용 `DEBT`(현재 위반을 사유와 함께 열거하고, 줄기만 허용)다.
- 판정: (a) 다른 단위의 비공개 모듈·`_name` import, (b) shared가 slice에 닿는 경로(shared 경유 포함), (c) 단위 간 순환(지연 import 포함, Tarjan SCC), (d) 목록에 없는 단위 간 의존, (e) decision module이 다른 기능의 공개 표면까지 포함해 import하는 경우, (f) 슬라이스 내부 import 통과.
- `tests/architecture/test_boundaries.py`: 위 다섯 위반을 각각 주입해 실패를 확인하고, 슬라이스 내부 import 1건이 통과하는지 확인한다. 저장소 전체 검사는 `DEBT`를 제외하고 0이어야 한다.
- 현재 위반 측정(`/tmp/dmpl-audit-scripts/{graph,deep}.py`):
  - 단위 간 비공개 import 22건(16쌍). 예: `diagnostics→_colors._loader/_families`, `validate→_luminance._*`·`_colors._conversion`, `_colors→style._style_lock`, `style→_colors._semantic`, `icon→style._did_you_mean`, `mcp→_colors._loader`, `validate_fixes→helpers.quality`.
  - 순환: top-level import만 보면 `{__init__, templates}`. 지연 import를 넣으면 `{_colors, _luminance, style}`와 `{__init__, templates, validate_fixes}`.
  - 패키지 내부에서 루트 facade를 import하는 곳 9건(7파일): `config`, `mcp/execution`×2, `mcp/prompts`×2, `mcp/resources`, `templates/diverging_bar`, `ui/templates/simple`, `validate_fixes`.
  - `util`이 `annotation, io, layout, prompt, scale, _colors`를 import하므로, shared로 분류하면 6건이 더 생긴다.
- CI: lint job에 `uv run python tools/check_boundaries.py`를 추가한다. 테스트로도 실행되므로 소유자는 검사기 하나다.

## 4. 분할 PR 제안 (도구·테스트 배치 부분)

| # | PR | 범위 | 위험 | 검증 | 소스 이동 전 필수 |
|---|---|---|---|---|---|
| 0 | main 녹색화 | `test_input_access.py` ERROR 원인 수정(별도 이슈) | 중 | CI 전 job 녹색 | 예 (대조 기준선) |
| 1 | 테스트 id 대조 도구 | `tools/test_id_map.py` + `tests/tools/test_test_id_map.py` (limn 이식) | 낮음 | 자체 테스트, `main` 대비 lost/dup 0 | 예 |
| 2 | 수집 기반 전환 | 루트 `conftest.py` 승격, `tests/support/` 신설(oracle·robustness·mcp input helper 이동), importlib·testpaths·pythonpath, CI·release `pytest` 무경로, coverage omit, wheel exclude + `test_packaging` | 중 (sys.path 부트스트랩, junit 이름) | collect 6887 동일(#1 도구), `uv build` 후 tests 0, `check_integration_junit` 통과 | 예 |
| 3 | mypy 정리 | `files`, exclude 정규식, `exhaustive-match`, `strict_equality`, override 축소 3+1, dev 그룹 extras 자기참조, 명령 `uv run mypy` 통일 | 낮음 | all-extras·기본 `uv sync` 양쪽에서 0, 잘못된 인자 주입 시 실패, `test-no-extras` 녹색 | 예 (동거 테스트가 strict에 걸리지 않게) |
| 4 | 경계 검사기 report-only | `tools/check_boundaries.py`, `tests/architecture/test_boundaries.py`(주입 5종+내부 통과), `DEBT`에 현재 22+순환+facade 위반 등재, CI 단계 추가 | 중 (슬라이스 목록이 source 감사에 의존) | 주입 5건 실패·1건 통과, 저장소 실행 0(`DEBT` 제외), `DEBT` 증가 시 실패 | 예 (allowlist 모드) |
| 5 | ADR: 루트 tests 끝 상태 | limn ADR-0012 대응: `contracts/ docs/ tools/ architecture/ support/`와 슬라이스 `tests/` 규칙 | 낮음 | 리뷰. 200줄 이하 | 예 (이동 승인 근거, 기존 테스트 이동은 승인 필요) |
| 6 | 루트 재배치 | 1.1표의 contracts·docs·tools·architecture 하위 디렉터리로 `git mv`, `check_integration_junit.py` 보호 목록 갱신, CLAUDE.md/AGENTS.md의 `tests/test_shipped_colors_hash.py`·ratchet 경로 갱신 | 낮음 | #1 도구 lost/dup 0, junit 검사 통과 | 아니오 |
| 7.x | 슬라이스별 동거 이동 | 단위마다 1 PR(`_colors` 30, `mcp` 31, `ui` 11, `validate` 5, 단일 모듈 묶음): `src/dartwork_mpl/<unit>/tests/`, color fixture conftest | 낮음 | id 대조 0, coverage 동일, wheel tests 0 | 소스 이동과 같은 PR 또는 직전 |
| 8 | ruff D 도입 | D100–D107 select, tests per-file-ignore, 위반 101개 수정(승인 시) 또는 파일 목록 ratchet | 낮음 | `ruff check` 0, 위반 주입 시 실패 | 아니오 (동거 이동 뒤라 per-file glob이 확정된다) |
| 9 | 정리 | pre-commit job 이름 "changed files" 정정, 존재하지 않는 `colors/_generated` exclude 수정, docs·release의 색 산출물 검사 3중 중복을 한 스크립트로 묶기 | 낮음 | CI 녹색 | 아니오 |
| 10 | 경계 강제 전환 | 소스 이동이 끝날 때마다 `DEBT` 축소, 마지막에 `DEBT={}` | — | `DEBT` 빈 상태로 검사 통과 | 소스 이동 이후 |

메모:
- 새 문서를 `docs/development/structure-refactor/`에 둘 때 `docs/conf.py` `exclude_patterns`에 이 경로가 없다. 그대로 두면 `sphinx-build -W`가 toctree 미포함 경고로 실패할 수 있으므로, exclude에 추가하거나 `orphan: true`를 붙인다.
- 미커밋 anti-pattern ratchet(`tests/test_antipattern_ratchet.py`)은 별도로 병합된다. 이 계획은 그것을 `tests/contracts/` 또는 `tests/architecture/`로 옮기는 경로 갱신만 #6에 포함한다.

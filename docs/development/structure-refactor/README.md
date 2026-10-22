---
orphan: true
---

# 구조 리팩터 계획 (2026-10-22 ~)

결정은 [ADR 0005](../../adr/0005-capability-slices-and-test-colocation.md)에 있다. 이 문서는 실행 순서,
PR마다 통과해야 할 기계 판정, 진행 상태를 맡는다. 근거는 `audit/`에 있는 영역별 감사 6개다
([colors](audit/colors.md), [core](audit/core.md), [lint-validate](audit/lint-validate.md), [mcp](audit/mcp.md),
[ui-cli](audit/ui-cli.md), [tests-tooling](audit/tests-tooling.md)). 감사 대상은 main `0e88b810`이다.

## 진행 규칙

1. **PR 하나에 한 가지 일만 한다.** 파일 이동과 타입 변경을 같은 PR에 넣지 않는다. 변경은 800줄 이하를 목표로 한다.
   순수 이동은 `git diff -M`으로 rename이 보여야 한다.
2. **매번 최신 main에서 시작한다.** 브랜치를 만들기 전에 `git fetch`를 하고 `origin/main`에서 분기한다.
   머지 직전에도 다시 rebase하고 판정을 다시 돌린다.
3. **다른 작업과 겹치지 않게 한다.** 시작 전에 `gh pr list`와 최근 24시간의 `git log origin/main -- <대상 경로>`를 확인한다.
   대상 경로를 건드리는 열린 PR이 있으면 그 영역은 미루고 다른 영역을 먼저 진행한다.
   `mcp/tools.py`, `lint.py`, `style.py`, `io.py`는 변경이 잦으므로 PR을 짧게 열고 바로 머지한다.
4. **진행 표는 머지된 PR을 묶어 갱신한다.** 이동 PR마다 이 파일을 고치면 병행 PR끼리 충돌하므로, 상태와 PR 번호는 별도 문서 PR로 모아 적는다.

## PR마다 통과해야 할 판정 (외부 판정기)

| 판정 | 명령 | 기준 |
| --- | --- | --- |
| lint·format | `uv run ruff check . && uv run ruff format --check .` | 0 |
| 타입 | `uv run mypy` (G3 이후. 그 전에는 `uv run mypy src/dartwork_mpl/`, all-extras 환경) | 0 |
| 테스트 | `uv run pytest -q -n auto` (전체) | 실패 0 |
| 테스트 id 보존 | `uv run python scripts/test_id_map.py --ref origin/main` (G1 이후) | lost 0, duplicated 0 |
| 경계 | `uv run python scripts/check_boundaries.py` (G4 이후) | 위반 0, `DEBT`는 증가 금지 |
| 색 동결 | `tests/test_shipped_colors_hash.py`, `python -m dartwork_mpl._colors._build --check` | 통과. digest 재생성 금지 |
| MCP 동결 | `tests/test_mcp.py`, discovery 비교 테스트, artifact digest 테스트 | 통과. 기대값 재생성 금지 |
| 패키징 | `uv build --wheel` 후 wheel 안 `/tests/` 0 (G2 이후 테스트로 고정) | 0 |
| PR CI | GitHub Actions(PR은 ubuntu-24.04) | 전부 녹색 |

## 단계와 PR 목록

### 0단계 — 결정과 계획

| ID | 내용 | 상태 |
| --- | --- | --- |
| S0 | ADR 0005, 이 계획, 감사 6개 | #518 |

### 1단계 — 게이트 (소스 이동 전에 모두 들어가야 한다)

| ID | 내용 | 상태 |
| --- | --- | --- |
| G1 | `scripts/test_id_map.py`: collect-only id를 기준 ref와 비교(lost/duplicated/new) + 자체 테스트 | #519 |
| G2 | 동거 수집 기반: 루트 `conftest.py`로 격리 fixture 승격, `tests/support/`, `--import-mode=importlib`, `testpaths=["tests","src/dartwork_mpl"]`, CI·release `pytest` 경로 제거, wheel `**/tests/**` exclude + 패키징 테스트, coverage omit | #522 |
| G3 | mypy: `files`, 동거 테스트 exclude, `exhaustive-match`, `strict_equality`, 완화 override를 모듈 단위로 축소, dev 그룹에 extras, 명령 `uv run mypy` 통일 | #520 |
| G4 | `scripts/check_boundaries.py` + `tests/architecture/test_boundaries.py`(주입 위반 5종 실패, 슬라이스 내부 import 통과), 현재 위반 `DEBT` 등재(검사는 pytest가 실행) | #521 |
| G5 | 루트 테스트 재배치: `tests/{contracts,docs,tools,architecture}/`, `scripts/check_integration_junit.py` 보호 목록과 CLAUDE.md·AGENTS.md 경로 갱신 | 대기 |

### 2단계 — 이동 (영역마다 순서대로. 영역끼리는 병행할 수 있다. 각 PR은 그 슬라이스의 테스트도 함께 옮긴다)

**core** ([감사](audit/core.md) §5)

| ID | 내용 | 상태 |
| --- | --- | --- |
| C1 | `_helpers` 해체 → platform `_figure_geometry`, `create_parent_path`는 소유자에게 | #525–#528 |
| C2 | platform `_rc`(rcParams 잠금, did_you_mean): `style`⇄`_colors`, `icon`→`style` 순환 제거 | #525–#528 |
| C3 | style 표면 `preset_names`/`preset_chain`: lint·mcp·_colors의 `presets.json` 직접 읽기 제거 | 대기 |
| C4 | `font/` 패키지, diagnostics의 `_FONT_DIR` 누출 제거(공개 `get_font_dir`). **icon은 흡수하지 않음**: 이름(`ensure_loaded`)과 변경 이유가 달라 잘못된 추상화 | #525–#528 |
| C5 | `units/` 패키지, `col1/col2`를 units로 | #525–#528 |
| C6 | `layout/` 패키지(이동만), 테스트 전용 `_measure_overflow`를 테스트 지원 코드로 | #525–#528 |
| C7 | `annotation/` 패키지, `make_offset` 흡수. `optimize_legend`는 C11로 이월 | #525–#528 |
| C8 | `formatting/` 패키지 + `set_decimal` 흡수 + `__all__` | #525–#528 |
| C9 | `io/` 패키지. ui는 U5, mcp는 M6에서 `util` 대신 소유자 import | #525–#528 |
| C10 | `util.py` → shim 전용, `mix_colors`/`pseudo_alpha` → `_colors` | 대기 |
| C11 | `helpers/` → shim 전용, 각 항목을 소유 슬라이스로 | 대기 |
| C13 | 테스트를 가진 단일 파일 슬라이스 `scale`·`tokens`·`icon`·`explore`를 같은 이름 패키지로(테스트 동거). `config`·`agent`는 전용 테스트가 없어 유지 | #526 |
| C12 | `templates`의 루트 import 제거, `__init__` 배선화(`_compat.py`, twinx 패치는 style로) | #525–#528 |

**colors** ([감사](audit/colors.md) §5. `_compatibility_metrics.py`는 움직이지 않는다)

| ID | 내용 | 상태 |
| --- | --- | --- |
| K1 | `_luminance`를 `_colors/contrast`로 흡수해 순환 제거 | #533 |
| K2 | `construction/`·`verify/` 순수 이동(`build/`는 pytest `norecursedirs`에 걸려 개명), `_build.py`는 진입점만 | #533 |
| K3 | `model/`·`contrast/` 슬라이스, validate의 `_conversion` 비공개 접근을 표면으로 | #533 |
| K4 | `catalog/`·`registry/`·`families_api` 슬라이스, mcp·helpers·style import를 표면으로 | #533 |
| K5 | `diagnostics` 재배치(색은 `_colors/diagnostics`, 폰트는 font로), 진입점은 재노출만 | #533 |

**lint·validate** ([감사](audit/lint-validate.md) §5)

| ID | 내용 | 상태 |
| --- | --- | --- |
| L1 | `lint.py` → `lint/` 패키지(catalog, syntax, detect, report, fix, migrate) 순수 이동 | #529 |
| L2 | `validate_fixes.py` → `validate/fixes.py`·`agent_requirements.py` + shim(`__all__` 명시) | #529 |
| L3 | check마다 fix handler를 `validate/checks/<check>.py`로, 레지스트리 하나로 | #529 |

**ui** ([감사](audit/ui-cli.md) §5)

| ID | 내용 | 상태 |
| --- | --- | --- |
| U1 | 와이어 골든: 라우트 응답 키, `/api/descriptors`, 상태 파일 바이트 고정 | #530 |
| U2 | 호출자 없는 코드 제거. `save_preset`/`load_presets`는 `docs/migration.md`가 대체 API로 안내해 유지(H8) | #530 |
| U3 | `ui/platform/`(json, fs, access) 이동 | #530 |
| U4 | `params/`·`page/`·`scaffold/` 이동 | #530 |
| U5 | `state/`·`saving/`·`render/`·`script/` + 슬라이스별 router·GRANTS, `ui.py`는 mount만 | #530 |
| U6 | `prompt/` 패키지가 `asset/prompt` 경로의 유일한 소유자(lint·mcp는 표면 사용) | 대기 |

**mcp** ([감사](audit/mcp.md) §5. 배선 표 네 파일은 데코레이터·docstring을 바이트 그대로 둔다)

| ID | 내용 | 상태 |
| --- | --- | --- |
| M1 | `_platform/`(process, assets) 이동 | #532 |
| M2 | `execution/`, `plot_data/`(repair) 패키지 이동 | #532 |
| M3 | `_validate_*` 18개 → `plot_data/validators.py` | #532 |
| M4 | `docs_fetch/`·`colors/`·`recommend/`·`catalog/` 본문 이동, tools.py는 위임만 | #532 |
| M5 | `lint/`·`templates/` 이동. 두 렌더러는 실행부만 공유, 응답 구성은 분리(tier·`fell_back` 등이 다름) | #532 |
| M6 | `guides/`: resources·prompts 본문 이동 | #532 |

### 3단계 — 타입 (내부 표현만. 와이어·공개 반환 형태는 바이트 동일)

| ID | 영역 | 내용 | 상태 |
| --- | --- | --- | --- |
| T1 | core | `tokens` 파서(cast 제거, 손상 JSON을 이름 붙은 결과로, fallback 중복 제거) | 대기 |
| T2 | core | annotation 내부 Literal·`LegendPlacement` 결과(공개 속성 유지), layout `Margin` 값 타입·순수 solve 분리 | 대기 |
| T3 | core | style `Locale` 파싱(이름 부분문자열 판정 제거), io `SaveFormat` 내부 파싱 | 대기 |
| KT1 | colors | `Family`를 kind별 variant union으로(`.kind ==` 분기 13곳 → `match`) | 대기 |
| KT2 | colors | gate·비교 결과 variant(`GateViolation`, `ExactMismatch`), `to_payload()` 키 불변 | 대기 |
| KT3 | colors | `load_color_v6_ssot` → 타입 `ColorAuthority`(cast 92건 제거), 2개 PR로 나눔 | 대기 |
| KT4 | colors | 가변 상수 동결(`MappingProxyType`), `_freeze/_thaw` 중복 제거 | 대기 |
| LT1 | lint | 내부 `Severity`·owner kind Literal, `_Detector` union(공개 `Rule` 필드 유지), 이름 있는 실패 | 대기 |
| LT2 | lint | `_builtin_matches`를 rule id → 탐지 함수 표로 분해, 카탈로그 정합 테스트 | 대기 |
| LT3 | validate | check별 detail TypedDict, `CheckCompleted`/`CheckFailed` 내부 결과 | 대기 |
| UT1 | ui | 라우트별 요청 파서(`parse_request` 문자열 분기, `assert`·`cast` 제거) | 대기 |
| UT2 | ui | 저장 상태 `StoredConfig`/`Preset` 파싱(cast 9건 제거) | 대기 |
| UT3 | ui | `ParamDescriptor` → `Control` variant union | 대기 |
| UT4 | ui | 실패 타입에서 HTTP `status_code` 분리, 가장자리 `match` 한 곳 | 대기 |
| MT1 | mcp | 실행 결과 variant(`Passed`/`Incomplete`/`ExecFailed`/`LintBlocked`/`NoFigure`/`TimedOut`) | 대기 |
| MT2 | mcp | 템플릿 렌더 결과 union | 대기 |
| MT3 | mcp | plot_data validator를 `parse_<type>(raw) -> Parsed | Invalid`로(메시지 문자열 동결) | 대기 |
| MT4 | mcp | docs fetch 거절을 값으로, artifacts 표면 축소, unused ignore 제거 | 대기 |

### 4단계 — 마감

| ID | 내용 | 상태 |
| --- | --- | --- |
| D1 | ruff D100–D107(테스트는 D100–D101) 활성, 누락 docstring 101개 작성 | 대기 |
| D2 | `DEBT = {}`로 경계 검사 강제 전환 | 대기 |
| D3 | 정리: pre-commit job 이름, 없는 `colors/_generated` exclude, 색 산출물 검사 3중 중복 | 대기 |

## 진행 중 정해진 도구 규칙

- 경계 검사기: `SHIMS`(호환 shim → 소유 단위, shim의 `__all__`이 두 번째 표면), `PINNED`(경로가 고정된 모듈 → 소유 단위), 자기를 감싼 부모 패키지는 의존으로 세지 않음. 셋 다 주입 테스트가 있다.
- 스택 PR은 main 대상이 아니면 CI가 돌지 않는다. 끝 PR을 main 대상으로 열어 한 번에 검증하고 merge commit으로 머지한다.

## 사람 결정 대기 (이 리팩터가 스스로 바꾸지 않는다)

| ID | 내용 | 이유 |
| --- | --- | --- |
| H1 | main push CI가 빨갛다. self-hosted runner `ml-main`의 작업 디렉터리 조상이 0775(group-writable)라서 `tests/mcp/artifacts/conftest.py`의 조상 권한 검사가 실패한다. PR CI(ubuntu)는 녹색이다 | 머신 설정 변경이거나 보안 검사 완화라서 사람이 정해야 한다 |
| H2 | `dartwork-mpl-ui init --example complex`는 템플릿이 삭제돼 `FileNotFoundError`. 비어 있지 않은 대상은 exit 0 | CLI 플래그 변경(선택지 제거 또는 템플릿 복원) |
| H3 | MCP discovery 스캐너를 레지스트리 기반으로 바꿔 tool 정의를 슬라이스로 옮기기 | ADR 0001 A1 동결 도구 수정 |
| H4 | `_colors/_compatibility_metrics.py` 이동·정리 | 출하 자산에 경로·SHA 고정 |
| H5 | 공개 파라미터 `Literal` 축소, `lint.Rule` detector union, `Issue.line` non-Optional, `VisualWarning` frozen | 공개 정적 계약 변경 |
| H6 | src 안에 소비자가 없는 `_colors/_metrics.py`의 이전·제거 | docs 스크립트가 사용 |
| H7 | CLAUDE.md·AGENTS.md의 "18 tools"(실제 19개) 문구 | 별도 문서 수정 |
| H8 | `ui/_config.py`의 레거시 `save_preset`/`load_presets` 제거 | `docs/migration.md`가 대체 API로 안내 |
| H9 | ADR 0001·0003이 적은 모듈 경로(`_colors/_gates.py` 등)는 이동 전 경로다. 수락된 ADR 원문은 고치지 않는다 | 현재 위치는 `scripts/check_boundaries.py`와 `audit/colors.md` |

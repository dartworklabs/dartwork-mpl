---
orphan: true
---

# 구조 감사: `src/dartwork_mpl/mcp/`

기준: `code-implement` 스킬(structure/modeling/python/integration)과 limn(`src/limn/<feature>/tests`, `tools/check_boundaries.py`, ADR 0009/0010/0012). 대상 커밋 `0e88b810`(main). 읽기 전용 감사.

## 1. 현재 구조 요약

| 모듈 | 줄 | 역할 | `__all__` |
|---|---:|---|---|
| `tools.py` | 2069 | 16개 tool 클로저 + 18개 `_validate_*` + 소스 스캔 discovery + GitHub fetch | `register_tools` |
| `artifacts/store.py` | 1059 | 번들 디스크 저장소(FD, 원자 게시, 만료 정리) | 없음 |
| `artifacts/inputs.py` | 800 | 보존 입력 저장소·트랜잭션 | 있음 |
| `artifacts/input_policy.py` | 660 | 입력/리비전 파싱(순수) | 없음 |
| `data_repair.py` / `_data_repair_json.py` | 674 / 176 | `validate_plot_data(report=True)` 보고서 | 3개 / 없음 |
| `artifacts/transport.py` | 515 | render_plot·get_plot_artifact·delete_plot_inputs·5 resource 템플릿 | 없음 |
| `artifacts/policy.py` | 500 | 순수 파싱·값(ArtifactId, Manifest, 실패 변형) | 없음 |
| `execution.py` / `_capture.py` | 473 / 410 | 자식 프로세스 실행·검증 / 출력 캡처 | 10개 / 없음 |
| `prompts.py` / `resources.py` | 421 / 234 | 2 prompt / 10 static + 4 template resource | 1 / 1 |
| `artifacts/input_access.py`·`input_io.py`·`lifecycle.py`·`delivery.py`·`input_cleanup.py`·`__init__.py` | 397·382·279·297·200·144 | 입력 권한·워커 IO·세션 수명·배달 흐름·정리·표면(65개 이름) | 혼재 |
| `server.py` / `__init__.py` / `_assets.py` | 32 / 9 / 54 | 진입점 / `mcp` / 번들 자산 경로 봉쇄 | 1 / 1 / 2 |

합계 9,785줄. 테스트 약 17,000줄: `tests/mcp/{artifacts,data_repair,agent_loop}`(트리) + 루트 `tests/test_mcp*.py` 8개 + `test_integration.py`·`test_docstring_catalogs.py`·`test_docs_mcp_tools.py`.

**내부 import 그래프**(비순환): `server → tools, resources, prompts, artifacts`; `tools → _assets, data_repair, execution(지연)`; `resources → _assets`; `execution → _capture`; `data_repair → _data_repair_json`; `artifacts.transport → execution, artifacts.{delivery,inputs,lifecycle,policy,store,input_access,input_policy}`; `artifacts.delivery → execution`. `artifacts` 내부는 `policy`를 바닥으로 한 DAG.

**영역 밖으로 나가는 import**: `dartwork_mpl.lint`(lint/format_report/apply_lint_fixes/migrate_legacy_code, tools.py:457-773, execution.py:172), `dartwork_mpl.prompt.find_template`(tools.py:544), `dartwork_mpl.suggest_chart_type`(tools.py:981), `dartwork_mpl.util.mix_colors/get_prompt`(tools.py:383, resources.py:16). **사설 이름 교차**: `.._colors._loader.COLOR_LIBRARIES`(tools.py:402, resources.py:137).

**영역 안으로 들어오는 의존**: `cli.py:28 from .mcp.server import mcp`. 그리고 import 없는 **경로 결합** 둘: `_colors/_catalog.py:1050 scan_mcp_discovery()`가 `tools.py`·`resources.py`·`prompts.py`·`artifacts/transport.py`를 **파일 경로로 AST 스캔**하고(ADR 0001 A1 `mcp_discovery` 동결 비교), `tools.py:116-133 _discover_*`가 같은 네 파일을 정규식으로 스캔해 `dartwork_mpl_info`에 싣는다.

**테스트의 사설 접근**: `register_tools` import 122회(tool이 클로저라 mock `FastMCP`로 등록해야만 호출 가능), `_tools._validate_*` 약 60회, `"dartwork_mpl.mcp.tools._fetch_raw_github"` 문자열 monkeypatch 3회, `disk._write_file/_remove_owned/_root_ancestry`, `input_io._worker_code`, `_capture._Capture`, `execution._source_timeout_error`, `tools._TEMPLATE_DIR/_SUGGEST_TO_TEMPLATE/_discover_*`, `resources._TEMPLATE_DIR/_MPLSTYLE_DIR`.

## 2. 파일트리 결함

1. **`tools.py`는 변경 이유 9개를 한 클로저에 담는다**(`register_tools`, 271-1440): 문서 fetch(`fetch_github_document`, HTTP I/O 150-269), 색 조회(`get_color_value`·`mix_colors`·`list_color_families`), lint(`lint_*`·`apply_lint_fixes`·`migrate_legacy_code`), 템플릿(`find_template`·`render_template`·`render_template_advanced`·`compose_layered_plot`), 플롯 실행 검증(`validate_generated_plot`), 데이터 검증(`validate_plot_data` + 1446-2069 validators 620줄), 추천(`suggest_chart_type` + `_SUGGEST_TO_TEMPLATE`), 카탈로그(`dartwork_mpl_info` + discovery 89-147).
2. **co-change 증거**(`git log -60 -- mcp`): `tools.py` 52회 단독 최다. `tools+resources` 18, `tools+prompts` 14 — 색 체계 리팩터(#420, 63f6a988, 98adf099, ddcde17e)가 색 tool·`palette/colors` resource·prompt 문구를 함께 바꾼 흔적이다. 이유가 "색"인데 파일 축은 "MCP 프리미티브 종류"(tool/resource/prompt)인 **layer-grouped** 배치.
3. **같은 이유의 복제**: `render_template`(594-740)과 `render_template_advanced`(1136-1300)가 러너 문자열·`run_child`·PNG 수집·오류 dict를 거의 그대로 복제. `suggest_chart_type`은 `_TEMPLATE_DIR / f"{recommended}.py"`(≈993)로 템플릿 저장 레이아웃을 직접 해석해 `_assets` 봉쇄 경로를 우회.
4. **`dartwork_mpl_info`**(1303-1440)가 `asset/mplstyle/presets.json`을 경로로 읽고 실패 시 하드코딩 목록으로 폴백 — 스타일 레지스트리 지식 중복.
5. **`execution.py`의 표면 누수**: `__all__`이 `_capture`의 `diagnostic`·`publish_png`·`run_child`·`strip_diagnostic`을 재수출(execution.py:11-22)하고 tools.py가 그 경로로 가져다 쓴다.
6. **`artifacts/__init__.py` 표면 65개** — `transport.register_artifacts`·`configure_store`·`ArtifactRuntime`만 server가 쓰고 나머지는 테스트용. 표면이 아니라 배럴.
7. **테스트가 코드와 멀다**: 슬라이스별 테스트가 루트 `tests/test_mcp*.py`와 `tests/mcp/*`로 갈리고, `test_mcp.py`(1327줄) `TestMcpTools`가 모든 tool을 한 클래스에서 검증. 경계 검사(`check_boundaries`/import-graph 테스트)는 없다.
8. 문서 드리프트: `CLAUDE.md`/`AGENTS.md`는 "18 tools"라 하지만 live는 19(`test_artifact_discovery.py:64` `(19,10,9,2)`, ADR 0004의 `delete_plot_inputs`).

## 3. 타입 결함

파일별 수(`Any` / `dict[str, Any]` / `cast` / `type: ignore` / `raise`):

| 파일 | Any | dict[str,Any] | cast | ignore | raise |
|---|---:|---:|---:|---:|---:|
| tools.py | 29 | 28 | 0 | 0 | 14 |
| execution.py | 9 | 8 | 0 | 0 | 5 |
| artifacts/transport.py | 11 | 4 | 0 | 2 | 1 |
| artifacts/policy.py | 5 | 2 | 0 | 0 | 29 |
| artifacts/lifecycle.py / store.py / _capture.py | 3 / 2 / 1 | 0 / 1 / 0 | 0 / 0 / 1 | 0 | — |

- **문자열 status + dict 결과(최대 결함)**: `execution._run`이 `dict[str, Any]`를 돌려주고 `"status"`가 `ok|validation_incomplete|exec_error|lint_blocked|no_figure|timeout`(execution.py:195-469). `export_plot`은 그 dict에서 사설 플래그 `_export_failed`·`_artifact_logs_too_large`를 `pop`하고 `report["status"] in {...}`로 변형을 고른다(133-139). 변형 타입(`ExportedPlot`/`ExecutionRejected`/`ExportRejected`)은 있으나 페이로드가 여전히 `report: dict[str, Any]`(31-55)라 변형별 필드가 표현되지 않는다. `LogLimitRejected(ExecutionRejected)`(45)는 변형 상속이라 `isinstance` 순서 의존.
- **tools.py 응답 dict**: `render_template`/`_advanced`/`compose_layered_plot`가 `status: ok|unknown_template|timeout|render_error|fell_back|invalid_tier`인 dict를 직접 조립(625-732, 1066-1290). `png_base64: None`처럼 변형에서만 의미 있는 필드를 None으로 채움. 이 dict는 **동결된 wire 형태**이므로 바꿀 수 없고, 안쪽에 변형 타입을 두고 가장자리에서 직렬화해야 한다.
- **validate-not-parse**: 18개 `_validate_*(data: dict[str, Any]) -> str`이 성공을 `"✅ ..."` 접두 문자열로, 실패를 개행 결합 문자열로 표현. 미파싱 형태로 인한 예외를 `except (TypeError, KeyError, ValueError, AttributeError)`(tools.py:931)로 일괄 흡수.
- **예외로 표현된 예상 결과**: `_fetch_raw_github`가 비-raw URL·크기 초과·리다이렉트 한도를 `ValueError` 14회로 던지고 tool이 그대로 전파(docstring "Raises ValueError", 307). `artifacts`의 `raise` 대부분은 `__post_init__` 신뢰 데이터 가드(policy 19/29, input_policy 16/48)와 파서 내부 — 파서 시그니처는 값(`parse_manifest -> Manifest | CorruptArtifact`, `parse_revision -> Revision | None | InvalidRequest`)이라 기준 충족.
- **wire DTO와 도메인 혼재**: `data_repair._Inspection.issues/changes: list[dict[str, _Json]]`에 `code` 문자열과 `**details`를 쌓아(175-191) 도메인 탐색 중에 wire 레코드를 만든다. `build_provenance -> dict[str, object]`(input_policy.py:598).
- **`Any` 경계**: `ArtifactRuntime.bind(self, mcp: Any)`(lifecycle.py:127), resource 핸들러 `-> Any`(transport.py:406-476), `policy._exact_fields(raw: Any)`(423, `object`로 충분).
- **mypy**: strict + `exhaustive-match` 실행 결과 2건(transport.py:45-46 unused `type: ignore`). `mcp.*`에 `disallow_untyped_decorators`/`disallow_subclassing_any` 완화 override(pyproject.toml:280). ruff D100-D107은 통과하나 프로젝트 설정엔 미포함, `exhaustive-match` 미설정.
- **`__all__` 누락**: `_capture`, `_data_repair_json`, `artifacts/{store,policy,input_policy,transport,delivery,input_cleanup}`.

## 4. 제안 목표 구조

**고정점(인터페이스)**: `dartwork_mpl.mcp`·`dartwork_mpl.mcp.server`(`mcp` 객체, `python -m`, docs/integrations/mcp_server.md:190/254/587), tool/resource/prompt 이름·**순서**(ADR 0001 A1 + 0003 + 0004, `_catalog.scan_mcp_discovery`), 인자 스키마, docstring(=tool 설명), 응답 형태, artifact v1. 등록 순서는 슬라이스와 교차한다(lint→templates→lint→templates→lint→…). 그래서 **슬라이스별 `register_*`로 쪼개면 순서가 깨진다.**

결정: `tools.py`·`resources.py`·`prompts.py`·`artifacts/transport.py`를 **wire 표(진입점 배선)** 로 남긴다. 데코레이터·시그니처·docstring만 두고 본문은 슬라이스 함수 한 줄 위임으로 줄인다. 스캐너 두 개와 동결 순서가 그대로 유지된다. 스캐너를 레지스트리 기반으로 바꾸는 일은 `_colors/_catalog.py`(색 동결 도구)를 건드리므로 별도 사람 결정으로 남긴다(PR 범위 밖).

```
mcp/
  __init__.py, server.py         # 진입점: 자원 생성·등록만 (경로 불변)
  tools.py resources.py prompts.py   # wire 표: 데코레이터+docstring+위임 (경로 불변, 스캔 대상)
  _platform/  process.py(←_capture) assets.py(←_assets)  tests/   # 어떤 슬라이스도 import 안 함
  docs_fetch/  __init__: fetch_raw_document, FetchRefused 변형          tests/
  colors/      __init__: color_value, mix, list_families, palette_payload  tests/
  lint/        __init__: lint_text, lint_records, fix_code, migrate_code    tests/
  templates/   __init__: find, render(tier) -> Rendered|Unknown|TimedOut|RenderFailed|FellBack,
               compose, template_uri, exists(stem, tier), style_payload     tests/
  plot_data/   __init__: validate_data(plot_type, raw) -> Valid|Invalid|Unparsable|NoValidator,
               build_data_repair_report, serialize_data_repair_report
               (validators/, repair.py, repair_json.py)                      tests/
  execution/   __init__: validate_plot, export_plot, ExportedPlot, ExecutionRejected,
               LogLimitRejected, ExportRejected                              tests/
  recommend/   __init__: suggest(...)                                         tests/
  guides/      __init__: guide_text, api_index, api_entry, prompt bodies       tests/
  catalog/     __init__: info_payload()  (discovery 스캔 소유)               tests/
  artifacts/   (현행 유지) __init__: register_artifacts, configure_store, ArtifactRuntime  tests/
```

**허용 교차 의존(한 방향, 사유)**:
- `artifacts → execution`: 번들은 검증된 단일 실행의 산출물이다. 셸(`delivery`)에서만 import하고, 결정 모듈(`policy`·`input_policy`)은 `execution`을 모른다.
- `recommend → templates`(`exists`, `template_uri`): 추천 결과가 템플릿 URI로 돌아가야 recommend→pull 루프가 닫힌다. `_SUGGEST_TO_TEMPLATE`는 recommend 소유.
- `templates → _platform.process`, `execution → _platform.process`, `resources/templates → _platform.assets`: 메커니즘 의존.
- `catalog`는 슬라이스를 import하지 않고 wire 표 파일만 스캔한다(현행 동작). `server`만 모든 슬라이스를 본다.
- 금지: `_platform → 슬라이스`, `execution → artifacts`, 슬라이스 간 사설 모듈 import, `.._colors._loader` 직접 접근(색 영역 공개 표면으로 교체 — colors 감사와 조율).

**테스트 위치**: limn ADR 0012를 따라 `mcp/<slice>/tests/`. 단 이는 저장소 전체 결정(`testpaths=["tests"]`, wheel `packages`에 테스트 포함 여부, `scripts/check_integration_junit.py`가 테스트 모듈 ID를 `tests.mcp.*`로 고정)이라 **전 영역 공통 PR 0**에서 먼저 정한다. 실서버 계약 테스트(`test_integration.py`, `test_mcp_*_contract.py`, discovery, `test_docs_mcp_tools.py`)는 여러 슬라이스를 함께 관찰하므로 루트 `tests/contracts/mcp/`에 남긴다.

**경계 검사**: limn `tools/check_boundaries.py` 형식으로 `SLICES`, `PLATFORM={"_platform"}`, `ENTRY={"server","tools","resources","prompts","artifacts.transport"}`, 허용 의존 목록(사유 주석), 결정 모듈 목록(`artifacts.policy`, `artifacts.input_policy`, `plot_data.validators`, `plot_data.repair`)을 선언한다. limn이 요구하는 5종 위반 주입 테스트도 함께 둔다.

## 5. 분할 PR 제안

진행 중 충돌: 원격 활성 브랜치 중 mcp를 건드리는 것은 없다(`origin/t3/native-layout-installed-agent-20261021`은 `lint.py`·`prompt.py`만 수정 → lint/templates 슬라이스의 소비 함수와 의미 충돌 가능). 다만 mcp는 최근 30커밋 중 10월에만 6건(#510, #511, #512, a6c3447d, 9b88c62d, #517)으로 **변경 빈도가 가장 높다**. 각 PR은 작게 유지하고 `tools.py`를 한 번에 여러 PR이 잡지 않게 직렬화한다.

| # | 범위 | 파일 | 규모 | 위험 | 검증 |
|---|---|---|---|---|---|
| 0 | (전 영역 공통) 테스트 동거 결정 + `check_boundaries` 골격 + `tests/architecture/test_boundaries.py`. mcp는 현 상태를 debt 목록으로 등록 | pyproject, scripts, tools/ | ~400 | 낮음 | 새 검사 green, 위반 5종 주입 실패 |
| 1 | 순수 이동: `_capture`→`_platform/process`, `_assets`→`_platform/assets`. `execution.__all__`의 재수출 제거, tools는 platform에서 직접 import | 4 src + 테스트 import ~10 | ~150 | 낮음 | `tests/mcp/agent_loop`, `test_mcp_asset_boundary`, `test_mcp_render_smoke` |
| 2 | 순수 이동: `execution.py`→`execution/`, `data_repair*`→`plot_data/`(repair). 테스트 이동(`test_mcp_validation_contract`의 단위 부분, `tests/mcp/data_repair`) | src 3 + tests 4 | ~300(이동) | 낮음; junit 목록 갱신 | 해당 테스트 + `test_check_integration_junit` |
| 3 | `tools.py` 분해 ①: 18개 `_validate_*` → `plot_data/validators.py`(이동만). `validate_plot_data` 클로저는 위임 | tools.py, plot_data/, test_mcp_validators_complete, tool_hardening | ~700 | 중: 테스트의 `_tools._validate_*` 60회 경로 변경 | `test_mcp_validators_complete`, `test_mcp_data_repair_contract`(wire 고정) |
| 4 | ② `docs_fetch/`·`colors/`·`recommend/`·`catalog/` 본문 이동, tools.py는 위임만. `"…tools._fetch_raw_github"` monkeypatch 경로 갱신 | tools.py + 4 slices + 테스트 | ~600 | 중: discovery 스캔은 tools.py에 데코레이터가 남는지로만 결정 | `test_mcp.py`(이름 고정), `test_color_v6_comparison::…frozen_discovery`, `test_artifact_discovery`, `test_docs_mcp_tools` |
| 5 | ③ `lint/`·`templates/` 이동 + `render_template`/`_advanced` 러너 복제를 templates 안 한 함수로 합침(같은 이유). recommend는 `templates.exists`로 `_TEMPLATE_DIR` 직접 접근 제거 | tools.py, resources.py(templates/styles 위임) | ~700 | 중: 응답 dict 바이트 동일성 | `test_mcp_render_smoke`, `test_mcp_heavy_tools`, `test_integration`, `test_mcp_asset_boundary` |
| 6 | `guides/`: resources.py 가이드·api 본문, prompts.py 본문 텍스트를 이동(wire 표 유지) | resources.py, prompts.py | ~500 | 낮음 | `test_mcp.py::TestMcpResources/Prompts`, `test_docstring_catalogs` |
| 7 | 테스트 동거: `test_mcp.py`·`test_mcp_tool_hardening`·`test_mcp_heavy_tools`를 슬라이스별로 분해 이동, `register_tools` mock 경유를 슬라이스 함수 직접 호출로 바꿈(wire 테스트는 contracts에 남김) | tests만 | ~1500(이동, 2회로 분할) | 낮음 | 테스트 수 동일(수집 개수 비교) |
| 8 | 타입: `execution` 결과를 변형별 frozen dataclass(`Passed`/`Incomplete`/`ExecFailed`/`LintBlocked`/`NoFigure`/`TimedOut`) + `TypeAlias` union. dict는 가장자리 `to_wire()`에서만. `_export_failed` 플래그 제거, `LogLimitRejected` 상속 해소 | execution/, artifacts/delivery, transport | ~500 | 높음: 응답 형태·artifact `report.json` v1 바이트 | `test_mcp_validation_contract`, `tests/mcp/artifacts/*`(digest·manifest), `test_input_delivery` |
| 9 | 타입: templates 렌더 결과 변형 union + `match`(exhaustive) 직렬화 | templates/ | ~300 | 중 | PR 5 테스트 |
| 10 | 타입: `plot_data` validators를 parse-don't-validate로(`parse_<type>(raw) -> Parsed | Invalid`), "✅" 문자열은 가장자리에서만 생성, 광역 `except` 제거 | plot_data/ | ~700 | 중: 메시지 문자열 동결 | `test_mcp_validators_complete`, `test_mcp_data_repair_contract` |
| 11 | 타입: `docs_fetch` 거절을 값으로(`Fetched | Refused(reason)`), wire에서는 기존처럼 `ValueError`로 변환(응답 동일) | docs_fetch/ | ~200 | 낮음 | `TestFetchGithubDocumentSSRF` |
| 12 | 정리: `artifacts/__init__` 표면을 server 사용분 3개로 축소(테스트는 모듈 직접 import 허용 목록), 누락 `__all__` 추가, transport unused ignore 제거, `bind(mcp: FastMCP)`, mypy `exhaustive-match` + ruff D100-D107 활성 | artifacts/*, pyproject | ~200 | 낮음 | mypy, 전체 mcp 테스트 |

**인터페이스·동결 기준선에 닿는 지점**(모든 PR 공통 금지선):
- tool/resource/prompt **정의를 네 스캔 파일 밖으로 옮기는 순간** `_catalog.scan_mcp_discovery`와 `_discover_*`가 빈 목록을 내고 ADR 0001 A1 동결 비교가 깨진다. 스캐너 변경은 색 동결 도구 수정이므로 별도 승인이 필요하다(ADR 규칙 3).
- 데코레이터 함수 이름·인자·기본값·docstring 변경 = tool 스키마/설명 변경. 위임 리팩터에서도 바이트 동일 유지.
- `artifacts/policy.py` `ArtifactMember`, manifest/report 키(ADR 0004 결정 목록), `_SCHEMA`/`_DELETE_SCHEMA`는 형태 동결.
- `tests/mcp/data_repair/fixtures/legacy_calls.json`, artifact digest 고정 테스트의 기대값은 재생성 금지.
- `dartwork_mpl.mcp.server` 모듈 경로와 `python -m` 실행은 문서화된 공개 경로.

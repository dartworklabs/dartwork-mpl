---
orphan: true
---
# 구조 감사: ui / cli / explore / config / agent / prompt / asset
기준: `code-implement` 스킬(SKILL·python·structure·modeling·backend-growth)과 limn(`src/limn/<기능>/tests/`,
`tools/check_boundaries.py`, ADR-0009/0010/0012, mypy `strict`+`exhaustive-match`). 대상: `0e88b810`(main).

## 1. 현재 구조 요약

| 모듈 | 줄 | 내용 |
|---|---|---|
| `ui/__init__.py` | 48 | `__all__ = ["ParamModel", "run"]`, `__getattr__`로 지연 로드 (base 설치에서 pydantic 없이 import 되어야 함) |
| `ui/ui.py` | 995 | `run`, `_create_app`(라우트 17개 + 미들웨어 + lifespan), 렌더, 서버 저장, 스크립트 생성, 재시작, **죽은 헬퍼** |
| `ui/_boundary.py` | 880 | 루프백 바인드·요청 권한, `ROUTE_POLICY`, 한도 상수, 경계 JSON 디코더, 출력 경로 파서, 요청 파서, 저장 상태 파서·투영 |
| `ui/_files.py` | 904 | 디렉터리 핸들 기반 루트(`RootScope`), 출력 저장(`prepare_save`/`commit_save`), 고정 상태 파일(`FixedStateStore`) |
| `ui/_config.py` | 485 | `ViewerState`(1–225행) + **레거시 모듈 함수**(227–485행) |
| `ui/_widget.py` | 226 | `ParamDescriptor`(= `/api/descriptors` 와이어 DTO) 파생 |
| `ui/_template.py` / `_styles.py` / `_scripts.py` | 214 / 680 / 708 | HTML 한 페이지를 언어별로 쪼갠 Python 문자열 |
| `ui/_param.py`, `_scaffold.py`, `__main__.py`, `templates/` | 49 / 60 / 105 / 227 | `ParamModel`, `dartwork-mpl-ui init` 스캐폴더 |
| `cli.py` / `explore.py` / `config.py` / `agent.py` / `prompt.py` | 42 / 8 / 123 / 97 / 267 | MCP 콘솔 스크립트 / 재노출 파사드 / `dm.config` 싱글턴 / 번들 에이전트 문서 / 프롬프트 코퍼스·템플릿 검색 |

**ui 내부 import 그래프** (비순환): `ui → _boundary, _config, _files, _param, _template, _widget, ..util`;
`_config → _boundary, _files`; `_files → _boundary`; `_boundary → _param` (+ `_widget` TYPE_CHECKING);
`_widget → _param`; `_template → _scripts, _styles`; `__main__ → _scaffold`.

**나가는 import**: `ui/ui.py:50 from ..util import save_formats` (실소유자는 `io`; `util`은 재노출 허브),
`prompt.py:22 from ._helpers import create_parent_path` (루트 private 모듈), `explore.py:5 from ._colors import …`
(private 패키지), `explore.py:6 from .diagnostics import plot_fonts`.

**영역으로 들어오는 import**: `__init__.py:67/82/115` (agent, config, prompt), `util.py:17` (prompt 재노출),
`layout.py:353,486`·`io.py:256,439` (함수 안 지연 `from .config import config`), `mcp/tools.py:544`
(`prompt.find_template`). ui 를 import 하는 패키지 코드는 없다 (최상위 `dm.ui` 아님).

**경로 지식 누수 (asset)**: `asset/prompt` 경로를 `prompt.py:24`, `lint.py:39`, `mcp/resources.py:26`,
`mcp/_assets.py:12-13`, `mcp/tools.py:56-57` 다섯 곳이 각자 계산한다. `asset/mplstyle`도 `mcp/*` 3곳 + `_colors/_catalog.py:50`.

**테스트의 private import**: `tests/test_ui_*.py` 11개 파일, private 참조 49건 (`test_ui_param.py` 20건 —
`_config._config_path`/`_preset_path` mock, `test_ui_main.py` 6, `test_ui_http_security.py` 5, `test_ui_security.py` 5 …).

## 2. 파일트리 결함

1. **죽은 프로덕션 코드 ~370줄.** `ui/_config.py:227-485` (`save_config`/`load_config`/`save_preset`/`load_presets`/
   `delete_preset`/`set_base_dir`/`_serializable`/`_atomic_write_text`)는 src 안 호출자가 0이다 (`grep` 확인; `ui.py`는
   `ViewerState` 메서드만 부른다). 모듈 docstring이 "legacy internal contracts"라 적지만 소비자는 `tests/test_ui_param.py`,
   `tests/test_ui_hardening.py`뿐이다. `ui/ui.py:729-831, 889-897` (`_format_validation_error`, `_build_model_checked`,
   `_build_model`, `_parse_list`)도 같은 상태 — 요청 파싱이 `_boundary._active`로 옮겨간 뒤 남은 사본이다.
2. **`_boundary.py`는 경계가 아니라 기술 층이다.** 바뀌는 이유가 최소 다섯 개: 로컬 접근 정책(169–268), JSON 한도
   디코더(269–382), 출력 경로(383–425), 요청 스키마(427–785), 저장 상태 포맷(787–880). 이 파일은 단일 커밋
   `4c28bbd3`에서 880줄로 생겼고 이후 변경이 없어 co-change 증거는 아직 없다; 판단 근거는 소비자다 —
   `_config`는 저장 상태 부분만, `_files`는 `RelativeOutput`/`StateKind`/실패 타입만, `ui.py`는 접근·요청만 쓴다.
3. **`_files.py`가 두 기능을 섞는다.** 출력 저장(266–770)과 설정 파일 저장소(776–904)가 `RootScope`·락을 공유한다.
   공유 메커니즘(디렉터리 핸들, `RootScope`)은 플랫폼, 나머지 둘은 각각 `saving`·`state` 기능 소유다.
   또 `_files`(파일시스템 셸)가 `_boundary`의 `InvalidStoredState`·`LimitExceeded`·`StateKind`를 import해
   `FileFailure` 유니언(`_files.py:113-122`)에 와이어 오류를 섞는다 — 플랫폼이 기능 타입을 아는 방향.
4. **`_config.py`는 설정이 아니라 뷰어 상태(config+presets) 기능**이다. 상태 파일명이 `_config.py:251-252`·`_files.py:785-791`에 중복.
5. **라우트 문자열 3중 중복.** `ui.py`의 데코레이터 17개, `_boundary.ROUTE_POLICY`(138–166), `parse_request`의
   `model_routes`·분기(717–783). 라우트 하나를 추가하면 세 파일을 같이 고쳐야 한다 (co-change 강제).
6. **`_styles.py`/`_scripts.py`/`_template.py`는 기술 층이 아니다** — 한 HTML 페이지(클라이언트)의 언어별 분할이며
   이유가 하나(프런트엔드)다. 커밋 이력상 `_template.py`(16회)가 쪼개진 결과이고 `_template↔ui` 13회 공동 변경.
   한 폴더(`ui/page/`)로 모으면 충분하다. 다만 JS(`_scripts.py`, `fetch(` 16곳)가 `/api/descriptors`의 키
   (`type_name`, `min_value` …)와 모든 라우트를 읽으므로 이 폴더가 와이어 계약의 두 번째 정본이다.
7. **`ui.py`가 진입점과 기능을 겸한다.** `run`/`_create_app`(배선) 안에 렌더(`render_bytes`), 이미지·스크립트 저장
   (`save_image` 294–343, `save_script` 344–380), 스크립트 생성(`_generate_script` 904–995), 시그니처 해석
   (`_extract_param_model`), 프로세스 재시작(`_schedule_restart`)이 함께 있다. import 시 `matplotlib.use("Agg")`(90행) 전역 부작용.
8. **스캐폴더 결함 (실제 버그).** `__main__.py:85` `--example` 선택지에 `complex`가 있으나 `templates/complex.py`는
   `dc750a27`에서 삭제됐다. `dartwork-mpl-ui init x --example complex`는 디렉터리를 만든 뒤 `FileNotFoundError`.
   비어 있지 않은 대상은 `_scaffold.py:30`에서 print 후 정상 종료(exit 0) — 실패가 값도 종료 코드도 아니다.
9. **테스트가 코드에서 멀다.** ui 테스트 3,804줄이 전부 `tests/test_ui_*.py`(평면)에 있고 파일명이 소스 파일과
   1:1이 아니다 (`test_ui_param.py`가 `_config` 레거시를, `test_ui_hardening.py`가 죽은 `_build_model_checked`를 시험).
   `pyproject.toml` `testpaths = ["tests"]`, wheel은 `src/dartwork_mpl` 통째 — 동거 테스트는 아직 수집·배포 설정이 없다.
10. **경계 검사 부재** — limn `tools/check_boundaries.py`·`tests/architecture/` 대응물이 없다.
11. **asset/**: 확장자·종류별 층 폴더(`font`, `color`, `mplstyle`, `prompt`, `icon`, `tokens`, wheel 전용 `agent`).
    하위 폴더마다 소유 모듈이 다르다(`font.py`, `_colors`, `style.py`, `prompt.py`, `icon.py`, `tokens.py`, `agent.py`).
    경로는 `importlib.resources`·hatch `force-include`·`CLAUDE.md`/`AGENTS.md`/`llms.txt`(6곳의 `asset/prompt/…`) 에
    박혀 있어 **이동하면 인터페이스가 바뀐다**. 권고: 옮기지 말고 하위 폴더별 소유자 한 곳만 경로를 계산하게 한다.
12. `config.py` 두 필드는 layout의 tick-font 채택 기능 소유(소비자 `layout`/`io` 지연 import). `explore.py`는 문서화된 파사드라 유지.

## 3. 타입 결함

| 파일 | `Any` | `dict[str, Any]` | `cast(` | `type: ignore` | `assert` |
|---|---|---|---|---|---|
| `ui/ui.py` | 16 | 7 | 6 | 1 (`:929`) | 7 |
| `ui/_boundary.py` | 10 | 2 | 9 | 0 | 0 |
| `ui/_config.py` | 16 | 15 | 7 | 0 | 0 |
| `ui/_widget.py` | 16 | 3 | 0 | 0 | 0 |
| `ui/_files.py`, cli/config/agent/prompt/explore | 0 | 0 | 0 | 0 | 0 |

1. **모든 라우트가 받는 하나의 파서 + 문자열 디스패치.** `parse_request(route_template: str, …) -> ParsedRequest |
   InputFailure` (`_boundary.py:707`). 호출자는 결과를 다시 `assert isinstance(parsed, ModelRequest)` 7회
   (`ui.py:398,414,460,479,531,561,582`)로 좁힌다. `post_config`는 `cast(str, request.scope["route"].path)`(`ui.py:456`)로
   어떤 경로로 들어왔는지 문자열을 꺼내 분기한다. → 라우트별 파서 함수로 쪼개면 assert·cast가 사라진다.
2. **변형에서만 의미 있는 Optional 필드.** `StateRequest.tabs: tuple[Tab,…] | None`, `fig_width: int | None`
   (`_boundary.py:443-449`): `/api/config`에서는 항상 None, `/api/save-state`에서만 의미. →
   `ParamsUpdate(model)` | `FullStateUpdate(model, tabs, fig_width)`.
   `SaveRequest.output: RelativeOutput | None`(`:460`) — "자동 이름"과 "지정 이름"은 다른 답(타임스탬프 생성)이다.
3. **문자열 kind + Optional 묶음 = `ParamDescriptor`** (`_widget.py:30-48`): 가변 dataclass, `type_name: str`(7종),
   `min_value/max_value/step: Any`(숫자만), `choices: list[Any] | None`(Literal만), `widget_hint: str | None`.
   `_boundary._active`(:637-650)와 JS가 `type_name` 문자열로 분기. 와이어 키는 계약이므로 내부는
   `NumberControl | TextControl | BoolControl | ChoiceControl | ListControl` 유니언, 와이어 dict는 투영 함수 한 곳.
4. **파싱했지만 타입으로 안 바꾼 저장 상태.** `StoredConfig.value: dict[str, JsonValue]`,
   `StoredPresets.value: list[dict[str, JsonValue]]`(`_boundary.py:787-800`) — 구조를 검사한 뒤 dict 그대로 두므로
   투영·편집에서 `cast` 9건(`_boundary.py:847,855,860,874,875`, `_config.py:103,117,186,214`).
   `parse_stored(kind: Literal["config","presets"], …) -> StoredConfig | StoredPresets | …`(:803)도 kind 문자열로
   두 파서를 한 함수에 접어 호출자가 `isinstance`로 다시 푼다 → `parse_config(raw)`, `parse_presets(raw)`.
5. **와이어 실패에 HTTP 상태가 붙어 있다.** 실패 dataclass 16종이 `status_code`/`code` ClassVar를 가진다
   (`_boundary.py:63-127`, `_files.py:54-110`, `_config.py:65-72`). 결정 쪽 타입이 전송(HTTP) 지식을 품은 것 —
   매핑은 엣지(`_refusal_response`) 한 곳에 `match`로 두어야 한다. 단 `detail`/`code` 문자열은 와이어 계약.
6. **기대 결과를 예외로.** `_validate_export_format`가 `HTTPException(400)` (`ui.py:758-771`, 2개 라우트);
   `_state_name`의 `ValueError`(`_files.py:791`)는 Literal이면 도달 불가. `run`의 `ValueError`/`TypeError`는 공개
   계약(docstring Raises)이라 유지. `agent_doc_path`의 `ValueError`(`agent.py:63`)도 공개 계약 — 내부에 `AgentDoc =
   Literal[...]`를 두는 정도.
7. **`app.state` 경유 상태**: `cast(… , app.state.viewer_state)` 등 3건(`ui.py:279,298,348`) — lifespan이 클로저/holder에 담으면 사라진다.
8. **`prompt.find_template`**(`prompt.py:123-233`): `tier: str | None`인데 알 수 없는 문자열은 조용히 "all"(:186);
   반환 `list[dict[str, object]]`에서 `"tier"` 키가 `tier`가 None일 때만 빠진다(변형별 Optional 키). `_index.json`은
   검증 없이 dict이고 `"advanced"`가 템플릿 id와 같은 층의 센티널 키다. 공개 반환 형태는 유지하고 내부에
   `TemplateMatch` + `Tier = Literal["basic","advanced","all"]` 파싱 후 엣지에서 dict 투영.
9. **mypy override.** `pyproject.toml:280-283` `module = ["dartwork_mpl.mcp.*", "dartwork_mpl.ui.*"]`에
   `disallow_untyped_decorators = false`, `disallow_subclassing_any = false`. 측정: ui extra(pydantic·fastapi·uvicorn)를
   얹은 환경에서 override 없이 `mypy --strict`(py3.10) → ui 오류는 `__main__.py:41,45` InquirerPy 2건뿐이고 이는
   별도 override(:290)가 덮는다. **즉 ui에 대해 이 override는 불필요하다** (원인은 `ignore_missing_imports = true`로
   extra가 없을 때 `BaseModel`이 `Any`가 되는 것). `exhaustive-match` 미설정(limn은 켬).
10. **현재 mypy 오류 (`ui/_boundary.py`)**: 이 worktree의 `.venv`(extra 없음)에서
    `uv run --frozen mypy src/dartwork_mpl/ui/ …` → 4건: `:494`, `:550`, `:554` `"type" has no attribute "model_fields"`,
    `:610` `lru_cache` 인자 `type[Any]` not Hashable. extra를 얹으면(`--with pydantic fastapi uvicorn InquirerPy`) 0건.
    CI(`ci.yml:40`)는 all-extras라 통과하지만 pre-commit mypy 훅(`.pre-commit-config.yaml:38`)은 로컬 venv 의존 —
    extra 없이 sync한 개발 환경에서 이 4건이 뜬다.

## 4. 제안 목표 구조
`ui`는 패키지 전체에서 하나의 슬라이스이고 그 안을 기능 하위 슬라이스로 나눈다. 테스트는 각 폴더의 `tests/`.

```
ui/
  __init__.py      # __all__ = ["ParamModel", "run"] — 지연 로드 그대로 (인터페이스)
  __main__.py      # 진입점: argparse → scaffold.init_project. main 경로 유지 (콘솔 스크립트)
  ui.py            # 진입점: run(), create_app() — 라우터 mount·미들웨어·lifespan만. 파일명 유지(아래 위험 참조)
  platform/        # 업무 무지: json.py(경계 JSON 한도·JsonValue), fs.py(RootScope·디렉터리 핸들·capabilities·락)
                   #           access.py(normalize_bind, authorize_request — grant 표는 인자로 받음)
  params/          # ParamModel, Control 유니언, controls_from_model, controls_wire(), parse_active(),
                   #   param_model_of(fn) ; GET /api/descriptors, /api/defaults 핸들러
  state/           # parse_config/parse_presets → 타입화된 StoredConfig/Preset, project(), ViewerState,
                   #   FixedStateStore ; /api/config(GET·POST), /api/save-state, /api/preset(s) 핸들러
  saving/          # OutputName 파서, prepare_save/commit_save, SaveReceipt·실패 변형 (핸들러 없음: 메커니즘 슬라이스)
  render/          # figure_to_bytes, ExportFormat 파서 ; /api/render, /api/export/{fmt}, /api/save-server/image/{fmt}
  script/          # generate_script ; /api/script, /api/save-server/script
  page/            # get_html + CSS + JS ; GET /, /api/meta, /api/health
  scaffold/        # init_project, templates/ ; pydantic·fastapi import 금지 (base 설치)
```

각 하위 슬라이스 `__init__.py`의 `__all__` = 진입점이 쓰는 라우터(`router`)·grant 표(`GRANTS`) + 다른 슬라이스가
쓰는 값/연산만. 예: `params.__all__ = ["ParamModel", "Control", "controls_from_model", "parse_active",
"ActiveRejected", "param_model_of", "router", "GRANTS"]`; `saving.__all__ = ["OutputName", "parse_output_name",
"prepare_save", "commit_save", "SaveReceipt", "SaveFailure"]`; `state.__all__ = ["ViewerState", "router", "GRANTS"]`.

허용 슬라이스 의존 (한 방향, 경계 검사 허용목록에 이유와 함께 등록):
- `state → params`: 저장 상태는 활성 파라미터 모델과 선언 필드명을 담는다 (투영·`dropped_fields`).
- `render → params, saving`: 렌더 요청은 활성 모델을 받고, 서버 이미지 저장은 출력 슬롯을 쓴다.
- `script → params, saving`: 스크립트는 모델 소스·값을 담고, 서버 저장은 출력 슬롯을 쓴다.
- 모든 슬라이스 → `platform` (역방향 금지). `platform/fs.py`는 `InvalidStoredState` 등 기능 타입을 모른다 —
  자기 실패(`NotRegular`, `IOFailure` …)만 돌려주고 `state`가 번역한다.
- `page`, `scaffold`는 아무 슬라이스도 import하지 않는다. 진입점 `ui.py`만 모든 슬라이스의 `router`/`GRANTS`를 조합해
  `access`에 넘긴다 → 라우트 문자열 정본이 슬라이스 하나로 줄어든다.
- 영역 밖: `ui/ui.py`의 `..util` → `..io` (같은 공개 함수). 생성 스크립트 본문의 `from dartwork_mpl.util import
  save_formats`(`ui.py:978`)는 **사용자 파일 출력 포맷**이라 그대로 둔다.

루트 모듈: `cli.py`(배선만, 현재 적합) 유지. `explore.py` 유지(파사드). `config.py`는 layout 쪽 감사와 함께
tick-font 채택 슬라이스로 옮기고 `dartwork_mpl.config` 재노출을 남기는 안 — 이 영역 단독으로는 하지 않는다.
`prompt.py`는 `prompt/` 패키지로 승격해 `asset/prompt` 경로의 유일한 소유자(`prompt_path`, `template_index()`,
`template_source(id)` 공개)가 되고, `lint.py`·`mcp/*`는 그 표면만 쓴다 (mcp 감사와 조율). `agent.py` 유지.

테스트 배치: limn ADR-0012 방식 — 슬라이스 하나만 보는 테스트는 `ui/<slice>/tests/`, HTTP 계약 전체를 보는
`test_ui_http_security.py`류와 경계 검사는 루트 `tests/`(`tests/architecture/test_boundaries.py`). 전제 설정:
`testpaths = ["tests", "src/dartwork_mpl"]`, hatch wheel `exclude = ["src/dartwork_mpl/**/tests"]`, mypy
`exclude`에 tests 추가, `--import-mode=importlib` 검토(현재 `tests/__init__.py`가 있어 rootdir 패키지 모드).
**인터페이스에 닿는 지점**: `dartwork_mpl.ui`/`ParamModel`/`run` 시그니처·Raises, `dartwork_mpl.ui.__main__:main`,
`dartwork_mpl.cli:main`, `--example` 선택지, 모든 HTTP 경로·메서드·응답 키(`detail`/`code`/`paths`, 성공 dict),
`/api/descriptors` 키 이름과 null 표기, 상태 파일명 `.dartwork_ui_config.json`/`.dartwork_ui_presets.json`과 JSON 형태,
`dm.find_template` 반환 dict 형태(MCP `find_template` 도구도 동일), `asset/**` 경로, 생성 스크립트 본문.
`dartwork_mpl.ui.ui`는 문서에 없지만(문서는 `dartwork_mpl.ui`만 7회) 사용자 import 가능성 때문에 이름 유지.

## 5. 분할 PR 제안
순서: 기계 판정기(CLAUDE.md 규칙 2) → 죽은 코드 제거 → 이동(동작 불변) → 타입 변경. 충돌 후보: `git log --oneline -30 -- src/dartwork_mpl/ui`의 최근 대형 변경은 `4c28bbd3`(#510, 10/20)·`5c080a9a`(#513);
UI를 건드리는 열린 브랜치가 있으면 PR 3–6과 충돌한다. `pyproject.toml`은 다른 영역 PR과 거의 확실히 충돌한다.

| # | 범위 | 파일 | 규모 | 위험 | 검증 |
|---|---|---|---|---|---|
| 1 | **와이어 골든**: `/api/descriptors`·각 라우트 성공/거부 응답 키·상태 파일 바이트를 고정 | `tests/test_ui_wire_golden.py` + 픽스처 | ~300 | 낮음 | 현재 main에서 통과 |
| 2 | **mypy 정리**: `ui.*` override 제거, `exhaustive-match` 켜기(ui만 overrides로), pre-commit mypy를 `--all-extras` venv로 | `pyproject.toml`, `.pre-commit-config.yaml` | ~20 | 중 (mcp 공유 override 분리) | extra 유무 양쪽에서 mypy |
| 3 | **스캐폴더 버그**: `complex` 처리(템플릿 복원 vs 선택지 제거 — 후자는 CLI 플래그 변경이라 사람 결정), 비어있지 않은 대상 exit≠0 | `ui/__main__.py`, `_scaffold.py`, 테스트 | ~80 | 인터페이스 | 실패 테스트 먼저 |
| 4 | **죽은 코드 제거**: `_config.py:227-485`, `ui.py:729-831,889-897`과 그 테스트 | `_config.py`, `ui.py`, `test_ui_param.py`, `test_ui_hardening.py` | −~600 | 낮음 | 전체 ui 테스트 + 골든 |
| 5 | **경계 검사 도입** (limn `check_boundaries` 축소판, ui 하위 슬라이스 목록·허용 의존 표, 5종 주입 위반 확인) | `tests/architecture/test_ui_boundaries.py` | ~250 | 낮음 | 주입 위반 5종 실패 확인 |
| 6 | **이동 1 — platform**: `_boundary` JSON 한도·`_files` RootScope/핸들 → `ui/platform/`; `access` 분리 | 신규 3, `_boundary`, `_files`, import 수정 | ~700 (대부분 이동) | 중 | 골든 + 검사 |
| 7 | **이동 2 — params/page/scaffold**: `_param`·`_widget`·`_active` → `params/`; `_template/_styles/_scripts` → `page/`; `_scaffold`+`templates/` → `scaffold/` (hatch 포함 경로 확인) | 이동 위주 | ~400 diff | 중 (템플릿 패키징) | wheel 빌드 후 `init` 실행 |
| 8 | **이동 3 — state/saving/render/script + APIRouter**: 핸들러를 슬라이스로, `ui.py`는 mount만; `ROUTE_POLICY`→슬라이스 `GRANTS` 조합 | `ui.py` 분해 | ~800 | 높음 (미들웨어 `_matched_route`가 include된 라우트를 보는지) | 골든 + `test_ui_http_security.py` |
| 9 | **테스트 동거 설정 + 이동**: testpaths·hatch exclude·mypy exclude, 슬라이스 단위 테스트 이동(사람 승인 필요 — SKILL "기존 테스트 이동은 승인 후") | `pyproject.toml`, `tests/test_ui_*` | 이동 위주 | 중 (wheel에 tests 유입) | `uv build` 후 wheel 목록 확인 |
| 10 | **타입 1 — 요청**: `parse_request` → 라우트별 파서, `StateRequest` → `ParamsUpdate`/`FullStateUpdate`, `SaveRequest` 변형, `assert`/`cast` 제거, `ExportFormat` 파싱(HTTPException 제거) | `params/`, `state/`, `render/`, `script/` | ~400 | 중 | 골든 불변 |
| 11 | **타입 2 — 저장 상태**: `StoredConfig`/`Preset` 필드 타입화, `parse_config`/`parse_presets`, cast 9건 제거; 파일명 상수 1곳 | `state/` | ~350 | 중 (바이트 보존 계약) | 상태 파일 골든 바이트 |
| 12 | **타입 3 — 컨트롤**: `ParamDescriptor` → `Control` 유니언 + `controls_wire()`; `_active` 분기를 `match`로 | `params/` | ~300 | 중 (JS 계약) | `/api/descriptors` 골든 |
| 13 | **타입 4 — 실패의 HTTP 분리**: 실패 dataclass의 `status_code` ClassVar 제거, 엣지 `match` 한 곳 | 전 슬라이스 + `ui.py` | ~300 | 중 | 골든(상태·code 불변) |
| 14 | **prompt/asset 소유권**: `prompt/` 패키지, `asset/prompt` 경로 단일화, `find_template` 내부 타입화(반환 형태 불변) | `prompt.py`, `lint.py`, `mcp/{tools,resources,_assets}.py` | ~400 | 중 (mcp 감사와 조율) | `test_prompt.py`, MCP 도구 테스트 |

이동 PR(6–9)과 타입 PR(10–14)은 섞지 않는다. 4가 6–8보다 먼저여야 이동량이 줄어든다.

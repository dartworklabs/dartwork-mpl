---
orphan: true
---

# ADR 0005: 기능 슬라이스, 테스트 동거, 경계 검사로 집행하는 구조

| 항목 | 값 |
| --- | --- |
| **상태** | Accepted |
| **날짜** | 2026-10-22 |
| **결정자** | 프로젝트 소유자 (2026-10-22 구조 리팩터 요청: "인터페이스를 제외한 파일트리·타입 전부, limn 수준으로 엄격하게") |
| **대체** | 없음. ADR 0001–0004의 동결은 그대로 유지한다 |
| **근거 자료** | [구조 리팩터 계획](../development/structure-refactor/README.md), 같은 폴더의 `audit/*.md` 6개 |

## 맥락

`src/dartwork_mpl`은 152개 모듈(약 41k줄)이 평면 모듈과 기술 층 이름(`util`, `_helpers`,
`helpers/`, `ui/_boundary`, `ui/_files`)으로 묶여 있다. 감사에서 확인한 사실은 다음과 같다.

- 2,000줄 안팎의 파일이 여러 능력을 섞는다(`mcp/tools.py` 8개 능력, `lint.py` 4개 일, `_colors/_catalog.py`).
- 패키지 경계를 넘는 비공개 import가 22건(16쌍), 지연 import로 가린 순환이 3개다
  (`style`⇄`_colors`, 루트⇄`templates`, 루트⇄`templates`⇄`validate_fixes`).
- 테스트 135개 항목이 루트 `tests/`에 평면으로 있다. 슬라이스 하나만 관찰하는 파일이 113개다.
- import 경계를 검사하는 장치가 없다. mypy strict는 켜져 있지만 `exhaustive-match`가 없고,
  docstring 규칙(D100–D107)도 없다.
- 결과·상태를 `dict[str, Any]`와 문자열 status/kind 필드로 나르는 곳이 많다
  (`mcp.execution._run`, `_colors` gate 위반, `ui.parse_request`, validate fix handler).

팀 코딩 스킬(`code-implement`)과 기준 저장소 limn(ADR 0009·0010·0012, `tools/check_boundaries.py`)은
능력 단위 슬라이스, 선언된 표면, 테스트 동거, 기계 경계 검사를 요구한다.

## 결정

### 1. 인터페이스 동결선

다음은 이 리팩터 전체에서 바뀌지 않는다. 바꾸려면 별도 결정이 필요하다.

- `dm.__all__`의 모든 이름, `docs/development/api-stability.md`가 공개라고 적은 하위 모듈 경로
  (`dartwork_mpl.font`, `.lint`, `.validate`, `.validate_fixes`, `.helpers.*`, `.templates.*`, `.tokens`,
  `.util`, `.diagnostics`, `.mcp`, `.mcp.server`, `.ui`, `.ui.ui`, `._colors`(migration.md가 안내)).
- 공개 함수의 시그니처와 정적 타입. 예를 들어 `side: str`을 `Literal`로 좁히는 일도 공개 계약 변경이다.
- MCP tool·resource·prompt의 이름, **등록 순서**, 인자 스키마, docstring, 응답 형태, artifact v1
  (ADR 0001 A1, 0003, 0004). 등록 순서를 스캔하는 네 파일(`mcp/tools.py`, `resources.py`,
  `prompts.py`, `artifacts/transport.py`)은 배선 표로 남는다.
- CLI 명령·플래그, UI HTTP 경로와 응답 키, 상태 파일명과 JSON 형태, `asset/**` 경로.
- 출하 색값과 그 검증 고정점: `tests/test_shipped_colors_hash.py`, `_colors/_compatibility_metrics.py`
  (경로와 바이트 SHA가 출하 자산에 고정), `python -m dartwork_mpl._colors._build`.

### 2. 슬라이스 배치

- 능력(capability) 하나가 패키지 하나다: `src/dartwork_mpl/<능력>/`. 공개 경로가 모듈 이름이면
  **같은 이름의 패키지로 바꿔** 경로를 유지한다. 이름이 바뀌는 경우에만 재노출 shim을 남긴다
  (`util.py`, `icon.py`, `helpers/*`, `validate_fixes.py`).
- 각 슬라이스는 `__init__.py`의 `__all__`로 표면을 선언한다. 나머지는 비공개다.
- 업무를 모르는 메커니즘(figure 측정, rcParams 잠금, MCP 프로세스 캡처, UI JSON·파일 핸들)은
  platform 모듈에 둔다. platform은 어떤 슬라이스도 import하지 않는다.
- 진입점(`dartwork_mpl/__init__.py`, `cli.py`, `ui/ui.py`, `ui/__main__.py`, `mcp/server.py`,
  MCP 배선 표 네 개, `_colors/_build.py`)은 배선만 한다.
- 슬라이스 사이 의존은 업무 이유가 있을 때만 한 방향으로 허용하고, 그 이유를 검사기의 허용 목록에 적는다.

### 3. 테스트 배치 (limn ADR 0012와 같은 끝 상태)

- 슬라이스 하나만 관찰하는 테스트는 `src/dartwork_mpl/<능력>/tests/`에 둔다.
  2026-10-22 요청을 기존 테스트 이동의 승인으로 본다.
- 루트 `tests/`는 해체하지 않는다. 여러 기능을 함께 보는 계약(`tests/contracts/`), 문서·산출물 대조
  (`tests/docs/`), 스크립트·도구 검사(`tests/tools/`), 저장소 구조 검사(`tests/architecture/`),
  수집하지 않는 공용 도우미(`tests/support/`)를 둔다. `tests/robustness/`, `tests/visual/`은 그대로 둔다.
- wheel에는 테스트가 들어가지 않는다(`**/tests/**` exclude, 검사로 고정).
- 이동 PR마다 collect-only 테스트 id를 이동 전과 대조해 잃거나 중복된 id가 0이어야 한다.

### 4. 타입

- 결과·거절·상태는 variant마다 frozen dataclass를 두고 `TypeAlias` union으로 묶는다.
  문자열 status/kind/reason 필드와 일부 경우에만 의미 있는 Optional 필드는 없앤다.
- 경계(YAML·JSON·요청·저장 파일·MCP 인자)에서 한 번 파싱해 타입 값으로 만든다. `cast`는 파싱이 아니다.
- **새 타입은 내부 표현에만 쓴다.** 와이어·공개 반환 형태(dict 키, 메시지 문자열, 예외 계약)는
  가장자리에서 기존 모양으로 바꿔 바이트 단위로 유지한다.
- mypy는 strict에 `exhaustive-match`·`strict_equality`를 더하고, 완화 override는 모듈 단위로 좁힌다.

### 5. 집행

- `tools/check_boundaries.py`(AST 전용)와 `tests/architecture/test_boundaries.py`가 다섯 위반을 잡는다.
  다른 슬라이스 비공개 import, shared·platform이 슬라이스에 닿는 경로, 슬라이스 순환,
  허용 목록에 없는 의존, decision 모듈의 다른 기능 import다.
- 현재 위반은 `DEBT` 목록에 사유와 함께 올린다. 목록은 줄어들기만 한다. 마지막 PR에서 비운다.
- ruff D100–D107을 켠다. 테스트에는 D100–D101만 적용한다.

## Trade-off

**장점**: 한 능력을 한 폴더에서 이해하고 고칠 수 있다. 경계 위반이 리뷰가 아니라 CI에서 실패한다.
타입이 불가능한 상태를 막아 분기 검사와 `cast`가 줄어든다.

**비용**: 약 60개의 PR이 필요하다. 진행 중인 다른 작업은 이동된 경로로 rebase해야 한다.
`mcp/tools.py`처럼 배선 표가 남는 곳은 완전한 슬라이스 소유가 아니다.

## 대안

| 대안 | 선택하지 않은 이유 |
| --- | --- |
| 한 번에 전체 이동 | 다른 작업과의 충돌과 회귀 판정이 불가능할 만큼 커진다 |
| 테스트를 `tests/<능력>/`에 거울 배치 | 코드와 테스트가 두 트리로 갈라져 동거 원칙(Locality of Behaviour)에 어긋난다 |
| MCP 스캐너를 레지스트리 기반으로 바꿔 tool 정의도 슬라이스로 이동 | 색 동결 도구(`_colors/_catalog.py`) 수정이다. ADR 0001의 잠금을 이 ADR이 풀 수 없다(CLAUDE.md 규칙 3) |
| 공개 파라미터를 `Literal`로 좁혀 타입 강화 | 공개 정적 계약 변경이다. 동결선 밖이다 |

## 결과

- 실행 순서와 진행 상태는 [구조 리팩터 계획](../development/structure-refactor/README.md)이 맡는다.
- 이 ADR이 다루지 않는 사람 결정은 계획 문서의 "사람 결정 대기" 절에 모은다.

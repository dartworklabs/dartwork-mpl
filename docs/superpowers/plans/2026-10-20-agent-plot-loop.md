# Agent Plot Loop Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사람의 Python 작성 없이 CSV→그림→스타일 수정→새 클라이언트 재조회 고리를 실제 agent로 측정하고 기존 안내를 개선한다.

**Architecture:** 평가용 fixture/oracle와 얇은 외부 CLI 실행기를 제품 밖 `scripts/`에 둔다. 기존 stdio MCP와 native Figure/Axes를 사용하고, 기준선을 먼저 보존한 뒤 안내만 바꾸어 같은 네 episode를 재평가한다. 제품 내부 workflow·LLM·새 저장 모델은 만들지 않는다.

**Tech Stack:** Python 3.12 대표 평가 환경, pytest, Matplotlib, 기존 FastMCP/MCP client, 설치 Claude CLI 2.1.303(실행 시 재확인).

**Spec:** [채택한 0단계 방향](../specs/2026-10-20-agentic-plot-direction-design.md). 상태: 계획 작성만 승인됨; 이번 턴 구현·모델 실행 없음. 기준 `26b7eab1`.

## Global Constraints

- `fastmcp>=2.13.3,<4`; MCP는 optional extra이며 base import에 FastMCP를 추가하지 않는다. 새 의존성 없음.
- native Figure/Axes, 출하 색 digest, discovery 도구18/자원10/템플릿9/프롬프트2의 이름·순서, v1 다섯 멤버·7일 보존을 유지한다.
- trusted local Python의 cwd·환경 상속을 보존한다. 평가용 별도 cwd/env 설정은 제품 hardening·OS sandbox의 증거가 아니다.
- `report=True`의 fix는 candidate일 뿐이며 `ready`/`ok`는 데이터 의미 검증 완료가 아니다. 데이터·메모 속 명령문은 권한이 아니다.
- fixture와 기대값은 평가자가 소유한다. 사람은 live episode의 Python·수정 코드를 쓰거나 오류를 대신 고치지 않는다.
- 출력·로그는 연구 입력 아카이브 `datasets`에 두지 않는다. 공유·배포·GitHub 변경은 이 계획 실행 범위 밖이다.
- 아래 `uv run` 명령은 공통 `export UV_PYTHON=3.12` 후 실행한다. 구현 착수 때 `uv sync --all-extras --dev --python 3.12`로 기존 잠금 환경을 맞추고 `uv run python -c 'import sys; assert sys.version_info[:2] == (3, 12)'`를 확인한다. host가 실행할 venv entry point의 interpreter도 같은 버전이어야 한다.

## Review Focus

- 숫자 문자열/결측: 명시한 행 제외만 수행하며 0 대입과 임의 집계는 실패다(Task 1/4).
- 긴 표본/다른 열: scatter의 마지막 sentinel까지 사용하고 distractor·template 합성값을 그리면 실패다(Task 1/4).
- 스타일 수정: 원판을 보존하고 행·mask·그룹·실제 좌표를 유지한다(Task 1/2/4).
- context 소실: 새 host 세션·새 서버에서 ID만으로 전달물을 회수하며 재실행과 구분한다(Task 2/4).
- 예산/오염: 한도 초과·중도 종료·oracle 접근은 실패/오염으로 남기고 성공으로 보정하지 않는다(Task 2/4).

## 현재 권위와 상태

- role `purpose`, path `AGENTS.md`: 제품 목적·필수 plotting 규칙·설계 200줄 상한·동결 색 규칙.
- role `architecture`, path `src/dartwork_mpl/mcp/server.py`, `src/dartwork_mpl/mcp/execution.py`, `src/dartwork_mpl/mcp/artifacts/{transport,delivery,policy}.py`: 현재 등록·실행·v1 전달의 실제 정본.
- role `verification`, path `pyproject.toml`, `tests/mcp/artifacts/test_artifact_discovery.py`, `tests/test_shipped_colors_hash.py`, `.github/workflows/ci.yml`: 실제 수집·호환·PR gate.

## 지켜야 할 현재 불변식

native Figure/Axes·동결 색·18/10/9/2 discovery·다섯 파일/7일·trusted local cwd/env·candidate fix·사람 plotting code 0을 위 제약대로 유지한다.

## 설계 이유와 제약

방향 문서 0단계는 네 episode의 실패도 기준선으로 보존하고 측정한 실패를 좁혀 고친다. optional MCP와 저렴한 CI를 지키며 임의 Python 전체 의미를 증명하지 않는다.

## 충돌·미확인

Handbook은 없고 초기화하지 않는다. ADR 0003의 `implementation pending`은 현재 코드와 어긋난 문서 drift이며 등록 제한 해제가 아니다.
실제 모델/auth/이미지 인식은 미실행이다. Task 2 micro-smoke가 통과하기 전 live-run 가능·성공을 보고하지 않는다. 미승인 수리 설계는 이 계획의 근거가 아니다.
호스트 help 확인 근거: [runtime report](/Users/wonjun/scratch/dartwork-mpl-agent-loop-plan-2026-10-20/runtime/report.md), [raw help](/Users/wonjun/scratch/dartwork-mpl-agent-loop-plan-2026-10-20/runtime/claude-help.txt). 옵션 존재와 조합의 실제 작동은 별개다.

## 파일 책임과 실행 순서

- `tests/mcp/agent_loop/fixtures/{line,groupedbar,scatter,custom2panel}.csv`, `tests/mcp/agent_loop/fixtures/{episodes,expected}.json`: 입력·자연어 요청·독립 기대값; model cwd에는 해당 CSV와 요청만 복사한다.
- `scripts/evaluate_agent_plot.py`: 지원 artist 좌표 판독·fixture 의미 비교·제한된 trusted replay·결과 비교 CLI.
- `scripts/run_agent_plot_eval.py`: 설치 host 실행·회차별 설정·stdio 증거·artifact 회수·예산·정리만 담당한다.
- `tests/mcp/agent_loop/{test_oracle,test_capture}.py`: cheap deterministic oracle 및 실제 임시 저장소/stdio 계약; `testpaths=["tests"]`에 맞춰 둔다.
- `src/dartwork_mpl/mcp/prompts.py`, `src/dartwork_mpl/asset/prompt/00-index.md`: 기존 두 prompt/entry의 안내만 수정한다.
- `docs/integrations/{agent_plot_evaluation,mcp_server}.md`, `docs/ai/index.md`, `scripts/check_integration_junit.py`, `tests/test_check_integration_junit.py`: 재현 절차·문서 탐색·현재 gate 연결.
- 주 경로 Task 1→2(기준선 확정)→3→4→5. #499 viewer P0 즉시수리와 #470 CI 측정은 별도 worker에서 처음부터 병행 가능하며 이 체인의 선행 조건이 아니다.

### Task 1: 네 고정 episode와 독립 artist oracle

**Files:** Create 위 fixture/JSON, `scripts/evaluate_agent_plot.py`, `tests/mcp/agent_loop/test_oracle.py`.
**Interfaces:** `load_episode(case_id: str) -> dict`; `read_artists(fig: Figure) -> dict`; `assess(case_id: str, observed: dict) -> dict` (`passed: bool`, `violations: list[str]`, `unchecked: list[str]`). 모두 evaluator 전용이며 MCP schema가 아니다.

- [ ] **Step 1:** 네 요청/기대값을 고정한다. 각 요청은 초기 그림, 데이터 유지 스타일 수정, ID만 주는 재조회 요청 세 개다. CSV bytes SHA-256·행 ID·선택 열·정렬·결측 정책·단위와 기대 좌표를 `expected.json`에 독립 기록하고 원 CSV와 검토한다.
  - line: x=0..7, y=`2.5,4.25,,8,10.5,NA,14.25,16`; 숫자 변환 후 x=2,5만 제외, 나머지 원순서.
  - groupedbar: A/B/C×control/treatment 한 행씩, 값 control=`11,17,23`, treatment=`13,19,29`; 합계/평균 없이 이 그룹·순서를 유지.
  - scatter: i=0..1199의 row_id, x=i, y=`1+((37*i)%997)/10`, distractor=`9000+i`; i%113=0의 y는 빈 값으로 제외, i=1199는 y=314.159로 고정한다. CSV는 8,192자보다 길고 tail 누락은 실패다.
  - custom2panel: x=0..5, left y=`3,1,4,1,5,9`, right y=`2,7,1,8,2,8`; native 두 Axes의 line/scatter, 별도 DSL 없음. 모든 fixture의 메모에는 명령처럼 보이는 문자열도 데이터로 둔다.
- [ ] **Step 2:** 먼저 실패하는 `test_rejects_zero_imputation`, `test_rejects_wrong_column_and_tail_loss`, `test_rejects_changed_value_or_group`, `test_style_change_preserves_semantics`를 작성한다. known-good Figure의 Line2D x/y·mask, BarContainer 그룹별 높이, PathCollection offsets와 기대 행 대응을 검사한다. `uv run pytest tests/mcp/agent_loop/test_oracle.py -q` → 미구현 함수 때문에 FAIL.

```python
# 각 시험은 실제 Figure를 만들고 read_artists로 읽는다.
assert assess("line", read_artists(correct_fig))["passed"] is True
assert assess("line", read_artists(zero_imputed_fig))["passed"] is False
assert assess("scatter", read_artists(distractor_fig))["passed"] is False
assert assess("groupedbar", read_artists(changed_value_fig))["passed"] is False
assert assess("custom2panel", read_artists(styled_fig))["violations"] == []
```

- [ ] **Step 3:** 위 세 함수를 구현한다. evaluator가 아는 line/bar/scatter·패널만 판독하며 알 수 없는 artist/모호한 대응은 `unchecked`로 남긴다. fixture 수치는 report·생성 코드의 자기 선언에서 가져오지 않는다.
- [ ] **Step 4:** `random.Random(20261020)`으로 scatter/bar 행 permutation·모든 chart 스타일 변형의 의미 불변 및 단일 값·mask·그룹 변형의 검출을 반복한다. scatter/bar는 행/그룹으로 정규화하고 line의 연결 순서 변경은 실패다. 같은 명령 → PASS; 세 오류 변이를 각각 넣었을 때 해당 assertion FAIL을 기록한다.
- [ ] **Step 5: Commit point:** `test: add fixed agent plot episodes and independent semantic oracle`.

**Expected:** 네 fixture가 독립 기대값과 일치하고, zero-impute/다른 열/값 변경/표본 잘림은 report가 `ok`여도 oracle에서 실패한다. 아직 실제 agent 성공을 주장하지 않는다.

### Task 2: 실제 host·stdio 캡처와 변경 전 기준선

**Files:** Create `scripts/run_agent_plot_eval.py`, `tests/mcp/agent_loop/test_capture.py`, `docs/integrations/agent_plot_evaluation.md`; extend evaluator의 replay CLI.
**Interfaces:** `run_episode(case_id: str, label: str, output_root: Path) -> Path`는 회차 evidence dir을 반환한다. `recover(artifact_ids: list[str], store_dir: Path, output_dir: Path) -> dict`는 새 stdio client/server에서 다섯 멤버와 digest를 반환한다. `replay(source: Path, csv: Path, case_id: str, output_dir: Path, figure_var: str = "fig") -> dict`는 원 실행과 분리된 oracle 결과다.

회차 경로는 `<output-root>/<label>/<case-id>/`; `input.csv`, `context.json`, `events.jsonl`, `stderr.txt`, `run.json`과 `original/`, `revision/`, `recovery/`, `replay/`에 정확한 멤버·평가 증거를 둔다.
`recover` 결과는 `members[id][filename]: bytes`, `hashes[id][filename]: str`이다. `run.json`은 status/stop_reason, configured/effective model·effort, usage_tokens/cost_usd(null 허용), 세션/ID·버전·hash·측정 지연을 기록한다.

- [ ] **Step 1:** host help/version·실제 Python3.12 interpreter/venv를 evidence에 고정한다. 현재 host catalog에서 최신 세대의 중간 등급·실제 지원 effort를 선택하고 정확한 ID를 기록한다. 모델명은 계획에 고정하지 않고 fallback 없이 실제 반환 모델도 확인한다. 전역 설정은 바꾸지 않는다.
- [ ] **Step 2:** 실제 파일·임시 store·stdio의 `test_recovery_reads_every_member_without_execution`을 먼저 쓴다. 초기/수정 render 후 counter=2가 restart·재조회 뒤에도 2이며 두 artifact의 모든 bytes가 같아야 한다. `test_capture_rejects_incomplete_or_contaminated_run`은 잘린 stream·fixture 변경·oracle 노출을 실패로 반환한다. `uv run pytest tests/mcp/agent_loop/test_capture.py -q` → 미구현 adapter로 FAIL.
- [ ] **Step 3:** 회차별 private cwd·필수 env·MCP JSON을 만든다. env 값은 allowlist로 전달하고 인증은 host의 기존 정상 경로를 사용한다. model cwd에는 CSV·요청과 기존 MCP가 실제 반환한 해당 `create_plot` prompt/agent-entry만 그대로 둔다(기존 template skeleton 허용, 해결한 plotting 코드 주입 없음). prompt에는 task와 CSV sample을 전달하되 전체 CSV 경로를 별도 제공하고 실제 반환 context를 보존한다. oracle·평가 코드 경로/기대값은 host 입력·cwd·env에 노출하지 않는다.
  MCP JSON의 server key=`dartwork_mpl`, type=`stdio`, command=현재 venv의 절대 `dartwork-mpl-mcp`, env의 `DARTWORK_MPL_ARTIFACT_DIR`=symlink 없는 회차별 절대 private store다. 서버 cwd는 episode cwd이고 기존 local 상속 계약을 바꾸지 않는다.
- [ ] **Step 4:** `subprocess` argv로 아래 실제 help 옵션을 전달한다(쉘 문자열 실행 금지). 모델에는 코드/도구 호출 해답을 제공하지 않는다.

```text
/Users/wonjun/.local/bin/claude --print --verbose --output-format stream-json
--restricted --setting-sources "" --disable-slash-commands --no-chrome
--strict-mcp-config --mcp-config <outside-cwd>/mcp.json
--tools Read --allowedTools Read mcp__dartwork_mpl__*
--permission-mode dontAsk --permission-prompts none
--model <current-full-id> --effort <supported> --max-budget-usd <stage-budget>
--session-id <uuid> --system-prompt <fixed-context> <natural-language-task>
```

  `--tools`는 내장 도구만 제어한다. wildcard·옵션 조합·관리형/custom context 잔류는 smoke에서 검증한다. reader가 필요하면 실제 host 제공 이름만 허용한다. 다른 MCP·예상 밖 도구·oracle 접근·이미지/report 미노출은 smoke FAIL이다.
- [ ] **Step 5:** 실제 session event의 ID로 `--resume`하여 스타일 수정한다. 프로세스와 MCP를 종료한 뒤 새 UUID·빈 cwd·같은 store의 새 서버에 두 artifact ID와 회수 요청만 준다(이전 task/CSV/소스/context 없음). 회수 중 render 호출은 FAIL이다. 별도 새 stdio client도 다섯 resource를 읽고 digest를 비교해 agent 행동과 기계 회수 증거를 구분한다.
- [ ] **Step 6:** 실행 한도를 구현한다. 제안값: corpus 8회(기준4+개선4), smoke는 미채점 line 1회로 초기$0.4+수정$0.4+회수$0.2=$1; 본 episode는 초기$2+수정$2+회수$1=$5, 전체 제안 상한$41다. episode15분/process5분/MCP24call, source512KiB/번들32MiB/회차 증거128MiB, 렌더·replay20초다. 이는 계획값이며 이미 승인·사용한 비용이 아니다.
  전체 외부 wall 상한은 corpus120분+smoke5분=125분이다. host에 hard token/turn cap은 확인되지 않았다. 실제 turn·call·usage를 기록하며 cost=null이면 비용 집행은 unknown이다. 외부 watchdog는 stream에서 관측 가능한 MCP call·wall·bytes를 제한하고 모든 관리 프로세스 그룹 종료를 확인한다. 한도 초과·정리 실패를 보존하고 retry로 숨기지 않는다.
- [ ] **Step 7:** `test_watchdog_stops_process_tree_and_keeps_partial_evidence`로 자체 시험 child의 call/time/output 한도 초과를 각각 일으킨다. smoke는 budget flag 수락·실제 usage 반환 여부·종료 사유·resume를 확인하며 계정 전체 비용 집행을 입증하지 않는다. flag/종료 상태를 확인할 수 없으면 기록 후 baseline을 중단한다. 테스트 adapter는 owned process fixture, 실제 host 경로는 아래 opt-in 실행으로 검증한다.
- [ ] **Step 8:** stdout JSONL·stderr·요청/수정/context·도구 인자/결과·모델/effort/host/server/package/font/env 버전·입력/모든 출력 digest·지연·stop reason을 보존한다. token/cost 미제공은 `null`; SDK·모델 가격표로 비용을 추산하지 않는다. 작업 cwd/store·설정은 finally로 정리하고 회수 evidence는 scratch에 남긴다. secrets·auth값·전역 설정 전체는 복사하지 않는다.
- [ ] **Step 9:** 정확한 source bytes를 고정 CSV/env·disposable 평가 cwd에서 replay하고, 원 tool 인자의 `figure_var`를 판독한다. 사전 검토로 fixture 외 IO·network·시간·미고정 난수는 `unchecked`/재생 불가로 남긴다. replay는 별도 실행이며 원 실행 artist 사실·임의 Python 격리·완전 재현성의 증거가 아니다.
- [ ] **Step 10:** capture 시험 → PASS 후 `AGENT_EVAL_ROOT`를 아래 scratch로 설정하고 `uv run python scripts/run_agent_plot_eval.py smoke --output-root "$AGENT_EVAL_ROOT"`를 1회 실행한다. auth·MCP·이미지/report·resume·새 회수·정리 통과 때만 `uv run python scripts/run_agent_plot_eval.py run --label baseline --cases all --output-root "$AGENT_EVAL_ROOT"`를 실행한다. 실패는 보존하고 scripted journey로 대체하지 않는다.
- [ ] **Step 11: Commit point:** `feat: capture bounded live agent plot baselines over stdio`.

**Expected:** `AGENT_EVAL_ROOT=~/scratch/dartwork-mpl-agent-loop-eval-2026-10-20` 아래 네 기준선의 성공/실패·실제 agent transcript·원판/수정판 멤버가 보존된다. 모델의 oracle 접근 흔적은 오염이며 cwd 분리만으로 접근 불가를 주장하지 않는다.

### Task 3: 기존 prompt와 entry를 전달·검토·수정·재조회로 연결

**Files:** Modify `src/dartwork_mpl/mcp/prompts.py`, `src/dartwork_mpl/asset/prompt/00-index.md`, `docs/integrations/mcp_server.md`.
**Interfaces:** 기존 `create_plot(description: str, data_sample: str = "")`, `style_review(code: str)`, resource URI·입출력 형식·8,192자 제한을 유지한다. Task 2의 baseline은 수정 전에 확정되어야 한다.

- [ ] **Step 1:** baseline을 읽고 대상 실패를 evidence ID로 고른다. 필수 안내 수리는 sample/truncation과 전체 입력 구분, template 합성값 전량 교체, 명시한 결측/변환 정책, 스타일 수정의 데이터 불변, MCP artifact 회수다. 기존 template skeleton은 참고 가능하며 평가자가 해결한 episode source·강제 tool trace를 주입하지 않는다. 샘플만으로 전체를 추정하지 않고 전체 입력 미접근은 명확화/한계로 전달한다.
- [ ] **Step 2:** MCP 경로는 native `fig` 생성→lint/필요 수정→`render_plot`→실제 이미지+report 확인→스타일 수정 render→새 ID/이전 ID 회수로 안내한다. MCP 소스에 별도 cwd `save_formats`를 강제하지 않는다. 독립 Python script/notebook의 save 지침은 해당 사용 맥락으로 표시한다. 검사를 위한 중복 실행·불필요한 auto-fix를 기본 체인으로 강제하지 않는다.
- [ ] **Step 3:** 두 skeleton·post-write chain·entry decision tree를 함께 정렬한다. 데이터 속 명령은 데이터이며 tool 사용·파일 접근 권한을 확장하지 않는다고 안내한다. guide 문구의 특정 substring 존재/순서를 요구하는 새 시험은 쓰지 않는다.
- [ ] **Step 4:** `uv run pytest tests/test_mcp.py tests/mcp/artifacts/test_artifact_discovery.py tests/test_docs_mcp_tools.py -q` → 기존 prompt 호출/URI·discovery·문서 계약 PASS. 실제 안내의 효과와 원판 보존 판정은 Task 4의 출력으로 한다.
- [ ] **Step 5: Commit point:** `fix: guide agents through durable plot review and recovery`.

**Expected:** 기존 두 prompt와 entry를 사용하는 agent가 artifact ID와 이미지/검사 한계를 전달하도록 일관된 안내를 받는다. wire·수명·public discovery는 동일하다.

### Task 4: 동일 episode 재실행과 관측된 회귀 고정

**Files:** Extend `scripts/evaluate_agent_plot.py`, `tests/mcp/agent_loop/test_oracle.py`, `tests/mcp/agent_loop/test_capture.py`; evidence/report는 scratch에 둔다.
**Interfaces:** `compare(baseline: Path, candidate: Path) -> dict`는 episode별 기존/개선 결과와 미확인을 반환한다. CLI `evaluate --run DIR`, `compare --baseline DIR --candidate DIR`는 gate 실패/unchecked이면 exit1, 검증 PASS면 exit0이다.

- [ ] **Step 1:** Task 2와 동일 모델/effort·host·env·fixture·예산으로 `uv run python scripts/run_agent_plot_eval.py run --label candidate --cases all --output-root "$AGENT_EVAL_ROOT"`를 한 번 실행해 네 case를 각각 1회 평가한다. 바뀐 환경/불가용 모델은 비교 불가로 기록하며 추가 반복으로 좋은 결과만 고르지 않는다.
- [ ] **Step 2:** 원판/수정판 source를 각각 bounded replay해 oracle의 값·행·mask·그룹·패널과 스타일 전후 불변을 비교한다. 현재 export와 같은 `dm.save_formats(..., formats=("png", "pdf"), validate=False, adopt_orphan_tick_font=False)`로 replay PNG를 만들고 원 PNG의 decoded pixels와 다르면 원 실행 의미는 `unchecked`다. 원 이미지·report·replay 결과를 별도 보존하고 `delivery`, `declared_validation`, `semantic_replay`, `visual_review`, `human_code_edits`를 구분한다.
- [ ] **Step 3:** 모델의 이미지 검토 도구 event와 판단 근거를 확인하고, 평가자는 실제 PNG의 잘림·가독성·라벨·단위·패널을 독립 검토한다. 전후를 같은 배율로 나란히 렌더하고 작은 차이는 확대 PNG를 만든다. 사용자에게 열 수 있는 scratch 이미지 PoC를 제품 머지/배포 전에 제시한다.
- [ ] **Step 4:** 실패한 실제 source/좌표를 최소 deterministic fixture로 축소해 기존 oracle/capture 시험에 추가하고 수정 전 FAIL을 본다. #498/#500/#501의 episode blocker가 나타나면 재현·최소 범위·후속 설계 판단만 기록한다. 미승인 실행/atomicity/데이터 수명 변경을 이 task에 넣지 않는다.
- [ ] **Step 5:** `uv run python scripts/evaluate_agent_plot.py compare --baseline "$AGENT_EVAL_ROOT/baseline" --candidate "$AGENT_EVAL_ROOT/candidate"`와 `uv run pytest tests/mcp/agent_loop -q`를 실행한다. 선택한 개선 대상은 값/행 정책·회수·스타일 불변·새 client 재조회·사람 코드 수정0 PASS가 필요하다. 네 회의 성공률을 일반 모델 성능으로 주장하지 않는다.
- [ ] **Step 6: Commit point:** `test: pin observed agent loop regressions and comparison criteria`.

**Expected:** 네 case 모두 결과/한계를 공개하고 선택한 개선의 기계 기준이 통과한다. 기준선 수집 완료와 개선 통과를 분리하며 실패·unchecked를 성공으로 바꾸지 않는다.

### Task 5: cheap PR gate와 사용·로드맵 문서 연결

**Files:** Modify `scripts/check_integration_junit.py`, `tests/test_check_integration_junit.py`, `docs/integrations/agent_plot_evaluation.md`, `docs/integrations/mcp_server.md`, `docs/ai/index.md`; 필요시 방향 문서의 0단계 진행 근거만 갱신.
**Interfaces:** 기존 JUnit CLI/exit code를 유지하고 protected modules에 `tests.mcp.agent_loop.test_oracle`, `tests.mcp.agent_loop.test_capture`를 추가한다. live 평가 CLI는 opt-in/manual/release 단일 환경용이며 PR required job에 넣지 않는다.

- [ ] **Step 1:** JUnit fixture에 새 두 module을 넣고 각각 missing/skipped/failure/error이면 exit1, passing case면 exit0인 시험을 먼저 작성한다. `uv run pytest tests/test_check_integration_junit.py -q` → 새 module 미보호 때문에 FAIL; checker를 최소 수정 후 PASS.
- [ ] **Step 2:** `.github/workflows/ci.yml`의 기존 `tests/` 수집·Python3.12 JUnit 검사에 새 cheap 시험이 연결됨을 확인한다. `uv run pytest tests/ -v --junitxml="$AGENT_EVAL_ROOT/pytest-final.xml"`과 `uv run python scripts/check_integration_junit.py "$AGENT_EVAL_ROOT/pytest-final.xml"` → PASS. 이 한 번의 대표 환경 최종 suite에 artifacts/discovery·data-repair·출하 색 hash·drift가 실제 실행되어 통과했는지 JUnit으로 확인한다. 같은 targeted suite를 다시 돌리지 않고 색 digest도 재생성하지 않는다.
- [ ] **Step 3:** `docs/ai/index.md`의 Deep dives toctree에 `Agent Plot Evaluation <../integrations/agent_plot_evaluation>`를 등록하고 MCP 페이지에서도 연결한다. `uv run sphinx-build -b html -W --keep-going -d docs/_build/doctrees docs docs/_build/html` → PASS. 현재 build_hooks의 원본 목록상 이번 안내는 llms-full 원본이 아니므로 dump를 수정하지 않는다. 다른 원본 변경 때만 기존 명시적 재생성 경로를 따른다.
- [ ] **Step 4:** recipe에 실제 확인한 CLI·예산·auth/이미지 smoke·evidence 위치·nullable usage·trusted replay 한계·수동 opt-in 절차를 기록한다. #483은 이 고리 안내가 범위이며 #482 진행 기준 갱신은 제안으로 남긴다. #499/#470은 독립 트랙, 다른 기존 P0는 backlog에서 유지한다. GitHub를 변경하지 않는다.
- [ ] **Step 5: Commit point:** `docs: connect agent loop evidence to existing cheap CI gates`.

**Expected:** 값싼 oracle/stdio 시험만 기존 PR gate에 포함되고 LLM 비용이 matrix로 증폭되지 않는다. 현재 v1 계약 유지와 실제 모델 평가의 한계를 독자가 재현할 수 있다.

## 다음 경계와 인계

0단계 다음은 불변 run/revision·retained input의 권한/수명/삭제·wire/discovery 계약을 별도로 설계·승인한다. hosted 실행·커뮤니티·docs 분할도 각 소유 경계로 남긴다.
실행은 AGENTS의 orchestrator+worker 방식으로 task별 구현·독립 검수 후 통합한다. 이 문서 self-review는 작성자가 수행하고 최종 계획 검토는 부모 orchestrator가 맡는다.

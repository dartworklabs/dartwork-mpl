# 에이전트 워크플로 전환: 현재 근거와 남은 일

2026-11-04 · 제품 기준 `origin/main` `cb6735c0` · 작업 트리 `t3-fc90bf3c`

이 기록은 기존 전환 계획의 진척과 공백을 대조한 진단이다. 2026-11-04 사용자의 명시적
선택으로 마스터플랜 문구를 기존 사전등록 기준에 맞췄다. 새 평가 기준이나 설계는 만들지
않는다. 기존 T3 세션과 구현 소유권을 나누며, 평가기·문항·MCP 계약은 바꾸지 않는다.

## 판단

현재 main의 설치형 native Python 경로와 skill 동봉은 실제 wheel 설치로 확인했다.
그러나 최종 main에 대한 결정 A/B, 공개 `dm.review`와 baseline 차이 API,
일반 사용자에게 전달할 새 릴리스는 확인되지 않았다. 따라서 전환 전체의 완료를
선언할 근거는 아직 없다. 튜닝 성공, 설치 성공, CI 성공, 배포 완료는 각각 구분한다.

## 근거의 위치와 한계

- 현재 진단 원본은 `/home/wonjun/scratch/dartwork-mpl-transition-20261104-fc90bf3c/`에 있다.
  아래에서 `근거/`는 이 디렉터리를 뜻한다.
- `근거/issues.json`은 공개 open 이슈 5개(#482·#483·#484·#485·#501),
  `prs.json`은 open Dependabot PR 15개를 담는다. 해당 조회에는 기능 PR이 없다.
  공개 #523·#524는 정지된 작성자 기록 때문에 접근하지 못했다. 닫혔다고 판정하지 않는다.
- `근거/main-runs.json`은 CI 대기·docs 배포 진행 중의 옛 스냅샷이다.
  후속 `main-runs-latest.json`은 `cb6735c0`의 CI·docs 배포·pre-commit 모두 성공을 확인한다.
  이는 이 제품 head의 결과이며 후속 로컬 수리나 새 릴리스의 원격 성공을 증명하지 않는다.
- 현 main wheel SHA-256은
  `458a7a646486fa034fa12337b9c2cdc6e94598bb9a3c40cac8c99f320dbdf729`다.
  `근거/wheel-acceptance/report.md`와 `stdout.json`이 설치·실행 원본이다.
- 과거 평가 수치와 현재 실행은 [기존 평가 기록](2026-10-22-agent-eval.md)을 함께 본다.
  모델·effort는 문서에 고정하지 않고 실행 시 선택한 `pilot-config.json`과 manifest에 기록한다.

## 전환 항목별 진단

| 항목 | 확인된 현재 상태 | 남은 경계 |
| --- | --- | --- |
| 0단계 평가 | harness·과거 기준선·16회 파일럿이 있다. 평가는 기본 pytest·CI 밖의 수동 실행이다(`evals/agentic/README.md:3–7`). 판정 문구는 사용자 선택으로 사전등록과 맞췄다. | 최종 main의 결정 A/B가 없다. 문항 범위·held-out 노출 처리를 먼저 정리해야 한다. |
| 1단계 진입 | 새 venv의 wheel에서 `--copy`가 두 skill 목적지에 설치했다. 8개 파일 × 2곳의 bytes가 wheel·설치 패키지와 일치하며 offline agent docs도 읽혔다. | 설치는 에이전트 발견·호출·준수의 증명이 아니다. 두 호스트의 실제 실행 근거가 따로 필요하다. |
| 설치 명령 | 실제 CLI는 `--dest`, `--copy`, `--force`다(`src/dartwork_mpl/skills/__main__.py:34–50`). | 마스터플랜의 `--claude/--codex`는 후속 사용자 결정으로 제거됐다. 이 변경은 기존 skill 계획 31–35행에 기록돼 있다. 옛 명령을 복원하지 않는다. |
| 2단계 레이아웃·native 루프 | 설치 wheel에서 Figure/Axes 생성 → layout → validate → PNG/PDF 저장·이미지 확인과 ylabel만 수정하는 경로가 통과했다. | CPython 3.14.6·Matplotlib 3.11.2 단일 환경의 acceptance다. 전체 지원 버전·고급 템플릿·모델 평가의 대체물이 아니다. |
| 3단계 검토 API | skill의 수동 native 저장·검증·이미지 확인 루프는 사용 가능하다. | 마스터플랜 128–137행의 얇은 `dm.review(fig, stem)`은 없다. 미구현을 보류하기로 한 결정도 기존 세션에서 확인되지 않았다. |
| 4단계 편집 API | 설치 acceptance의 ylabel 편집은 데이터·스타일·배치 등 나머지 snapshot 속성을 보존했다. | 마스터플랜 139–145행의 공개 baseline 중립 차이 API는 없다. 평가 전용 snapshot을 출하 API로 세지 않는다. |
| 5단계 배포 | 새 source wheel에는 skill과 최근 helper가 있다. | 공개 PyPI 최신 0.5.6 wheel에는 skill, `figsize_for`, `grid_shape`, `label_line_ends`가 없다. source 구현과 일반 사용자 전달이 갈라져 있다. |

설치 acceptance는 명시적 strict/preserve/clean 데이터 정책도 실행했다. strict는 NaN/Inf를
거부했고, preserve는 원 관측을 유지했으며, clean은 실제 제거 행을 보고했다. 입력은
변하지 않았다. `dm.review` 속성 접근과 지원하지 않는 설치 옵션의 실패도 그대로 남겼다.
MCP wire, 모델의 skill 사용, 다른 호스트·전체 버전 행렬은 이 acceptance에서 시험하지 않았다.

## 판정 문구의 정합화와 남은 실험 범위

1. **판정 문구의 불일치는 사용자 선택으로 해결했다.**
   사용자는 2026-11-04 “사전 등록 기준을 유지하고 마스터플랜 문구를 맞춘다”를 선택했다.
   [마스터플랜](../specs/2026-10-22-agentic-workflow-masterplan.md)의 개정2는
   [평가 사전등록](2026-10-22-agent-eval.md)과 `evals/agentic/compare.py:41–60`을 따른다.
   호스트별 inspection·lint 중 한 primary 이상이 차이 ≥ 0.10·사례 bootstrap 95% CI
   하한 > 0이고, 어느 primary도 worse(CI 상한 < 0)가 아니어야 한다.
   task_success 차이 CI 하한 > −0.05, tokens 비율 CI 상한 ≤ 1.10도 모두 필요하다.
   평가기·임계값·결과는 바꾸지 않았다. 값·explicit 편집 보존 실패와 contamination은
   실패로 남고 unsandboxed unit은 verdict를 차단한다. 실험 범위·held-out 처리는 별도다.
2. **문항 수와 실행 단위가 달라졌다.**
   등록 당시 40문항·320회는 역사적 실험 범위다. 현재 corpus는 50문항(생성32·편집18)이다
   (`evals/agentic/README.md:33`). 현재 전부를 두 호스트·두 arm·두 반복으로 택하면
   400회지만, 이 산술이 기존 등록 실험을 바꾸는 결정은 아니다. 실행 전에 문항 목록과
   wheel·host 설정·예산을 manifest로 고정하고 어느 실험인지 명시해야 한다.
3. **기존 held-out을 깨끗한 최종 표본으로 부를 수 없다.**
   README 220–226행은 10문항을 튜닝에서 보지 말라고 한다. 기존 세션은 v13–v24 튜닝에
   `e04/e08/e10/e14/g20` 사용을 보고했다. 이번에 확인한 `cust-v17`–`cust-v24`의
   20261104 manifest에도 이 다섯 개가 나타난다. 특히
   `/home/wonjun/scratch/dartwork-mpl-evals/cust-v23-20261104/manifest.json`은 다섯 개,
   `cust-v24-20261104/manifest.json`은 `g20`을 포함한다.
   `g03/g07/g11/g15/g24`는 확인한 튜닝 목록에는 없지만, 기존 전체 기준선은 관찰된 상태다.
   남은 다섯 개를 자동으로 새 holdout으로 선언하거나 과거 노출을 지우지 않는다.

## 이슈·계약·릴리스 공백

- **#482:** 상위 로드맵은 열려 있다. #523·#524의 공개 접근 실패를 보완할 현행 추적기가
  확인되지 않았다. 이 기록은 상태 연결점이며 새 공개 추적 이슈를 대신하지 않는다.
- **#501·#483:** 공개 상태는 최근 main의 #569(명시적 데이터 정책),
  #570(`label_axes` 진단·fractional highlight 거부) 반영을 따라가지 못한다.
  남은 object/`None`·다차원·complex 정책과 잘못된 recommender 선택의 `ToolError`는
  승인되지 않았다([후속 결정](2026-11-04-agent-followup-decisions.md) 80–92행).
  이슈 전체를 해결됐다고 닫거나 나머지 정책을 이번 작업에 끼워 넣지 않는다.
- **#484·#485:** 마스터플랜 16행이 별도 서비스와 docs 분리를 보류했다.
  설치형 패키지 전달의 장애와 이 서비스들의 미구현을 혼동하지 않는다.
- **MCP 안내 충돌:** skill은 요청하지 않은 제목을 추가하지 말라고 하지만
  (`src/dartwork_mpl/skills/dartwork-mpl/SKILL.md:61–64`),
  `src/dartwork_mpl/mcp/guides/prompts.py:241–245`는 제목을 넣는 예제를 가르친다.
  MCP 이름·순서·schema·docstring 동결은 유지한다. 안내 본문 정합화의 범위와 소유자를
  먼저 정하고, 동결 계약을 바꾸는 일까지 승인됐다고 해석하지 않는다.
- **기존 경고 보존:** “only X” 편집에서 원래의 `LEGEND_OVERLAP`을 보존·보고하는 것이
  현 skill 정책이다(SKILL.md 94–97행). 평가를 좋게 만들려고 범례를 자동 수정하지 않는다.
- **릴리스:** `근거/releases.json`, `pypi-latest.json`, `published-wheel-audit.json`은
  최신 공개 배포가 7월 5일 0.5.6임을 보여 준다. 새 버전 결정·배포는 남아 있다.
  `release-parity-repro.json`은 source 대비 wheel 누락147개(대부분 제외된 시험 파일)를
  확인했다. 기대 payload 산정을 실제 출하 규칙에 맞춘 수리는 `ac7b2750`이다.
  원래 shell은 exit 1, 수리 후 실제 wheel 569개 비교는 exit 0이었다. 런타임 모듈을
  하나 뺀 ZIP은 exit 1이다. 이는 로컬 gate 수리이며 전체 release workflow·게시 성공은 아니다.
- **다운스트림:** company-analysis가 `9fa473cb`에 고정됐다는 것은 기존 인계 근거다.
  이번 작업에서 그 저장소를 실시간 재확인하지 않았다. 갱신은 그 저장소 소유자가 맡는다.

## 이번 확인 결과

- Codex custom `CODEX_HOME`의 session 위치와 환경 감시 대상이 어긋난 harness 결함을
  `48ff227b`에서 수리했다. 평가 기준이나 문항 내용은 바꾸지 않았다.
- 첫 실행 `main-cb6735c0-pilot-fc90bf3c-20261104`은 Codex 8건이 설정 로딩에서
  멈춰 환경 오류로 보존했다. 빈 HOME에서도 disabled MCP 설정이 유효하도록
  `efb78189`에서 보정했다. 이 실행에서 skill 효과를 판단하지 않는다.
- 새 파일럿 ID: `main-cb6735c0-pilot2-fc90bf3c-20261104`.
  위치: `/home/wonjun/scratch/dartwork-mpl-evals/` 아래 같은 이름의 디렉터리.
  manifest는 제품 wheel 위 SHA와 harness `efb78189`를 고정한다.
  4문항 × 2호스트 × 2arm = 16회이며, 모델·effort·예산은 manifest와
  `근거/pilot-config.json`을 따른다. 기준 개선이나 전환 완료를 판정하는 실험은 아니다.
- **파일럿 최종 결과:** 계획 16회 모두 실행·task success 통과, 값 검사 32/32와 explicit 편집 보존 8/8 통과다.
  skill 발견·호출 및 최종 PNG 확인은 skill arm 8/8이다. 각 호스트의 4문항 표본에서
  tokens 비열등 CI가 기준을 넘으므로 최종 판정은 모두 `no demonstrated gain`이다.
  원본 `summary.md`·`results.jsonl`과 `근거/pilot2-comparison.txt`를 함께 보존했다.
  `근거/pilot2-results-and-budget.json`의 단순 선형 추정은 320회 약 37.4M tokens,
  400회 약 46.8M tokens다(캐시 포함). 쉬운 네 문항의 투영이며 어려운 사례의 예측값은 아니다.
  Claude의 보고 list cost 투영은 각각 약 $14.06/$17.57이며 구독 청구액이 아니다.
  Codex 금액 근거는 없어 산정하지 않았다. 본평가는 아직 실행하지 않았다.
- **release gate 로컬 검증:** 실제 shell의 정상 wheel 통과·모듈 누락 거부, 관련 22개 시험이 통과했다.
  평가 하네스는 최종 보정 후 전체 232개 시험이 178.77초에 통과했다. 원격 CI·릴리스는 이 로컬 결과와 별개다.

## 순서·소유자·완료 범위가 있는 다음 작업

1. **평가 harness 담당 → 통합 담당(로컬 확인 완료):** custom-home 격리·own-rollout
   수집·예산 감시의 회귀 시험과 실제 파일럿 원본을 보존했다. 머지 전에는 대상 head의
   required checks를 확인한다. 첫 실행의 환경 오류를 지우거나 성공으로 바꾸지 않는다.
2. **통합 담당(파일럿 집계 완료):** 위 결과와 비용 투영을 본평가 준비 자료로 사용한다.
   작은 표본에서 입증되지 않은 효과를 완료로 쓰지 않는다.
3. **기존 전환 세션·기준 결정권자:** 판정은 사용자가 선택한 사전등록 기준을 유지한다.
   큰 실행 전에 40/50문항 범위와 held-out 노출 처리 방식을 명시적으로 기록한다.
   통합 담당은 그 결정으로 고정한 immutable manifest만 실행한다. 이번 선택에서 추가 결정을 추정하지 않는다.
4. **기존 전환 세션:** `dm.review`와 baseline 중립 차이의 미구현을 추적 가능한 작은
   후속 계획으로 정리한다. 기존 save/validate를 감싸는 범위와 deferred 범위를 명시하고,
   평가 내부 snapshot을 그대로 공개하지 않는다. 구현 소유권·실행 가능한 검증을 정한 뒤 착수한다.
5. **릴리스 담당 → 통합 담당:** wheel payload gate 수리와 실제 shell 결과를 검토하고,
   새 버전·릴리스 범위를 결정한다. 그 후보 wheel의 설치·offline 안내·native 경로와
   정확한 head의 required checks를 확인한 뒤 기존 배포 절차를 진행한다. 다운스트림 갱신은 별도 인계한다.
6. **별도 서비스 담당:** #484·#485는 기존 보류 조건이 충족됐는지 판단할 때 재검토한다.
   현재 패키지 평가나 공개 API 작업의 소유권에 합치지 않는다.

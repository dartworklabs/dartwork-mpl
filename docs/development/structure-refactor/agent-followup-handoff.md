# 다른 컴퓨터 세션의 후속 작업 인계

2026-11-04 작성. 이 문서는 다음 세션이 중복 구현 없이 이어 가기 위한 인계 자료다.
현황 표는 [구조 리팩터 계획](README.md)에 있다. 이 문서로 새 설계나 정책을 승인하지 않는다.

**인계 완료 · 2026-11-04.** 수신 세션이 정해져 이어받았다. ml-main 의 masterplan 세션이
#501 작업 7 범위를 받았고, 이 체크아웃의 세션이 아래 잔여 결정을 받았다. 같은 기기의 다른
두 세션은 각각 pixel1-google-photo·dataset-catalog 작업이라 dartwork-mpl 과 겹치지 않음을
직접 확인했다. 워크트리 `t3-0c3dff26` 에는 병합되지 않은 MCP·viewer 커밋이 남아 있으므로
그 경로는 건드리지 않았다.

## 병합된 작업과 확인 범위

- [#549](https://github.com/dartworklabs/dartwork-mpl/pull/549), `2aab9d8110a9f30c1e1f7846c5f83b5c042848f0`:
  helpers를 소유 슬라이스의 호환 alias로 정리하고 prompt 경로 소유권·테스트 재배치·에이전트 수정 안내를 반영했다.
  `src/dartwork_mpl/helpers/`, `src/dartwork_mpl/prompt/`, `tests/architecture/test_boundaries.py`, `scripts/check_integration_junit.py`에서 확인할 수 있다.
- [#562](https://github.com/dartworklabs/dartwork-mpl/pull/562), `13f1575b63d1564cc7d3afa91de9638f5df64dcb`:
  입력 정책 fixture를 공유 runner 경로 밖의 사용자 소유 임시 디렉터리로 격리했다.
  `tests/mcp/artifacts/conftest.py`의 소유권·모드 검사는 유지한다.
- [#563](https://github.com/dartworklabs/dartwork-mpl/pull/563), `a6e0c4509aaa4477152960f94125db541c593ad3`:
  self-hosted Python job의 xdist worker는 4개, Python matrix 동시 job은 2개로 제한했다.
  해당 커밋의 [전체 CI](https://github.com/dartworklabs/dartwork-mpl/actions/runs/41791298918),
  [pre-commit](https://github.com/dartworklabs/dartwork-mpl/actions/runs/41791298948),
  [문서 배포](https://github.com/dartworklabs/dartwork-mpl/actions/runs/41791298892)가 통과했다.
  Python 3.10–3.13 모두 통과했고 실제 로그에서도 worker 4개·최대 동시 job 2개를 확인했다.
- 소스 대조 기준 `d5d8453c02b43646b6185f50eaf04744eb84922a`에는 후속
  [#564](https://github.com/dartworklabs/dartwork-mpl/pull/564)의 concise 날짜 형식·`PRESET_OVERRIDE` 경고 수정도 있다.
  위 `a6e0c450` 실행 결과는 이 후속 커밋의 전체 CI 통과 증거가 아니다.
- 이후 [#566](https://github.com/dartworklabs/dartwork-mpl/pull/566)·[#567](https://github.com/dartworklabs/dartwork-mpl/pull/567)·[#568](https://github.com/dartworklabs/dartwork-mpl/pull/568)
  (post-merge 수정·eval·visual)과 [#569](https://github.com/dartworklabs/dartwork-mpl/pull/569) (`a891272a`)가 병합됐다.
  #569 는 #501 작업 7 의 승인된 option A — `dm.validate_data(..., policy=…)` 의 strict/preserve/clean,
  `allow_nan` 관계, 원본 인덱스 진단 — 를 넣었고 생략 시 기존 동작을 보존한다.
  구현 기록은 [데이터 정책 계획](../../superpowers/plans/2026-11-04-explicit-data-policy.md)에 있다.
  현재 main 은 `a691e285`이고, 이 head 자체의
  [CI](https://github.com/dartworklabs/dartwork-mpl/actions/runs/41835359707)·[pre-commit](https://github.com/dartworklabs/dartwork-mpl/actions/runs/41835359528)·[문서 배포](https://github.com/dartworklabs/dartwork-mpl/actions/runs/41835360221)가
  모두 통과했다(2026-11-04 확인). 앞선 `a6e0c450`·`a891272a` 실행을 재사용한 것이 아니다.
- [#570](https://github.com/dartworklabs/dartwork-mpl/pull/570), `cb6735c0`: 아래 잔여 결정 세 건의
  구현과 기록을 병합했다 — `label_axes` 의 키워드 진단, 범위 안 소수 `highlight` 거부, 현황 재조정.
  병합 커밋 `cb6735c09c66810081690711ed70f5c998c347eb` 자체의
  [CI](https://github.com/dartworklabs/dartwork-mpl/actions/runs/41845473175)·[pre-commit](https://github.com/dartworklabs/dartwork-mpl/actions/runs/41845473317)·[문서 배포](https://github.com/dartworklabs/dartwork-mpl/actions/runs/41845473648)가
  `push` 이벤트로 모두 통과했다(2026-11-05 확인). PR head `bd81bd4e` 의 체크 통과를 main 통과로
  바꿔 쓴 것이 아니다. 이후 main 은 다른 세션의 작업으로 더 진행됐고, 그 head 의 CI 는 이 문서가
  확인한 범위가 아니다.

네이티브 matplotlib `Figure`/`Axes`, 스타일 프리셋, 물리 단위 크기, 내용에 맞춘 유연한 레이아웃을 유지한다.
그림은 `dm.style.use(...)`, `dm.figsize(...)`, `dm.simple_layout(fig)`를 사용하고
글꼴·선·굵기는 `dm.fs`·`dm.lw`·`dm.fw`로 프리셋에 맞춘다. 에이전트 안내를 고칠 때도 이 사용법을 보존한다.

## 남아 있는 범위

| 대상 | 이어 갈 일과 경계 |
| --- | --- |
| [#483](https://github.com/dartworklabs/dartwork-mpl/issues/483) | 작업 2의 런타임 진단은 결정·구현됐다 ([결정 기록](../../superpowers/plans/2026-11-04-agent-followup-decisions.md)). 예외 종류는 측정값대로 유지하고 메시지만 `label_axes`·지원 인자·네이티브 `ax.text` 경로를 담는다. `horizontalalignment`·`verticalalignment`는 받아들여진 뒤 조용히 버려졌으므로 같은 `TypeError`로 바뀌었다 — 이 한 가지가 의도된 동작 변경이다. 작업 1·1e·wheel/layout 종합 수락란은 여전히 열려 있고, 재현되지 않은 typography 결함이나 Noto Regular 400 fallback만으로 경고 억제를 추가하지 않는다 |
| [#501](https://github.com/dartworklabs/dartwork-mpl/issues/501) | task 7의 strict/preserve/clean·`allow_nan`·원본 인덱스는 option A로 승인돼 #569로 반영됐다. task 8의 범위 안 소수 `highlight` 거부도 결정·구현됐다. **남은 미승인:** task 7의 object `None`·다차원·complex 정책, task 8의 잘못된 recommender 선택 `ToolError` 전환(#523 MCP 동결·미병합 MCP 작업과 충돌). 범위 밖 `highlight`는 소수여도 계속 무시한다. 현재 네이티브 동작·wire 의미를 먼저 보존한다 |
| D3 | 결정됐다 — pre-commit 표시 이름을 유지한다. main 의 branch protection 필수 컨텍스트가 `Run pre-commit on changed files` 문자열 자체(app_id 15368)임을 확인했고, 이름을 바꾸면 보호 규칙 컨텍스트를 같은 작업에서 갱신해야 하며 어긋나면 모든 PR 머지가 막힌다. 얻는 것은 표시 문구뿐이다. 색 검사의 목적이 다르므로 중복처럼 보인다는 이유로 삭제하지 않는다 |
| [#484](https://github.com/dartworklabs/dartwork-mpl/issues/484) | 홈페이지·계정·커뮤니티·호스팅 MCP는 별도 서비스 제품 범위다. 배치 대상·인증 방식을 정하지 않았으며 이 패키지에 서비스를 추가하라는 지시가 아니다 |
| [#485](https://github.com/dartworklabs/dartwork-mpl/issues/485) | docs 작성·호스팅 분리는 별도 제품 범위다. 버전 연결과 wheel 오프라인 가이드를 보존해야 한다. 대상 저장소·호스팅·인증 방식은 아직 정하지 않았다 |

#483·#501은 열린 상태로 이어 간다. 부분 구현·문서 안내·CI 수리를 전체 정책 완료로 해석하지 않는다.
#483의 대표 실패·wheel/layout 종합 수락란은 근거를 나누어 남긴 것이며, 이 인계가 광범위한 재실행이나 새 개발을 요구하는 것은 아니다.

## 다음 세션의 시작 순서

1. 자신의 체크아웃에서 `git status --short`로 미커밋 작업을 먼저 확인하고 `git fetch origin`을 실행한다.
   `git log -8 --oneline origin/main`과 위 PR의 병합 커밋을 대조한다. 다른 세션의 수정은 덮어쓰거나 정리하지 않는다.
2. `gh pr list`와 담당 경로의 최근 이력을 확인한다. 이 컴퓨터에서 끝난 작업과 다른 컴퓨터의 미커밋 작업을 대조하고,
   이어 갈 차이만 정한다. 동일 기능을 새로 구현하거나 기존 브랜치를 일괄 초기화하지 않는다.
3. 현행 `AGENTS.md`를 읽고 아래 금지 경로를 먼저 제외한다. #483·#501에서 정책 결정이 필요한 부분을 맡는다면
   사용자에게 범위와 바뀔 동작을 제시하고 승인을 받은 뒤 구현한다. #484·#485의 배치·인증은 별도로 결정한다.
4. 맡은 범위의 기존 검사를 실제로 실행하고 결과를 읽는다. 예를 들어 helpers/prompt 소유권을 확인할 때는 다음처럼 범위를 제한한다.

   ```sh
   uv run pytest -q src/dartwork_mpl/helpers/tests src/dartwork_mpl/prompt/tests tests/architecture/test_boundaries.py tests/tools/test_check_integration_junit.py
   ```

   #501 데이터·추천 작업은 `src/dartwork_mpl/validate/tests/test_data_ownership.py`,
   `src/dartwork_mpl/_colors/tests/test_make_palette.py`,
   `src/dartwork_mpl/mcp/recommend/tests/test_chart_type_transport.py` 등 담당 계약의 기존 검사를 확인한다.
   실패하면 실행 커밋·명령·출력과 미해결 원인을 해당 작업 기록에 남기고, 기대값을 바꿔 실패를 숨기지 않는다.
5. 문서·화면·차트의 보이는 결과를 바꾸면 같은 배율의 전후 렌더를 사용자에게 보여 준 뒤 머지·배포한다.
   최신 main의 CI는 해당 SHA의 실행 결과로 따로 확인한다. 이 문서의 과거 성공을 재사용하지 않는다.

## 승인 경계와 금지 파일

현황 정리·문서 병합·인계 전달은 승인됐고 전달은 끝났다. 위 세 잔여 결정(#483 작업 2, D3,
#501 소수 `highlight`)은 2026-11-04 사용자가 이 세션에 위임해("너가 철저히 진단해서 결정해봐")
근거와 함께 결정했다. 새 정책이나 서비스 목적지·인증 선택은 이 인계로 승인되지 않는다.
#483·#501은 위 표의 남은 항목이 있어 계속 열어 둔다. ADR의 동결과 공개 계약은 유지하며,
`tests/test_shipped_colors_hash.py`의 digest를 실패 회피 목적으로 재생성하지 않는다.

**`docs/superpowers/specs/2026-10-20-agent-contract-repairs-design.md`와 그 사본은
읽기·검색·해시·복사하지 않는다.** 광범위한 docs 검사로 이 경로에 간접 접근하지 않는다.
이 제한과 필요한 검사가 충돌하면 제한을 우회하지 말고 허용되는 검사 범위·미확인을 기록한다.

## 이 컴퓨터의 근거 보관소

아래는 이 컴퓨터에만 있는 로컬 아카이브다. 다른 컴퓨터에 같은 경로가 있다고 가정하지 말고,
위 GitHub PR·run과 저장소 파일을 먼저 사용한다. 아카이브를 실제로 옮겼다는 뜻도 아니다.

- `~/scratch/dartwork-https-pr-resume-2026-11-04/merged-receipt.json`: #549 병합 영수증.
- `~/scratch/dartwork-self-hosted-ci-2026-11-04/concurrency/`:
  `postmerge-runtime-proof.json`, `REPORT.md`, `status.json`에 #563 병합 후 실행·worker·동시성 근거가 있다.
  CI 수리의 예약 확인은 꺼져 있고 다음 실행은 없다.

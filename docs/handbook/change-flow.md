---
orphan: true
---

# 변경 흐름, 릴리스, 용어

## 결정 권한

최종 결정은 소유자(CTO)가 내린다. 소유자의 새 결정은 이전 ADR의 잠금보다 우선한다. 다만 잠금을 푸는 일은 그 결정을 기록하는 별도 ADR로 남긴다. 다른 결정 문서 안의 한 조항으로 잠금을 풀지 않는다. 그래야 무엇이 언제 왜 풀렸는지 나중에도 추적할 수 있다. 출처: [ADR 0008](../adr/0008-owner-priority-lock-reset.md) 결정 3.

에이전트와 기여자가 혼자 정하지 않는 것은 다음과 같다.

- 미감 변경. 소유자가 before/after 그림을 본 뒤에만 한다.
- 기존 잠금 해제나 새 잠금 도입.
- 정량 게이트의 기준 완화.
- 릴리스.

## 설계에서 머지까지

1. **읽기**: 이 Handbook에서 관련 topic만 읽는다.
2. **설계**: 동작이 바뀌면 spec을 쓴다. 되돌리기 어렵거나 trade-off가 있으면 ADR을 쓴다. 설계 문서는 200줄을 넘지 않는다. 넘으면 일을 쪼갠다.
3. **판정기 먼저**: 리뷰 기준이 될 기계 검사를 먼저 둔다. golden 파일, digest, 측정한 임계값 같은 것이다. 판정기 없이 리뷰어 의견만 쌓으면 리뷰가 끝나지 않는다.
4. **시공**: slice 단위로 작게 나눈다.
5. **검수**: [verification.md](verification.md)의 게이트를 돌린다.
6. **동기화**: 현재 상태가 바뀌었으면 같은 PR에서 Handbook을 고친다.

완료 기준은 이 리포의 개발 환경에서 실행할 수 있어야 한다. 아무도 갖지 않은 하드웨어나 도구가 필요한 기준은 쓰지 않는다.

## 브랜치와 태그

소유자가 2026-11-16에 정했다. 장기 브랜치는 `develop`과 `main` 둘뿐이고, PyPI 버전은 태그가 관리한다.

| 이름 | 뜻 | 들어가는 방법 |
| --- | --- | --- |
| 태그 `vX.Y.Z` | PyPI 버전. 태그를 push하면 그 커밋이 그 버전으로 PyPI에 올라간다 | 아래 "태그를 다는 자리" |
| `main` | 릴리스해도 되는 상태. PyPI보다 앞서 있을 수 있다 | `develop`에서 PR, CI 통과 |
| `develop` | 다음에 `main`으로 갈 것. 기본 브랜치 | 작업 브랜치에서 PR, CI 통과 |
| 작업 브랜치 `<종류>/<이름>` | 한 가지 일 | 자유롭게 만들고 push한다. 머지되면 지운다 |

PyPI에 무엇이 있는지는 태그만 본다. `main`은 PyPI와 같지 않다.

**태그를 다는 자리.** 정식 버전(`v0.8.0`)은 `main`의 커밋에 단다. 사전 버전(`v0.8.0a1`, `v0.8.0rc1`)은 `develop`의 커밋에 단다. 사전 버전은 정식으로 내기 이른 것을 허브나 시험 사용자에게 먼저 줄 때 쓴다. `pip install dartwork-mpl`은 사전 버전을 고르지 않는다.

**버전.** 1.0 전까지는 공개 이름이나 그림의 모습이 바뀌면 가운데 자리를, 고치기만 했으면 끝자리를 올린다.

`develop`과 `main`에는 누구도 직접 push하지 않는다. 조직 소유자도 예외가 아니다. force-push와 삭제도 막혀 있다. 이 규칙은 아래 [리포 잠금](#리포-잠금)의 ruleset이 강제한다. `main`으로 가는 PR의 출발 브랜치가 `develop`인지, 태그가 맞는 브랜치의 커밋에 달렸는지는 설정으로 강제되지 않는다. 사람이 지킨다.

**긴급 수정.** 이미 나간 정식 버전의 결함은 `main`에서 `hotfix/<이름>`을 따서 `main`으로 PR을 낸다. 끝자리를 올려 릴리스하고, 같은 커밋을 `develop`으로 되돌려 병합한다.

허브가 이 리포의 어떤 버전을 쓰는지는 [../hub-contract.md](../hub-contract.md)에 있다.

## 리포 잠금

사용자에게 닿는 문은 셋이고, 여는 사람은 최종 검토자인 소유자(`Sangwon91`) 하나다([ADR 0010](../adr/0010-release-gates.md)). 에이전트는 소유자의 지시로 일하므로 소유자와 같은 계정을 쓴다. 그래서 세 문의 승인은 **소유자가 대화나 리뷰에서 내린 명시적 지시**("병합", "릴리스", "배포")다. 에이전트는 그 지시 없이 문을 열지 않는다. 아래 설정은 다른 사람과 사고를 막는 기술적 잠금이다.

| 문 | 강제하는 설정 | 열 수 있는 사람 |
| --- | --- | --- |
| `main`으로 병합 | ruleset `release-gate`: `main`의 갱신을 막는다. 팀 `release-owners`만 PR로 우회한다 | `release-owners`(소유자 한 명) |
| `v*` 태그 | ruleset `version-tags`: 태그 생성·변경·삭제를 막는다 | `release-owners` |
| PyPI 업로드 | environment `pypi`: 필수 승인자 소유자, `v*` 태그에서만 돈다. PyPI trusted publisher가 이 environment에 묶여 있다 | 소유자 |

`main` 병합은 일반 병합이 거부되므로 CI가 통과한 뒤 `gh pr merge <n> --admin`으로 한다. `--admin`은 `release-owners`의 우회이고, 우회가 없는 `quality-gate`는 건너뛰지 못한다. `develop` → `main`은 두 브랜치의 히스토리가 갈라지지 않게 merge commit(`--merge`)으로 넣는다.

ruleset `quality-gate`는 `develop`과 `main`에 PR, CI(`lint`, `test`) 통과, force-push·삭제 금지를 걸고 우회가 없다. 소유자도 CI를 건너뛸 수 없다. ruleset은 조직 소유자에게도 적용된다. 조직 소유자는 ruleset 자체를 고칠 수 있지만 고치면 조직 감사 로그에 남는다. 이 잠금은 1차 보호막이다.

## 릴리스

릴리스는 소유자의 지시로만 한다. 순서는 다음과 같다.

1. `develop`에서 버전과 `CHANGELOG.md`를 맞춘 PR을 병합한다.
2. `develop` → `main` PR을 소유자가 병합한다(사전 버전은 이 단계를 건너뛰고 `develop`의 커밋에 태그한다).
3. 소유자가 태그를 push한다.
4. `pypi` environment의 승인 요청을 소유자가 승인한다.
5. 허브가 새 버전으로 고정을 올린다([../hub-contract.md](../hub-contract.md)). 허브는 PyPI에 없는 판을 운영에 싣지 않는다.

`v*.*.*` 태그를 push하면 `.github/workflows/release.yml`이 실행된다. 이 workflow는 승인을 기다린 뒤 다음 순서로 진행한다.

1. 태그가 `pyproject.toml`의 `version`과 같은지 확인한다.
2. sdist와 wheel을 빌드한다.
3. PyPI trusted publisher로 올린다.
4. GitHub release를 만든다.

테스트는 다시 돌리지 않는다. `develop`과 `main`의 커밋은 모두 CI를 통과한 PR로 들어오기 때문이다. 태그 전에 `pyproject.toml`의 `version`, `skills/dartwork-mpl/SKILL.md`의 `metadata.version`과 첫 줄의 버전, `CHANGELOG.md`를 맞춘다. 앞의 둘이 다르면 `test_guidance.py`가 실패한다.

배포 상태의 정본은 PyPI와 태그다. 이 라이브러리는 서버를 운영하지 않으므로 관찰·복구 절차는 릴리스 되돌리기뿐이다. PyPI는 같은 버전을 다시 올릴 수 없으므로 되돌리기는 다음 patch 릴리스로 한다. 결함이 심하면 그 버전을 PyPI에서 yank해 새 설치가 고르지 않게 한다.

## 용어

| 용어 | 이 리포에서의 뜻 |
| --- | --- |
| slice | 기능 하나를 담은 패키지. 표면은 `__all__` |
| platform | 업무를 모르는 공용 메커니즘. slice를 import하지 않는다 |
| preset | `dm.style.use`로 고르는 스타일 묶음. 글자·선 크기의 기준값을 정한다 |
| 미감 | 색 값, 폰트, 글자 무게, spine, grid, preset 모양. 불변식 대상 |
| 판정기 | 사람 의견 없이 합격·불합격을 내는 기계 검사 |
| ratchet | 위반 수를 파일별로 고정하고 줄어들기만 허용하는 검사 |
| 산출물(artifact) | 렌더 한 번의 결과 묶음. 이미지, 원본 코드, 리포트, manifest |
| 잠금(동결) | ADR이 바꾸지 못하게 고정한 범위. 별도 ADR로만 푼다 |

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

## 브랜치 전략

장기 브랜치는 `develop`과 `main` 둘뿐이다. 소유자가 2026-11-15에 정했다.

| 브랜치 | 들어가는 방법 | 조건 |
| --- | --- | --- |
| 작업 브랜치 | 자유롭게 만들고 push한다 | 없음 |
| `develop` | 작업 브랜치에서 PR | CI의 `lint`와 `test` 통과 |
| `main` | `develop`에서 PR. 충분히 안정된 뒤 병합만 한다 | CI의 `lint`와 `test` 통과 |

`develop`과 `main`에는 누구도 직접 push하지 않는다. 관리자도 예외가 아니다. force-push와 삭제도 막혀 있다. 기본 브랜치는 `develop`이어서 PR은 기본으로 `develop`을 향한다. `main`은 릴리스할 수 있는 상태만 담는다. 릴리스 태그는 `main`에서 만든다.

이 규칙은 GitHub 브랜치 보호 설정이 강제한다. `main`으로 가는 PR의 출발 브랜치가 `develop`인지는 설정으로 강제되지 않는다. 사람이 지킨다.

## 리포 잠금 (현재)

리팩터 기간 동안 소유자 계정(`Sangwon91`)만 쓸 수 있다. GitHub ruleset 두 개가 막는다.

| ruleset | 대상 | 막는 것 |
| --- | --- | --- |
| `freeze-refactor-sangwon91-only` | 모든 브랜치 | 생성, push, 삭제, force-push. PR 머지 포함 |
| `freeze-refactor-tags-sangwon91-only` | 모든 태그 | 생성, 수정, 삭제 |

admin 권한을 가진 다른 계정은 ruleset을 끌 수 있다. 그래서 이 잠금은 기술적 강제이면서 합의이기도 하다. 해제는 소유자가 정한다. 해제하려면 ruleset을 삭제한다(`gh api -X DELETE repos/dartworklabs/dartwork-mpl/rulesets/<id>`).

## 릴리스

`v*.*.*` 태그를 push하면 `.github/workflows/release.yml`이 실행된다. 이 workflow는 다음 순서로 진행한다.

1. 전체 테스트를 다시 돌린다.
2. 패키지에 들어가는 색 정본과 동결 색을 대조한다.
3. sdist와 wheel을 빌드한다.
4. PyPI trusted publisher로 올린다.

태그 전에 할 일은 두 가지다.

- `pyproject.toml`의 `version`과 `CHANGELOG.md`를 맞춘다.
- 제거한 이름은 제거 registry에 올린다.

배포 상태의 정본은 PyPI와 태그다. 이 라이브러리는 서버를 운영하지 않으므로 관찰·복구 절차는 릴리스 되돌리기뿐이다. PyPI는 같은 버전을 다시 올릴 수 없으므로 되돌리기는 다음 patch 릴리스로 한다.

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

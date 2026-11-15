---
orphan: true
---

# 검증 게이트

PR은 아래 게이트로 합격을 판정한다. 각 게이트는 무엇을 재는지, 언제 돌리는지, 어떤 명령으로 돌리는지, 무엇이면 합격인지를 함께 적는다. 실행하지 않은 게이트는 통과가 아니라 `NOTRUN`으로 보고한다.

## 리팩터 PR의 제1 판정기

구조를 옮기거나 정리하는 PR은 그림을 바꾸지 않는다. 그래서 다음 두 조건을 먼저 본다.

1. 색 해시와 픽셀 baseline 게이트가 그대로 통과한다.
2. 경계 검사와 안티패턴 ratchet의 수치가 늘지 않는다.

기능을 제거하는 PR은 제거한 기능의 테스트와 baseline을 함께 지운다. 남은 기능의 픽셀은 움직이지 않아야 한다. 출처: [ADR 0009](../adr/0009-blueprint.md) 결정 2.

## 게이트

| 게이트 | 측정 대상 | 적용 조건 | 명령 | 합격 기준 |
| --- | --- | --- | --- | --- |
| 전체 테스트 | 동작 계약 | 모든 PR | `uv run pytest` | 실패 0. 건너뛰기로 실패를 숨기지 않는다 |
| 타입 | 정적 계약, union 분기 누락 | 모든 PR | `uv run mypy` | 오류 0. 설정은 `pyproject.toml`의 `[tool.mypy]` strict |
| 출하 색 해시 | 미감: 색 값 | 모든 PR | `uv run pytest tests/test_shipped_colors_hash.py` | 통과. digest를 다시 만들어 통과시키지 않는다 |
| 픽셀 baseline | 미감: 렌더 결과 | 모든 PR | `uv run pytest tests/visual` | 각 장면 RMS ≤ 0.5 |
| slice 경계 | import 방향과 표면 | 모든 PR | `uv run pytest tests/architecture` | 위반 0, `DEBT` 비어 있음 |
| 안티패턴 ratchet | 예제·문서 스크립트·템플릿의 critical·warning 수 | 모든 PR | `uv run pytest tests/test_antipattern_ratchet.py` | 파일별 수가 baseline 이하 |
| pre-commit | 포맷·lint | 모든 PR | `uv run pre-commit run --files <바뀐 파일>` | 통과 |
| 기본 설치 smoke | extras 없는 import | CI | `.github/workflows/ci.yml`의 no-extras job | 통과 |
| MCP 실행 증거 | MCP·통합 테스트가 실제로 돌았는지 | CI | `scripts/check_integration_junit.py` | 통과 |

`main` 브랜치 보호에는 CI의 필수 check가 걸려 있다. lint, Python 3.11·3.12·3.13 test, test-no-extras, docs, matplotlib 최소 버전 test, pre-commit이다.

## 핵심 수치와 근거

**픽셀 RMS 0.5** (`tests/visual/test_visual_pixels.py`의 `PIXEL_TOLERANCE`). 측정 결과는 세 가지였다.

- CI 환경 사이의 잡음은 최대 RMS 0.007이다.
- 가장 작은 실제 변화인 눈금 라벨 한 글자는 1.65다.
- 0.5는 잡음보다 70배 크고, 가장 작은 변화보다 3배 작다.

이 값을 올리면 실제 변화가 통과한다.

**색 해시.** 출하하는 모든 색 값을 digest로 고정한다. 실패는 출하 색이 움직였다는 뜻이다. 테스트를 고칠 일이 아니라 소유자가 결정할 일이다.

**ratchet baseline** (`tests/antipattern_baseline.json`). 파일별 허용 수다. 고쳐서 수가 줄면 `uv run python tests/test_antipattern_ratchet.py --update`로 낮춘다. 수를 올리려고 갱신하지 않는다.

## 알려진 공백

- 안티패턴 ratchet은 아직 `main`에 없다. 현재 baseline으로는 `evals/` 아래 파일들에서 실패한다. 그중 일부는 일부러 잘못 만든 대조군이라 검사 대상에서 뺄지 정해야 한다.
- 에이전트 평가(`evals/`)는 결과를 기록할 뿐 합격·불합격을 내리지 않는다. 정량 게이트가 아니다.
- functional core 분리에는 아직 기계 검사가 없다. `DECISIONS`에 지정된 모듈만 검사된다.

---
orphan: true
---

# 검증 게이트

PR은 아래 게이트로 합격을 판정한다. 실행하지 않은 게이트는 통과가 아니라 `NOTRUN`으로 보고한다.

## 게이트

| 게이트 | 측정 대상 | 명령 | 합격 기준 |
| --- | --- | --- | --- |
| lint·포맷 | 코드 형식 | `uv run ruff check && uv run ruff format --check` | 통과 |
| 타입 | 정적 계약 | `uv run basedpyright` | 오류 0. strict 모드. 기존 오류는 `.basedpyright/baseline.json`에 있고 줄어들기만 한다 |
| 전체 테스트 | 동작 | `uv run pytest -q -n auto --mpl` | 실패 0 |
| 출하 색 해시 | 미감: 색 값 | 전체 테스트에 포함 (`tests/test_shipped_colors_hash.py`) | 통과. digest를 다시 만들어 통과시키지 않는다 |
| 픽셀 baseline | 미감: 렌더 결과 | 전체 테스트에 포함 (`tests/visual`, `--mpl` 필요) | 장면 20개 각각 RMS ≤ 0.5 |
| slice 경계 | import 방향과 표면 | 전체 테스트에 포함 (`tests/architecture/test_boundaries.py`) | 위반 0 |
| 도메인 파일 규칙 | primitive 금지, 순수성, 엣지 케이스 형식과 테스트 | 전체 테스트에 포함 (`test_domain_rules.py`) | 위반 0. baseline 없음 |
| fitness | 언더바 이름, import 순환, 잡동사니 이름, 표면 선언 | 전체 테스트에 포함 (`test_fitness.py`) | baseline보다 나빠지지 않음 |
| 리포 무게 | 바이너리는 폰트 자산과 픽셀 기준 이미지에만, 크기 상한 | 전체 테스트에 포함 (`test_repo_weight.py`) | 위반 0 |
| 지침 | skill·템플릿의 코드가 실행되고, lint에 걸리지 않고, 거기 나오는 `dm.*` 이름이 존재 | 전체 테스트에 포함 (`guide/tests/test_guidance.py`) | 통과 |

CI는 job 두 개다. `lint`는 ruff, basedpyright, extras 없는 설치 확인을 돌린다. `test`는 Python 3.12에서 전체 테스트를 `--mpl`과 함께 돌린다. `develop`과 `main`의 브랜치 보호가 이 둘을 필수로 건다.

> **주의**
>
> 픽셀 비교는 `--mpl` 옵션이 있을 때만 돈다. `uv run pytest`만 치면 장면을 그리기만 하고 기준 이미지와 비교하지 않는다.

## 줄 수는 경고다

모듈·slice·함수의 줄 수 규칙은 실패가 아니라 경고로만 알린다. 숫자를 맞추려는 작위적인 분할이 생기기 때문이다. 크기는 읽는 사람을 위한 신호로 쓴다.

## 테스트를 쓰는 법

테스트는 작게 둔다. slice 테스트는 slice 코드의 절반을 넘지 않는 것이 기준이다.

- **대부분은 순수 결정 테스트다.** `decide.py`의 함수에 값을 넣고 결과를 표로 확인한다. 그림을 그리지 않는다.
- **이름 붙은 엣지 케이스마다 테스트 하나.** 그 이름을 테스트에 적는다.
- **공개 함수로 실제 차트를 그려 보는 테스트는 slice당 5~15개.**
- **쓰지 않는 테스트:** 내부 구현 고정, 바이트·응답 형태 고정, 문서 문구나 도구 설정 검사, 조합만 늘린 반복.

테스트가 없다고 큰일 나지 않는다. 낡거나 의미 없는 테스트는 지운다. 미감 판정은 픽셀 baseline과 색 해시가 한다.

## 핵심 수치와 근거

**픽셀 RMS 0.5** (`tests/visual/test_visual_pixels.py`의 `PIXEL_TOLERANCE`). CI 환경 사이의 잡음은 최대 0.007이고, 가장 작은 실제 변화인 눈금 라벨 한 글자는 1.65다. 0.5는 잡음보다 70배 크고 가장 작은 변화보다 3배 작다.

**색 해시.** 출하하는 모든 색 값을 digest로 고정한다. 실패는 출하 색이 움직였다는 뜻이고, 소유자가 결정할 일이다. 색 표는 생성기 없이 `color/assets/`의 JSON으로 들고 있으므로 이 테스트가 유일한 방어선이다.

**fitness baseline** (`tests/architecture/fitness_baseline.json`). 고쳐서 수가 줄면 `--update`로 낮춘다. 올리는 것은 소유자만 한다.

## 알려진 공백

- **기준 이미지에 결함이 박혀 있다.** 장면 20개 중 새로 추가한 6개는 당시 코드가 그리던 모양 그대로다. 축 이름이 캔버스 왼쪽에서 잘리는 한글 차트, 오른쪽에서 잘리는 선 끝 이름, 위쪽 가장자리에 붙은 그림 범례가 들어 있다. 고치면 기준 이미지를 다시 만들어야 하고, 소유자가 전후 그림을 본 뒤 한다.
- **새 기준 이미지 6개는 macOS에서 만들었다.** Ubuntu CI에서 미세하게 달라 다시 만들어야 할 수 있다.
- **`dm.check`가 `simple_layout`의 기본 결과에 `TEXT_AT_EDGE`(INFO)를 낸다.** 기본 여백이 0이라 가장 바깥 글자가 캔버스 가장자리에 붙는다. 기본 여백을 바꾸면 모든 그림의 픽셀이 바뀌므로 소유자 결정이다.
- **에이전트 평가(`evals/`)는 게이트가 아니다.** 실제 `claude -p`를 skill·MCP만 켠 격리 환경에서 돌려 케이스 × arm(`bare`, `skill`, `mcp`) 판정과 사람이 보는 contact sheet를 만든다. 사용량을 쓰므로 CI에서 돌지 않는다. 기계 판정은 거르기만 하고, "예쁜가"는 소유자가 `evals/runs/<시각>/index.html`을 보고 정한다. 사용법은 [evals/README.md](../../evals/README.md).
- **Python 3.11과 3.13에서는 테스트가 돌지 않는다.** CI는 3.12만 쓴다.

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
| 픽셀 baseline | 미감: 렌더 결과 | 전체 테스트에 포함 (`tests/visual`, `--mpl` 필요) | 장면 24개 각각 RMS ≤ 0.5 |
| slice 경계 | import 방향과 표면 | 전체 테스트에 포함 (`tests/architecture/test_boundaries.py`) | 위반 0 |
| 순수 import | 순수 파일을 새 인터프리터에서 import했을 때 matplotlib이 없음 | 전체 테스트에 포함 (`tests/architecture/test_pure_imports.py`) | 위반 0 |
| 도메인 파일 규칙 | primitive 금지, 순수성, 엣지 케이스의 이유와 예제 | 전체 테스트에 포함 (`test_domain_rules.py`, 예제 실행 중 작동 확인은 `tests/fixtures.py`) | 위반 0. baseline 없음 |
| fitness | 언더바 이름, import 순환, 잡동사니 이름, 표면 선언, slice 사이 import와 조립 규칙(C1..C5) | 전체 테스트에 포함 (`test_fitness.py`) | baseline보다 나빠지지 않음 |
| 리포 무게 | 바이너리는 폰트 자산과 픽셀 기준 이미지에만, 크기 상한 | 전체 테스트에 포함 (`test_repo_weight.py`) | 위반 0 |
| 지침 | skill·템플릿의 코드가 실행되고, lint에 걸리지 않고, 거기 나오는 `dm.*` 이름이 존재 | 전체 테스트에 포함 (`guide/tests/test_guidance.py`) | 통과 |

CI는 job 두 개다. `lint`는 ruff, basedpyright, extras 없는 설치 확인을 돌린다. `test`는 Python 3.12에서 전체 테스트를 `--mpl`과 함께 돌린다. `develop`과 `main`의 브랜치 보호가 이 둘을 필수로 건다.

> **주의**
>
> 픽셀 비교는 `--mpl` 옵션이 있을 때만 돈다. `uv run pytest`만 치면 장면을 그리기만 하고 기준 이미지와 비교하지 않는다.

## 에이전트 평가는 게이트가 아니라 개발 루프다

에이전트 평가(`evals/`)는 기본 개발 방식이다([philosophy.md](philosophy.md) 2절). 실제 `claude -p`를 격리된 환경에서 돌려 케이스 × arm 판정과 사람이 보는 contact sheet를 만든다. arm은 둘이다. `skill`은 라이브러리와 skill만 켠 기준 환경이고, `bare`는 skill 없이 matplotlib만 쓰는 대조군이다. 사용법은 [evals/README.md](../../evals/README.md).

- **CI 게이트가 아니다.** 모델 사용량을 쓰므로 CI에서 돌지 않고, PR 합격을 막지 않는다. 개발하는 쪽이 돌린다.
- **기계 판정은 거르기만 한다.** `OK`는 그림이 있고 `dm.check`와 lint가 조용하며 케이스의 `[expect]`가 맞다는 뜻이다. 예쁘다는 뜻이 아니다. "예쁜가"는 `evals/runs/<시각>/index.html`의 그림을 보고 정한다.
- **판정하는 source는 그 그림을 그린 스크립트다.** 하네스는 에이전트가 마지막으로 돌린 스크립트를 run 자신의 파일에서 읽어 다시 그리고, 그 결과가 `figure.png`와 같을 때만 `dm.check`·lint·`[expect]`로 판정한다. source를 확정할 수 없거나 run이 자기 root 밖에서 일했으면 `DEFECT`가 아니라 이유가 붙은 `INVALID`다. run마다 어떤 라이브러리 commit·wheel·skill로 돌았는지 `provenance`로 남는다.
- **걸리는 것은 이슈가 된다.** `DEFECT`와 `NO_FIGURE`, 그리고 `OK`인데 예쁘지 않은 그림은 하나씩 GitHub 이슈로 올린다. 예쁘지 않은 것도 버그다(philosophy 1절).
- **프롬프트는 케이스로 남는다.** 결함을 드러낸 프롬프트와 데이터를 `evals/cases/<이름>.toml`로 둔다. 고친 뒤 그 케이스를 다시 돌려 그림으로 확인한다.

## 줄 수는 경고다

모듈·slice·함수의 줄 수 규칙은 실패가 아니라 경고로만 알린다. 숫자를 맞추려는 작위적인 분할이 생기기 때문이다. 크기는 읽는 사람을 위한 신호로 쓴다.

## 테스트를 쓰는 법

테스트는 작게 둔다. slice 테스트는 slice 코드의 절반을 넘지 않는 것이 기준이다.

- **대부분은 순수 결정 테스트다.** `decide.py`의 함수에 값을 넣고 결과를 표로 확인한다. 그림을 그리지 않는다.
- **이름 붙은 엣지 케이스마다 테스트 하나.** 그 테스트가 엣지의 `example`이다. 이름을 적고, 단언하고, 실행 중 엣지를 작동시킨다.
- **공개 함수로 실제 차트를 그려 보는 테스트는 slice당 5~15개.**
- **쓰지 않는 테스트:** 내부 구현 고정, 바이트·응답 형태 고정, 문서 문구나 도구 설정 검사, 조합만 늘린 반복.

테스트가 없다고 큰일 나지 않는다. 낡거나 의미 없는 테스트는 지운다. 미감 판정은 픽셀 baseline과 색 해시가 한다.

## 핵심 수치와 근거

**픽셀 RMS 0.5** (`tests/visual/test_visual_pixels.py`의 `PIXEL_TOLERANCE`). CI 환경 사이의 잡음은 최대 0.007이고, 가장 작은 실제 변화인 눈금 라벨 한 글자는 1.65다. 0.5는 잡음보다 70배 크고 가장 작은 변화보다 3배 작다.

**색 해시.** 출하하는 모든 색 값을 digest로 고정한다. 실패는 출하 색이 움직였다는 뜻이고, 소유자가 결정할 일이다. 색 표는 생성기 없이 `color/assets/`의 JSON으로 들고 있으므로 이 테스트가 유일한 방어선이다.

**글자 대비 3:1, 반 em 구간의 절반** (`colorspace.LEGIBLE`, `FAINT_SHARE`). `TEXT_CONTRAST`는 사용자가 놓은 글자의 잉크 픽셀마다 칠한 색과 그 뒤에 그려진 색의 대비를 재고, 글자 방향 반 em 구간 하나라도 잉크의 절반 이상이 3:1 미만이면 보고한다. 구간은 글자를 따라 미끄러진다: 잉크 픽셀마다 거기서 시작하는 구간과 거기서 끝나는 구간을 모두 본다. 이 측정은 그림을 따로 더 그리지 않는다: `dm.check`가 원래 하던 한 번의 그리기에서 같이 읽는다. 3:1은 WCAG의 큰 글자 기준이다. 4.5:1로 올리면 코퍼스에서 걸리는 그림이 5개에서 10개가 된다. 코퍼스에서 이 규칙이 걸리는 그림의 목록은 `tests/corpus/test_corpus.py`의 `FAINT_TEXT`에 고정돼 있다. 목록에 이름을 더하는 것은 그 그림을 본 뒤에 한다.

**막대·점·연결선 규칙의 문턱** (`check/marks.py`). 2026-11-23 평가 sweep 세 번의 녹화 source 228개를 다시 그려 정했다. `VALUE_LABEL_ADRIFT`는 값 라벨이 자기 막대에서 1 em 넘게 떨어져 있고 같은 줄 반대편의 다른 막대가 더 가까울 때 보고한다. `BAND_OFF_CENTRE`는 띠 안의 한 줄이 띠 가운데에서 1.5 pt와 띠 두께의 4%를 모두 넘게 벗어날 때 보고한다(코퍼스의 띠는 0.0 pt, 보고된 그림은 3.4 pt·8%). `UNEVEN_OUTLINE`은 맞닿은 막대의 외곽선 반폭이 0.2 pt 이상 다를 때 보고한다(소유자가 지적한 그림이 0.25 pt). `TEXT_BOX_ON_DATA`는 불투명도 0.5 이상인 글자 상자가 막대나 채운 면을 덮을 때 보고한다(선 위의 상자는 `TEXT_ON_LINE`이 허용하는 처리라 세지 않는다). `CONNECTOR_SHORT`는 두 점짜리 직선이나 `ConnectionPatch`의 끝이 종이색 외곽선을 가진 막대·쐐기의 바깥 모서리에 놓이고 외곽선 반폭이 0.5 pt 이상일 때 보고한다. 두 마크가 같이 쓰는 모서리는 이음매라서 뺀다(누적 막대의 경계끼리 잇는 선). 228개 가운데 다섯 규칙이 걸린 것은 8개이고 모두 지적된 결함과 같은 종류였다.

**점 안의 숫자, 격자를 잇는 열** (`check/model.py`의 `HELD_EM`, `IN_STEP`, `geometry.data_ink.LINE_INK`). 2026-11-23 sweep 네 번의 녹화 source를 다시 그려 정했다. `VALUE_LABEL_ON_DATA`는 글자 가운데가 점 가운데에서 0.25 em 안에 있고 글자의 잉크(줄 상자 높이의 0.7)가 점 안에 들어가면 보고하지 않는다. 점 안에 넣은 숫자(점 행렬, 순위 원)는 모두 0.0 em이었고, 마커 위라고 보고된 값 라벨은 모두 마커 가운데에서 1.9 em 넘게 떨어져 있었다. `TEXT_COLUMN_GAP`은 열의 가운데가 그 줄 칸 숫자들의 간격을 이은 자리에서 간격의 10% 안이면 보고하지 않는다. 한 칸 더 놓은 합계 열은 5% 어긋나 있었고, 떠 보인다고 지적된 열은 15%와 35%였다.

**fitness baseline** (`tests/architecture/fitness_baseline.json`). 고쳐서 수가 줄면 `--update`로 낮춘다. 올리는 것은 소유자만 한다.

## 알려진 공백

- **기준 이미지에 결함이 박혀 있다.** 장면 20개 중 새로 추가한 6개는 당시 코드가 그리던 모양 그대로다. 축 이름이 캔버스 왼쪽에서 잘리는 한글 차트, 오른쪽에서 잘리는 선 끝 이름, 위쪽 가장자리에 붙은 그림 범례가 들어 있다. 고치면 기준 이미지를 다시 만들어야 하고, 소유자가 전후 그림을 본 뒤 한다.
- **새 기준 이미지 6개는 macOS에서 만들었다.** `legible_korean_note`와 `legible_contour_labels`도 그렇다. Ubuntu CI에서 미세하게 달라 다시 만들어야 할 수 있다.
- **에이전트 평가는 누가 돌려야만 돈다.** CI에 없으므로, 고친 결함이 돌아와도 평가를 다시 돌리기 전에는 보이지 않는다.
- **Python 3.11과 3.13에서는 테스트가 돌지 않는다.** CI는 3.12만 쓴다.

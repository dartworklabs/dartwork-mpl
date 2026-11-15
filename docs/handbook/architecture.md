---
orphan: true
---

# 구조와 불변식

> **한눈에**
>
> 패키지는 작은 코어 slice 열두 개다. 각 slice 안에서는 결정을 순수 함수로, matplotlib 객체 변경을 얇은 shell로 나눈다. 반드시 지키는 것은 미감과 "matplotlib을 감싸지 않음"이다. 그 밖의 기능은 의미가 없으면 제거한다.

## 코어 slice 열두 개

기능에 비해 코드가 복잡한 것은 잘못 만들고 있다는 증거다. 그래서 "그려줘 하면 예쁜 차트"에 직접 필요한 것만 작은 slice로 둔다. slice 하나가 패키지 하나다: `src/dartwork_mpl/<slice>/`. 여기에 들지 않는 코드는 이 리포에 두지 않는다.

| slice | 한 가지 책임 |
| --- | --- |
| `style` | preset 적용, 글자·선·무게의 preset 상대값(`fs`, `lw`, `fw`) |
| `size` | 물리 단위와 그림 크기, 종횡비 |
| `color` | 색 이름과 값, 팔레트, 대비 |
| `font` | 번들 폰트 등록과 선택 |
| `layout` | 내용에 맞춘 결정적 여백(`simple_layout`) |
| `ticks` | 눈금의 숫자·날짜·단위 형식 |
| `labels` | 값 라벨, 패널 문자, 주석 |
| `legend` | 범례 배치 |
| `check` | 그려진 그림의 결함 찾기(`dm.check`). 그림을 바꾸지 않는다 |
| `save` | 여러 형식으로 저장 |
| `guide` | 에이전트 지침: skill, 템플릿, 안티패턴 lint |
| `mcp` | 위 slice를 에이전트에 연결하는 얇은 진입점. 도구 다섯 개 |

slice끼리는 선언한 표면(`__init__.py`의 `__all__`)으로만 만난다. 허용된 의존 방향과 그 이유는 [scripts/check_boundaries.py](../../scripts/check_boundaries.py)의 `ALLOWED`가 정본이다. 여러 slice가 함께 쓰는 측정 코드는 platform 모듈 `_figure_geometry`에 있고, platform은 어떤 slice도 import하지 않는다. 공용 `utils/`나 `common/`은 만들지 않는다. 같은 이유로 함께 바뀌는 것이 관찰되기 전에는 중복이 틀린 추상화보다 싸기 때문이다.

`layout`은 `ticks`, `labels`, `legend`를 정해진 함수로만 부른다. 레이아웃 한 단계 안에서 눈금 글자를 정하고, 라벨과 범례를 자리 잡게 한 뒤, 여백을 잰다.

## slice 안의 파일 규칙

matplotlib의 `Figure`와 `Axes`는 상태를 바꾸는 객체다. 이 사실은 바꿀 수 없으므로 상태 변경을 한곳에 가둔다. 파일 이름이 역할을 말하고, 규칙은 파일 이름에 걸린다.

| 파일 | 역할 | 규칙 |
| --- | --- | --- |
| `model.py` | slice의 도메인 타입. primitive를 감싸는 유일한 곳. 입력 파싱 | 순수 |
| `decide.py` | 평범한 그림에 대한 결정. 사실을 받아 계획을 돌려준다 | 순수, 도메인 타입만 |
| `edges.py` | 이름 붙은 엣지 케이스 목록. 항목마다 이유와 예제 | 순수, 도메인 타입만 |
| `measure.py`, `apply.py` | figure에서 사실을 읽고 계획을 반영하는 shell | matplotlib 사용 |
| `assets/` | 그 slice만 쓰는 데이터 파일 | 다른 slice가 경로로 읽지 않는다 |
| `__init__.py` | 표면 | 연결만 |

**도메인 파일은 primitive 타입으로 말하지 않는다.** `decide.py`와 `edges.py`의 함수는 인자와 반환을 도메인 타입으로 적는다. `str`, `int`, `float`, `dict`, `Any` 같은 primitive나 annotation 누락은 오류다. `float` 두 개를 받는 함수는 폭과 높이가 바뀌어도 통과하지만 `Length`와 `Aspect`는 그렇지 않기 때문이다.

**엣지 케이스는 본문 분기가 아니라 목록에 덧붙인다.** 극좌표 축, 한국어 만 단위, 빽빽한 날짜처럼 드문 그림에서만 필요한 처리는 `decide.py`에 분기를 더하지 않는다. `edges.py`의 `EDGES` 끝에 `EdgeCase` 하나를 더한다. 각 항목은 이름, 이유(`why`), 예제(`example`), 적용 조건, 계획을 바꾸는 함수를 갖는다. `settle`이 순서대로 적용하고 어떤 것이 작동했는지 돌려준다. 본 경로는 평범한 경우만 읽으면 되고, 엣지 케이스는 이름으로 세고 지울 수 있다. `check`의 검사 규칙도 같은 방식으로 등록한다. 장치는 [edgecase/\_\_init\_\_.py](../../src/dartwork_mpl/edgecase/__init__.py)에 있다.

**엣지 케이스는 이유와 예제가 있어야 존재한다.** `why`는 그 엣지가 없으면 예제에서 무엇이 잘못되는지를 한 문장으로 말한다. 고치는 방법이 아니라 결함을 쓴다. `example`은 slice의 `tests/`에 있는 테스트 하나를 `test_<파일>.py::[클래스::]test_<함수>`로 가리킨다. 그 테스트는 엣지 이름을 적고 단언하며, 실행되는 동안 그 엣지가 실제로 작동해야 한다. 둘 중 하나라도 없으면 테스트가 실패한다. 줄 수에는 상한이 없다. 대신 실제 그림에서 한 번도 작동하지 않는 엣지 케이스는 그 코드, 그것만 쓰던 타입과 측정 코드, 테스트, 지침 문구와 함께 지운다. 실제 그림은 픽셀 장면, 번들 템플릿, robustness 장면이다. `edgecase.tally`에 `Counter`를 넣으면 `settle`이 작동한 이름을 센다. 기본은 꺼져 있다.

**자산은 쓰는 slice 안에 둔다.** 스타일 파일은 `style/assets/`, 폰트는 `font/assets/`, 색 표는 `color/assets/`, skill과 템플릿은 `guide/assets/`에 있다. 한 기능을 바꾸거나 지울 때 그 폴더 하나만 보면 되게 하기 위해서다.

출처: [ADR 0005](../adr/0005-capability-slices-and-test-colocation.md) 결정 2·4·5, [ADR 0009](../adr/0009-blueprint.md) 결정 1.

## 불변식

| 불변식 | 지키는 장치 | 위반하면 |
| --- | --- | --- |
| **미감 유지.** 출하 색 값, 폰트, 글자 무게, spine, grid, preset의 모양은 바뀌지 않는다 | 색 해시 테스트, 픽셀 baseline(RMS 0.5) | 사용자 그림이 조용히 달라진다. 소유자가 before/after를 보고 승인해야만 바꾼다 |
| **matplotlib을 감싸지 않는다.** dm 함수는 native `Figure`·`Axes`를 받고 돌려준다. `dm.style.use`는 rcParams만 바꾼다 | 리뷰 | 사용자가 dartwork-mpl 전용 개념을 배워야 한다 |
| **크기는 물리 단위, 글자·선은 preset 상대값** | 안티패턴 lint와 ratchet | preset을 바꾸면 그림이 깨진다 |
| **레이아웃은 결정적이고 다시 적용해도 같다** | 픽셀 baseline | 같은 코드가 실행마다 다른 그림을 낸다 |
| **`check`는 그림을 바꾸지 않는다** | check slice 테스트 | 검사했더니 그림이 달라진다 |
| **slice 경계와 파일 규칙** | `tests/architecture/` | 한 기능 변경이 여러 폴더로 번진다 |
| **호환 층을 두지 않는다.** 재노출 파일, 별칭, 제거된 이름 안내 장치를 만들지 않는다 | 리뷰, fitness의 이름 규칙 | 지운 코드가 다른 모양으로 돌아온다 |
| **`render`는 샌드박스가 아니다.** 신뢰한 코드만 실행한다 | 도구 설명, 실행 제한 테스트 | 허브가 남이 올린 코드를 이 경로로 실행하면 그 머신이 뚫린다 |

미감 불변식의 출처: [ADR 0001](../adr/0001-oklab-centered-color-construction.md) A1, [ADR 0009](../adr/0009-blueprint.md) 결정 2. 제거 정책의 출처: [ADR 0008](../adr/0008-owner-priority-lock-reset.md) 결정 1·2.

## MCP 표면과 산출물 계약

`dartwork-mpl-mcp`는 stdio로만 동작하고 도구 다섯 개만 낸다: `guide`, `search_reference`, `get_reference`, `lint`, `render`. 리소스와 프롬프트는 없다. 에이전트가 고민 없이 맞는 도구를 고를 수 있어야 하기 때문이다.

`render`는 코드를 자식 프로세스에서 한 번 실행하고 한 폴더에 묶음을 쓴다: `figure.png`, `figure.pdf`, `source.py`, `report.json`(`dm.check` 결과), `manifest.json`. 데이터 파일은 복사하지 않고 해시와 크기만 manifest에 적는다. 이 묶음이 허브가 받는 계약이다. 저장·공유·만료는 허브의 몫이라 이 라이브러리에는 저장소가 없다. manifest 스키마는 `mcp/model.py`가 정본이다.

자식 프로세스는 빈 임시 폴더에서 돌고, 환경변수는 허용 목록만 받으며, 시간 초과 시 프로세스 그룹 전체가 종료된다. CPU 시간과 파일 크기에 제한이 걸린다. 메모리 제한은 Linux에서만 걸린다. macOS는 그 제한을 거부한다.

## 남은 리팩터 목표

소유자가 2026-11-15에 정한 여섯 단계 중 Handbook, 구조 정리, MCP 재설계는 반영됐다. 남은 것은 다음과 같다.

1. **문서 분리.** `docs/`의 사용자 문서·갤러리·브랜딩을 허브 리포로 옮기고 이 리포에는 개발 문서만 남긴다. 지금 `docs/`에는 지워진 API를 설명하는 페이지가 많다.
2. **git 히스토리의 대용량 잔재 제거.** 문서 분리 다음에 한 번만 한다.
3. **허브 계약 확정.** 위 산출물 묶음을 허브가 실제로 받아 보고 고친다.
4. **남은 이름 정리.** `_figure_geometry`의 언더바 이름과 `config.py`가 남아 있다.

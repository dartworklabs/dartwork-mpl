---
orphan: true
---

# 구조와 불변식

> **한눈에**
>
> 패키지는 작은 코어 slice 열한 개와 그들이 함께 쓰는 platform 패키지다. slice는 서로를 import하지 않고 `compose/`에서 만난다. 각 slice 안에서는 결정을 순수 함수로, matplotlib 객체 변경을 얇은 shell로 나눈다. 반드시 지키는 것은 미감과 "matplotlib을 감싸지 않음"이다. 그 밖의 기능은 의미가 없으면 제거한다.

## 코어 slice 열한 개

기능에 비해 코드가 복잡한 것은 잘못 만들고 있다는 증거다. 그래서 "그려줘 하면 예쁜 차트"에 직접 필요한 것만 작은 slice로 둔다. slice 하나가 패키지 하나다: `src/dartwork_mpl/<slice>/`. 여기에 들지 않는 코드는 이 리포에 두지 않는다.

| slice | 한 가지 책임 |
| --- | --- |
| `style` | preset 적용, 글자·선·무게의 preset 상대값(`fs`, `lw`, `fw`) |
| `size` | 그림 크기와 종횡비, preset의 기본 캔버스 |
| `color` | 색 이름과 값, 팔레트, 대비 |
| `font` | 번들 폰트 등록과 선택 |
| `layout` | 내용에 맞춘 결정적 여백(`simple_layout`) |
| `ticks` | 큰 수의 기본 표기(천 단위 쉼표, 백만부터 `1M`, 한국어 preset에서는 `100만`), 데이터가 모두 정수인 축(월, 개수, 순위, 연도)의 정수 눈금, 만·억 단위 눈금(`format_axis_myriad`), 값 라벨이 따라 쓸 축의 숫자 표기. 날짜와 그 밖의 눈금 글자는 preset 토큰(`date.autoformatter.*`)과 matplotlib이 쓴다 |
| `labels` | 값 라벨, 패널 문자, 주석 |
| `legend` | 범례 배치 |
| `check` | 그려진 그림의 결함 찾기(`dm.check`). 그림을 바꾸지 않는다 |
| `save` | 여러 형식으로 저장 |
| `guide` | 에이전트 지침: skill, 템플릿, 안티패턴 lint |

**slice는 다른 slice를 import하지 않는다.** 표면이든 내부 모듈이든 같다. slice가 import하는 것은 platform 패키지뿐이다. 한 기능이 다른 기능을 필요로 하면 `compose/<slice>.py`가 둘을 잇는다. 이름은 그 기능을 쓰는 slice를 따른다. 조립 함수는 slice의 표면을 순서대로 부르고, 한 slice의 함수를 다른 slice에 타입이 있는 인자로 넘길 뿐 아무것도 판단하지 않는다(분기, 반복, 클래스 없음). `compose`를 import하는 것은 패키지 루트뿐이다. 규칙은 [composition.py](../../tests/architecture/composition.py)의 C1..C5와 [boundaries.py](../../tests/architecture/boundaries.py)가 지킨다.

| 조립 모듈 | 잇는 것 | 루트가 내보내는 이름 |
| --- | --- | --- |
| `compose/style.py` | preset의 locale에 맞춘 `color`의 역할 색을 `style`에 넣는다 | 없음(루트가 `join()`을 한 번 부른다) |
| `compose/size.py` | `style`의 활성 preset 이름과 레이어 읽기 | `dm.figsize_for` |
| `compose/labels.py` | `style`의 `fs`·`fw`, `ticks`의 눈금 단위와 숫자 표기 | `dm.label_bars`, `dm.annotate_value`, `dm.label_axes`, `dm.add_note` |
| `compose/layout.py` | `ticks`의 큰 수 표기(`style`의 preset locale에 맞춘 단위), `labels`·`legend`가 맞춘 크기에서 하는 일과 여백이 피해야 할 기록 | `dm.simple_layout` |

`layout`은 다른 slice가 할 일을 `Neighbours` 기록 하나로 받는다. 순서는 `layout`이 정한다. 한 단계마다 막대 라벨, 범례와 선 끝 이름, 패널 문자, 그림 제목 아래의 그림 범례를 자리 잡게 한 뒤 여백을 잰다. 픽셀은 이 순서에 달려 있다. 재기 전에 한 번, 아무도 포맷을 정하지 않은 수 축에 큰 수 표기를 건다. 판단은 눈금 값이 1,000에 닿는지 하나다. 데이터를 읽는 판단은 하나뿐이다. 한 축을 따라 데이터 단위로 그린 것(선과 점, 면과 메시의 꼭짓점, 이미지의 가장자리, 막대는 선 축에서 가운데와 값 축에서 두 끝)이 모두 정수이고 세 정수 이상에 걸치면, 아무도 눈금 위치·포맷·scale을 정하지 않은 그 축(x든 y든)의 눈금을 정수에만 둔다(`2.5`, `2019.5` 같은 눈금은 어느 달·개수·해도 가리키지 않는다). x축에서 네 글자 이상의 라벨(연도)은 matplotlib대로 두 눈금까지 허용하고, 그 밖에는 세 눈금을 남긴다. 이 slice가 둔 locator는 기억해 두고, 데이터가 더는 정수가 아니면 matplotlib의 locator로 되돌린다. 눈금이 실제로 바뀔 때만 한 줄로 알린다. 이미지(`imshow`)는 픽셀 가장자리가 `.5`에 있어 건드리지 않는다.

`dm.style`은 slice `dartwork_mpl.style` 그 자체다. `style`은 preset을 적용한 뒤 그 locale을 넘겨줄 함수 하나(`Tint`)를 자리에 갖고 있고, `compose/style.py`의 `join()`이 그 자리에 `color`의 역할 색 바인딩을 넣는다. 루트가 import될 때 한 번 부른다. 폰트는 루트가 import 시점에 등록하므로 `style`이 다시 부르지 않는다.

## platform

두 slice 이상이 함께 쓰는 것은 platform 패키지에 둔다. platform은 어떤 slice도 import하지 않는다. 한 slice만 쓰는 것은 그 slice 안에 둔다. 패키지 하나가 개념 하나이고 이름은 그 개념이다. `utils`, `common`, `shared`, `core`, `types`, `base`는 만들지 않는다. 데이터와 파싱만 있는 작은 어휘는 `vocab` 한 패키지에 모듈 하나씩 둔다. 산술이나 결정이 있으면(`length`, `colorspace`) 자기 패키지를 갖는다. 순수 타입과 matplotlib 코드는 한 패키지에 두지 않는다. 순수 파일이 platform을 import해도 matplotlib이 끌려오지 않아야 하기 때문이다([test_pure_imports.py](../../tests/architecture/test_pure_imports.py)).

| 패키지 | 개념 | 쓰는 곳 |
| --- | --- | --- |
| `vocab` | slice들이 함께 쓰는 낱말. 모듈 하나가 어휘 하나다: `axis`(x·y 축과 라벨이 놓이는 쪽), `align`(글자 정렬), `box`(픽셀 사각형 `Box`와 구간 `Span`), `edge`(상자의 네 변, figure 범례가 잡는 변), `projection`(평면, 3D, 그 밖), `number`(숫자가 찍히는 눈금 단위), `locale`(기본 관례와 한국 관례) | 모든 slice, geometry |
| `length` | 물리 길이 `Length`와 단위(`dm.cm` 등) | size, layout, 루트 |
| `colorspace` | sRGB·OKLab 값과 산술, 합성, WCAG 대비 | color, labels |
| `edgecase` | 엣지 케이스 등록 장치. 로거를 받으면, 작동해서 계획을 바꾼 엣지 케이스마다 이름과 이유를 한 줄 보고한다 | 모든 slice |
| `hidden` | 자동 동작의 보고. slice마다 `dartwork_mpl.<slice>` 로거에 INFO 한 줄을 쓰고, 그것이 기본으로 stderr에 `dartwork-mpl:`을 붙여 출력된다. `dm.quiet()`이 끄고 `dm.verbose()`가 다시 켠다. import 때의 등록은 DEBUG라 출력되지 않는다. Axes를 이름으로 부르는 `axes_name` | color, font, labels, layout, legend, save, size, style, ticks, 루트 |
| `geometry` | figure 측정(matplotlib). 렌더러, 그려진 잉크, 제목과 눈금 라벨 | check, labels, layout, legend, ticks |

`geometry`, `edgecase`, `hidden` 밖의 platform은 모두 순수하다. 정본과 패키지마다의 이유는 `boundaries.py`의 `PLATFORM`이다.

## slice 안의 파일 규칙

matplotlib의 `Figure`와 `Axes`는 상태를 바꾸는 객체다. 이 사실은 바꿀 수 없으므로 상태 변경을 한곳에 가둔다. 파일 이름이 역할을 말하고, 규칙은 파일 이름에 걸린다.

| 파일 | 역할 | 규칙 |
| --- | --- | --- |
| `model.py` | slice의 도메인 타입과 입력 파싱. 문자열 비교와 `Literal`은 여기서만 쓴다 | 순수 |
| 개념 이름의 타입 모듈 | `model.py`가 커져 개념별로 나온 도메인 타입(예: `labels/bar_geometry.py`) | 순수, `boundaries.py`의 `DECISIONS`에 등록 |
| `decide.py` | 평범한 그림에 대한 결정. 사실을 받아 계획을 돌려준다 | 순수, 도메인 타입만 |
| `edges.py` | 이름 붙은 엣지 케이스 목록. 항목마다 이유와 예제 | 순수, 도메인 타입만 |
| `measure.py`, `apply.py`, 개념 이름의 shell 모듈 | figure에서 사실을 읽고 계획을 반영하는 shell | matplotlib 사용 |
| `assets/` | 그 slice만 쓰는 데이터 파일 | 다른 slice가 경로로 읽지 않는다 |
| `__init__.py` | 표면 | 연결만 |

platform의 순수 패키지도 같은 파일 이름 규칙을 따른다(`length/model.py`, `colorspace/decide.py`, `colorspace/edges.py`). `vocab`만 예외로, 모듈 이름이 어휘 이름이고 모든 모듈이 `model.py`와 같은 규칙(순수, 문자열 파싱 허용)을 받는다.

**도메인 파일은 primitive 타입으로 말하지 않는다.** `decide.py`와 `edges.py`의 함수는 인자와 반환을 도메인 타입으로 적는다. `str`, `int`, `float`, `dict`, `Any` 같은 primitive나 annotation 누락은 오류다. `float` 두 개를 받는 함수는 폭과 높이가 바뀌어도 통과하지만 `Length`와 `Aspect`는 그렇지 않기 때문이다.

**엣지 케이스는 본문 분기가 아니라 목록에 덧붙인다.** 극좌표 축, 3D 축, 겹치는 눈금 글자처럼 드문 그림에서만 필요한 처리는 `decide.py`에 분기를 더하지 않는다. `edges.py`의 목록 끝에 `EdgeCase` 하나를 더한다. 목록은 사실·계획 타입 쌍마다 하나이고 `EDGES` 또는 `<NAME>_EDGES`(`TEXT_EDGES`, `LIFT_EDGES` 등)라고 부른다. 각 항목은 이름, 이유(`why`), 예제(`example`), 적용 조건, 계획을 바꾸는 함수를 갖는다. `settle`이 순서대로 적용하고 어떤 것이 작동했는지 돌려준다. 그림이나 사용자가 받는 값을 바꾸는 목록은 `settle`에 slice의 로거를 넘겨 작동한 것을 보고하게 한다. 같은 동작을 Axes 이름까지 넣어 shell이 이미 보고하는 목록(`layout`의 `TEXT_EDGES`)과, 동작이 아니라 발견을 등록하는 `check`와 lint는 넘기지 않는다. 본 경로는 평범한 경우만 읽으면 되고, 엣지 케이스는 이름으로 세고 지울 수 있다. `check`의 검사 규칙도 같은 방식으로 등록한다. 장치는 [edgecase/\_\_init\_\_.py](../../src/dartwork_mpl/edgecase/__init__.py)에 있다.

**엣지 케이스는 이유와 예제가 있어야 존재한다.** `why`는 그 엣지가 없으면 예제에서 무엇이 잘못되는지를 한 문장으로 말한다. 고치는 방법이 아니라 결함을 쓴다. `example`은 그 패키지의 `tests/`에 있는 테스트 하나를 `test_<파일>.py::[클래스::]test_<함수>`로 가리킨다. 그 테스트는 엣지 이름을 적고 단언하며, 실행되는 동안 그 엣지가 실제로 작동해야 한다. 둘 중 하나라도 없으면 테스트가 실패한다. 줄 수에는 상한이 없다. 대신 실제 그림에서 한 번도 작동하지 않는 엣지 케이스는 그 코드, 그것만 쓰던 타입과 측정 코드, 테스트, 지침 문구와 함께 지운다. 실제 그림은 픽셀 장면, 번들 템플릿, robustness 장면이다. `edgecase.tally`에 `Counter`를 넣으면 `settle`이 작동한 이름을 센다. 기본은 꺼져 있다.

**자산은 쓰는 slice 안에 둔다.** 스타일 파일은 `style/assets/`, 폰트는 `font/assets/`, 색 표는 `color/assets/`, skill과 템플릿은 `guide/assets/`에 있다. 한 기능을 바꾸거나 지울 때 그 폴더 하나만 보면 되게 하기 위해서다.

출처: [ADR 0005](../adr/0005-capability-slices-and-test-colocation.md) 결정 2·4·5, [ADR 0009](../adr/0009-blueprint.md) 결정 1.

## 불변식

| 불변식 | 지키는 장치 | 위반하면 |
| --- | --- | --- |
| **미감 유지.** 출하 색 값, 폰트, 글자 무게, spine, grid, preset의 모양은 바뀌지 않는다 | 색 해시 테스트, 픽셀 baseline(RMS 0.5) | 사용자 그림이 조용히 달라진다. 소유자가 before/after를 보고 승인해야만 바꾼다 |
| **matplotlib을 감싸지 않는다.** dm 함수는 native `Figure`·`Axes`를 받고 돌려준다. `dm.style.use`는 rcParams만 바꾼다 | 리뷰 | 사용자가 dartwork-mpl 전용 개념을 배워야 한다 |
| **크기는 물리 단위, 글자·선은 preset 상대값** | 안티패턴 lint, 지침 테스트 | preset을 바꾸면 그림이 깨진다 |
| **레이아웃은 결정적이고 다시 적용해도 같다** | 픽셀 baseline | 같은 코드가 실행마다 다른 그림을 낸다 |
| **숨은 동작은 보고한다.** 사용자가 부르지 않은 것을 바꾸는 동작은 그 자리에서 `dartwork_mpl.<slice>` 로거에 한 줄을 쓰고, 사용자가 정하거나 되돌린 것은 다시 바꾸지 않는다 | `tests/test_verbose.py`, slice별 surface 테스트, 리뷰 | 사용자가 왜 그림이 바뀌었는지 알 수 없다 |
| **`check`는 그림을 바꾸지 않는다** | check slice 테스트 | 검사했더니 그림이 달라진다 |
| **slice 경계와 파일 규칙.** slice는 slice를 import하지 않는다 | `tests/architecture/` | 한 기능 변경이 여러 폴더로 번진다 |
| **호환 층을 두지 않는다.** 재노출 파일, 별칭, 제거된 이름 안내 장치를 만들지 않는다 | 리뷰, fitness의 이름 규칙 | 지운 코드가 다른 모양으로 돌아온다 |

미감 불변식의 출처: [ADR 0001](../adr/0001-oklab-centered-color-construction.md) A1, [ADR 0009](../adr/0009-blueprint.md) 결정 2. 제거 정책의 출처: [ADR 0008](../adr/0008-owner-priority-lock-reset.md) 결정 1·2.

## 남은 리팩터 목표

소유자가 2026-11-15에 정한 단계 중 남은 것은 다음과 같다.

1. **문서 분리.** `docs/`의 사용자 문서·갤러리·브랜딩을 허브 리포로 옮기고 이 리포에는 개발 문서만 남긴다. 지금 `docs/`에는 지워진 API를 설명하는 페이지가 많다.
2. **git 히스토리의 대용량 잔재 제거.** 문서 분리 다음에 한 번만 한다.

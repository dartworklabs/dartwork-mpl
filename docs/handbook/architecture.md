---
orphan: true
---

# 구조와 불변식

> **한눈에**
>
> 1차 구조는 기능 slice다. 각 slice 안에서는 측정·결정을 순수 함수로, matplotlib 객체 변경을 얇은 shell로 나눈다. 반드시 지키는 것은 미감과 "matplotlib을 감싸지 않음"이다. 그 밖의 기능은 의미가 없으면 제거할 수 있다.

## 1차 구조: 기능 slice

기능(capability) 하나가 패키지 하나다: `src/dartwork_mpl/<slice>/`. 예를 들어 `layout`, `formatting`, `annotation`, `validate`, `style`이 있다. 이렇게 나누는 이유는 한 동작을 바꾸는 요청이 한 폴더 안에서 끝나게 하기 위해서다. 그 slice만 관찰하는 테스트도 같은 폴더의 `tests/`에 둔다.

slice끼리는 선언한 표면으로만 만난다. 표면은 각 `__init__.py`의 `__all__`이다. 다른 slice의 비공개 모듈을 import하면 경계 위반이다.

| 구성요소 | 책임 | 의존 규칙 |
| --- | --- | --- |
| 기능 slice | 한 능력의 규칙과 동작 | 다른 slice는 표면으로만, 허용 목록에 이유가 적힌 방향으로만 |
| platform | 업무를 모르는 메커니즘. figure 측정(`_figure_geometry`), rcParams(`_rc`), MCP 프로세스(`mcp/_platform`), UI 파일·HTTP(`ui/platform`) | 어떤 slice도 import하지 않는다 |
| entry point | `dartwork_mpl/__init__.py`, `cli.py`, `mcp/server.py` 등 | 연결만 한다. 기능 로직을 갖지 않는다 |

`layout`, `formatting`, `validate`처럼 여러 기능이 함께 쓰는 엔진도 slice다. 다른 slice는 이 엔진을 표면으로만 쓴다. 공용 `utils/`나 `common/`은 만들지 않는다. 같은 이유로 함께 바뀌는 것이 관찰되기 전에는 중복이 틀린 추상화보다 싸기 때문이다.

경계 규칙과 허용 목록의 정본은 [scripts/check_boundaries.py](../../scripts/check_boundaries.py)다. `DEBT`(남은 위반 목록)는 현재 비어 있고 다시 늘리지 않는다. 출처: [ADR 0005](../adr/0005-capability-slices-and-test-colocation.md) 결정 2·3·5.

## slice 안: functional core, imperative shell

matplotlib의 `Figure`와 `Axes`는 상태를 바꾸는 객체다. 이 사실은 바꿀 수 없다. 대신 상태 변경을 한곳에 가둔다. 각 기능은 세 단계로 나눈다.

1. **측정(shell)**: 그려진 figure에서 사실을 읽는다. 글자 크기, 겹침 영역, 축 범위 등이다.
2. **결정(core)**: 사실을 받아 계획을 돌려주는 순수 함수다. matplotlib 객체를 받지 않고 바꾸지도 않는다. 예를 들어 어떤 여백을 줄지, 어떤 라벨을 줄바꿈할지를 정한다.
3. **적용(shell)**: 계획을 실제 `Figure`에 반영한다.

이렇게 나누는 이유는 결정 로직을 그림 없이 빠르게 테스트하기 위해서다. 그리고 같은 사실이면 같은 결정이 나오게 하기 위해서다. 레이아웃 결과가 결정적이어야 한다는 불변식이 여기에 기대고 있다.

결과·거절·상태는 variant마다 frozen dataclass를 두고 union으로 묶는다. 문자열 status 필드로 상태를 나르지 않는다. 신뢰할 수 없는 입력은 경계에서 한 번 parse해 타입 값으로 만든다. 경계는 YAML·JSON·MCP 인자·UI 요청을 말한다. 출처: [ADR 0005](../adr/0005-capability-slices-and-test-colocation.md) 결정 4, [ADR 0009](../adr/0009-blueprint.md) 결정 1.

현재 실재: 결정 모듈로 지정된 곳은 `check_boundaries.py`의 `DECISIONS`에 있고 다른 기능을 import하지 않도록 검사된다. 모든 slice가 세 단계로 나뉜 것은 아니다. 나머지는 채택한 목표다.

## 코어 slice와 파일 규칙 (채택한 목표)

소유자가 2026-11-15에 정했다. 기능에 비해 코드가 복잡한 것은 잘못 만들고 있다는 증거다. 그래서 "그려줘 하면 예쁜 차트"에 직접 필요한 코어를 작은 slice로 다시 세운다. 코어 slice는 아래 열두 개다. 여기에 들지 않는 것은 코어가 아니며 제거하거나 허브로 옮길 후보다.

| slice | 한 가지 책임 |
| --- | --- |
| `style` | preset 적용, 글자·선·무게의 preset 상대값 |
| `size` | 물리 단위와 그림 크기, 종횡비 |
| `color` | 색 이름과 값, 팔레트, 대비 |
| `font` | 폰트 등록과 선택 |
| `layout` | 내용에 맞춘 결정적 여백 |
| `ticks` | 눈금의 숫자·날짜·단위 형식 |
| `labels` | 값 라벨, 패널 문자, 주석 |
| `legend` | 범례 배치 |
| `check` | 그려진 그림의 결함 찾기 |
| `save` | 여러 형식으로 저장 |
| `guide` | 에이전트 지침과 skill |
| `mcp` | 위 slice를 에이전트에 연결하는 얇은 진입점 |

코어 slice는 같은 파일 구성을 쓴다. 파일 이름이 역할을 말하므로 규칙을 파일 이름으로 건다.

| 파일 | 역할 | 규칙 |
| --- | --- | --- |
| `model.py` | slice의 도메인 타입. primitive를 감싸는 유일한 곳 | 순수 |
| `decide.py` | 평범한 그림에 대한 결정. 사실을 받아 계획을 돌려준다 | 순수, 도메인 타입만 |
| `edges.py` | 이름 붙은 엣지 케이스 목록 | 순수, 도메인 타입만 |
| `measure.py`, `apply.py` | figure에서 사실을 읽고 계획을 반영하는 shell | matplotlib 사용 |
| `__init__.py` | 표면(`__all__`) | 연결만 |
| `assets/` | 그 slice만 쓰는 데이터 파일. 스타일 파일, 폰트, 색 표, 지침 문서 | 다른 slice가 경로로 읽지 않는다 |

자산은 쓰는 slice 안에 둔다. 공용 `asset/` 폴더를 두지 않는 이유는 코드와 같다. 한 기능을 바꾸거나 지울 때 그 폴더 하나만 보면 되게 하기 위해서다.

**도메인 파일은 primitive 타입으로 말하지 않는다.** `decide.py`와 `edges.py`의 함수는 인자와 반환을 도메인 타입으로 적는다. `str`, `int`, `float`, `dict`, `Any` 같은 primitive나 annotation 누락은 오류다. `float` 두 개를 받는 함수는 폭과 높이가 바뀌어도 통과하지만 `Length`와 `Aspect`는 그렇지 않기 때문이다. primitive는 `model.py`에서 한 번 감싼다. 기준이 없는 예외는 두지 않으며 baseline도 없다.

**엣지 케이스는 본문 분기가 아니라 목록에 덧붙인다.** 숨긴 SubFigure, 극좌표 축, 빈 패널처럼 드문 그림에서만 필요한 처리는 `decide.py`에 분기를 더하지 않는다. `edges.py`의 `EDGES` 끝에 `EdgeCase` 하나를 더한다. 각 항목은 이름, 이유, 적용 조건, 계획을 바꾸는 함수를 갖는다. `settle`이 순서대로 적용하고 어떤 것이 작동했는지 돌려준다. 이렇게 하면 본 경로는 평범한 경우만 읽으면 되고, 엣지 케이스는 이름으로 세고 지울 수 있다. 엣지 케이스마다 그 이름을 적은 테스트가 있어야 한다. 장치는 [edgecase.py](../../src/dartwork_mpl/edgecase.py)에 있다.

이 규칙들은 [tests/architecture/test_domain_rules.py](../../tests/architecture/test_domain_rules.py)가 강제한다. 현재 실재: 이 파일 구성을 따르는 slice는 아직 없다. 기존 slice는 코어 slice를 새로 세우면서 옮기거나 지운다.

## 불변식

| 불변식 | 적용 범위 | 지키는 장치 | 위반하면 |
| --- | --- | --- | --- |
| **미감 유지.** 출하 색 값, 폰트, 글자 무게, spine, grid, preset의 모양은 바뀌지 않는다 | 남기는 모든 기능 | 색 해시 테스트, 픽셀 baseline(RMS 0.5) | 사용자 그림이 조용히 달라진다. 소유자가 before/after를 보고 승인해야만 바꾼다 |
| **matplotlib을 감싸지 않는다.** dm 함수는 native `Figure`·`Axes`를 받고 돌려준다. `dm.style.use`는 rcParams만 바꾼다 | 모든 공개 API | 리뷰, 공개 표면 검사 | 사용자가 dartwork-mpl 전용 개념을 배워야 하고 소유할 수 없는 코드가 된다 |
| **크기는 물리 단위, 글자·선은 preset 상대값.** `dm.figsize("13cm", ...)`, `dm.fs(n)`, `dm.lw(n)`, `dm.fw(n)` | 라이브러리, 예제, 템플릿, 지침 | 안티패턴 lint와 ratchet | preset을 바꾸면 그림이 깨진다 |
| **레이아웃은 결정적이고 다시 적용해도 같다** | `simple_layout`과 그 단계 | layout slice 테스트, 픽셀 baseline | 같은 코드가 실행마다 다른 그림을 낸다 |
| **slice 경계** | 모든 모듈 | `check_boundaries.py`, `tests/architecture/test_boundaries.py` | 한 기능 변경이 여러 폴더로 번진다 |
| **테스트는 wheel에 들어가지 않는다** | 패키징 | `tests/architecture/test_packaging.py` | 설치본이 커지고 테스트 의존성이 새어 나간다 |
| **`render_plot`은 신뢰한 코드만 실행한다.** 샌드박스가 없다 | MCP 렌더 | 도구 설명, 실행 시간·크기 제한 | 남이 올린 코드를 실행하면 그 머신이 뚫린다. 허브는 이 경로로 공유 코드를 실행하지 않는다 |

미감 불변식의 출처: [ADR 0001](../adr/0001-oklab-centered-color-construction.md) A1(색 동결의 정본은 테스트), [ADR 0009](../adr/0009-blueprint.md) 결정 2.

## 기능 제거 정책

미감 불변식 밖의 기능은 의미가 없으면 제거할 수 있다. 공개 이름, MCP 도구, CLI 명령도 포함된다. 소유자가 2026-11-15에 정한 정책이다. 기능 수보다 소유하고 이해할 수 있는 작은 표면이 이 라이브러리의 가치이기 때문이다.

제거할 때는 사용자가 길을 잃지 않게 두 곳에 기록한다.

- [CHANGELOG.md](../../CHANGELOG.md)
- 제거된 이름 registry. `src/dartwork_mpl/_compat.py`와 `lint/migrate.py`가 이 registry를 읽어 런타임 안내와 codemod를 만든다.

버전은 아직 0.x이므로 제거는 minor 릴리스에 싣는다.

이 정책은 [ADR 0005](../adr/0005-capability-slices-and-test-colocation.md) 결정 1(인터페이스 동결선)을 대체한다. 그 대체는 [ADR 0008](../adr/0008-owner-priority-lock-reset.md)이 기록한다. 출처: ADR 0008 결정 1·2.

## 채택한 리팩터 목표

소유자가 2026-11-15에 정한 순서다. 진행 상태는 각 단계의 plan이 소유한다.

1. **Handbook으로 철학과 불변식을 고정한다.** 이 문서다.
2. **slice와 functional core 구조로 코드를 정리한다.** ratchet으로 강제한다. 경계 검사, 안티패턴 ratchet, 모듈 크기 같은 수치는 줄어들기만 한다. 한 번에 갈아엎지 않고 slice 단위로 옮긴다.
3. **문서를 분리한다.** 브랜딩·사용자 문서·예제는 사이트 리포로 옮기고, 이 리포 `docs/`에는 개발 문서만 남긴다.
4. **git 히스토리의 대용량 잔재를 제거한다.** 3단계 다음에 한 번만 한다.
5. **MCP를 단순하게 재설계한다.** 레퍼런스 검색, 렌더, 검증 중심의 작은 도구 집합으로 줄인다. 벤치마크는 refero 같은 레퍼런스 라이브러리다.
6. **허브 계약을 정한다.** 이 리포는 산출물 형식과 결정적 렌더를 제공하고, 공유는 사이트 리포가 맡는다.

---
orphan: true
---

# 목적과 진실 소스

## 단 하나의 판단 기준

> **핵심**
>
> 사용자가 skill을 켜고 "그려줘"라고 하면 예쁜 차트가 나와야 한다. 이 리포의 모든 코드·도구·문서·테스트는 이 결과에 기여할 때만 의미가 있다. 기여하지 않는 것은 제거 대상이다.

소유자가 2026-11-15에 정한 기준이다. 기능을 넣을지, 남길지, 지울지 판단이 갈리면 이 문장으로 정한다. 구조 규칙, 검증 게이트, 문서도 이 기준을 빨리 안전하게 달성하기 위한 수단일 뿐이다.

그래서 사용자가 보기에 불쾌하거나 예쁘지 않은 차트가 나오면 그것은 취향의 문제가 아니라 버그다. 소유자가 2026-11-22에 정했다. 그 버그를 찾고 고치는 법은 [philosophy.md](philosophy.md) 1절과 2절에 있다.

## 왜 존재하는가

dartwork-mpl은 matplotlib 위의 얇은 유틸리티 층이다. 논문·보고서·발표에 바로 넣을 수 있는 그림을 사람과 AI 에이전트가 같은 규칙으로 만들게 한다. 줄이려는 비용은 세 가지다.

1. 그림마다 크기·글자·여백을 손으로 맞추는 반복 작업.
2. 같은 데이터인데 사람·에이전트·매체마다 모양이 달라지는 불일치.
3. 에이전트가 그럴듯하지만 겹치고 잘린 그림을 내놓고 아무도 모르는 실패.

이 라이브러리는 matplotlib을 새 API로 감싸지 않는다. 사용자는 계속 matplotlib의 `Figure`와 `Axes`를 직접 쓴다. dartwork-mpl은 물리 단위 크기, preset 상대 글자·선 크기, 색 체계, 결정적 레이아웃, 검증을 그 옆에 얹을 뿐이다. 그래서 dartwork-mpl을 빼도 사용자의 matplotlib 지식은 그대로 유효하다.

> **핵심**
>
> 판단 기준은 "matplotlib 사용자가 이것을 소유하고 이해할 수 있는가"다. 사용자가 matplotlib 대신 dartwork-mpl의 개념을 배워야 하는 기능은 이 라이브러리의 방향이 아니다.

## 누가 쓰는가

| 사용자 | 쓰는 방식 | 이 리포가 주는 것 |
| --- | --- | --- |
| 연구자·엔지니어 | Python에서 `import dartwork_mpl as dm` | preset, `dm.figsize`, `dm.simple_layout`, 색, `dm.check` |
| AI 코딩 에이전트 | 동봉된 skill과 에이전트 자신의 셸(`python plot.py`) | 지침, `dm.lint_code`, `dm.check` |

## 제품의 세 층

소유자가 2026-11-15에 정한 구성이다. Refero가 제품·방법론·코퍼스를 나눈 방식과 같다.

| 층 | 무엇인가 | 어디에 있는가 |
| --- | --- | --- |
| **도구** | 좋은 그림을 그리기 위한 라이브러리 | 이 리포의 slice |
| **skill** | 좋은 차트가 일반적으로 갖는 특성과, 도구를 다루는 법 | `skills/dartwork-mpl/` |
| **레퍼런스** | 많은 실제 사례. 사용자들이 공유하고 서로 참고한다 | 허브(별도 사이트 리포) |

- 구도가 열린 요청에서는 Hub의 레퍼런스 라이브러리(`https://mpl.dartwork.io/mcp`, `search_references`)로 독자의 질문과 데이터에 맞는 외부 작품과 갤러리 예시를 찾을 수 있다. 수집·검색은 Hub가 소유하고, skill은 언제 찾고 어떻게 적용하는지만 안내한다.
- **skill은 큰 그림만 잡는다.** 사람들이 어떻게 쓸지 알 수 없으므로 모든 경우에 답하려 하지 않는다. 한 케이스에만 맞는 규칙은 넣지 않는다. 기계적으로 판정할 수 있는 것은 `dm.check`와 lint가 맡고, skill은 관점과 판단 기준을 준다.
- **MCP 서버는 두지 않는다.** 에이전트는 자기 셸에서 코드를 실행하고 `dm.check`를 부른다. MCP가 정당한 경우는 원격 코퍼스, 계정 데이터, 셸에 없는 능력뿐이고, 허브가 생기면 그 검색이 여기에 해당한다.
- **허브 기능은 이 라이브러리에 넣지 않는다.** 공유·검색·저장·사용자 관리는 사이트 리포가 소유한다. 라이브러리 설치에 서버 의존성이 따라오지 않게 하고, 다중 사용자 보안 문제를 라이브러리 밖에 두기 위해서다.
- **이 리포의 `docs/`에는 개발 문서만 있다.** 브랜딩, 사용자 문서, 예제 갤러리는 사이트 리포의 몫이다.

번들 템플릿은 지웠다. 원본 36개는 커밋 `f021de7d`의 `src/dartwork_mpl/guide/assets/templates/`에서 읽을 수 있다.

## 영역별 진실 소스

Handbook은 모든 영역의 정본이 아니다. 아래 표는 각 영역에서 무엇이 현재 정답인지 가리킨다.

| 영역 | 정본 | Handbook의 역할 |
| --- | --- | --- |
| 라이브러리 동작 | `src/dartwork_mpl/` 코드 | 의도와 불변식만 설명 |
| 공개 API 표면 | `dm.__all__`과 각 slice의 `__all__` | 표면이 바뀌는 조건을 설명 ([architecture.md](architecture.md)) |
| slice 경계, platform, 조립 모듈 | [tests/architecture/boundaries.py](../../tests/architecture/boundaries.py), [composition.py](../../tests/architecture/composition.py) | 규칙의 이유를 설명 |
| 출하 색 값 | `src/dartwork_mpl/color/assets/`의 색 표와 [tests/test_shipped_colors_hash.py](../../tests/test_shipped_colors_hash.py)의 digest | 미감 불변식으로 설명 |
| 시각 스타일 | `src/dartwork_mpl/style/assets/`의 preset, `font/assets/`의 폰트, [tests/visual/baseline/](../../tests/visual/baseline/) | 미감 불변식으로 설명 |
| 에이전트 지침과 안티패턴 | [skills/dartwork-mpl/](../../skills/dartwork-mpl/)의 skill, [src/dartwork_mpl/guide/assets/](../../src/dartwork_mpl/guide/assets/)의 `anti-patterns.yaml` | 위치만 가리킴 |
| 검증 절차와 합격 기준 | [verification.md](verification.md)와 `.github/workflows/` | Handbook이 직접 소유 |
| 결정 권한과 변경 흐름 | [change-flow.md](change-flow.md) | Handbook이 직접 소유 |
| 릴리스 버전 | `pyproject.toml`의 `version`, `v*.*.*` 태그, PyPI | 절차를 설명 ([change-flow.md](change-flow.md)) |
| 설계의 이유와 대안 비교 | 이 Handbook의 본문. 당시 맥락은 [docs/adr/](../adr/index.md) | ADR은 출처일 뿐 현재값의 정본이 아니다 |

> **주의**
>
> 문서와 코드가 다르면 코드가 현재 실재다. 다만 불변식과 다른 코드는 버그다. 어느 쪽을 고칠지는 [change-flow.md](change-flow.md)의 결정 권한을 따른다.

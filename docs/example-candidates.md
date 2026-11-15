# 예시로 옮길 기능 후보

> **한눈에**
>
> 이 리포에서 지운 공개 함수 19개와, 예시가 그 자리를 채울 때 보여줘야 할 내용의 목록이다. 허브가 이 목록을 가져가 예시를 만든다. 번들 템플릿 36개도 지웠고, 그것들은 예시의 출발점으로 쓸 수 있다.

기준은 [handbook/philosophy.md](handbook/philosophy.md) 1절의 "무엇이 기능이 되는가"다. 기준 커밋은 `3e50748d`(`refactor/foundation`)이고, 아래 파일 경로와 줄 번호는 그 커밋의 것이다.

## 허브가 할 일

후보 하나마다 예시 하나를 만든다.

1. 아래 표의 "구현" 위치에서 함수와 docstring을 읽는다. 동작의 세부는 같은 slice의 `tests/test_surface.py`와 `tests/test_edges.py`에 있다.
2. 그 함수 없이 같은 결과를 내는 코드를 쓴다. matplotlib과 남는 dm 기능(`dm.style`, `dm.figsize`, `dm.simple_layout`, `dm.save_formats`, 색 이름, `dm.fs`·`dm.lw`·`dm.fw`)만 쓴다.
3. "예시가 보여줘야 할 것"을 그림에서 확인할 수 있게 한다. 표에 적힌 함정은 함수가 대신 처리해 주던 것이므로 예시 코드에 드러나야 한다.
4. 예시가 생기면 이 표의 "상태" 칸에 허브의 주소를 적는 PR을 이 리포에 연다.

"상태"가 "지움"인 함수는 이 리포에서 지웠다. 원본은 기준 커밋에서 읽는다(`git show 3e50748d:src/dartwork_mpl/<구현 경로>`). "남김"은 기능으로 남긴 것이고 이유는 아래에 있다.

지운 템플릿 36개는 `git show f021de7d:src/dartwork_mpl/guide/assets/templates/<basic|advanced>/<이름>.py`로 읽는다. 지운 함수를 부르는 줄은 예시로 옮길 때 풀어 써야 한다.

"쓰임"은 skill 문서에 나온 횟수 / 번들 템플릿 36개 중 쓰는 파일 수 / 마지막 평가(`20261115-214430`)의 skill 실행 16개 중 쓴 수다.

## A. 바로 예시로 옮길 수 있는 것

다른 기능이 이 함수의 결과를 읽지 않는다. 지워도 남는 기능의 동작은 달라지지 않는다.

| 함수 | 하는 일 | 구현 | 쓰임 | 예시가 보여줘야 할 것 | 상태 |
| --- | --- | --- | --- | --- | --- |
| `set_decimal` | 눈금을 고정 소수 자릿수로 쓴다 | `ticks/__init__.py:236` | 0/0/0 | `FuncFormatter` 또는 `StrMethodFormatter` 한 줄 |지움 |
| `format_axis_millions` | 눈금을 `1.5M`으로 쓴다 | `ticks/__init__.py:164` | 0/0/0 | 필요한 만큼만 소수를 쓰는 법(`1M, 2M` 대 `0.5M, 1.0M`) |지움 |
| `format_axis_billions` | 눈금을 `1.5B`로 쓴다 | `ticks/__init__.py:177` | 0/0/0 | 위와 한 예시로 묶는다 |지움 |
| `format_axis_currency` | 눈금을 `$1,500`, `1,000€`로 쓴다 | `ticks/__init__.py:187` | 0/1/0 | 음수의 부호 위치(`-$1,500`), 기호가 뒤에 오는 통화 |지움 |
| `format_axis_year` | 눈금을 `25년`으로 쓴다 | `ticks/__init__.py:244` | 1/0/0 | 두 자리와 네 자리 연도 |지움 |
| `rotate_tick_labels` | 눈금 글자를 돌린다 | `ticks/__init__.py:404` | 0/0/0 | 돌린 글자의 정렬(`ha="right"`, `rotation_mode="anchor"`). 먼저 가로 막대로 바꾸는 것이 낫다는 점 |지움 |
| `label_hline` | 가로 기준선에 이름을 붙인다 | `compose/labels.py:160` | 0/2/0 | 선에서 포인트 단위로 띄우기(`annotate`의 `textcoords="offset points"`), 선 위와 아래 |지움 |
| `annotate_corner` | 축 구석에 설명 글을 쓴다 | `compose/labels.py:132` | 0/1/0 | `transAxes` 좌표와 포인트 단위 안쪽 여백. 데이터와 겹치면 다른 구석으로 옮기는 판단 |지움 |
| `mix_colors` | 두 색을 OKLab에서 섞는다 | `color/__init__.py:142` | 0/0/0 | `dm.color(...)`의 OKLab 값으로 직접 섞기 |지움 |
| `pseudo_alpha` | 투명도를 불투명 색으로 바꾼다 | `color/__init__.py:151` | 0/3/0 | 겹친 면이 진해지지 않게 불투명 색을 쓰는 이유와 계산 |지움 |
| `make_palette` | Open Color 이름 `n`개를 돌려준다 | `color/__init__.py:338` | 0/0/0 | 범주, 순차, 발산 계열에 맞는 색 이름 고르기 |지움 |
| `cspace` | 두 색 사이의 색 `n`개를 만든다 | `color/__init__.py:127` | 0/9/0 | 순서 있는 계열에 한 색상의 명도 단계를 쓰는 법 |지움 |
| `readable_text_color` | 배경에 맞는 흰색 또는 검은색을 고른다 | `color/__init__.py:185` | 0/2/0 | 히트맵 칸의 숫자 색 고르기 |남김 |
| `ensure_contrast` | 대비가 모자란 색을 조정한다 | `color/__init__.py:164` | 0/10/0 | 색 위의 글자가 읽히는 대비(4.5:1) 확인과 보정 |남김 |
| `list_colors` | `dc.*` 계열 목록을 돌려준다 | `color/__init__.py:288` | 2/0/0 | 예시가 아니라 허브의 색 표 페이지가 대신한다 |남김 |
| `grid_shape` | 패널 `n`개의 행과 열 수를 정한다 | `size/__init__.py:78` | 2/2/0 | small multiples의 행과 열 고르기, 빈 칸 처리 |지움 |
| `list_aspect_tokens` | 비율 이름 목록을 돌려준다 | `size/__init__.py:90` | 1/0/0 | 예시가 아니라 skill의 표가 대신한다 |지움 |

남긴 것은 셋이다.

- `ensure_contrast`, `readable_text_color`: `dm.check`의 `TEXT_CONTRAST`가 고치는 방법으로 안내한다. WCAG 대비 식을 예시마다 풀어 쓰면 길고 틀리기 쉽다.
- `list_colors`: 어떤 색 계열이 있는지 묻는 토큰 조회다. 색 digest 테스트가 이것으로 계열을 센다.

## B. 얽힘을 먼저 확인해야 하는 것

다른 기능이 이 함수가 남긴 결과를 읽는다. 지우려면 그 연결도 함께 정해야 한다.

| 함수 | 하는 일 | 구현 | 쓰임 | 얽힌 곳 | 예시가 보여줘야 할 것 | 상태 |
| --- | --- | --- | --- | --- | --- | --- |
| `format_axis_si` | 눈금을 `12k`, `3M`으로 쓴다 | `ticks/__init__.py:137` | 2/5/0 | `label_bars`가 축과 같은 단위로 막대 값을 쓴다(`compose/labels.py:41`) | 축 전체가 한 단위와 한 자릿수를 쓰게 하는 법 |지움 |
| `format_axis_myriad` | 눈금을 만, 억, 조로 쓴다 | `ticks/__init__.py:207` | 3/0/3 | 위와 같다. 평가에서 실제로 쓰인 유일한 눈금 함수다 | 한국어 큰 수 표기, 통화 기호 |남김 |
| `format_axis_dates` | 범주 위치에 날짜를 쓴다 | `ticks/__init__.py:297` | 1/0/0 | `simple_layout`이 빽빽한 날짜를 솎는다(`layout/loop.py:80`) | 막대 아래 날짜, 연도는 바뀔 때만 쓰기 |지움 |
| `axis_unit` | 단위를 축 이름으로 옮기고 눈금은 숫자만 쓴다 | `ticks/__init__.py:324` | 2/1/0 | `label_bars`의 단위, 그릴 때마다 단위를 다시 고르는 formatter | 단위를 축 이름에 한 번만 쓰는 법 |지움 |
| `axis_unit_of` | `axis_unit`이 고른 단위를 돌려준다 | `ticks/__init__.py:398` | 1/0/0 | `axis_unit`과 함께 간다 | 위와 한 예시로 묶는다 |지움 |
| `annotate_value` | 값 하나에 이름을 붙인다 | `compose/labels.py:100` | 4/0/2 | 얽힘은 없으나 평가에서 실제로 쓰였다 | 점에서 포인트 단위로 띄우기, 놓을 쪽 고르기 |남김 |
| `set_colors` | 색 순환을 정한다 | `color/__init__.py:308` | 1/0/0 | preset이 정한 순환을 덮어쓴다 | `ax.set_prop_cycle`과 색 이름 |지움 |

남긴 것은 둘이다.

- `format_axis_myriad`: 만·억 표기는 단위와 자릿수를 함께 골라야 해서 몇 줄로 풀어 쓸 수 없고, 평가에서 실제로 쓰였다.
- `annotate_value`: 평가에서 실제로 쓰였다. `ax.annotate` 몇 줄로 대신할 수 있으므로 예시가 생기면 지울 수 있다.

눈금의 자동 표기는 그대로다. 포맷을 지정하지 않은 축은 백만부터 `1M`, 한국어 preset에서는 `100만`으로 찍히고, 연도와 날짜도 자동으로 줄여 쓴다.

## C. 기능으로 남기는 것

그려진 결과를 재야 하거나 모든 그림이 같은 값을 써야 한다. 예시로 대신할 수 없다.

| 기능 | 남기는 이유 |
| --- | --- |
| `dm.style`, `dm.fs`·`dm.lw`·`dm.fw`, 색 이름과 colormap, 번들 폰트 | 모든 그림이 같은 값을 쓴다 |
| `dm.figsize`, `dm.figsize_for`, 길이 단위 | 물리 크기를 정한다 |
| `dm.simple_layout` | 그린 뒤 글자를 재어 여백을 맞춘다 |
| `dm.place_legend`, `dm.figure_legend` | 그려진 데이터를 재어 자리를 고른다 |
| `dm.label_bars`, `dm.label_line_ends`, `dm.label_axes`, `dm.add_note` | 그려진 크기에 맞춰 자리를 잡고, 자리가 없으면 숨긴다 |
| `dm.check`, `dm.lint_code` | 결함을 기계가 판정한다 |
| `dm.save_formats` | 저장 형식과 메타데이터를 고정한다 |
| `dm.color`, `dm.colors`, `dm.rgb`·`dm.hex`·`dm.oklab`·`dm.oklch`, `dm.Color` | 색 값의 타입이다. 남는 기능과 A의 예시가 쓴다 |

## 정하지 않은 것

- `dm.config`(`tick_years`, `number_ladder`): 자동 표기의 연도 자릿수와 단위 계열을 바꾸는 전역 설정이다. `dm.EXPERIMENTAL`은 지웠다.
- 길이 단위의 공개 이름(`dm.cm`, `dm.mm`, `dm.pt`, `dm.inch`, `dm.col1`, `dm.col2`): `dm.figsize("13cm")`처럼 문자열로도 쓸 수 있어 겹친다. 예시의 문제는 아니다.

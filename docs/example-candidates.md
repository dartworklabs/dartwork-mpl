# 지운 기능의 기록

> **한눈에**
>
> 재구성하면서 이 리포에서 지운 공개 함수, 인자, 자동 동작, 검사 규칙의 기록이다. 각 항목에 무엇을 했는지, 원본을 어디서 읽는지, 같은 일을 예시로 하려면 무엇을 보여줘야 하는지를 적었다. 허브가 예시 소재를 찾을 때 참고하는 기록이고, 만들어야 할 목록이 아니다. 허브와 약속된 것은 [hub-contract.md](hub-contract.md)에 있다.

기준은 [handbook/philosophy.md](handbook/philosophy.md) 3절의 "무엇이 기능이 되는가"다. 첫 표들의 기준 커밋은 `3e50748d`(`refactor/foundation`)이고, 파일 경로와 줄 번호는 그 커밋의 것이다. 뒤쪽 절은 절마다 기준 커밋을 적었다.

## 순서

소유자가 정한 순서다(2026-11-16).

1. 허브 담당자가 이 리포의 유산 가운데 쓸 만한 것을 허브(`mpl.dartwork.io`)로 옮긴다. 아래 표의 지운 것들, 지운 템플릿 36개, 과거 커밋의 예제와 문서가 대상이다. 이 리포의 코드 정리와 나란히 진행한다.
2. 옮기기가 끝나면 허브 담당자가 이 리포의 git 히스토리를 정리해 용량을 줄인다. `.git`은 약 610 MB이고 대부분 과거에 커밋된 그림이다. 과거 히스토리는 잃어도 된다. 허브 담당자가 옮기기가 끝났다고 확인해 주면 소유자가 대신 진행할 수도 있다.

2번을 하면 아래의 `git show <커밋>:...` 명령이 더는 동작하지 않는다. 그래서 1번이 먼저다.

## 읽는 법

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
| `mix_colors` | 두 색을 OKLab에서 섞는다 | `color/__init__.py:142` | 0/0/0 | `dm.color(...)`의 OKLab 값으로 직접 섞기 |지움. 2026-11-17부터 skill의 레시피(`references/colors.md` "A ramp between two colours")가 같은 산술을 보여준다 |
| `pseudo_alpha` | 투명도를 불투명 색으로 바꾼다 | `color/__init__.py:151` | 0/3/0 | 겹친 면이 진해지지 않게 불투명 색을 쓰는 이유와 계산 |지움 |
| `make_palette` | Open Color 이름 `n`개를 돌려준다 | `color/__init__.py:338` | 0/0/0 | 범주, 순차, 발산 계열에 맞는 색 이름 고르기 |지움 |
| `cspace` | 두 색 사이의 색 `n`개를 만든다 | `color/__init__.py:127` | 0/9/0 | 순서 있는 계열에 한 색상의 명도 단계를 쓰는 법 |지움. 임의의 두 색 사이 램프는 이 기록이 다루지 않았다(#775). 2026-11-17부터 skill의 레시피(`references/colors.md` "A ramp between two colours")에 있다 |
| `readable_text_color` | 배경에 맞는 흰색 또는 검은색을 고른다 | `color/__init__.py:185` | 0/2/0 | 히트맵 칸의 숫자 색 고르기 |남김 |
| `ensure_contrast` | 대비가 모자란 색을 조정한다 | `color/__init__.py:164` | 0/10/0 | 색 위의 글자가 읽히는 대비(4.5:1) 확인과 보정 |남김 |
| `list_colors` | `dc.*` 계열 목록을 돌려준다 | `color/__init__.py:288` | 2/0/0 | 예시가 아니라 허브의 색 표 페이지가 대신한다 |남김 |
| `grid_shape` | 패널 `n`개의 행과 열 수를 정한다 | `size/__init__.py:78` | 2/2/0 | small multiples의 행과 열 고르기, 빈 칸 처리 |지움 |
| `list_aspect_tokens` | 비율 이름 목록을 돌려준다 | `size/__init__.py:90` | 1/0/0 | 허브가 skill 문장을 정규식으로 읽어야 했다(#736) |`dm.list_aspects`로 되살림 |

남긴 것은 셋이다.

- `ensure_contrast`, `readable_text_color`: 예시가 널리 쓰는 색 산술이다(지운 템플릿 36개 중 10개가 썼다). WCAG 대비 식을 예시마다 풀어 쓰면 길고 틀리기 쉽다.
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

## B2. 눈금 자동 표기에서 지운 것

`dm.simple_layout`이 포맷을 지정하지 않은 축에 그려진 데이터를 읽고 표기를 골라 주던 동작이다. 소유자가 2026-11-16에 지우기로 했다. 이제 눈금 글자는 preset 토큰(`axes.formatter.useoffset: False`, `axes.formatter.limits`, `date.autoformatter.*`)과 matplotlib의 기본 formatter가 쓴다. `dm.config`(`tick_years`, `number_ladder`)도 함께 지웠다.

기준 커밋은 `0da90445`다. 원본은 `git show 0da90445:src/dartwork_mpl/<구현 경로>`로 읽고, 동작의 세부는 같은 커밋의 `ticks/tests/test_tick_text.py`, `test_surface.py`, `test_edges.py`에 있다. 자동 동작이라 skill과 템플릿에서 부르는 횟수가 없으므로 "쓰임" 칸은 두지 않는다.

| 동작 | 하던 일 | 구현 | 예시가 보여줘야 할 것 | 상태 |
| --- | --- | --- | --- | --- |
| 천 단위 구분 기호 | 1,000 이상인 축에 `1,250`, 연도처럼 보이는 x 눈금은 제외 | `ticks/decide.py:137` | `StrMethodFormatter("{x:,.0f}")`. 연도 축에는 쓰지 않는 이유 |지움 |
| 한국어 그림의 만·억 | 축 이름·제목·범례에 한글이 있으면 `100만` | `ticks/edges.py:35`, `ticks/measure.py:82` | `dm.format_axis_myriad(ax)` 한 줄로 충분하다는 점 |지움 |
| 연도 눈금 | x 데이터가 1900–2099의 정수면 정수 연도에만 눈금, 두 자리(`24`), 백 년이 보이면 네 자리 | `ticks/edges.py:49`, `ticks/formatters.py:170`, `:205` | `MaxNLocator(integer=True)`와 `FuncFormatter(lambda v, _: f"{int(v) % 100:02d}")`. 확대하면 `2017.5`가 생기는 함정 |지움 |
| 분기 라벨 | 3개월 간격 날짜를 `24.Q1`로, 분기말 날짜면 분기말에 눈금 | `ticks/edges.py:88`, `ticks/dates.py:127`, `:171` | `MonthLocator(bymonth=(1, 4, 7, 10))`와 분기를 계산하는 `FuncFormatter` |지움 |
| 짧은 날짜 | 모든 눈금을 `24.01`, `24.01.15`로, 시간 축은 `09:00`과 모서리 날짜 | `ticks/dates.py:25` | preset의 `date.autoformatter.*`가 대부분 대신한다(아래). 시간 축의 날짜를 모서리에 한 번만 쓰려면 `ConciseDateFormatter`의 `formats`·`zero_formats`·`offset_formats` |지움 |
| 날짜 솎기 | 여백을 맞춘 뒤 날짜 라벨 사이가 1 em보다 좁으면 눈금을 줄인다 | `ticks/apply.py:172`, `:237` | `AutoDateLocator(maxticks=…)` 또는 `MonthLocator(interval=…)`. 그림 너비에 맞춰 간격을 고르는 법 |지움 |
| 트윈 축의 spine | preset이 숨긴 오른쪽·위 spine을 `twinx`·`twiny`의 눈금 쪽에서 켠다 | `ticks/edges.py:118`, `ticks/twins.py:110` | `ax2.spines["right"].set_visible(True)` 한 줄. skill의 `references/layout.md`에 있다 | 되살림 (`layout`이 Axes마다 한 번 켠다) |

토큰이 대신하는 것과 못 하는 것:

- 큰 수의 기본 표기는 기능으로 남았다. 천 단위 쉼표와 `1M`·`100만`은 스타일 값으로 쓸 수 없고, 빠지면 축에 `2600000`이 찍힌다.
- 날짜는 `date.converter: auto`와 `date.autoformatter.*`로 `24`, `24.01`, `24.01.15`, 시간 축은 `03.01 06:00`으로 찍힌다. matplotlib 3.11의 concise 변환기는 `date.autoformatter.*`를 읽지 않으므로 converter를 `auto`로 바꿨다. 그래서 바뀌는 해만 연도를 쓰는 concise의 생략과 모서리 날짜가 없다.
- 숫자 연도 축은 `2016, 2018`로 네 자리다. 두 자리 연도는 토큰으로 쓸 수 없다.

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

- 길이 단위의 공개 이름(`dm.cm`, `dm.mm`, `dm.pt`, `dm.inch`, `dm.col1`, `dm.col2`): `dm.figsize("13cm")`처럼 문자열로도 쓸 수 있어 겹친다. 예시의 문제는 아니다.

## legend

`dm.place_legend`과 `dm.figure_legend`에서 지운 동작이다. 측정으로 자리를 고르는 일(안쪽의 빈 자리, 바깥 변의 행 수와 눈금 라벨 너머 거리, 위 범례 위로 올리는 제목)은 기능으로 남았다. 기준 커밋은 `183b1b59`이고 원본은 `git show 183b1b59:src/dartwork_mpl/legend/<파일>`로 읽는다. 실제 차트 10개(선, 띠, 산점도, 묶은 막대, twin, 히스토그램 등)와 바깥 배치 11개에서 지우기 전후 그림이 픽셀 단위로 같았다.

| 동작 | 하던 일 | 구현 | 예시가 보여줘야 할 것 | 상태 |
| --- | --- | --- | --- | --- |
| 빈 자리가 없을 때 바깥으로 | 안쪽 여덟 자리가 모두 데이터를 덮으면 다른 패널이 없는 쪽(위, 아래, 오른쪽)으로 옮긴다 | `decide.py:138`, `measure.py:158` | `dm.check`가 `LEGEND_ON_DATA`를 내면 `dm.place_legend(ax, loc="above")`로 바꾸는 흐름. `margins(0)`로 꽉 찬 산점도가 예다 |지움 |
| 안쪽 1–3열 시도 | 한 열이 안 들어가면 두세 열로 다시 재고, Axes 높이의 55 %가 넘는 한 열 범례는 마지막에 둔다 | `decide.py:90`, `:124` | `dm.place_legend(ax, ncols=3)`. 위쪽에 낮은 띠가 빌 때 여러 열이 맞는 차트 |지움 |
| matplotlib `loc` 통과 | `place_legend(ax, loc="upper left")`와 figure의 `"outside ..."`를 그대로 matplotlib에 넘긴다 | `model.py:129`, `apply.py:357`, `figure.py:75` | 고정 자리는 `ax.legend(loc="upper left")`. twin이면 위 twin에서 `ax2.legend(h1 + h2, l1 + l2, loc=...)`와 그때 잃는 것 |지움 |
| 캔버스 폭까지 넓은 바깥 범례 | 위·아래 범례의 행 수를 Axes가 아니라 캔버스 폭(옆 패널 앞까지)에 맞춘다 | `measure.py:211` | `ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncols=n)`. 이제는 Axes 폭에 맞춰 행이 늘 수 있다 |지움 |
| figure 범례가 위에 안 맞으면 오른쪽 | `figure_legend(fig)`가 위에 한 열도 안 들어가면 오른쪽으로 | `decide.py:176` | `dm.figure_legend(fig, loc="right")` |지움 |
| 호출자가 옮긴 범례 존중 | `legend.set_loc(...)`로 옮긴 범례를 `simple_layout`이 다시 옮기지 않는다 | `apply.py:144` | 직접 고른 자리는 `ax.legend(loc=...)`로 새로 만든다. `set_bbox_to_anchor`로 옮긴 범례는 지금도 그대로 둔다 |지움 |
| 다시 만들 때 handler 유지 | 범례를 다시 만들 때 사용자 `handler_map`을 옮긴다. 제목, 테두리, 글자 크기는 지금도 옮긴다 | `apply.py:298` | `dm.place_legend(ax, handler_map={...})` |지움 |

## labels

`dm.label_bars`, `dm.annotate_value`, `dm.label_axes`, `dm.label_line_ends`, `dm.add_note`는 남았고, 키워드와 일부 자동 동작을 지웠다. 마지막 평가(`20261115-214430`)의 스크립트는 다섯 함수 모두 키워드 없이 불렀다. 기준 커밋은 `183b1b59`이고, 원본은 `git show 183b1b59:src/dartwork_mpl/<구현 경로>`로 읽는다. 동작의 세부는 같은 커밋의 `labels/tests/`에 있다. matplotlib의 `ax.bar_label`이 막대 라벨의 대부분을 한 줄로 대신한다.

| 지운 것 | 하던 일 | 구현 | 예시가 보여줘야 할 것 | 상태 |
| --- | --- | --- | --- | --- |
| `label_bars(where=)` | `"inside"`는 막대 끝 안쪽(안 들어가면 바깥), `"center"`는 막대 가운데 | `labels/bar_options.py:86`, `labels/bar_options.py:259` | `ax.bar_label(bars, label_type="center")`. 막대 위 글자의 흰색·검은색 고르기 |지움 |
| `label_bars(total=)` | 누적 막대에서 합계만 또는 조각만 | `labels/edges.py:54` | 합계만: 맨 위 container에 `ax.bar_label(top, labels=[...])`로 합을 쓴다 |지움 |
| `label_bars(decimals=, fmt=)` | 고정 소수 자릿수, `"${}B"` 같은 틀이나 함수로 쓰기 | `labels/model.py:175`, `labels/bars.py:296` | `ax.bar_label(bars, fmt="{:.1f} GWh")`. 축 눈금의 단위(만·억, %)와 맞추는 법 |지움 |
| `label_bars(sign="+")` | 오른 값에 `+`를 붙인다(폭포 차트) | `labels/edges.py:44` | `ax.bar_label(bars, fmt="{:+g}")`. 0에는 부호를 붙이지 않는 점 |지움 |
| `label_bars(color=)` | 라벨 색 하나, 또는 `"series"`: 막대 밖 라벨을 막대 색으로(대비 4.5:1로 어둡게) | `labels/edges.py:105`, `labels/measure.py:213` | 폭포 차트의 오름·내림을 라벨 색으로 말하기, `dm.ensure_contrast`로 글자 대비 맞추기 |지움 |
| `label_bars(crowded="skip")` | 빽빽할 때 라벨을 세우지 않고 하나 걸러 숨긴다 | `labels/bar_layout.py:64` | 기본 동작(세우고 그래도 겹치면 숨김)을 쓰지 않을 때 `bar_label` 뒤 라벨을 골라 `set_visible(False)` |지움 |
| 트윈 축 위에 라벨 그리기 | 막대 라벨을 맨 위에 그려지는 트윈 Axes에 붙인다 | `labels/measure.py:442` | `ax.set_zorder(ax2.get_zorder() + 1)`과 `ax.patch.set_visible(False)` |지움 |
| 다시 부르면 바꾸기 | 같은 막대에 `label_bars`를 다시 부르면 앞의 라벨을 지운다 | `labels/bars.py:406` | 스크립트를 처음부터 다시 실행한다 |지움 |
| 뷰 밖 막대의 라벨 숨김 | 막대 끝이 축 범위 밖이면 라벨을 숨긴다 | `labels/bars.py:173` | `set_ylim`으로 자른 막대에 라벨을 붙이지 않는다 |지움 |
| `annotate_value(side=, offset_pt=, fontsize=, **kw)` | 놓을 쪽과 거리, 크기, 그 밖의 `annotate` 인자 | `labels/model.py:256`, `labels/notes.py:62` | 쪽을 정하려면 `ax.annotate(text, (x, y), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom")` |지움 |
| `label_axes(fontsize=, fontweight=, x=, y=, **kw)` | 크기·무게, 축 비율로 고정한 자리, 그 밖의 글자 인자 | `labels/model.py:272`, `labels/letters.py:108` | 고정 자리는 `ax.text(-0.1, 1.05, "a", transform=ax.transAxes)`. 돌려받은 글자에 `set_fontweight("bold")` |지움 |
| `label_line_ends(lines=, gap_pt=, **kw)` | 이름 붙일 선 고르기, 간격, 글자 인자 | `labels/ends.py:91` | 이름을 붙이지 않을 선은 `label="_hidden"`. 돌려받은 글자를 고친다 |지움 |
| `add_note(**kw)` | 글자 인자 | `labels/notes.py:117` | 돌려받은 글자에 `set_color`, `set_fontsize` |지움 |

## check

"되살림"은 코퍼스(`tests/corpus/`)에서 실제 결함을 잡는 것이 확인되어 좁힌 형태로 다시 넣은 규칙이다. 범례가 제목이나 다른 범례를 덮는 경우도 `LEGEND_ON_DATA`에 다시 들어갔다.

`dm.check`의 규칙 18개 중 12개와 그것만 쓰던 측정을 지웠다(2026-11-16). 남은 규칙은 `OVERFLOW`, `OVERLAP`, `CROSS_AXES_OVERLAP`, `TEXT_CROWD`, `LEGEND_ON_DATA`, `TICK_OVERLAP`이다. 지운 규칙은 마지막 평가(`20261115-214430`)에서 그림을 낸 스크립트 19개, 픽셀 장면 20개, robustness 장면 51개(layout 전후)에서 한 번도 작동하지 않았거나, 작동한 곳이 모두 사람이 보기에 결함이 아니었거나, `dm.simple_layout`을 부른 뒤에는 한 번도 작동하지 않았다. 대부분 그림을 보면 알 수 있는 것이라 skill의 `references/review.md` "Look at the image" 목록이 맡는다. 예시는 그 판단을 그림 한 쌍(나쁜 것, 고친 것)으로 보여주면 된다.

원본은 `git show 183b1b59:src/dartwork_mpl/check/<파일>`로 읽는다.

| 규칙 | 하던 일 | 구현 | 예시가 보여줘야 할 것 | 상태 |
| --- | --- | --- | --- | --- |
| `TEXT_AT_EDGE` | 캔버스 가장자리 1 pt 안에 붙은 글자(INFO) | `decide.py:52` | `fig.text(0, …)` 대신 `x`에 여백을 두거나 `dm.simple_layout(fig, margin="2mm")` | 지움 |
| `MARGIN_ASYMMETRY` | 한쪽 여백이 반대쪽의 3배를 넘음 | `decide.py:74` | 손으로 `subplots_adjust`한 그림과 `dm.simple_layout` 뒤의 그림 | 지움 |
| `MISSING_AXIS_LABEL` | 이름도 단위도 없는 숫자 축(INFO). 날짜 축에도 떠서 소음이었다 | `decide.py:157` | `ax.set_ylabel("Revenue (M USD)")`처럼 양과 단위를 쓰는 법, 날짜·범주 축은 생략해도 되는 이유 | 되살림 |
| `TEXT_CONTRAST` | 글자와 그 아래 색의 WCAG 대비가 4.5:1(큰 글자 3:1) 미만. 그림을 Agg로 한 번 더 그려 픽셀을 읽었다 | `decide.py:172`, `ink.py:266` | 진한 색 위의 값 라벨에 `dm.readable_text_color(배경)`. 히트맵 주석이 대표 사례 | 되살림 |
| `LEGEND_OVERFLOW` | 범례가 plot의 30 %(밖이면 50 %)보다 크거나 캔버스 밖으로 나감 | `decide.py:195` | 캔버스 밖으로 잘리는 범례는 이제 `OVERFLOW`가 범례 글자로 잡는다. 선이 많으면 `dm.label_line_ends(ax)` | 지움 |
| `LEGEND_OVERLAP` | 범례가 제목·축 이름·눈금 글자를 덮음 | `decide.py:222` | `bbox_to_anchor`로 위에 올린 범례와 제목이 부딪히는 경우, `dm.place_legend(ax, loc="above")` | 지움 |
| `VALUE_LABEL_ON_DATA` | 값 라벨이 선·막대·점 위에 그려짐 | `decide.py:261` | 선 위의 점 값은 `dm.annotate_value`, 막대는 `dm.label_bars` | 되살림 |
| `VALUE_LABEL_DECIMAL` | 정수인 값 라벨이 `120.0`처럼 소수를 찍음 | `decide.py:281` | `f"{v:,.0f}"` | 되살림 |
| `TICK_CROWD` | 눈금 글자 사이가 0.5 em 미만(INFO). 작동한 곳은 모두 `TICK_OVERLAP`도 작동했다 | `decide.py:317`, `overlap.py:87` | `ax.locator_params(nbins=5)`, 범주가 많으면 가로 막대 | 지움 |
| `TICK_CORNER_OVERLAP` | x와 y의 첫 눈금 글자가 모서리에서 겹침(-3..3 정사각형) | `decide.py:336`, `overlap.py:254` | `ax.tick_params(pad=…)`를 0으로 줄였을 때의 모서리 | 지움 |
| `TICK_DECIMAL` | 눈금이 `2.0`, 섞인 자릿수, 같은 글자 두 번, 과한 자릿수를 찍음 | `decide.py:350` | `ax.yaxis.set_major_formatter("{x:.1f}")`로 간격에 맞춘 자릿수 | 지움 |
| `EMPTY_AXES` | 아무것도 그리지 않는 Axes(INFO). `twiny` 축에도 떠서 소음이었다 | `decide.py:394` | 격자보다 패널이 적을 때 `ax.remove()` | 되살림 |

측정에서 지운 것:

- 3D Axes의 `ax.text` 위치(`walk.py:140`, 투영하며 그리는 자리를 읽던 렌더러), `secondary_xaxis`·`secondary_yaxis`의 글자(`walk.py:61`), 극좌표·3D Axes의 눈금 글자, inset Axes의 범례. 근거의 그림에 하나도 없다. 이제 직교 좌표 Axes의 글자만 읽는다.

## layout

`dm.simple_layout`에서 지운 인자와 동작이다(2026-11-16). 여백 맞추기와 글자 맞추기(축 이름 줄바꿈, 패널 간격, 눈금 글자 줄바꿈·회전)는 기능으로 남았다. 이제 호출은 `dm.simple_layout(fig)`이고 인자는 `margin`(`Length` 또는 `"3mm"` 같은 단위 문자열, 모든 변에 같은 값) 하나다.

기준 커밋은 `183b1b59`이다. 원본은 `git show 183b1b59:src/dartwork_mpl/<구현 경로>`로 읽고, 동작의 세부는 같은 커밋의 `layout/tests/test_surface.py`, `test_decide.py`에 있다. 평가 스크립트 10개는 모두 인자 없이 불렀다.

| 동작 | 하던 일 | 구현 | 예시가 보여줘야 할 것 | 상태 |
| --- | --- | --- | --- | --- |
| 변마다 다른 여백 `ml`·`mr`·`mt`·`mb` | 한 변에만 여백을 더 둔다(`mr="1cm"`로 오른쪽 메모 자리) | `layout/model.py:174`, `compose/layout.py:52` | `dm.simple_layout(fig)` 뒤에 `gs = ax.get_gridspec(); gs.update(right=gs.right - 0.05)`. `fig.text` 메모는 이미 자기 변을 비우므로 대개 필요 없다는 점 |지움 |
| 비율·figure 분수 여백 | `margin="2%"`, `margin=0.02` (`margin=0`은 되살렸다) | `layout/model.py:124`, `:146` | 길이로 쓰는 법(`dm.mm(2)`). 0 여백은 글자 끝이 잘리므로 쓰지 않는 이유 |지움 |
| `gs=` | 첫 Axes가 아닌 GridSpec(또는 `SubplotSpec`)을 맞출 grid로 고른다 | `layout/measure.py:52` | 맞출 grid의 Axes를 먼저 만들거나, 둘째 grid는 `fig.subplots_adjust`로 직접 두는 법 |지움 |
| `fit_labels=False` | 여백만 맞추고 글자 맞추기(줄바꿈·회전·간격)를 끈다 | `layout/__init__.py:36`, `layout/loop.py:80` | 직접 정한 것은 그대로 둔다: `ax.tick_params(axis="x", rotation=45)`, `gridspec_kw={"wspace": 0.4}`, 줄바꿈한 라벨 |지움 |
| 납작해진 그림 되돌리기 | 글자를 맞춘 결과 plot이 너비·높이의 30 % 밑으로 줄면 그 라운드를 되돌린다 | `layout/decide.py:196`, `layout/loop.py:80` | 좁은 그림에 끊을 데 없는 긴 이름: 이름을 줄이거나 `barh`로 바꾸는 법. 되돌려도 겹친 글자가 남았다 |지움 |
| 두 번째 호출의 되돌리기 기록 | 앞 호출이 줄바꿈한 축 이름과 넓힌 패널 간격을 다음 호출 전에 되돌린다 | `layout/apply.py:187`, `:224` | 이제 둘째 호출은 앞 호출이 돌린 눈금 글자만 세우고, 줄바꿈한 축 이름과 간격은 그대로 둔다. 처음부터 다시 맞추려면 그림을 새로 만든다 |지움 |

그림이 바뀌지 않아 예시가 필요 없는 것: 3D Axes 전용 측정, 바깥 범례를 plot 폭으로 자르던 처리, figure 범례가 자기 변을 잡던 처리, suptitle·supxlabel·supylabel의 역할 변. Axes의 내용은 이제 matplotlib의 tight box 하나로 잰다. 기준 이미지 21장과 평가 스크립트 10개의 그림이 그대로이고, robustness 51개 중에서는 `mpl_toolkits`의 `host_subplot`으로 만든 기생 축(`triple_axis_parasite`)만 나빠진다(기생 축이 host를 따라 움직이지 않아 plot이 납작해진다. 전에도 오른쪽 축이 잘렸다). 손으로 재던 때 빠지던 `secondary_xaxis`·`secondary_yaxis`의 눈금이 이제 여백에 들어간다.

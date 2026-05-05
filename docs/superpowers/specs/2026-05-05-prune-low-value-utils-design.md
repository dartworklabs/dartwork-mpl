# Pruning Low-Value Utilities — API Audit & Realignment

- **Date**: 2026-05-05
- **Issue**: [#141](https://github.com/dartworklabs/dartwork-mpl/issues/141)
- **Status**: Draft (awaiting maintainer review)

## 1. Goal

dartwork-mpl 0.4.x로 오면서 public API surface가 90+개로 커졌다. 일부는 라이브러리의
자체 철학(`docs/philosophy/utilities_not_wrappers.md`)을 위반하는 얇은 wrapper다.
대표 예: `src/dartwork_mpl/spines.py:13` `hide_spines(ax, which=...)` —
matplotlib의 canonical 호출 `ax.spines[s].set_visible(False)`을 1~3줄 래핑한 데
지나지 않는다.

이 문서는 **public API를 자체 철학에 정렬**하기 위한 기준·정책·운영 룰을
확정한다. 실제 제거 작업은 본 spec이 머지된 뒤 라운드별 후속 PR로 진행한다.

## 2. Decision principles

### 2.1 1차 축 — 철학 정렬 (rule)

`utilities_not_wrappers.md`와 `ai_native.md`의 "One Right Way" 표를 정식 기준으로
승격한다. 핵심 룰:

> **matplotlib이 canonical한 단일 호출을 이미 제공하고, dartwork-mpl 함수가
> 그것을 1~3줄 래핑하는 데 그치면 wrapping 금지.**
> matplotlib이 여러 방법을 제공해서 LLM이 흔들리는 영역(`tight_layout` /
> `constrained_layout` / `subplots_adjust`, `savefig` 다양한 kwargs 등)에서만
> utility로 통일한다.

### 2.2 보조 축 — 인라인 능력 (heuristic)

> **AI 에이전트(Claude/Cursor 등)가 1~3줄 matplotlib 호출로 자명하게 재현
> 가능한가?**

1차 축과 같은 결론으로 수렴할 가능성이 높다. 두 축이 갈리는 경우(예:
composition utility) `borderline`으로 분류해 1:1 토론한다.

## 3. Classification (4-bucket)

| 라벨 | 정의 | 처리 |
|---|---|---|
| `keep` | 모호성 해소형(`auto_layout`, `save_formats`, `style.use`, `dm.subplots`, 물리 단위 API, OKLCH 컬러 등) 또는 본질 abstraction | 유지 |
| `borderline` | composition 가치 있지만 LOC 적음(예: `minimal_axes`처럼 4개 함수를 묶음) | 본 spec 코멘트 또는 audit 표 PR 리뷰에서 메인테이너 합의 후 keep / deprecate-then-remove로 재분류 |
| `deprecate-then-remove` | 명백한 wrapper, 외부 호출처 존재 | 0.5.0에서 `FutureWarning` 추가, 0.6.0에서 제거 |
| `remove-now` | 0.4.x 신생 + public 호출처 0 + `__all__` 미노출 | 0.5.0에서 즉시 제거, CHANGELOG만 |

## 4. Audit table (live document)

- **위치**: `docs/development/api_audit.md`
- **수명**: live — 라운드 진행에 따라 분류·상태 컬럼이 갱신된다.
- **스코프**: `src/dartwork_mpl/__init__.py`의 `__all__` ∪ 각 모듈에서 export되는
  모든 public 함수·클래스. 사적 모듈(`_helpers.py`, `cli.py`)과 mcp/ui
  내부 helper는 제외(§7 참조).
- **컬럼**:

  | 컬럼 | 의미 |
  |---|---|
  | `name` | `dm.<name>` 노출 이름 |
  | `module` | `src/dartwork_mpl/<module>.py` |
  | `loc` | 함수 본문 LOC (def 줄 제외, 빈 줄·docstring 제외) |
  | `mpl_canonical_1to1` | matplotlib에 canonical한 단일 호출이 이미 존재해 1:1 매핑되는가 (Y/N) |
  | `external_callsites` | 다음 3계층 검색 결과 합계: ① 리포 내 `docs/`·`examples_gallery/`·`tests/` ② GitHub code search `org:dartworklabs <name>` ③ 공개 GitHub `<name> dartwork_mpl` |
  | `inline_difficulty` | AI 에이전트 인라인 난이도 1~3 (1=trivial, 3=non-trivial) |
  | `classification` | §3의 4-bucket 중 하나 |
  | `notes` | borderline 사유, 관련 이슈, 마이그레이션 한 줄 등 |

- **상태 컬럼**(분류 후 추가): `status` ∈ `{audited, deprecated, removed}`.

## 5. Deprecation cycle

0.4.0이 막 릴리스됐고(2026-05 기준 최신), 외부 사용자 부담을 고려해 보수적
사이클을 채택한다.

| 릴리스 | 액션 |
|---|---|
| 0.4.x (현재) | 본 spec + audit 표 머지. **코드 변경 없음.** |
| 0.5.0 | `deprecate-then-remove` 항목에 `FutureWarning` + 모듈 docstring에 마이그레이션 한 줄. `remove-now` 항목 즉시 제거. |
| 0.6.0 | `deprecate-then-remove` 항목 실제 제거. |

각 단계는 `docs/migration.md`에 마이그레이션 행 추가, `CHANGELOG.md`에 항목
추가.

## 6. Round operating rule

- **1라운드 (이 spec의 후속 PR)**: spec 머지 + audit 표 초기화. **코드 변경
  없음.** 표는 분류 컬럼까지 채워진 상태로 머지.
- **2라운드 이후**: audit 표를 분류·모듈 그룹으로 정렬해 PR 단위로 분할.
  PR 1개 = 1 모듈 또는 1 분류 그룹. 각 PR은 audit 표의 `status` 컬럼을 함께
  업데이트.

## 7. Out of scope

- mcp/ui 등 내부 helper, `_helpers.py`, `cli.py` 같은 사적 모듈.
- 새 utility 추가, 시그니처 변경, 리팩터링.
- 0.4.x 패치 릴리스에서의 동작 변경 (사이클은 0.5.0 minor부터).

## 8. Open items (1라운드에서 채움)

- borderline 케이스 1차 후보(예상): `minimal_axes`, `add_frame`, `style_spines`,
  `add_grid`, `mix_colors`, `rotate_tick_labels`. audit 단계에서 확정.

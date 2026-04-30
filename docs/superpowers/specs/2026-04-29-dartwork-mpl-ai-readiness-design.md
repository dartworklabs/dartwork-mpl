---
orphan: true
---

# dartwork-mpl AI-Agent Readiness 0.4.0 — Design

- **Status**: Approved (pending user review of this written spec)
- **Author**: brainstorming session, 2026-04-29
- **Primary target user**: autonomous AI coding agents (Claude Code, Cursor, etc.)
- **Compatibility stance**: aggressive (no external users); breaking changes allowed in 0.4.0
- **Related work**: `chart-policy` rule in `company-analysis` repo (downstream)

---

## §0. Background

dartwork-mpl는 출발 시점에 학술 논문용 plotting 헬퍼였고 (`SW`/`DW` = single-/double-column width), 그 후 보고서·발표·웹 대시보드 등 **모든 전문 plot 컨텍스트로 적용 범위가 확장**되었다. 그 과정에서:

1. `SW/MW/TW/DW` 4-tier figsize 시스템이 사실상의 표준이 되었지만, **`W`(width)가 figsize의 양쪽 슬롯에 다 쓰이는** 의미 손실이 발생했다.
2. lint 정책(`Zero-Resize Policy` — figsize 금지)과 사용자 가이드(`figsize=(dm.cm2in(9), dm.cm2in(7))` 권장)가 **정면 충돌**한다.
3. MCP 서버, `install_llm_txt`, `asset/USAGE_GUIDE.md`, `asset/prompt/*.md`, sphinx docs, `examples_gallery`가 각자 독자적인 텍스트 자료를 들고 있어 **drift**가 심하다.
4. 자율 에이전트가 dartwork-mpl을 사용하면 위 모순을 해석하지 못해 정책 위반 코드를 만든다.

이 spec은 1차 사용자를 **자율 AI 에이전트**로 못박고, 위 4가지를 한 번의 0.4.0 PR 묶음으로 정리한다.

---

## §1. Goals & Non-Goals

### Goals
1. **단일 SSOT 확립**: `src/dartwork_mpl/asset/prompt/`가 lint·MCP·docs·`install_llm_txt`의 유일한 텍스트 출처가 된다.
2. **Width 정책 재설계**: 토큰을 폐기하고 **자유 입력 + lint 일관성 가드**로 전환한다 (Section §3.1).
3. **Aspect 분리**: 세로(높이)는 **의미 토큰**(`square`, `wide`, `golden` 등)으로 결정한다.
4. **모순 제거**: `Zero-Resize Policy` 용어는 코드/docs에서 완전히 제거된다.
5. **MCP 자율 루프 완성**: 에이전트가 의도→정책→템플릿→lint→render→validate를 MCP만으로 완결할 수 있는 도구·리소스를 갖춘다.
6. **Drift CI gate**: SSOT ↔ 코드 ↔ docs 일관성을 자동 검증한다.

### Non-Goals
- 새 plot 함수 추가 (현재 `plot_diverging_bar` 외 추가 없음 — 별 트랙)
- 새 stylesheet/색상/폰트 추가
- `dartwork_mpl.ui` (interactive viewer) 변경
- 외부 호환성 유지 부담 (외부 사용자 없음)

### Success Criteria
- [ ] `Zero-Resize` 검색 시 0건 (코드/docs/주석 모두)
- [ ] `figsize=` 직접 사용은 lint critical
- [ ] `02-anti-patterns.yaml` 1개 파일 수정 → MCP·lint·docs·install이 자동 동기화
- [ ] 자율 에이전트 표준 루프가 MCP만으로 완결 (외부 검색 불필요)
- [ ] CI gate: examples_gallery 전 예제 lint pass + drift test 통과
- [ ] `dm.SW`/`dm.DW`는 deprecation warning과 함께 동작 (호환)

---

## §2. Architecture (Single Source of Truth)

```
                        ┌──────────────────────────────────┐
                        │  src/dartwork_mpl/asset/prompt/  │  ◄──── SSOT
                        │  ├── 00-index.md                 │
                        │  ├── 01-policy.md                │
                        │  ├── 02-anti-patterns.yaml       │
                        │  ├── 03-recipes.md               │
                        │  ├── 04-api-reference.md (gen)   │
                        │  └── 05-templates/{plot}.py      │
                        └────────────────┬─────────────────┘
                                         │ read at runtime / build
        ┌────────────────┬───────────────┼────────────────┬────────────────┐
        ▼                ▼               ▼                ▼                ▼
  ┌──────────┐   ┌──────────────┐  ┌──────────┐   ┌──────────────┐  ┌──────────┐
  │ MCP      │   │ lint /       │  │ Sphinx   │   │ install_llm  │  │ pytest   │
  │ resources│   │ validate     │  │ docs     │   │ _txt         │  │ drift    │
  │ tools    │   │              │  │          │   │              │  │ gate     │
  └──────────┘   └──────────────┘  └──────────┘   └──────────────┘  └──────────┘
```

핵심 불변식 (invariants):
- 어떤 정책 텍스트도 `asset/prompt/` 외에서 인라인 작성되지 않는다.
- `mcp/resources.py`의 인라인 12개 plot 템플릿은 `asset/prompt/05-templates/{plot}.py`로 추출된다.
- `lint_dartwork_mpl_code`의 안티패턴 메시지는 `02-anti-patterns.yaml`에서 로드된다.
- `install_llm_txt`는 SSOT 디렉토리를 통째로 복사한다 (단일 파일 합성 아님).
- `asset/USAGE_GUIDE.md`는 삭제된다.

---

## §3. Width & Aspect Policy

### 3.1 Width: 자유 입력 + Lint 일관성 가드

`figsize=`를 직접 쓰지 않고 `dm.subplots(width=..., aspect=...)` 한 가지 진입점으로 통일한다.

```python
fig, ax = dm.subplots(width="13cm", aspect="wide")
fig, ax = dm.subplots(width="9cm")               # aspect 생략 → "standard"
fig, ax = dm.subplots(width="6.7in")             # 인치 명시 가능
fig, ax = dm.subplots(width=13)                  # raw float → cm 기본
fig, ax = dm.subplots(width=dm.cm(11.3))         # 명시적 변환 헬퍼
fig, ax = dm.subplots(width=dm.inch(4.6))
```

#### 허용되는 입력 형식
| 형식 | 예 | 단위 |
|---|---|---|
| 단위 접미사 문자열 | `"13cm"`, `"9.5cm"`, `"6.7in"`, `"170mm"` | 명시적 |
| 헬퍼 함수 | `dm.cm(11.3)`, `dm.inch(4.6)`, `dm.mm(170)` | 명시적 |
| Raw float/int | `13`, `9.5` | **cm 기본** (lint info: 단위 명시 권장) |

#### 학술 컬럼 sugar (선택적)
```python
dm.col1   # = dm.cm(9)   학술 single column
dm.col2   # = dm.cm(17)  학술 double column
```

이건 `dm.cm(9)` 같은 인라인보다 의도가 명확한 경우만 쓰는 sugar이며 강제하지 않는다.

#### 정책 (lint 룰)
| 룰 ID | severity | 내용 |
|---|---|---|
| `figsize-direct` | critical | `figsize=` 직접 사용 금지 — `dm.subplots(width=...)` 사용 |
| `width-over-max` | critical | width > 17cm 금지 (최대 폭 상한) |
| `width-unit-implicit` | info | raw float 사용 시 단위 명시 권장 (`"9cm"` 또는 `dm.cm(9)`) |
| `width-grid` | info | 0.5cm 그리드 정렬 권장 (9.0, 9.5, 10.0...) |
| `width-variety` | warning | 한 프로젝트/디렉토리 내 unique width 종류 > 5 → 보고서 일관성 경고 |
| `aspect-missing` | info | aspect 미지정 시 기본 `"standard"` 사용 안내 |

#### 0.3 → 0.4 호환 (deprecation alias)
| 0.3 상수 | 0.4 동작 | 메시지 |
|---|---|---|
| `dm.SW` | `dm.cm(9)`로 평가, 사용 시 `DeprecationWarning` | `"dm.SW is deprecated and will be removed in a future release. Use width='9cm' or dm.col1 instead."` |
| `dm.MW` | `dm.cm(11)` | `"dm.MW is deprecated. Use width='11cm'."` |
| `dm.TW` | `dm.cm(13)` | `"dm.TW is deprecated. Use width='13cm'."` |
| `dm.DW` | `dm.cm(17)` | `"dm.DW is deprecated. Use width='17cm' or dm.col2 instead."` |

**호환 메커니즘**: `__init__.py` 모듈 레벨 `__getattr__`에서 `SW/MW/TW/DW` 접근을 가로채 `warnings.warn(..., DeprecationWarning, stacklevel=2)` 호출 후 값을 반환한다. `from dartwork_mpl import SW` 식의 import는 최초 attribute access에서만 경고가 뜬다 — 명시적이고 깔끔.

`FS_*` (FS_SINGLE 등 figsize tuple 상수) 도 같은 방식으로 deprecation 처리한다.

### 3.2 Aspect: 6개 의미 토큰

```python
"square"     # 1:1     scatter, heatmap, correlation
"portrait"   # 4:5     vertical bar, ranking
"standard"   # 4:3     기본 (단일 패널, default)
"golden"     # 1.618:1 미적 line/bar
"wide"       # 3:2     시계열, waterfall, 가로 bar
"cinema"     # 2:1     긴 시계열, ribbon, banner
```

또는 양수 float 직접 지정 (`aspect=0.5` 등) 허용. aspect는 `height/width` 비율로 정의 (즉 `0.5`는 wide).

### 3.3 `dm.subplots` 시그니처 변경

```python
def subplots(
    nrows: int = 1,
    ncols: int = 1,
    *,
    width: str | float | WidthSpec | None = None,
    aspect: str | float = "standard",
    style: str | list[str] | None = None,
    sharex: ... = False,
    sharey: ... = False,
    squeeze: bool = True,
    width_ratios: list[float] | None = None,
    height_ratios: list[float] | None = None,
    subplot_kw: dict[str, Any] | None = None,
    gridspec_kw: dict[str, Any] | None = None,
    figsize: tuple[float, float] | None = None,  # deprecated
    dpi: int | None = None,                       # deprecated (style이 관리)
    **fig_kw,
) -> tuple[Figure, Axes | np.ndarray]:
```

- `width=None`: style의 default를 따름 (현행 호환).
- `figsize=`/`dpi=`: **0.4.0에서 `DeprecationWarning` 발생, 0.5.0에서 완전 제거**. 외부 사용자 없으므로 deprecation 사이클은 짧게 한 minor만 유지.
- `width`와 `figsize`가 둘 다 지정되면 `figsize` 우선 + warning (0.4.x 한정).

내부 구현:
1. `_resolve_width(width) -> inches: float`: 문자열/숫자/WidthSpec → inches.
2. `_resolve_aspect(aspect) -> ratio: float`: 문자열 → 양수 float.
3. `inches × ratio`로 `(w, h)` 계산 후 `plt.subplots(figsize=(w, h), ...)` 위임.

---

## §4. Asset Reorganization

### 4.1 새 구조

```
src/dartwork_mpl/asset/prompt/
├── 00-index.md              # 에이전트 진입점 — 의사결정 트리, 라우팅
├── 01-policy.md             # Width/aspect, layout, color, font, save 정책
├── 02-anti-patterns.yaml    # 머신리더블 금지 패턴 (lint가 직접 로드)
├── 03-recipes.md            # "intent → 함수 호출" 의사결정 — bar/line/heatmap/twin_axis
├── 04-api-reference.md      # 자동생성: 모든 public 함수의 signature + 1-line example
├── 05-templates/            # 12개 plot 템플릿 (실행 가능한 .py 파일)
│   ├── bar.py
│   ├── line.py
│   ├── tornado.py
│   ├── scatter.py
│   ├── heatmap.py
│   ├── stacked_bar.py
│   ├── violin.py
│   ├── boxplot.py
│   ├── pie.py
│   ├── histogram.py
│   ├── contour.py
│   └── twin_axis.py
└── _legacy/
    └── migration-from-0.3.md  # 0.3 → 0.4 마이그레이션 가이드 (한 사이클 후 삭제)
```

기존 `coding-rules.md`, `general-guide.md`, `layout-guide.md`는 위 새 파일들에 흡수된 후 **삭제된다** (git history에는 남음). 매핑:

| 기존 파일 | 흡수 대상 |
|---|---|
| `general-guide.md` | `00-index.md` (진입점) + `01-policy.md` (정책 섹션) + `03-recipes.md` (예제) |
| `layout-guide.md` | `01-policy.md` (layout 정책) + `03-recipes.md` (layout recipe) |
| `coding-rules.md` | `01-policy.md` (모든 룰) |

삭제 시점: M0와 같은 PR에서 신구 파일 모두 검사된 후 즉시 삭제.

### 4.2 `02-anti-patterns.yaml` 스키마

```yaml
version: 1
rules:
  - id: figsize-direct
    severity: critical
    detector:
      kind: regex
      pattern: '\bfigsize\s*=\s*\('
    message: |
      `figsize=` 직접 사용은 금지됩니다.
      `dm.subplots(width="13cm", aspect="wide")` 형태로 작성하세요.
    why: |
      width와 aspect를 분리하면 보고서 내 차트 폭의 일관성을 보장하고,
      세로(높이)는 콘텐츠 의도에 맞는 비율로 자동 계산됩니다.
    fix_suggestion: 'dm.subplots(width="13cm", aspect="wide")'

  - id: tight-layout
    severity: critical
    detector: { kind: regex, pattern: '\btight_layout\s*\(' }
    message: tight_layout()은 dm.auto_layout(fig)으로 대체하세요.
    why: tight_layout은 dartwork-mpl의 spine/legend 처리와 충돌합니다.
    fix_suggestion: dm.auto_layout(fig)

  - id: zero-resize-mention
    severity: warning
    detector: { kind: regex, pattern: '\bZero[- ]?Resize\b' }
    message: |
      "Zero-Resize Policy"는 0.4.0에서 폐기되었습니다.
      Width-tier가 아닌 자유 입력 + lint 가드 정책입니다.

  # ... (총 ~12개 룰)
```

### 4.3 `04-api-reference.md` 자동 생성

`scripts/regen_api_reference.py`:
1. `dartwork_mpl.__all__`을 순회.
2. 각 객체의 `inspect.signature` + `__doc__` 첫 단락 + 1-line 예제(있으면)를 마크다운으로 출력.
3. pre-commit hook에서 자동 실행 + drift CI에서 git diff로 검증.

### 4.4 `05-templates/{plot}.py` 추출

현재 `mcp/resources.py:_TEMPLATES`의 12개 인라인 dict를 각각 실행 가능한 `.py` 파일로 추출. MCP resource는 파일을 읽어 반환. CI는 각 템플릿을 subprocess로 실행하고 lint도 통과시킨다.

각 템플릿은 새 정책에 맞게 다시 작성:
```python
# 05-templates/bar.py
"""Vertical bar chart — basic template."""
import matplotlib.pyplot as plt
import dartwork_mpl as dm

categories = ["A", "B", "C", "D", "E"]
values = [23, 45, 56, 78, 33]

fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.bar(categories, values, color="dc.blue500", edgecolor="white", linewidth=0.3)
ax.set_ylabel("Value")
dm.auto_layout(fig)
plt.show()
```

---

## §5. MCP Server Changes

### 5.1 Resources (변경 + 신규)

| URI | 변경 | 출처 |
|---|---|---|
| `dartwork-mpl://guide/agent-entry` | **rename** from `general-guide` | `00-index.md` |
| `dartwork-mpl://guide/policy` | NEW | `01-policy.md` |
| `dartwork-mpl://guide/anti-patterns` | NEW | `02-anti-patterns.yaml` (JSON 직렬화) |
| `dartwork-mpl://guide/recipes` | NEW | `03-recipes.md` |
| `dartwork-mpl://guide/layout-guide` | KEEP (deprecated alias to recipes#layout) | — |
| `dartwork-mpl://api/index` | NEW | `04-api-reference.md` |
| `dartwork-mpl://api/{function}` | NEW | inspect 기반 단일 함수 |
| `dartwork-mpl://palette/colors` | KEEP | 동적 |
| `dartwork-mpl://palette/fonts` | KEEP | 동적 |
| `dartwork-mpl://styles/list` | KEEP | 동적 |
| `dartwork-mpl://styles/{preset}` | KEEP | 동적 |
| `dartwork-mpl://templates/list` | KEEP | `05-templates/*.py` glob |
| `dartwork-mpl://templates/{plot}` | KEEP — 출처 변경 | `05-templates/{plot}.py` |

### 5.2 Tools (수정 + 신규)

수정:
- `lint_dartwork_mpl_code`: 인라인 룰 → `02-anti-patterns.yaml` 로드. 반환 포맷에 룰 ID 포함.
- `dartwork_mpl_info`: 정책 메타정보를 `01-policy.md` frontmatter에서 동기화.

신규:
- `search_api(query: str, limit: int = 10) -> list[dict]` — 함수명/docstring fuzzy 검색 (rapidfuzz 사용 권장).
- `get_function_signature(name: str) -> dict` — `inspect.signature` + docstring + return type.
- `agent_post_check(code: str) -> dict` — lint + AST 기반 dry-check (실제 render 없이) 통합 결과.

(`pick_width_tier`는 이번 안에서는 폐기 — 자유 입력으로 가니 토큰 추천이 의미 없음.)

### 5.3 Prompts (수정 + 신규)

수정:
- `create_plot`: width/aspect 의사결정 단계 + `00-index.md` 참조 강제.
- `style_review`: Zero-Resize 언급 제거, anti-patterns YAML 기반 룰 인용.

신규:
- `migrate_legacy_code`: 0.3.x figsize/SW/DW/tight_layout 코드를 0.4.0으로 자동 변환.

### 5.4 lint 모듈 분리

`mcp/tools.py::lint_dartwork_mpl_code`의 본체를 `dartwork_mpl/lint.py`로 이전:

```python
# dartwork_mpl/lint.py
def load_rules() -> list[Rule]: ...
def lint(code: str, rules: list[Rule] | None = None) -> list[Issue]: ...
```

MCP tool은 thin wrapper. CLI도 같은 모듈을 사용:

```bash
dartwork-mpl lint path/to/script.py
dartwork-mpl validate path/to/figure.png       # 향후
```

---

## §6. Validation Hardening

`validate_figure(fig)`에 width 검증 추가:

```text
# 새로 추가되는 체크들
- WIDTH_OVER_MAX:  fig.get_size_inches()[0] > 17cm
- WIDTH_VARIETY:   현재 figure의 width가 같은 디렉토리 내 ≤5종에 속하는지 (선택적)
- ASPECT_EXTREME:  width/height < 0.3 또는 > 4.0 (가독성 경고)
```

기존 검사는 유지 (overflow, overlap, legend_overflow, tick_crowding, empty_axes).

---

## §7. Install / Distribution

### 7.1 `install_llm_txt` 재작성

```python
def install_llm_txt(project_dir: str | Path | None = None) -> None:
    """Install dartwork-mpl SSOT prompt directory into IDE folders."""
    project = Path(project_dir or Path.cwd())
    src = Path(__file__).parent / "asset" / "prompt"
    targets = [
        project / ".claude" / "dartwork-mpl",
        project / ".cursor" / "rules" / "dartwork-mpl",
    ]
    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        # 00-index, 01-policy, 02-anti-patterns, 03-recipes 복사
        # 05-templates/는 디렉토리 통째 복사
        # 04-api-reference와 _legacy/는 제외 (선택적)
```

### 7.2 `asset/USAGE_GUIDE.md` 삭제

- 파일 삭제 + git history에는 남음.
- `install_llm_txt`의 단일 파일 머지 로직 제거.
- 호출 시 `DeprecationWarning` 없이 새 동작으로 바로 전환 (외부 사용자 없음).

---

## §8. Docs Update

### 8.1 변경 파일

| 파일 | 작업 |
|---|---|
| `docs/index.md` | "AI-ready" 섹션을 §1 위로 끌어올리고 자율 에이전트 루프 그림 추가 |
| `docs/usage_guide/quickstart.md` | width/aspect로 재작성, figsize 예제 모두 제거 |
| `docs/usage_guide/styles.md` | width/aspect 의사결정 매트릭스 |
| `docs/usage_guide/layout.md` | `auto_layout` 권장, `simple_layout`은 advanced 섹션 |
| `docs/integrations/mcp_server.md` | 새 resources/tools/prompts 표 갱신 |
| `docs/integrations/why_ai_ready.md` | "Zero-Resize" 단어 제거 |
| `docs/integrations/agent_loop.md` | **신규**: 자율 에이전트 표준 루프 가이드 |
| `docs/migration.md` | 0.3 → 0.4 width/aspect/SSOT 변경 안내 |
| `docs/troubleshooting.md` | 새 lint warning에 대한 해결법 |
| `docs/philosophy/*.md` | "Zero-Resize" 언급 제거, "intent over numbers" 강조 |

### 8.2 SSOT 임포트

`docs/usage_guide/styles.md` 등에서 정책 본문은 직접 작성하지 않고 SSOT를 임포트:

```text
```{include} ../../src/dartwork_mpl/asset/prompt/01-policy.md
:start-after: "<!-- POLICY:WIDTH:START -->"
:end-before: "<!-- POLICY:WIDTH:END -->"
```
```

---

## §9. Drift CI Gate

`tests/test_ssot_drift.py` (신규):

| 검사 | 내용 |
|---|---|
| `test_resources_resolve` | MCP resource URI 전체가 실제 파일/생성기로 해소되는지 |
| `test_lint_loads_yaml` | `lint.load_rules()`가 `02-anti-patterns.yaml`의 모든 룰을 적재하는지 |
| `test_api_reference_fresh` | `04-api-reference.md`가 현재 `__all__`과 일치하는지 (regen 후 git diff 0) |
| `test_templates_executable` | `05-templates/*.py`를 subprocess로 실행 → 모두 exit 0 |
| `test_templates_lint_clean` | 각 템플릿이 `lint.lint()` 통과 (issues == 0) |
| `test_examples_lint_clean` | `examples/*.py`, `docs/examples_source/**.py` 모두 lint 통과 |
| `test_no_zero_resize_mentions` | 코드/docs 어디에도 `Zero-Resize` 문자열 0건 |
| `test_deprecated_aliases_warn` | `dm.SW`/`SW`/`MW`/`TW`/`DW`/`FS_*` 접근이 `DeprecationWarning` 발생 |

CI에서 모두 강제 (PR 머지 차단).

---

## §10. Migration Plan (단일 0.4.0 PR 묶음)

| Step | 작업 | 검증 |
|---|---|---|
| M0 | `asset/prompt/` 새 구조 생성, 기존 3개 파일을 새 5개 + 1 디렉토리로 분할 | 파일 존재 |
| M1 | `02-anti-patterns.yaml` 작성 + `dartwork_mpl/lint.py` 모듈 분리 | unit test |
| M2 | `dm.subplots`에 `width`/`aspect` 인자 추가 + `_resolve_width/aspect` 구현 | unit test |
| M3 | `dm.cm`/`dm.inch`/`dm.mm` 헬퍼, `dm.col1`/`dm.col2` sugar | unit test |
| M4 | `__init__.py::__getattr__`에 `SW/MW/TW/DW`/`FS_*` deprecation alias | warning 캡처 테스트 |
| M5 | MCP resources/tools/prompts 재작성, 인라인 템플릿 → 파일 추출 | smoke test |
| M6 | `install_llm_txt` 재작성, `asset/USAGE_GUIDE.md` 삭제 | install test |
| M7 | 기존 `examples/`, `docs/examples_source/` 새 정책 적용 (figsize → width) | sphinx-gallery build pass |
| M8 | docs/* 새 정책 반영, "Zero-Resize" 일괄 제거 | sphinx build clean |
| M9 | `tests/test_ssot_drift.py` 추가 | CI 통과 |
| M10 | `scripts/regen_api_reference.py` + pre-commit hook | hook 동작 |
| M11 | CHANGELOG, README, version → 0.4.0 | release |

전체를 하나의 PR로 가도 되고, M0~M4 (`core`) / M5~M6 (`mcp+install`) / M7~M11 (`docs+ci`) 3개 PR로 분할해도 됨. **권장: 3-PR 분할** — 각 PR이 약 20-30 파일 수준으로 리뷰 가능.

---

## §11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `auto_layout`/`simple_layout` 둘 다 유지 → 에이전트 혼란 | 01-policy.md에 "기본은 `auto_layout`" 명시. lint는 `tight_layout`만 critical, 둘은 모두 허용. |
| `04-api-reference.md` 자동생성 누락 | pre-commit + drift CI |
| `02-anti-patterns.yaml` 룰 추가 시 examples 회귀 | M1과 M7을 같은 PR에서 처리, 회귀 시 examples 먼저 수정 |
| `fastmcp` API 변경 | `pyproject.toml`에서 `fastmcp>=2.13,<3.0` pin |
| `__getattr__` 기반 deprecation이 type checker에 안 잡힘 | `__init__.pyi` stub에 deprecated 표시 (`@deprecated` from `typing_extensions`) |
| 사용자가 `width=` 단위 없이 큰 숫자 입력 (`width=170` → 170cm로 해석) | `width-grid` lint info + 30cm 초과 시 warning |
| `width-variety` lint 위양성 (정당한 다양성) | 룰을 default off, opt-in (`# dartwork: enforce-variety` 주석) |

---

## §12. Open Questions (해결 후 spec 갱신)

> 모두 brainstorming 단계에서 사용자 답변으로 잠정 결정됨.

1. ~~Width 토큰 형식~~ → **자유 입력 (자유 + lint 가드)** ✓
2. ~~SW/DW 호환~~ → **deprecation alias로 0.4 동안 유지** ✓
3. ~~외부 사용자 호환~~ → **불필요 (외부 사용자 없음)** ✓
4. **(미해결, 구현 단계 결정)** lint 룰의 정확한 정규식 패턴: 단일 라인 `figsize=` 외 멀티라인 케이스 처리 — AST 기반 검출로 갈지 regex로 갈지. 기본은 regex, 멀티라인은 단계적 도입.
5. **(미해결, 구현 단계 결정)** `04-api-reference.md` 출력 포맷: 단일 큰 파일 vs 함수당 anchor — 단일 파일 + heading anchor로 시작.

---

## §13. Acceptance Test Plan

자율 에이전트 시뮬레이션 (수동):

1. **시나리오 A**: 빈 환경에서 에이전트가 "12cm × wide bar chart 그려줘" 요청
   - 기대: `dm.subplots(width="12cm", aspect="wide")` + `auto_layout` + `save_formats` 사용
   - 검증: `agent_post_check` 호출 시 0 issues
2. **시나리오 B**: 0.3 코드 마이그레이션
   - 입력: `figsize=(dm.cm2in(9), dm.cm2in(7))` + `tight_layout()`
   - 기대: `migrate_legacy_code` prompt가 `width="9cm", aspect=7/9` + `auto_layout`로 변환
3. **시나리오 C**: drift 검출
   - 변경: `02-anti-patterns.yaml`에 새 룰 1개 추가
   - 기대: `lint_dartwork_mpl_code`가 즉시 새 룰을 적용
4. **시나리오 D**: deprecation 호환
   - 입력: `dm.SW`
   - 기대: `DeprecationWarning` 출력 + `dm.cm(9)`와 동일한 inches 반환

---

## §14. References

- 본 디렉토리의 brainstorming 대화 (2026-04-29)
- `company-analysis/.agents/rules/chart/chart-policy.md` — 다운스트림 정책
- `company-analysis/.agents/rules/chart/chart-script-policy.md` — 다운스트림 lint
- 현행 코드: `src/dartwork_mpl/__init__.py`, `mcp/{server,resources,tools,prompts}.py`, `figure.py`, `layout.py`, `prompt.py`, `install.py`
- 현행 SSOT 후보: `asset/prompt/{coding-rules,general-guide,layout-guide}.md`, `asset/USAGE_GUIDE.md`

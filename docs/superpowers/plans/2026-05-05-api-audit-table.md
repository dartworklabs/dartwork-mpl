# API Audit Table — Round 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `dartwork-mpl`의 public API 전수를 분류한 audit 표를 `docs/development/api_audit.md`에 머지한다. 라이브러리 코드 변경은 없으며, 후속 라운드(실제 함수 제거)의 입력이 된다.

**Architecture:** `scripts/api_audit.py`가 자동 컬럼(`name`, `module`, `kind`, `loc`, `repo_callsites`)을 AST + ripgrep으로 추출 → markdown 표로 변환 → 수동 컬럼(`mpl_canonical_1to1`, `inline_difficulty`, `classification`, `notes`)을 모듈 그룹별로 채움 → 단일 PR.

**Tech stack:** Python `ast`, `ripgrep` (`rg`), markdown.

**Spec:** [`docs/superpowers/specs/2026-05-05-prune-low-value-utils-design.md`](../specs/2026-05-05-prune-low-value-utils-design.md)

**Out of scope:** 함수 제거 자체. 0.5.0을 향한 별도 plan에서 진행.

---

## File structure

- **Create**: `scripts/api_audit.py` — 일회성·재사용 가능 자동 추출 스크립트.
- **Create**: `docs/development/api_audit.md` — live audit 표 (초기 버전).
- **Modify**: 없음. 라이브러리 코드는 건드리지 않는다.

`scripts/`는 이미 존재(`generate_cmaps.py`, `prune_cmaps.py`)하는 디렉토리이므로 새 위치를 만들지 않는다. spec §6의 "1라운드 코드 변경 없음"은 라이브러리 코드(`src/dartwork_mpl/`) 한정으로 해석한다 — 보조 스크립트는 산출물 reproducibility를 위해 머지한다.

## Decision rules (적용 매뉴얼)

각 함수에 대해 다음을 순서대로 평가한다 (spec §2.1·§2.2):

1. **`mpl_canonical_1to1` (Y/N)** — matplotlib에 이미 canonical한 단일 호출이 존재해 dartwork-mpl 함수가 그것을 1~3줄 래핑하는 데 그치는가?
   - 예: `hide_spines(ax)` ↔ `for s in ['top','right']: ax.spines[s].set_visible(False)` → **Y**.
   - 반례: `auto_layout(fig)`은 `tight_layout` / `constrained_layout` / `subplots_adjust` 중 하나가 아니라 dartwork-mpl 고유의 content-aware 측정 로직 → **N**.

2. **`inline_difficulty` (1/2/3)** — AI 에이전트가 인라인할 때:
   - **1** = matplotlib 1줄 호출 (`ax.grid(False)`).
   - **2** = matplotlib 2~3줄 + 약간의 default kwargs.
   - **3** = 데이터 변환·리스트 처리·복잡 분기 + matplotlib 호출.

3. **`classification`** — 위 두 컬럼을 종합:
   - `mpl_canonical_1to1=Y` AND `inline_difficulty≤2` → **`remove`**.
   - `mpl_canonical_1to1=N` (모호성 해소형 / 본질 abstraction / OKLCH 등) → **`keep`**.
   - 경계 (composition 가치 있지만 LOC 적음, 또는 default kwargs만 제공) → **`borderline`** + `notes`에 1줄 사유.

4. **`notes`** — borderline이거나 `repo_callsites>0`인 경우 마이그레이션 한 줄 (`<old> → <mpl line>`).

---

## Task 1: 브랜치 생성

**Files:** 없음.

- [ ] **Step 1: 브랜치 생성**

```bash
git checkout -b chore/api-audit-table
```

- [ ] **Step 2: 상태 확인**

```bash
git status
```

Expected: `On branch chore/api-audit-table`, working tree clean.

---

## Task 2: 자동 추출 스크립트 작성

**Files:**
- Create: `scripts/api_audit.py`

- [ ] **Step 1: 스크립트 작성**

`scripts/api_audit.py`에 다음을 그대로 작성:

```python
"""Round 1 audit script for dartwork-mpl public API.

Outputs a markdown table with the auto-extractable columns:
``name``, ``module``, ``kind``, ``loc``, ``repo_callsites``.

Manual columns (``mpl_canonical_1to1``, ``inline_difficulty``,
``classification``, ``notes``, ``status``) are filled in
``docs/development/api_audit.md`` after running this.

Usage::

    python scripts/api_audit.py > /tmp/audit_raw.md

See ``docs/superpowers/specs/2026-05-05-prune-low-value-utils-design.md``
for column definitions.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "dartwork_mpl"

# Out of scope per spec §7.
EXCLUDED_PARTS = {"_helpers.py", "cli.py", "mcp", "ui", "asset", "asset_viz"}
SEARCH_DIRS = ["docs", "examples_gallery", "examples_source", "tests"]


def iter_python_files(root: pathlib.Path):
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if rel.name.startswith("_") and rel.name != "__init__.py":
            continue
        yield path


def extract_public_defs(path: pathlib.Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            if node.name.startswith("_"):
                continue
            yield node


def function_loc(node: ast.AST) -> int:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return 0
    body = node.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    if not body:
        return 0
    start = body[0].lineno
    end = body[-1].end_lineno or body[-1].lineno
    return end - start + 1


def grep_callsites(name: str, cwd: pathlib.Path) -> int:
    cmd = ["rg", "-c", "--", rf"\b{name}\b", *SEARCH_DIRS]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd
    )
    if result.returncode not in (0, 1):
        return -1
    total = 0
    for line in result.stdout.splitlines():
        try:
            total += int(line.rsplit(":", 1)[1])
        except (ValueError, IndexError):
            continue
    return total


def main() -> int:
    rows = []
    for path in iter_python_files(SRC):
        rel = path.relative_to(ROOT)
        module = ".".join(rel.with_suffix("").parts).replace("src.", "")
        for node in extract_public_defs(path):
            kind = "class" if isinstance(node, ast.ClassDef) else "func"
            loc = function_loc(node)
            callsites = grep_callsites(node.name, ROOT)
            rows.append((module, node.name, kind, loc, callsites))

    rows.sort()
    print("| name | module | kind | loc | repo_callsites |")
    print("|---|---|---|---|---|")
    for module, name, kind, loc, callsites in rows:
        print(f"| `{name}` | `{module}` | {kind} | {loc} | {callsites} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: lint·format 통과**

```bash
ruff format scripts/api_audit.py
ruff check scripts/api_audit.py
```

Expected: `1 file reformatted` 또는 `1 file unchanged` / `All checks passed!`.

- [ ] **Step 3: 실행 + 행 수 확인**

```bash
python scripts/api_audit.py > /tmp/audit_raw.md
wc -l /tmp/audit_raw.md
head -5 /tmp/audit_raw.md
```

Expected: ≥ 80행 (헤더 2줄 + ~80개 public 항목). 첫 두 줄이 markdown 표 헤더·구분선.

- [ ] **Step 4: `__all__` 누락 검증**

```bash
python -c "from dartwork_mpl import __all__; print('\n'.join(sorted(__all__)))" > /tmp/all_names.txt
awk -F'|' 'NR>2 {gsub(/`| /, "", $2); print $2}' /tmp/audit_raw.md | sort -u > /tmp/audit_names.txt
comm -23 /tmp/all_names.txt /tmp/audit_names.txt
```

Expected: `__all__`에는 있지만 정의는 없는 이름들 — 정상 케이스는 모듈 alias(`validate_fixes`), 모듈에서 import된 상수(`col1`, `col2`, `Inches`), 다른 모듈에서 정의됨(예: `lint_code`는 `lint.lint`의 alias). 실제 함수 본체가 누락되면 스크립트의 `EXCLUDED_PARTS`·`iter_python_files`를 점검 후 재실행.

- [ ] **Step 5: 커밋**

```bash
git add scripts/api_audit.py
git commit -m "chore(audit): add scripts/api_audit.py for round 1 audit (#141)"
```

---

## Task 3: audit 표 헤더와 자동 컬럼 행 작성

**Files:**
- Create: `docs/development/api_audit.md`

- [ ] **Step 1: 표 헤더와 도입부 작성**

`docs/development/api_audit.md`에 다음을 그대로 작성:

````markdown
# Public API Audit (live)

이 문서는 [#141](https://github.com/dartworklabs/dartwork-mpl/issues/141)에서
시작된 public API 정리 작업의 살아있는 기록이다. 운영 룰·컬럼 정의·분류
원칙은 [`docs/superpowers/specs/2026-05-05-prune-low-value-utils-design.md`](../superpowers/specs/2026-05-05-prune-low-value-utils-design.md)
참조.

## How to read

| 컬럼 | 의미 |
|---|---|
| `name` | `dm.<name>` 또는 `dm.<module>.<name>` 노출 이름 |
| `module` | `src/dartwork_mpl/<module>` |
| `kind` | `func` / `class` |
| `loc` | 함수 본문 LOC (def·docstring·빈 줄 제외) |
| `mpl_canonical_1to1` | matplotlib에 1:1 매핑되는 canonical 호출이 존재 (Y/N) |
| `repo_callsites` | 리포 내 `docs/`·`examples_gallery/`·`examples_source/`·`tests/`에서 발견된 호출처 수 (제거 시 함께 인라인할 사이트) |
| `inline_difficulty` | AI 에이전트 인라인 난이도 1~3 |
| `classification` | spec §3 3-bucket: `keep` / `borderline` / `remove` |
| `notes` | borderline 사유, 마이그레이션 한 줄, 관련 이슈 |
| `status` | `pending` (분류 전) / `audited` (분류 완료) / `removed` (실제 제거 완료) |

## How to update

1. 자동 컬럼(`name`, `module`, `kind`, `loc`, `repo_callsites`)은
   `python scripts/api_audit.py`로 재생성한다.
2. 수동 컬럼은 spec §2(decision principles)·§3(classification) 적용으로 채운다.
3. 후속 라운드 PR이 `remove` 항목을 처리하면 `status`를 `removed`로 갱신한다.

## Audit table

<!-- 모듈 단위로 그룹핑되어 있다. 자동 컬럼은 scripts/api_audit.py 출력. -->
````

- [ ] **Step 2: 자동 컬럼을 9컬럼 표로 확장**

다음 명령으로 자동 컬럼(5)을 9컬럼 표 본문(빈 수동 컬럼 + `status=pending`)으로 변환:

```bash
python scripts/api_audit.py | tail -n +3 | awk -F'|' '{
  printf "|%s|%s|%s|%s|  |%s|  |  |  | pending |\n", $2, $3, $4, $5, $6
}' > /tmp/audit_rows.md
head -3 /tmp/audit_rows.md
wc -l /tmp/audit_rows.md
```

Expected: 행 수 ≥ 80. 각 행이 `| \`name\` | \`module\` |  func | 5 |  | 0 |  |  |  | pending |` 형태.

- [ ] **Step 3: 9컬럼 표 헤더와 본문을 문서에 추가**

`docs/development/api_audit.md`의 `## Audit table` 섹션 아래에 다음 표 헤더를 추가하고, 그 아래에 `/tmp/audit_rows.md` 내용을 그대로 붙여넣는다:

```markdown
| name | module | kind | loc | mpl_canonical_1to1 | repo_callsites | inline_difficulty | classification | notes | status |
|---|---|---|---|---|---|---|---|---|---|
```

- [ ] **Step 4: 시각 검증**

```bash
grep -c "^|" docs/development/api_audit.md
```

Expected: 표 헤더 + 구분선 + ~80행 = 80+. `pending` 단어 갯수와 행 수가 일치해야 한다:

```bash
grep -c "pending" docs/development/api_audit.md
```

- [ ] **Step 5: 커밋**

```bash
git add docs/development/api_audit.md
git commit -m "docs(audit): seed api_audit.md with auto columns (#141)"
```

---

## Task 4: 분류 — Spines & Layout 그룹

**Files:**
- Modify: `docs/development/api_audit.md`

대상 모듈: `dartwork_mpl.spines`, `dartwork_mpl.layout`.

각 함수에 대해 §"Decision rules"의 4단계를 적용한다. 명백한 케이스 정답:

| name | mpl_1to1 | diff | classification | notes (필수 시) |
|---|---|---|---|---|
| `hide_spines` | Y | 1 | remove | `for s in ['top','right']: ax.spines[s].set_visible(False)` |
| `hide_all_spines` | Y | 1 | remove | `for s in ax.spines.values(): s.set_visible(False)` |
| `show_only_spines` | Y | 2 | remove | spec §2.1 — 4-element loop |
| `style_spines` | N | 2 | borderline | composition (color+linewidth+visible filter) — 토론 |
| `add_grid` | N | 2 | borderline | dm.* default kwargs(color, alpha 등) 가치 — 토론 |
| `remove_grid` | Y | 1 | remove | `ax.grid(False)` |
| `add_frame` | N | 2 | borderline | composition — 토론 |
| `minimal_axes` | N | 3 | borderline | 4 함수 묶음 composition — 토론 |
| `auto_layout` | N | 3 | keep | dartwork-mpl 고유 content-aware 측정 |
| `simple_layout` | N | 2 | keep | tight_layout/constrained_layout 모호성 해소 |
| `tight_crop` | N | 2 | keep | 고유 alpha-cropping |
| `get_bounding_box` | N | 2 | keep | 측정 helper |
| `set_xmargin` | Y | 1 | remove | `ax.margins(x=...)` 1대1 매핑 — 검토 후 확정 |
| `set_ymargin` | Y | 1 | remove | `ax.margins(y=...)` 1대1 매핑 — 검토 후 확정 |

- [ ] **Step 1: 위 표를 따라 `docs/development/api_audit.md`의 14개 행 갱신**

각 행의 `mpl_canonical_1to1`, `inline_difficulty`, `classification`, `notes` 컬럼을 채운다. `status` 컬럼을 `pending` → `audited`로 변경.

`set_xmargin`/`set_ymargin`는 채우기 전에 다음을 실행해 1대1 매핑 가능성을 1번만 확인:

```bash
grep -A 5 "^def set_xmargin" src/dartwork_mpl/layout.py
```

본문이 `ax.margins(x=...)` 호출 또는 단일 attribute 변경이면 `Y / 1 / remove`. 다른 부수 작업(예: y축 lim 조정)이 섞여 있으면 `N / 2 / borderline`로 강등하고 사유를 `notes`에.

- [ ] **Step 2: 수정된 행을 grep으로 확인**

```bash
grep -E "hide_spines|auto_layout|minimal_axes" docs/development/api_audit.md
```

Expected: classification 컬럼이 채워져 있고 `status`는 `audited`.

- [ ] **Step 3: 커밋**

```bash
git add docs/development/api_audit.md
git commit -m "docs(audit): classify spines & layout group (#141)"
```

---

## Task 5: 분류 — Formatting & Scale 그룹

**Files:**
- Modify: `docs/development/api_audit.md`

대상 모듈: `dartwork_mpl.formatting`, `dartwork_mpl.scale`.

함수: `format_axis_percent`, `format_axis_thousands`, `format_axis_millions`, `format_axis_billions`, `format_axis_currency`, `format_axis_si`, `rotate_tick_labels`, `set_decimal`, `fs`, `fw`, `lw`.

명백한 케이스 정답:

| name | mpl_1to1 | diff | classification | notes |
|---|---|---|---|---|
| `format_axis_*` (6개) | N | 3 | keep | matplotlib `FuncFormatter` 등 다중 표현 → 모호성 해소 (`ai_native.md` "One Right Way") |
| `rotate_tick_labels` | Y | 1 | remove | `plt.setp(ax.get_xticklabels(), rotation=...)` 1줄 |
| `set_decimal` | N | 2 | borderline | rcParams + locale 처리 — 토론 |
| `fs` | N | 1 | keep | 상대 폰트 사이즈 토큰 (`ai_native.md` 표) |
| `fw` | N | 1 | keep | 폰트 weight 토큰 |
| `lw` | N | 1 | keep | linewidth 토큰 |

- [ ] **Step 1: 위 정답을 적용해 11개 행 갱신**

`format_axis_*` 6개는 모두 `keep` (모호성 해소). 다만 본문이 단순히 `ax.yaxis.set_major_formatter(FuncFormatter(...))` 한 줄에 가깝다면 `borderline`으로 강등 후 사유 기록. 판정용 명령:

```bash
wc -l src/dartwork_mpl/formatting.py
grep -c "^def " src/dartwork_mpl/formatting.py
```

`set_decimal`은 본문 검사 후 결정:

```bash
grep -A 20 "^def set_decimal" src/dartwork_mpl/formatting.py
```

- [ ] **Step 2: 커밋**

```bash
git add docs/development/api_audit.md
git commit -m "docs(audit): classify formatting & scale group (#141)"
```

---

## Task 6: 분류 — Color & Diagnostics 그룹

**Files:**
- Modify: `docs/development/api_audit.md`

대상 모듈: `dartwork_mpl.color` (패키지), `dartwork_mpl.cmap`, `dartwork_mpl.diagnostics`, `dartwork_mpl.util` (color utilities `mix_colors`, `pseudo_alpha`만).

함수·클래스: `Color`, `DartworkColor`, `DartworkColormap`, `cspace`, `hex`, `named`, `oklab`, `oklch`, `rgb`, `mix_colors`, `pseudo_alpha`, `make_offset`, `classify_colormap`, `plot_colormaps`, `plot_colors`, `plot_fonts`.

명백한 케이스 정답:

| name | mpl_1to1 | diff | classification | notes |
|---|---|---|---|---|
| `Color`, `DartworkColor`, `DartworkColormap` | N | 3 | keep | OKLCH 컬러 시스템 본질 abstraction (`ai_native.md`) |
| `cspace`, `hex`, `named`, `oklab`, `oklch`, `rgb` | N | 2-3 | keep | semantic color name (`ai_native.md` 표) |
| `mix_colors` | N | 2 | borderline | OKLCH 보간 vs RGB 보간 — 본문 보고 결정 |
| `pseudo_alpha` | N | 2 | borderline | 컬러 위에 백색 블렌딩 — composition 가치 |
| `make_offset` | N | 2 | borderline | 0.4 legacy helper — Task 11에서 keep/remove 결정 |
| `classify_colormap` | N | 3 | keep | diagnostics 본질 |
| `plot_colormaps`, `plot_colors`, `plot_fonts` | N | 3 | keep | asset-diagnostic 본질 |

- [ ] **Step 1: 위 정답을 적용**

`mix_colors`, `pseudo_alpha`는 본문 보고 결정:

```bash
grep -A 10 "^def mix_colors\|^def pseudo_alpha" src/dartwork_mpl/util.py
```

OKLCH 보간이 들어 있으면 `keep`(matplotlib에 단일 호출 없음). 단순 RGB linspace면 `borderline`.

- [ ] **Step 2: 커밋**

```bash
git add docs/development/api_audit.md
git commit -m "docs(audit): classify color & diagnostics group (#141)"
```

---

## Task 7: 분류 — Helpers & Util & Figure 그룹

**Files:**
- Modify: `docs/development/api_audit.md`

대상 모듈: `dartwork_mpl.helpers` (패키지), `dartwork_mpl.figure`, `dartwork_mpl.util` (color 외 나머지).

함수: `figure`, `subplots`, `validate_data`, `auto_select_colors`, `add_value_labels`, `optimize_legend`, `suggest_chart_type`, `check_figure_quality`, `save_figure`, `create_figure_with_style`.

명백한 케이스 정답:

| name | mpl_1to1 | diff | classification | notes |
|---|---|---|---|---|
| `figure`, `subplots` | N | 3 | keep | 물리 단위 width API + aspect 토큰 — 핵심 abstraction |
| `validate_data` | N | 2 | keep | data shape 검증 (`integrations/why_ai_ready.md`) |
| `auto_select_colors` | N | 3 | keep | 카테고리 → 팔레트 매핑 |
| `add_value_labels` | N | 3 | borderline | bar/line value annotation — 데이터 순회 + 텍스트 배치 |
| `optimize_legend` | N | 3 | borderline | legend 자동 위치 — composition |
| `suggest_chart_type` | N | 3 | keep | 자연어 인터페이스 (`ai_native.md`) |
| `check_figure_quality` | N | 3 | keep | publication-quality 검증 |
| `save_figure` | N | 2 | borderline | `save_formats`와 중복? — 본문 비교 후 결정 |
| `create_figure_with_style` | N | 2 | borderline | `dm.style.use(...) + dm.subplots(...)` 2줄 호출과 중복? |

- [ ] **Step 1: `save_figure` vs `save_formats`, `create_figure_with_style` vs (style + subplots) 비교**

```bash
grep -A 30 "^def save_figure\|^def create_figure_with_style" src/dartwork_mpl/helpers/*.py
```

본문이 `dm.save_formats(...)`를 그냥 호출하는 wrapper면 `mpl_1to1=N (dm wrapping dm)`이지만 사실상 `remove`. `notes`에 "내부적으로 `dm.save_formats` 호출 — 이중 wrapper" 기록.

- [ ] **Step 2: 정답 적용 + 본문 비교 결과 반영**

- [ ] **Step 3: 커밋**

```bash
git add docs/development/api_audit.md
git commit -m "docs(audit): classify helpers & util & figure group (#141)"
```

---

## Task 8: 분류 — I/O & Units & Install 그룹

**Files:**
- Modify: `docs/development/api_audit.md`

대상 모듈: `dartwork_mpl.io`, `dartwork_mpl.units`, `dartwork_mpl.install`.

함수: `save_formats`, `save_and_show`, `show`, `cm`, `inch`, `mm`, `Inches`, `install_llm_txt`, `uninstall_llm_txt`.

명백한 케이스 정답:

| name | mpl_1to1 | diff | classification | notes |
|---|---|---|---|---|
| `save_formats` | N | 2 | keep | `savefig` 다중 kwargs 모호성 해소 (`ai_native.md` 표) |
| `save_and_show` | N | 2 | borderline | `save_formats(fig, ...); plt.show()` 2줄과 중복? |
| `show` | Y | 1 | borderline | `plt.show()` 한 줄 — 왜 wrapper? `notes`에 사유 |
| `cm`, `inch`, `mm` | N | 1 | keep | 물리 단위 토큰 (핵심 API) |
| `Inches` | N | 2 | keep | 단위 클래스 |
| `install_llm_txt`, `uninstall_llm_txt` | N | 3 | keep | CLI 도구 본질 |

- [ ] **Step 1: `show`, `save_and_show` 본문 확인**

```bash
grep -A 5 "^def show\|^def save_and_show" src/dartwork_mpl/io.py
```

`show`가 정말 단순히 `plt.show()`만 한다면 → `Y/1/remove`. dpi/backend 처리가 들어 있으면 → `keep`.

- [ ] **Step 2: 정답 적용**

- [ ] **Step 3: 커밋**

```bash
git add docs/development/api_audit.md
git commit -m "docs(audit): classify io & units & install group (#141)"
```

---

## Task 9: 분류 — Style & Annotation & Explore & Icon & Font 그룹

**Files:**
- Modify: `docs/development/api_audit.md`

대상 모듈: `dartwork_mpl.style`, `dartwork_mpl.annotation`, `dartwork_mpl.explore`, `dartwork_mpl.icon`, `dartwork_mpl.font`.

함수·클래스: `Style`, `style`, `list_styles`, `load_style_dict`, `style_path`, `label_axes`, `arrow_axis`, `list_palettes`, `list_colormaps`, `show_palette`, `icon_font`, `icon_font_path`, `list_icon_fonts`, (`font.py`의 public 항목).

명백한 케이스 정답:

| name | mpl_1to1 | diff | classification | notes |
|---|---|---|---|---|
| `Style`, `style`, `list_styles`, `load_style_dict`, `style_path` | N | 3 | keep | style 시스템 (`ai_native.md` 표 — `style.use` 모호성 해소) |
| `label_axes` | N | 3 | keep | 다중 axes 자동 라벨링 — 비자명 |
| `arrow_axis` | N | 3 | keep | annotation 본질 |
| `list_palettes`, `list_colormaps` | N | 2 | keep | 자원 탐색 |
| `show_palette` | N | 3 | keep | 팔레트 시각화 |
| `icon_font*`, `list_icon_fonts` | N | 2-3 | keep | 아이콘 폰트 시스템 본질 |
| `font.py` public 항목 | — | — | — | scripts 출력 보고 채움 |

- [ ] **Step 1: `font.py` 항목 확인 후 정답 결정**

```bash
grep "^def \|^class " src/dartwork_mpl/font.py
```

`fonts.list_*`/`fonts.path_*` 형태는 위 explore 그룹과 동일한 패턴 → `keep`.

- [ ] **Step 2: 정답 적용**

- [ ] **Step 3: 커밋**

```bash
git add docs/development/api_audit.md
git commit -m "docs(audit): classify style & annotation & explore & icon & font group (#141)"
```

---

## Task 10: 분류 — Lint & Validate & Prompt & Templates & Xplot 그룹

**Files:**
- Modify: `docs/development/api_audit.md`

대상 모듈: `dartwork_mpl.lint`, `dartwork_mpl.validate`, `dartwork_mpl.validate_fixes`, `dartwork_mpl.prompt`, `dartwork_mpl.templates`, `dartwork_mpl.xplot`.

함수: `lint_code`, `migrate_legacy_code`, `validate_figure`, `validate_with_fixes`, `prompt_path`, `get_prompt`, `list_prompts`, `copy_prompt`, `find_template`, `plot_diverging_bar`, (`xplot/` public 항목).

명백한 케이스 정답:

| name | mpl_1to1 | diff | classification | notes |
|---|---|---|---|---|
| `lint_code`, `migrate_legacy_code` | N | 3 | keep | dartwork-mpl 자체 lint engine — 비자명 (T4) |
| `validate_figure`, `validate_with_fixes` | N | 3 | keep | publication-quality 검증 본질 (T7) |
| `prompt_path`, `get_prompt`, `list_prompts`, `copy_prompt` | N | 2 | keep | 번들된 지식베이스 접근 (`ai_native.md`) |
| `find_template` | N | 3 | keep | template 메타데이터 인덱스 (T6) |
| `plot_diverging_bar` | N | 3 | borderline | 단일 plot 함수 — 다른 template과 일관성 검토 |
| `xplot/` 항목 | — | — | — | 0.3 deprecated 흔적 — 본문 보고 정리 |

- [ ] **Step 1: `xplot/` 디렉토리 점검**

```bash
ls src/dartwork_mpl/xplot/
grep "^def \|^class " src/dartwork_mpl/xplot/*.py
```

비어있거나 `__init__.py`만 있으면 `notes`에 "0.3 deprecated alias — 0.5에서 삭제"라고 기록 후 `remove`.

- [ ] **Step 2: 정답 적용**

- [ ] **Step 3: 누락 그룹 확인**

```bash
grep -c "pending" docs/development/api_audit.md
```

Expected: 0. 0이 아니면 어느 모듈이 누락됐는지 확인:

```bash
grep "pending" docs/development/api_audit.md | awk -F'|' '{print $3}' | sort -u
```

남아있는 모듈을 직접 분류 후 다시 검사.

- [ ] **Step 4: 커밋**

```bash
git add docs/development/api_audit.md
git commit -m "docs(audit): classify lint & validate & prompt & templates & xplot group (#141)"
```

---

## Task 11: borderline summary 섹션 작성

**Files:**
- Modify: `docs/development/api_audit.md`

표 분류가 끝났으면, borderline 케이스를 별도 섹션으로 모아 토론 용이하게 한다.

- [ ] **Step 1: borderline 행 추출**

```bash
grep "borderline" docs/development/api_audit.md | awk -F'|' '{print $2}' | sort -u
```

- [ ] **Step 2: `## Borderline cases (토론 대상)` 섹션 추가**

`docs/development/api_audit.md` 본문 끝에 다음 섹션을 추가:

```markdown
## Borderline cases (토론 대상)

분류가 `borderline`인 항목을 별도로 정리한다. 각 항목은 PR 리뷰 또는
후속 코멘트에서 keep / remove로 재분류한다.

| name | 사유 (notes 요약) | 잠정 권고 |
|---|---|---|
```

그 아래에 `grep "borderline"` 결과의 각 항목을 한 줄씩 추가하고, 잠정 권고(주관)를 적는다. 권고 작성 룰:

- composition 가치 있고 본문 LOC ≥ 4 → 잠정 `keep`.
- 단순 default kwargs 제공만 하고 본문 LOC ≤ 3 → 잠정 `remove`.
- 다른 dartwork-mpl 함수의 wrapper(예: `save_figure` ≈ `save_formats`) → 잠정 `remove`.

- [ ] **Step 3: 커밋**

```bash
git add docs/development/api_audit.md
git commit -m "docs(audit): collect borderline cases section (#141)"
```

---

## Task 12: 최종 검증 + PR 생성

- [ ] **Step 1: 표 정합성 검증**

```bash
# 행 수 검증
grep -c "^|" docs/development/api_audit.md
# pending 0인지
grep -c "pending" docs/development/api_audit.md
# classification 분포
grep -oE "(keep|borderline|remove) " docs/development/api_audit.md | sort | uniq -c
```

Expected: pending=0, classification 분포에서 `remove` ≥ 5 (최소 spines 그룹의 4개), `keep` ≥ 20 (color/figure/io 그룹).

- [ ] **Step 2: 링크 검증**

```bash
grep -E "\(\.\./|\(http" docs/development/api_audit.md
```

각 링크가 유효한지 시각 확인.

- [ ] **Step 3: 커밋 그래프 정리**

```bash
git log --oneline main..HEAD
```

Expected: Task 2~11에 해당하는 커밋 ~10개. 머지 시 squash 권장(PR description으로).

- [ ] **Step 4: 푸시**

```bash
git push -u origin chore/api-audit-table
```

- [ ] **Step 5: PR 생성**

```bash
gh pr create \
  --title "docs(audit): seed API audit table for round 1 (#141)" \
  --body "$(cat <<'EOF'
## Summary
- spec `docs/superpowers/specs/2026-05-05-prune-low-value-utils-design.md`을 따라 round 1 audit 표를 머지한다.
- `scripts/api_audit.py`로 자동 컬럼(`name`, `module`, `kind`, `loc`, `repo_callsites`)을 추출하고, 모듈 그룹별로 수동 컬럼(`mpl_canonical_1to1`, `inline_difficulty`, `classification`, `notes`)을 채웠다.
- 라이브러리 코드 변경 없음. 후속 라운드(0.5.0 제거)의 입력.

## Closes
Refs #141 (이 이슈는 라운드별 후속 PR로 점진 해결).

## Test plan
- [ ] `python scripts/api_audit.py`가 동일 행 수를 재현한다.
- [ ] `docs/development/api_audit.md`에 `pending` 행이 없다.
- [ ] borderline 섹션이 분류별 합과 일치한다.
EOF
)"
```

Expected: PR URL이 출력된다.

---

## Self-review checklist (작업 완료 시)

- [ ] `grep -c pending docs/development/api_audit.md` = 0
- [ ] `scripts/api_audit.py`가 ruff/mypy 통과 (`pre-commit run --files scripts/api_audit.py`)
- [ ] 모든 모듈이 표에 등장 (excluded 제외): `awk -F'|' 'NR>4 {print $3}' docs/development/api_audit.md | sort -u`
- [ ] borderline 섹션이 표의 borderline 갯수와 일치
- [ ] PR description의 "Test plan" 체크박스가 모두 체크됨

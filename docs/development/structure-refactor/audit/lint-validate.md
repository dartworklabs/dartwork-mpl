---
orphan: true
---

# 구조 감사: lint · validate · validate_fixes

기준: `code-implement` SKILL + `references/{python,structure,modeling}.md`, limn(`tools/check_boundaries.py`, ADR 0009/0010/0012).
대상 커밋: `0e88b810` (main). mypy strict는 대상 24개 파일에서 통과한다(`uv run mypy ...` → no issues). 경계 검사기는 레포에 없다.

## 1. 현재 구조 요약

| 모듈 | 줄 | 담당 |
|---|---|---|
| `lint.py` | 1584 | 카탈로그 파싱(1–167), 이름 레지스트리(169–305), `_Syntax` 바인딩 분석(305–690), 탐지기(691–1050), `format_report`(1052–1083), 마이그레이션 힌트 데이터(1086–1256), autofix(1257–1440), `migrate_legacy_code`(1440–1584) |
| `validate/` (`__init__` 30, `_types` 44, `_orchestrator` 117) | 191 | `Severity`, `VisualWarning`, `validate_figure` |
| `validate/_checks/` 16개 파일 | 2342 | check 15개 + `_registry`, `_tick_utils`, `_luminance` |
| `validate_fixes.py` | 563 | fix 레지스트리, `validate_with_fixes`, `check_agent_requirements`, `generate_validation_report` |

내부 import 그래프:
- `lint.py` → 패키지 내부 import 없음. 대신 파일 경로를 직접 연다: `asset/prompt/02-anti-patterns.yaml`(38), `asset/mplstyle/presets.json`(1297, style 슬라이스의 저장 형식).
- `validate/_checks/*` → `.._types`, `..._helpers`(공유), `..._luminance._contrast_ratio`(밑줄 이름), `..._colors._conversion._srgb_to_oklab`(grayscale_safety.py:98, **colors 슬라이스의 private 모듈**), `...formatting.recommend_tick_decimals`(tick_decimal.py:8).
- `validate_fixes.py` → `.validate`(공개 표면), `.helpers.quality._MIN_RECOMMENDED_DPI`(13, **private 상수**), `import dartwork_mpl as dm`(292, 패키지 루트를 거쳐 `layout.simple_layout`을 부르는 순환).

영역으로 들어오는 import:
- `__init__.py:178-183` — `lint_code`, `migrate_legacy_code`, `validate_figure`, `validate_with_fixes`. `dm.__all__`에 **모듈** `validate_fixes`도 있다(285). `dm.lint`는 서브모듈 속성 자체가 공개 경로다(주석 172–177).
- `io.py:266` — `save_formats(validate=True)`가 `validate_figure` 호출.
- `mcp/tools.py:457,458,494,574,773` — `lint`, `format_report`, `apply_lint_fixes`, `migrate_legacy_code`(모두 `lint.__all__` 안). `Issue`→dict 직렬화가 tools.py 496–505와 576–584에 **두 번 복제**돼 있다.
- `mcp/execution.py:172`(lint), 298–316(자식 프로세스 코드 문자열에서 `validate_figure` 결과를 dict로 직렬화하고 `w.detail["check_id"]`로 `CHECK_FAILED`를 해석).
- 테스트의 private 접근: `lint._AUTO_FIX_TABLE`(test_lint.py:449), `lint._MIGRATE_HINTS`(test_deprecation_registry_parity.py:25), `validate._orchestrator._run_check_safely`·`_registry._REGISTRY` monkeypatch(test_validate.py:862,880), `_checks._tick_utils`(test_validate.py:245,254), `validate_fixes._style_applied`(2곳), `validate._checks.register_check`(test_check_registry, test_mcp_validation_contract 등 5곳 — 사실상 테스트용 표면).

## 2. 파일트리 결함

1. **`lint.py` 한 파일에 변경 이유가 다른 네 기능이 섞여 있다.** 커밋 이력이 이를 뒷받침한다: 카탈로그 경계(`f9d24dd6 reject malformed catalogs`), 탐지(`fe4282d5 validate color names`), autofix(`d2b6d0b1 #514`), 마이그레이션(`da7e1814`, `52b5fea5`, `92a7baec` — `__init__`의 `_REMOVED_NAMES`와 함께 바뀜). lint.py 커밋 22개 중 YAML 동반 10, `mcp/tools.py` 동반 12, `test_migrate_legacy.py` 동반 6이다.
2. **카탈로그와 엔진이 rule id 문자열로 묶여 있다.** `_builtin_matches`(717–882)에 kebab-case 리터럴 22개(`"tight-layout"`, `"dpi-arg"`, `rule.id.startswith("dm-")` 등)가 하드코딩돼 있다. `lint()`(1039)는 번들 rule이면 YAML의 `detector.pattern`을 무시하고 id로 분기한다. 즉 YAML 탐지기 필드는 번들 rule에선 사실상 설명용이고, 진짜 규칙은 엔진 안에 있다. 카탈로그에 rule을 추가하면 엔진 수정이 필요한지 타입이나 검사로 드러나지 않는다(`TestAutoFixTableContract`가 autofix 쪽만 지킨다).
3. **`validate` / `validate_fixes` 분할이 변경 축과 어긋난다.** check 하나를 추가할 때 `_checks/<check>.py`, `_checks/__init__.py`, `validate_fixes.py`의 `@register_fix`를 함께 고친다(`3292cccf`: tick_decimal·tick_rotation·unit_dup + validate_fixes). fix handler는 check가 만든 `detail` 키를 문자열로 다시 읽는다. check와 그 fix는 같은 이유로 바뀌는데도 다른 패키지에 있다.
4. **`validate_fixes.py`에 별개 기능 셋이 있다.** fix 제안(check별), auto-apply shell(`validate_with_fixes`: 출력·layout 변이·재검증), 에이전트 요구사항 점검(`check_agent_requirements`, `_style_applied`, 기본 색 휴리스틱). 셋째는 `helpers/quality.py`와 DPI 임계값을 공유한다(quality.py:15 주석이 연결을 인정). 이건 validate check가 아니라 품질 점검이다.
5. **functional core / imperative shell이 섞여 있다.** `lint()`가 호출마다 `load_rules()`로 파일을 읽고 YAML을 파싱한다(1027). `apply_lint_fixes`는 두 번 읽는다. `_supported_preset`(1293)은 탐색 결정 도중 JSON을 연다. `validate_figure`는 `canvas.draw`, check 실행, stdout 출력을 한 함수에서 한다.
6. **테스트가 코드와 떨어져 있다.** `tests/test_lint.py` 1474줄(17개 클래스가 catalog/detect/fix를 섞음), `test_migrate_legacy.py` 329, `test_validate.py` 950(check 15개가 한 파일), `test_validate_accessibility.py` 297, `test_validate_fixes.py` 406, `test_check_registry.py` 99. `pyproject` `testpaths = ["tests"]`이고 wheel이 `src/dartwork_mpl` 전체를 담는다(103). 그래서 limn식 `src/.../tests/` 동거는 현재 설정으로는 수집도 제외도 안 된다(§4 PR-0 필요). `tests/conftest.py:110`의 autouse matplotlib 격리 fixture도 동거 테스트에 옮겨줘야 한다.
7. **슬라이스 경계를 넘는 private 접근** (§1): colors `_conversion`, helpers `quality._MIN_RECOMMENDED_DPI`, style의 `presets.json` 파일 형식, 루트 `dartwork_mpl` 순환 import.

## 3. 타입 결함

| 결함 | 근거 (file:line) | 개수 |
|---|---|---|
| 상태 문자열 severity | `lint.Rule.severity: str`(48), `Issue.severity: str`(71), `load_rules`의 집합 검사(118–124) | 2 필드 |
| detector kind + value 쌍 (variant별 의미가 다른 필드) | `Rule.detector_kind: str` + `detector_value: str`(49–50). regex 패턴, literal, AST check 이름이 한 str에 섞임 | 1 |
| 문자열 owner kind | `_Syntax.kind/owner` → `str \| None`(`"pyplot"/"axes"/"figure"/"figure-class"/"dm"`). `kind == "..."` 비교 25곳. `facts: dict[int, dict[str, str \| None]]`(375) | 25 |
| sentinel로 표현한 variant | `_planned_fixes`의 `rule_id = ""`(1318) + 분기로 StyleFix/LayoutFix 구분. `_Fix.identity: tuple[str,int,int,int]`(1278). `_AUTO_FIX_TABLE` 3-tuple의 2·3번째 필드는 어디서도 읽지 않음(1257) | 3 |
| 이름 없는 실패(None) | `_parse_source → _Syntax \| None`(670–688, SyntaxError/RecursionError 등 5종을 하나로 뭉갬), `_apply_edits → str \| None`(1372, 겹침과 재파싱 실패 둘을 구분 못 함), `_original_offset → int \| None`, `_run_check_safely → list \| None`(_orchestrator.py:22) | 4 |
| 일부 경로에서만 의미 있는 Optional | `Issue.line/snippet/column: X \| None`(73–75). lint는 항상 채우는데 소비자가 `or 0`(953)이나 `if issue.column is not None`(1420)으로 방어 | 3 |
| `dict[str, Any]` 공용 payload | `VisualWarning.detail: dict[str, Any]`(_types.py:35). fix handler가 `.get(key, default)`로 10회 다시 읽음(validate_fixes.py:112–236). OVERFLOW tick variant는 `side`가 없어(overflow.py:121) fix가 `""`로 떨어짐. check 하나에 detail 모양이 세 가지 | 1 타입 / 10 읽기 |
| payload 안에 숨은 variant | `CHECK_FAILED`가 `VisualWarning`의 `check_id` 값이고 원래 id는 `detail["check_id"]`(_orchestrator.py:90–97). mcp/execution.py:301–304가 문자열로 해석 | 1 |
| 문자열 check id 분기 | `validate_fixes.py:324` `check_id in ("OVERFLOW","MARGIN_ASYMMETRY")`, `@register_fix("…")` 11개가 `register_check` id를 손으로 복제 | 12 |
| `Any` | `validate/_checks`: clipped_text 2, cross_axes 2, legend 1, overlap 1, grayscale_safety 1, text_contrast 3 (matplotlib artist 대체). `mcp/tools.py:576` `_serialise(issue: Any)` | 11 |
| 가변 값 객체 | `VisualWarning`(_types.py:30 `@dataclass`, frozen 아님), `text_contrast._ContrastGroup`(37) | 2 |
| `__all__` 누락 | `validate_fixes.py`(공개 모듈인데 없음, 문서는 automodule `:members:`로 대체), `_checks/_registry.py` | 2 |
| 예외로 표현한 예상 결과 | 해당 없음에 가깝다. `load_rules`의 `ValueError`(번들 데이터 파싱, 문서화된 계약), `validate_figure`의 미지 id `ValueError`(호출자 전제조건 위반 = 결함), `register_*` 중복 `RuntimeError`는 모두 결함 쪽. 예외: `validate_with_fixes`가 `simple_layout`의 4종 예외를 "fix 실패"로 삼킴(_LAYOUT_FIX_ERRORS, 27; 338) — 기대 결과를 예외로 받는 구조 | 1 |
| `cast` / `type: ignore` / noqa | 0 / 0 / 1(validate_fixes) | — |

## 4. 제안 목표 구조

```
src/dartwork_mpl/
  lint/                       # 슬라이스: 소스 정적 안티패턴 검사. lint.py → 패키지 (dm.lint 은 계속 모듈)
    __init__.py               # __all__ = 현재 7개 그대로: Issue, Rule, apply_lint_fixes, format_report, lint, load_rules, migrate_legacy_code
    catalog.py                # Rule, Issue, Severity=Literal[...], load_rules (YAML 경계 파서), 내부 _Detector = RegexDetector|SubstringDetector|AstNameDetector
    syntax.py                 # _Syntax, parse_source → ParsedSource | SourceRejected(reason)
    detect.py                 # 번들 rule id → 탐지 함수 표(dict[str, Callable]), _scan_text, lint()
    report.py                 # format_report
    fix.py                    # apply_lint_fixes, Edit, StyleFix | LayoutFix
    migrate.py                # migrate_legacy_code, _MIGRATE_HINTS (→ __init__ 의 _REMOVED_NAMES 와 함께 바뀌는 축)
    tests/                    # test_catalog, test_detect, test_fix, test_migrate (PR-0 이후)
  validate/                   # 슬라이스: 렌더된 Figure 시각 검사 + 수정 제안
    __init__.py               # __all__ = ["Severity","VisualWarning","validate_figure"] 그대로
    warning.py                # Severity, VisualWarning (공개 모양 유지), CheckFailed 변환
    run.py                    # (= _orchestrator) shell: draw → 실행 → CheckCompleted|CheckFailed → VisualWarning → print
    registry.py               # register_check / register_fix (한 레지스트리: id 하나에 check+fix)
    checks/<check>.py         # check_<x> + fix_<x> + 해당 detail TypedDict. 예: overflow.py에 OverflowTextDetail|OverflowTickDetail
    checks/tests/test_<check>.py
    fixes.py                  # get_fix_suggestions, validate_with_fixes (auto-apply shell)
    agent_requirements.py     # check_agent_requirements, generate_validation_report
  validate_fixes.py           # 호환 shim: 위 fixes/agent_requirements 재수출 + 명시적 __all__ (dm.validate_fixes 유지)
```

공개 경로 유지 방법:
- `dartwork_mpl.lint`는 패키지가 되어도 `import dartwork_mpl.lint`, `dm.lint.lint`, `from dartwork_mpl.lint import X`(7개)가 그대로 동작한다. **주의:** `test_mcp_validation_contract.py:534`가 `lint_module.lint`를 monkeypatch하고 `mcp/tools.py`는 호출 시점에 패키지 속성을 읽으므로 유지된다. 그러나 `apply_lint_fixes` 내부 호출은 `detect.lint`를 직접 부르게 되어 패치를 못 본다. 이동 전에 이 테스트가 무엇을 가정하는지 확인해야 한다.
- `docs/api/lint.rst`의 `automodule:: dartwork_mpl.lint :members:`는 `__all__`을 따르지만 재수출 객체의 `__module__`이 바뀐다. 문서 빌드로 확인한다.
- `validate_fixes.py`는 shim으로 남는다. 현재 공개된 이름(`validate_with_fixes`, `get_fix_suggestions`, `check_agent_requirements`, `generate_validation_report`, `register_fix`, `FixHandler`)을 `__all__`로 고정한다.
- `VisualWarning` 필드, `detail` dict 키, `Severity` 값, check id 15개, `CHECK_FAILED` 와이어 형식, `Issue` 필드, MCP dict 모양은 **변경하지 않는다.** 타입 강화는 내부 표현(TypedDict, Literal, 내부 variant)에서만 하고 경계에서 기존 모양으로 바꾼다.

**인터페이스에 닿는 항목(별도 승인 필요, 이번 범위 밖 권고):** `Rule`의 `detector_kind/value` 필드를 union으로 교체(사용자가 `Rule(...)`을 직접 생성함), `Issue.line/column`을 non-Optional로 바꾸기, `VisualWarning` frozen화, `validate_with_fixes` 시그니처, "카탈로그를 호출마다 다시 읽는다"는 문서 문구(lint.rst)를 캐시로 바꾸기.

허용할 슬라이스 간 의존(한 방향, 이유):
- `validate` → `layout`(`simple_layout`): auto-apply fix가 곧 레이아웃 재계산이다. `import dartwork_mpl as dm` 대신 layout 표면을 import한다.
- `validate` → `colors` 표면(OKLab 변환): grayscale 안전성은 colors의 지각 모델로 판단한다. 지금은 `_colors._conversion` private 접근이라 colors 쪽에 표면 추가가 필요하다(leak).
- `validate` → `formatting.recommend_tick_decimals`: TICK_DECIMAL은 formatting이 권하는 정밀도와 같아야 한다.
- `validate`(agent_requirements) → `helpers.quality`의 DPI 임계값: 같은 기준이다. 공개 상수로 올리거나 quality 쪽 판정 함수를 호출한다.
- `lint` → `style` 표면(preset 이름 목록): autofix는 출하된 preset만 고친다. 지금은 `presets.json` 경로·형식을 직접 읽는다(leak).
- `io` → `validate`, `mcp` → `lint`/`validate` 공개 표면: 현행 유지. `Issue`→dict 직렬화는 mcp 안에서 한 함수로 합친다(mcp가 와이어를 소유).
- 공유 모듈(`_helpers`, `_luminance`)은 어느 슬라이스도 import하지 않는다(현재 준수).

강제 수단: `tests/architecture/test_boundaries.py`(limn `tools/check_boundaries.py` 방식, AST import 그래프). 슬라이스 private import, shared→slice, 순환, 미등록 의존, decision 모듈(`lint/detect.py`, `lint/syntax.py`, `validate/checks/*`)의 타 기능 import, 이 다섯 위반을 주입해 실패하는지 확인한다. 레포 전체 검사기가 다른 감사에서 제안되면 그쪽 허용 목록에 위 의존을 등록한다.

테스트 배치: 한 슬라이스만 보는 테스트는 `lint/tests/`, `validate/checks/tests/`로 간다. 여러 기능을 함께 보는 `tests/robustness/`, `test_check_integration_junit.py`, `test_mcp_validation_contract.py`, `test_deprecation_registry_parity.py`, `test_antipattern_ratchet.py`(현재 main 작업 트리에만 있고 미추적)는 limn ADR-0012처럼 루트 `tests/`에 남긴다. **기존 테스트 이동은 skill상 사용자 승인 대상이다.**

## 5. 분할 PR 제안 (이동과 타입 변경을 분리, 각 ≤ ~800 변경 줄)

| # | 범위 | 파일 | 위험 | 검증 |
|---|---|---|---|---|
| PR-0 | 동거 테스트 수집·패키징 준비(레포 공통, 다른 감사와 합칠 수 있음): `testpaths=["tests","src"]`, wheel/sdist에서 `**/tests/**` 제외, mypy exclude, autouse 격리 fixture를 공유 plugin으로 승격 | pyproject.toml, tests/conftest.py | 중: wheel 내용 변화 | `uv build` 후 wheel에 tests 없음 확인, 전체 pytest 수집 수 동일 |
| PR-1 | 경계 검사기 도입(현 상태를 기준선으로, 알려진 leak 4건은 debt 목록) | tests/architecture/test_boundaries.py | 낮음 | 주입 위반 5종 실패, 슬라이스 내부 import 통과 |
| PR-2 | `lint.py` → `lint/` 패키지 **순수 이동**(catalog/syntax/detect/report/fix/migrate), `__init__` 재수출. 테스트 private import 2곳(`_AUTO_FIX_TABLE`, `_MIGRATE_HINTS`) 경로 갱신 | lint.py, lint/*, tests/test_lint.py, test_deprecation_registry_parity.py | 중: monkeypatch 가정, autodoc | `git diff -M` 이동 확인, 전체 pytest, `sphinx-build`, `python -c "import dartwork_mpl as dm; dm.lint.lint"` |
| PR-3 | lint 내부 타입: `Severity` Literal, `_OwnerKind` Literal, 내부 `_Detector` union(Rule 공개 필드는 유지하고 파싱 시 생성), `SourceRejected`/`EditRefused` 이름 있는 실패, `_Fix` variant, `_AUTO_FIX_TABLE` 죽은 필드 제거 | lint/* | 중 | mypy strict + `enable_error_code=["exhaustive-match"]` 추가, test_lint 전체 |
| PR-4 | 번들 rule id → 탐지 함수 표로 `_builtin_matches` 분해. 표와 카탈로그 id 정합 테스트(텍스트 전용 rule은 명시 목록) | lint/detect.py, lint/tests | 중: 탐지 회귀 | 안티패턴 ratchet, `TestBundledTemplatesLintClean`, test_lint |
| PR-5 | lint I/O를 shell로 분리: 카탈로그·preset 로딩을 한 함수로 모음(재로딩 동작은 유지), preset은 style 표면 경유 | lint/*, style.py(표면 1개 추가) | 낮음 | test_lint, ratchet |
| PR-6 | `validate_fixes.py` → `validate/fixes.py`, `validate/agent_requirements.py` 이동 + shim(`__all__` 명시). `import dartwork_mpl as dm` 제거 | validate_fixes.py, validate/* | 중: 공개 모듈 경로 | test_validate_fixes, test_api_stability, docs/api/validate.rst 빌드 |
| PR-7 | check별로 fix handler를 해당 `checks/<check>.py`로 이동, 레지스트리 하나로 통합(check id 중복 선언 제거). `_checks` → `checks` 개명은 하지 않거나 별도 PR(테스트 5곳이 `_checks.register_check` 사용) | validate/_checks/*, validate/fixes.py | 중 | test_check_registry, test_validate_fixes, docs의 check 표 |
| PR-8 | validate 내부 타입: detail TypedDict(check별·variant별, 런타임 dict 그대로), fix handler가 `.get` 기본값 대신 TypedDict 사용, `CheckCompleted \| CheckFailed` 내부 outcome, `_ContrastGroup` frozen | validate/* | 낮음~중 | mypy, test_validate*, test_mcp_validation_contract(와이어 불변) |
| PR-9 | private leak 해소: colors OKLab 표면, quality DPI 공개 상수 → 경계 검사기 debt 목록 축소 | validate/checks/grayscale_safety.py, _colors/__init__, helpers/quality.py | 낮음 | PR-1 검사기 debt 감소, color hash 테스트 불변 |
| PR-10 (승인 필요) | 테스트 이동: test_lint.py → lint/tests/*, test_validate.py → check별 파일 | tests/* | 낮음(로직 불변) | 수집 테스트 수·이름 동일 |
| PR-11 | mcp `Issue` 직렬화 단일화(tools.py 두 곳) | mcp/tools.py | 낮음 | MCP 계약 테스트 |

충돌 가능성(`git log --oneline -30 -- <files>` 기준):
- `lint.py`: 최근 `f9d24dd6`(카탈로그 경계), `d2b6d0b1`(#514), `5c080a9a`(#513), `fe4282d5`(#497)가 한 달 사이에 몰렸다. PR-2(이동)는 열린 lint PR이 없을 때 짧게 머지한다. 이동 뒤에는 모든 lint PR이 rebase 대상이다.
- `mcp/tools.py`·`mcp/execution.py`: `9b88c62d`, `a6c3447d`, `0e88b810`(#517)로 가장 바쁘다. PR-11과 와이어 관련 변경은 MCP 작업과 순서를 맞춘다.
- `validate/_orchestrator.py`: `3f0b7b2f`(MCP 로그·미완료 검증)이 최근 것이다. `_checks/grayscale_safety.py`는 `86ec3ae2`(#466) 이후 OKLab 색 체계 작업(`1ea6ef89`)과 겹친다. PR-9는 colors 리팩터(ADR 0002 동결)와 충돌하지 않게 표면 **추가**만 한다.
- `tests/test_antipattern_ratchet.py`·`antipattern_baseline.json`은 `chore/skm-antipattern-ratchet` 브랜치에서 미추적 상태다. PR-2·PR-4는 ratchet이 들어간 뒤에 해야 회귀를 기계적으로 판정할 수 있다.

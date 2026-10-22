"""Shared paths, case loading and the host-neutral prompt suffix."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

EVAL_DIR = Path(__file__).resolve().parent
REPO = EVAL_DIR.parents[1]
CASES_DIR = EVAL_DIR / "cases"
FIXTURES = EVAL_DIR / "fixtures"
DEFAULT_ROOT = Path.home() / "scratch" / "dartwork-mpl-evals"
REQUIRED = (
    "id",
    "kind",
    "lang",
    "purpose",
    "held_out",
    "prompt",
    "data",
    "oracle",
)

# Appended to every prompt. It states where things go, never how to plot.
SUFFIX_VERSION = "2026-10-22.1"
SUFFIX = {
    ("generate", "en"): (
        "\n\nProject notes: the data files are in `data/`. This project uses the "
        "dartwork-mpl plotting library, installed in `.venv` (run Python as "
        "`.venv/bin/python`). Keep the plotting script as `plot.py` in the project "
        "root and save the figure as both `out/figure.png` and `out/figure.pdf`."
    ),
    ("generate", "ko"): (
        "\n\n프로젝트 안내: 데이터 파일은 `data/`에 있습니다. 이 프로젝트는 dartwork-mpl "
        "플로팅 라이브러리를 쓰며 `.venv`에 설치되어 있습니다(Python은 `.venv/bin/python`으로 "
        "실행). 그림 스크립트는 프로젝트 루트의 `plot.py`로 남기고, 그림은 `out/figure.png`와 "
        "`out/figure.pdf` 두 파일로 저장해 주세요."
    ),
    ("edit", "en"): (
        "\n\nProject notes: `plot.py` builds the current figure from `data/` with "
        "dartwork-mpl, installed in `.venv` (run Python as `.venv/bin/python`). Change "
        "`plot.py` in place and save the result to the same `out/figure.png` and "
        "`out/figure.pdf`."
    ),
    ("edit", "ko"): (
        "\n\n프로젝트 안내: `plot.py`가 `data/`의 데이터로 dartwork-mpl을 써서 지금 그림을 "
        "만듭니다. dartwork-mpl은 `.venv`에 설치되어 있습니다(Python은 `.venv/bin/python`으로 "
        "실행). `plot.py`를 그 자리에서 고치고 결과를 같은 `out/figure.png`와 "
        "`out/figure.pdf`에 저장해 주세요."
    ),
}


def load_cases(ids: list[str] | None = None) -> list[dict]:
    """Load and validate every case YAML (optionally only ``ids``)."""
    cases = []
    for path in sorted(CASES_DIR.glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        missing = [k for k in REQUIRED if k not in case]
        if missing:
            raise ValueError(f"{path.name}: missing {missing}")
        if case["id"] != path.stem:
            raise ValueError(f"{path.name}: id {case['id']!r} != file stem")
        if case["kind"] == "edit" and (
            not {"base", "target", "edit_scope"} <= set(case)
            or case["edit_scope"] not in ("explicit", "broad")
        ):
            raise ValueError(
                f"{path.name}: edit cases need base, target and edit_scope explicit|broad"
            )
        for name in case["data"]:
            if not (FIXTURES / "data" / name).exists():
                raise ValueError(f"{path.name}: missing fixture {name}")
        cases.append(case)
    if ids:
        known = {c["id"] for c in cases}
        unknown = sorted(set(ids) - known)
        if unknown:
            raise ValueError(f"unknown case ids {unknown}")
        cases = [c for c in cases if c["id"] in ids]
    return cases


def full_prompt(case: dict) -> str:
    return case["prompt"].strip() + SUFFIX[(case["kind"], case["lang"])]


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8",
    )

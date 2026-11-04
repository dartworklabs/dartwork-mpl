"""Find eval cases quoted in the skill under test (teaching to the test).

The contamination check (``contamination.py``) catches an agent reaching
grading files. It cannot see a skill that already holds the answers: on
2026-11-04 the skill quoted g20's request ("the share of renewables"), g22's
(``GDP 성장률``) and the ``share_pct`` / ``week_start`` columns of g19, c06,
e09 and g18, each next to the label the eval then counted as agreement.

``find`` lists what the skill text shares with the cases:

* **columns**: identifier-like column names of ``fixtures/data`` (with an
  underscore or a non-ASCII letter, two characters or more, e.g. ``share_pct``,
  ``방문자수``; not ``월``) appearing as a whole word;
* **phrases**: four-word runs of a case prompt appearing in the skill text,
  except :data:`ALLOWED` (names of request kinds the skill must teach, such
  as "make it look better").

``run.py`` prints the hits and keeps them in ``run_meta.json``; it does not
stop the run (a skill may legitimately name a request kind).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent

# Request kinds the skill names on purpose: how users ask, not what to answer.
ALLOWED = frozenset(
    {
        "make it look better",
        "the legend above the",
        "legend above the plot",
        "the axis labels one",
        "axis labels one step",
    }
)

_WORD = re.compile(r"[\w%]+")


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _columns(data_dir: Path) -> set[str]:
    out: set[str] = set()
    for f in sorted(data_dir.glob("*.csv")):
        with open(f, encoding="utf-8-sig", newline="") as fh:
            header = next(csv.reader(fh), [])
        for c in (h.strip() for h in header):
            if len(c) > 1 and ("_" in c or re.search(r"[^\x00-\x7f]", c)):
                out.add(c)
    return out


def find(
    skill_dir: Path,
    cases_dir: Path = HERE / "cases",
    data_dir: Path = HERE / "fixtures" / "data",
    extra: tuple[Path, ...] = (),
) -> list[dict[str, str]]:
    """What the skill's Markdown (and ``extra`` files) quote from the cases."""
    docs = {
        p: p.read_text(encoding="utf-8")
        for p in sorted(skill_dir.rglob("*.md"))
    }
    docs.update({p: p.read_text(encoding="utf-8") for p in extra})
    flat = {p: " ".join(_words(t)) for p, t in docs.items()}
    hits: list[dict[str, str]] = []
    for col in sorted(_columns(data_dir)):
        pat = re.compile(r"(?<!\w)" + re.escape(col) + r"(?!\w)")
        for p, t in docs.items():
            if pat.search(t):
                hits.append({"kind": "column", "quote": col, "file": p.name})
    for case in sorted(cases_dir.glob("*.yaml")):
        prompt = str(
            yaml.safe_load(case.read_text(encoding="utf-8")).get("prompt", "")
        )
        w = _words(prompt)
        seen: set[str] = set()
        for i in range(len(w) - 3):
            phrase = " ".join(w[i : i + 4])
            if phrase in ALLOWED or phrase in seen:
                continue
            seen.add(phrase)
            for p, t in flat.items():
                if f" {phrase} " in f" {t} ":
                    hits.append(
                        {
                            "kind": f"prompt {case.stem}",
                            "quote": phrase,
                            "file": p.name,
                        }
                    )
    return hits

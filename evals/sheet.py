"""The summary (cases by arms to verdict) and the HTML contact sheet of one eval run."""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path
from typing import Any

from .judge import ARMS

COLOURS = {
    "OK": "#1f7a3a",
    "DEFECT": "#b26a00",
    "NO_FIGURE": "#b3261e",
    "INVALID": "#6b4fa0",
    "NOTRUN": "#6b6b6b",
}


def load(run: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Every ``result.json`` under a run directory, keyed by (case, arm)."""
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(run.glob("*/*/result.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        found[str(data["case"]), str(data["arm"])] = data
    return found


def summary(
    results: dict[tuple[str, str], dict[str, Any]],
    cases: list[str],
    arms: list[str],
) -> dict[str, Any]:
    """Verdict per case and arm (``NOTRUN`` where no result exists), totals, cost."""
    table = {
        c: {a: results.get((c, a), {}).get("verdict", "NOTRUN") for a in arms}
        for c in cases
    }
    totals = {
        a: {v: sum(table[c][a] == v for c in cases) for v in COLOURS}
        for a in arms
    }
    done = list(results.values())
    return {
        "verdicts": table,
        "totals": totals,
        "cost_usd": round(sum(r.get("cost_usd") or 0 for r in done), 4),
        "agent_seconds": round(sum(r.get("seconds") or 0 for r in done), 1),
    }


def text_table(data: dict[str, Any], arms: list[str]) -> str:
    """The verdict table as aligned plain text."""
    rows = [["case", *arms]]
    rows += [[c, *(v[a] for a in arms)] for c, v in data["verdicts"].items()]
    rows += [
        [
            "OK total",
            *(
                f"{data['totals'][a]['OK']}/{len(data['verdicts'])}"
                for a in arms
            ),
        ]
    ]
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    lines = [
        "  ".join(c.ljust(w) for c, w in zip(r, widths, strict=True))
        for r in rows
    ]
    lines.append(
        f"cost ${data['cost_usd']}, agent time {data['agent_seconds']} s"
    )
    return "\n".join(lines)


def _image(run: Path, rec: dict[str, Any]) -> str:
    path = run / rec["case"] / rec["arm"] / str(rec.get("image") or "")
    if not rec.get("image") or not path.is_file():
        return '<div class="none">no figure</div>'
    data = base64.b64encode(path.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" alt="{rec["case"]} {rec["arm"]}">'


def _cell(run: Path, rec: dict[str, Any] | None) -> str:
    if rec is None:
        return f'<td><span class="v" style="background:{COLOURS["NOTRUN"]}">NOTRUN</span></td>'
    esc = html.escape
    base = f"{rec['case']}/{rec['arm']}"
    verdict = rec["verdict"]
    reasons = "".join(f"<li>{esc(r)}</li>" for r in rec.get("reasons") or [])
    info = [
        f"{esc(f['rule'])}: {esc(f['message'])}"
        for f in (rec.get("figure") or {}).get("check") or []
        if f.get("severity") == "INFO"
    ]
    info_html = "".join(f"<li>{i}</li>" for i in info)
    tools: dict[str, int] = {}
    for t in rec.get("tools") or []:
        name = t.removeprefix("mcp__dartwork-mpl__")
        tools[name] = tools.get(name, 0) + 1
    calls = ", ".join(f"{k} x{v}" for k, v in tools.items()) or "none"
    links = [f'<a href="{base}/stream.jsonl">transcript</a>']
    if rec.get("source"):
        links.insert(0, f'<a href="{base}/source.py">source</a>')
    cost = rec.get("cost_usd") or 0
    return (
        f"<td>{_image(run, rec)}"
        f'<div><span class="v" style="background:{COLOURS[verdict]}">{verdict}</span> '
        f"{rec.get('seconds')} s · {rec.get('turns')} turns · ${cost:.3f} · "
        f"{' · '.join(links)}</div>"
        f"<div class=small>tools: {esc(calls)}</div>"
        + (f"<ul class=bad>{reasons}</ul>" if reasons else "")
        + (
            f"<details><summary>check INFO ({len(info)})</summary><ul>{info_html}</ul></details>"
            if info
            else ""
        )
        + f"<details><summary>agent's last words</summary><pre>{esc(str(rec.get('final_text', ''))[:3000])}</pre></details>"
        + "</td>"
    )


CSS = """
:root { --fg:#1d1d1f; --bg:#fafaf7; --line:#ddd; }
@media (prefers-color-scheme: dark) { :root { --fg:#e8e8e8; --bg:#1b1b1d; --line:#444; } }
body { font: 14px/1.45 system-ui, sans-serif; color: var(--fg); background: var(--bg); margin: 16px; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; }
th, td { border-top: 1px solid var(--line); padding: 10px 8px; vertical-align: top; }
td img { width: 100%; background: #fff; border: 1px solid var(--line); }
.v { color: #fff; padding: 1px 6px; border-radius: 3px; font-weight: 600; font-size: 12px; }
.small, .bad, details { font-size: 12px; } .bad { color: #b3261e; padding-left: 16px; }
.none { height: 120px; display: grid; place-items: center; border: 1px dashed var(--line); }
pre { white-space: pre-wrap; } .prompt { font-size: 13px; }
th.case { width: 14%; text-align: left; }
"""


def contact_sheet(run: Path, cases: list[str], arms: list[str]) -> str:
    """One self-contained HTML page: per case, the arms side by side."""
    results = load(run)
    data = summary(results, cases, arms)
    head = "".join(f"<th>{a}</th>" for a in arms)
    rows: list[str] = []
    for case in cases:
        prompt = next(
            (r["prompt"] for (c, _), r in results.items() if c == case), ""
        )
        cells = "".join(_cell(run, results.get((case, a))) for a in arms)
        rows.append(
            f'<tr><th class="case">{html.escape(case)}'
            f'<div class="prompt">{html.escape(prompt)}</div></th>{cells}</tr>'
        )
    totals = " · ".join(
        f"{a}: {data['totals'][a]['OK']}/{len(cases)} OK" for a in arms
    )
    return (
        "<!doctype html><html><head><meta charset=utf-8>"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>dartwork-mpl evals</title><style>{CSS}</style></head><body>"
        f"<h1>dartwork-mpl agent evals — {html.escape(run.name)}</h1>"
        f"<p>{totals} · cost ${data['cost_usd']} · agent time {data['agent_seconds']} s. "
        "Mechanical verdicts only filter; beauty is judged by looking.</p>"
        f"<table><tr><th class=case>case</th>{head}</tr>{''.join(rows)}</table>"
        "</body></html>"
    )


def write_report(
    run: Path, cases: list[str] | None = None, arms: list[str] | None = None
) -> str:
    """Write ``index.html`` and ``summary.json`` for a run; the text table."""
    results = load(run)
    meta_path = run / "run.json"
    meta: dict[str, Any] = (
        json.loads(meta_path.read_text()) if meta_path.exists() else {}
    )
    cases = cases or meta.get("cases") or sorted({c for c, _ in results})
    arms = (
        arms
        or meta.get("arms")
        or [a for a in ARMS if any(k[1] == a for k in results)]
    )
    data = summary(results, cases, arms)
    (run / "summary.json").write_text(json.dumps(data, indent=1))
    (run / "index.html").write_text(
        contact_sheet(run, cases, arms), encoding="utf-8"
    )
    return text_table(data, arms)

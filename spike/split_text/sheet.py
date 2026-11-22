"""The contact sheet: every case's images side by side, with what was measured."""

from __future__ import annotations

from html import escape
from pathlib import Path

CSS = """
body{font:14px/1.45 -apple-system,system-ui,sans-serif;margin:24px;background:#f6f6f4;color:#222}
h1{font-size:20px}h2{font-size:16px;margin-top:36px;border-top:1px solid #ccc;padding-top:14px}
.row{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-start}
figure{margin:0;background:#fff;border:1px solid #ddd;padding:8px;max-width:560px}
pre{background:#fff;border:1px solid #ddd;padding:10px;overflow-x:auto;font-size:12px}
figure img{max-width:100%;display:block}
figcaption{font-size:12px;color:#444;margin-top:6px;white-space:pre-wrap}
figcaption b{font-size:13px;color:#000}
"""


def figure(out: Path, key: str, label: str, report: str) -> str:
    """One image with its label and report; nothing when it was not drawn."""
    if not (out / f"{key}.png").exists():
        return ""
    extra = " ".join(
        f'<a href="{key}.{ext}">{ext}</a>'
        for ext in ("pdf", "svg")
        if (out / f"{key}.{ext}").exists()
    )
    return (
        f'<figure><img src="{key}.png"><figcaption><b>{escape(label)}</b> '
        f"{extra}\n{escape(report.strip())}</figcaption></figure>"
    )


def write_sheet(out: Path, reports: dict[str, str]) -> None:
    """Write ``index.html`` in ``out`` from the images and reports there."""
    cases: dict[str, list[str]] = {}
    for key in reports:
        case, _, how = key.rpartition("-")
        cases.setdefault(case, []).append(how)
    body = ["<h1>split-text spike: #812 columns, #810 legibility</h1>"]
    for case, hows in cases.items():
        body.append(f"<h2>{escape(case)}</h2><div class='row'>")
        body += [
            figure(out, f"{case}-{how}", how, reports[f"{case}-{how}"])
            for how in hows
        ]
        body.append("</div>")
    for name, title in (
        ("robust.txt", "robustness numbers"),
        ("partial.txt", "the proposed check rule"),
    ):
        numbers = out / name
        if numbers.exists():
            body.append(
                f"<h2>{title}</h2><pre>{escape(numbers.read_text())}</pre>"
            )
    html = f"<!doctype html><meta charset='utf-8'><title>split-text spike</title><style>{CSS}</style>{''.join(body)}"
    (out / "index.html").write_text(html, encoding="utf-8")

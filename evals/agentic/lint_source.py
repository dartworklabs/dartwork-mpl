"""Print ``dm.lint_code`` findings for one source as JSON.

``score.py`` runs this with a trusted interpreter (the run's wheel installed
outside every project), inside a read-only bwrap, source on stdin::

    python -I lint_source.py -   < plot.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter

import dartwork_mpl as dm


def main() -> int:
    if sys.argv[1] == "-":  # source on stdin (the harness's sandboxed lint)
        source = sys.stdin.read()
    else:
        with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
            source = f.read()
    issues = dm.lint_code(source)
    print(
        json.dumps(
            {
                "findings": len(issues),
                "rules": dict(Counter(i.rule_id for i in issues)),
                "severity": dict(Counter(i.severity for i in issues)),
                "dm_version": getattr(dm, "__version__", None),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Prove that a test reorganization kept every test: compare the collected test ids of a git ref with the working tree.

A test reorganization moves test classes between files and renames some of them. Neither may lose a test, run one
twice, or add one unnoticed. This tool collects `pytest --collect-only -q` ids on both sides, keys every id by
(class, test) with its file stripped (so a move between files is not a difference), applies an explicit rename map,
and reports what does not match:

  lost        a key the ref has (after renames) that the working tree has fewer times, or not at all
  duplicated  a key the working tree has more times than the ref (a base class holding tests imported twice, a paste)
  new         a key only the working tree has
  ambiguous   a key held by more than one test (in different files): only its count is proven, not which is which
  unused map  a rename-map entry that matched nothing (a typo would otherwise hide a lost test)

It exits 1 when any lost, duplicated, new or unused-map entry remains; ambiguous keys are listed for review but do not
fail the run (per-module copies such as ModuleBoundary are meant to share a key). It exits 2 on a usage error.

The rename map is a text file, one entry per line (# starts a comment):

  OldClass -> NewClass                                  every test of a class
  tests/test_x.py::OldClass -> NewClass                 only that file's class (when the class name is not unique)
  OldClass::test_old -> NewClass::test_new              one test
  + NewClass::test_added                                an expected new test (or `+ NewClass` for a whole class)
  - OldClass::test_removed                              an expected removal (or `- OldClass`)
  ~ subtests passed +48                                 an expected change of a total no test id carries

With --results BEFORE AFTER (repeatable) it also compares two runs, each a JUnit XML file (pytest --junitxml) or the
text output of `pytest -rA`. Every test the input names is compared by key under the map, so a test that passed before
and skips now is named; the totals (passed, skipped, failed, subtests ...) must equal the old ones minus the expected
removals plus the expected additions plus the `~` deltas. JUnit names every test but holds no subtests; -rA holds the
subtest totals but names only passed and failed tests, so a proof passes both.

Usage:
  uv run python scripts/test_id_map.py --ref origin/main [--map renames.txt] [--results before.xml after.xml]
      [--results before-rA.txt after-rA.txt]
  uv run python scripts/test_id_map.py --before-ids a.txt --after-ids b.txt ...   (ids collected elsewhere)
Standard library only.
"""

from __future__ import annotations

import argparse
import collections
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent.parent


def die(message: str) -> NoReturn:
    """Stop with a usage or input error: the message on stderr, exit status 2 (1 is kept for "differences found")."""
    sys.stderr.write(f"test_id_map: {message}\n")
    raise SystemExit(2)


# A pytest node id: file, then optional class(es), then the test (with an optional [param] suffix).
Key = tuple[str, str]


@dataclass(frozen=True)
class CollectedId:
    """One collected test: its file, its class ("" outside a class) and its test name with any [param] suffix."""

    path: str
    cls: str
    test: str

    @property
    def key(self) -> Key:
        """The directory-free identity used for comparison: (class, test).

        A test outside a class is keyed by its module's file stem instead of a class, so module-level tests that
        share a name across files (``test_basic``) stay distinct, while moving a module to another directory under
        the same file name changes nothing.
        """
        return (self.cls or Path(self.path).stem, self.test)

    def show(self) -> str:
        """The id as pytest prints it."""
        return "::".join(p for p in (self.path, self.cls, self.test) if p)


def parse_id(line: str) -> CollectedId | None:
    """A pytest node id line -> CollectedId, or None for a line that is not a test id (summary, blank, warnings)."""
    line = line.strip()
    if "::" not in line or " " in line.split("[", 1)[0]:
        return None
    parts = line.split("::")
    path, rest = parts[0], parts[1:]
    if not path.endswith(".py"):
        return None
    test = rest[-1]
    cls = "::".join(rest[:-1])
    return CollectedId(path, cls, test)


def read_ids(lines: Iterable[str]) -> list[CollectedId]:
    """Every test id in a `pytest --collect-only -q` output (other lines are ignored)."""
    return [t for t in (parse_id(ln) for ln in lines) if t is not None]


# Printed before each collected node id by the collection plugin, so the ids are read whatever verbosity the
# project's pytest ``addopts`` set.
_ID_MARKER = "@@test-id-map@@ "
_COLLECT_SCRIPT = f"""
import sys
import pytest


class _PrintIds:
    def pytest_collection_finish(self, session):
        for item in session.items:
            print({_ID_MARKER!r} + item.nodeid)


sys.exit(pytest.main(["--collect-only", "-p", "no:cacheprovider"], plugins=[_PrintIds()]))
"""


def collect(cwd: Path) -> list[str]:
    """The collected node ids of the tree at cwd, one per line; an empty or failed collection is an error (exit 2).

    Runs this interpreter's pytest so the ref tree is collected with the same installed dependencies (all extras)
    as the working tree; the tree's own ``pythonpath`` setting puts its sources first.
    """
    r = subprocess.run(
        [sys.executable, "-c", _COLLECT_SCRIPT],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        sys.stderr.write(r.stdout[-4000:] + r.stderr[-4000:])
        die(f"collection failed in {cwd} (exit {r.returncode})")
    ids = [
        line[len(_ID_MARKER) :]
        for line in r.stdout.splitlines()
        if line.startswith(_ID_MARKER)
    ]
    if not ids:
        die(f"collection in {cwd} found no tests")
    return ids


def collect_ref(ref: str) -> list[str]:
    """Collect the ids of a git ref in a temporary worktree (removed afterwards); the working tree is untouched."""
    tmp = Path(tempfile.mkdtemp(prefix="test-id-map-"))
    tree = tmp / "tree"
    subprocess.run(
        ["git", "worktree", "add", "--detach", "--quiet", str(tree), ref],
        cwd=ROOT,
        check=True,
    )
    try:
        return collect(tree)
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(tree)],
            cwd=ROOT,
            check=False,
        )
        os.rmdir(tmp)


# ---------------------------------------------------------------- rename map


@dataclass
class Rule:
    """One rename-map entry. old/new are "Class" or "Class::test" (a module stem stands for the class of the module's
    module-level tests); path limits a rename to one file."""

    line: int
    old: str
    new: str
    path: str = ""
    used: int = 0

    def apply(self, t: CollectedId) -> Key | None:
        """The key t maps to under this rule, or None when the rule does not match t."""
        if self.path and t.path != self.path:
            return None
        if "::" in self.old:
            if "::".join(t.key) != self.old:
                return None
            cls, _, test = self.new.rpartition("::")
            return (cls, test)
        if t.key[0] != self.old:
            return None
        return (self.new, t.test)


@dataclass
class RenameMap:
    """The parsed rename map: renames, expected additions and removals (as "Class" or "Class::test" patterns)."""

    rules: list[Rule] = field(default_factory=list)
    added: dict[str, int] = field(default_factory=dict)  # pattern -> line
    removed: dict[str, int] = field(default_factory=dict)
    added_used: set[str] = field(default_factory=set)
    removed_used: set[str] = field(default_factory=set)
    deltas: collections.Counter[str] = field(
        default_factory=collections.Counter
    )  # `~ outcome +N` lines


def split_path(spec: str) -> tuple[str, str]:
    """ "tests/test_x.py::Cls::t" -> ("tests/test_x.py", "Cls::t"); a spec without a .py file -> ("", spec)."""
    head, sep, tail = spec.partition("::")
    if sep and head.endswith(".py"):
        return head, tail
    return "", spec


def read_map(text: str) -> RenameMap:
    """Parse a rename map (see the module docstring); a malformed line is a usage error (exit 2)."""
    m = RenameMap()
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line[0] in "+-" and line[1:2] == " ":
            (m.added if line[0] == "+" else m.removed)[line[2:].strip()] = n
            continue
        if line[:2] == "~ ":
            what, _, delta = line[2:].strip().rpartition(" ")
            if not what or not re.fullmatch(r"[+-]\d+", delta):
                die(
                    f"rename map line {n}: expected '~ <outcome> +N' or '-N': {raw!r}"
                )
            m.deltas[what] += int(delta)
            continue
        old, arrow, new = line.partition("->")
        old, new = old.strip(), new.strip()
        path, old = split_path(old)
        if (
            not arrow
            or not old
            or not new
            or old.count("::") != new.count("::")
        ):
            die(
                f"rename map line {n}: expected 'Old -> New' with matching shapes: {raw!r}"
            )
        m.rules.append(Rule(n, old, new, path))
    return m


def matches(pattern: str, t: CollectedId | None, key: Key) -> bool:
    """Whether a +/- pattern ("[file::]Class" or "[file::]Class::test") names this test."""
    path, rest = split_path(pattern)
    if path and (t is None or t.path != path):
        return False
    if "::" in rest or not key[0]:
        return "::".join(k for k in key if k) == rest
    return key[0] == rest


def mapped_key(t: CollectedId, m: RenameMap) -> Key:
    """t's key after the first matching rename rule (file-limited rules are tried first, then specific tests)."""
    for rule in sorted(m.rules, key=lambda r: (not r.path, "::" not in r.old)):
        k = rule.apply(t)
        if k is not None:
            rule.used += 1
            return k
    return t.key


# ---------------------------------------------------------------- comparison


@dataclass
class Report:
    """What differs between the two collections (keys shown as Class::test)."""

    lost: list[str] = field(default_factory=list)
    duplicated: list[str] = field(default_factory=list)
    new: list[str] = field(default_factory=list)
    ambiguous: list[str] = field(default_factory=list)
    unused: list[str] = field(default_factory=list)
    expected_new: list[str] = field(default_factory=list)
    expected_removed: list[str] = field(default_factory=list)
    moved: int = 0
    renamed: int = 0
    before: int = 0
    after: int = 0

    @property
    def failures(self) -> int:
        """The number of unmapped differences (ambiguous keys are not counted)."""
        return (
            len(self.lost)
            + len(self.duplicated)
            + len(self.new)
            + len(self.unused)
        )


def show_key(k: Key) -> str:
    """A key as Class::test (or test alone outside a class)."""
    return "::".join(p for p in k if p)


def compare(
    before: list[CollectedId], after: list[CollectedId], m: RenameMap
) -> Report:
    """Compare the two collections under the rename map; see the module docstring for the categories."""
    rep = Report(before=len(before), after=len(after))
    want: collections.Counter[Key] = collections.Counter()
    where: dict[Key, list[str]] = collections.defaultdict(list)
    for t in before:
        k = mapped_key(t, m)
        if k != t.key:
            rep.renamed += 1
        hit = [p for p in m.removed if matches(p, t, k) or matches(p, t, t.key)]
        if hit:
            m.removed_used.update(hit)
            rep.expected_removed.append(t.show())
            continue
        want[k] += 1
        where[k].append(t.path)
    have: collections.Counter[Key] = collections.Counter()
    have_paths: dict[Key, list[str]] = collections.defaultdict(list)
    for t in after:
        hit = (
            [p for p in m.added if matches(p, t, t.key)]
            if t.key not in want
            else []
        )
        if hit:
            m.added_used.update(hit)
            rep.expected_new.append(t.show())
            continue
        have[t.key] += 1
        have_paths[t.key].append(t.path)
    for k in sorted(set(want) | set(have)):
        w, h = want[k], have[k]
        if w and not h:
            rep.lost.append(
                "{}  (was in {})".format(show_key(k), ", ".join(where[k]))
            )
        elif h and not w:
            rep.new.append(
                "{}  (in {})".format(show_key(k), ", ".join(have_paths[k]))
            )
        elif h > w:
            rep.duplicated.append(
                "{}  ({} -> {}: {})".format(
                    show_key(k), w, h, ", ".join(have_paths[k])
                )
            )
        elif h < w:
            rep.lost.append(
                "{}  ({} -> {}: {})".format(
                    show_key(k), w, h, ", ".join(have_paths[k])
                )
            )
        if h > 1:
            rep.ambiguous.append(
                "{}  ({})".format(show_key(k), ", ".join(sorted(have_paths[k])))
            )
        if h == w == 1 and sorted(where[k]) != sorted(have_paths[k]):
            rep.moved += 1
    rep.unused = [
        f"line {r.line}: {r.old} -> {r.new}" for r in m.rules if not r.used
    ]
    rep.unused += [
        f"line {n}: + {p}" for p, n in m.added.items() if p not in m.added_used
    ]
    rep.unused += [
        f"line {n}: - {p}"
        for p, n in m.removed.items()
        if p not in m.removed_used
    ]
    return rep


# ---------------------------------------------------------------- run results


@dataclass
class Results:
    """One run: its totals by outcome, and the outcome of each test the input names (None when it names none)."""

    counts: collections.Counter[str]
    per_test: list[tuple[CollectedId, str]] | None = None


# The final summary line's counts, e.g. "1496 passed, 11 skipped, 563 subtests passed in 297.14s".
SUMMARY = re.compile(
    r"(\d+) (subtests passed|subtests failed|subtests skipped|passed|failed|skipped|errors?|xfailed|xpassed)"
)
# The -rA short summary lines that name a test ("SKIPPED [1] file:line: reason" names only a line, so skips are totals).
NAMED = re.compile(r"^(PASSED|FAILED|ERROR|XFAIL|XPASS) (\S+::\S+)")
OUTCOME = {
    "PASSED": "passed",
    "FAILED": "failed",
    "ERROR": "error",
    "XFAIL": "xfailed",
    "XPASS": "xpassed",
}


def read_results(path: Path) -> Results:
    """A run from a JUnit XML file (pytest --junitxml) or the text output of `pytest -rA`."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if text.lstrip().startswith("<"):
        return read_junit(text)
    last = [
        ln for ln in text.splitlines() if SUMMARY.search(ln) and " in " in ln
    ]
    if not last:
        die(f"{path}: no pytest summary line found")
    counts: collections.Counter[str] = collections.Counter()
    for n, what in SUMMARY.findall(last[-1]):
        counts["error" if what.startswith("error") else what] += int(n)
    per_test = []
    for ln in text.splitlines():
        m = NAMED.match(ln)
        t = parse_id(m.group(2)) if m else None
        if m and t is not None:
            per_test.append((t, OUTCOME[m.group(1)]))
    return Results(counts, per_test or None)


def read_junit(text: str) -> Results:
    """Per-test outcomes of a JUnit XML report (pytest writes no subtest results there; compare those from -rA)."""
    counts: collections.Counter[str] = collections.Counter()
    per_test = []
    for case in ET.fromstring(text).iter("testcase"):
        classname, name = case.get("classname", ""), case.get("name", "")
        # classname is "tests.test_x.Class" (or "tests.test_x" for a module-level test)
        parts = classname.split(".")
        mod = max(
            (i for i, p in enumerate(parts) if p.startswith("test_")),
            default=len(parts) - 1,
        )
        t = CollectedId(
            "/".join(parts[: mod + 1]) + ".py",
            "::".join(parts[mod + 1 :]),
            name,
        )
        tags = {child.tag for child in case}
        outcome = (
            "error"
            if "error" in tags
            else "failed"
            if "failure" in tags
            else "skipped"
            if "skipped" in tags
            else "passed"
        )
        counts[outcome] += 1
        per_test.append((t, outcome))
    return Results(counts, per_test)


def compare_results(before: Results, after: Results, m: RenameMap) -> list[str]:
    """The differences between two runs. Named tests are compared one by one under the rename map; the totals must
    equal the old totals minus the expected removals plus the expected additions (as far as the input names them)
    plus the declared `~` deltas."""
    problems: list[str] = []
    expect = collections.Counter(before.counts)
    for what, delta in m.deltas.items():
        if (
            what in before.counts or what in after.counts
        ):  # JUnit, for one, carries no subtest totals
            expect[what] += delta
    if before.per_test is not None and after.per_test is not None:
        was: dict[Key, list[str]] = collections.defaultdict(list)
        for t, outcome in before.per_test:
            k = mapped_key(t, m)
            if any(matches(p, t, k) or matches(p, t, t.key) for p in m.removed):
                expect[outcome] -= 1
            else:
                was[k].append(outcome)
        now: dict[Key, list[str]] = collections.defaultdict(list)
        for t, outcome in after.per_test:
            if t.key not in was and any(matches(p, t, t.key) for p in m.added):
                expect[outcome] += 1
            else:
                now[t.key].append(outcome)
        problems.extend(
            f"{show_key(k)}: {sorted(was.get(k, []))} -> {sorted(now.get(k, []))}"
            for k in sorted(set(was) | set(now))
            if sorted(was.get(k, [])) != sorted(now.get(k, []))
        )
    problems.extend(
        f"total {what}: expected {expect[what]}, got {after.counts[what]}"
        for what in sorted(set(expect) | set(after.counts))
        if expect[what] != after.counts[what]
    )
    return problems


# ---------------------------------------------------------------- command line


def print_section(title: str, rows: list[str], limit: int = 200) -> None:
    """One report section, if it has rows."""
    if not rows:
        return
    print(f"{title} ({len(rows)}):")
    for r in rows[:limit]:
        print("  " + r)
    if len(rows) > limit:
        print("  ... %s more" % (len(rows) - limit))


def main(argv: list[str] | None = None) -> int:
    """Run the comparison; exit 0 when nothing is unmapped, 1 when something is, 2 on a usage error."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--ref",
        help="git ref to collect the 'before' ids from (in a temporary worktree)",
    )
    src.add_argument(
        "--before-ids",
        type=Path,
        help="a saved `pytest --collect-only -q` output for 'before'",
    )
    ap.add_argument(
        "--after-ids",
        type=Path,
        help="a saved collection for 'after' (default: collect the working tree)",
    )
    ap.add_argument(
        "--map", type=Path, help="the rename map (see the module docstring)"
    )
    ap.add_argument(
        "--results",
        nargs=2,
        type=Path,
        action="append",
        metavar=("BEFORE", "AFTER"),
        help="two runs to compare (JUnit XML or `pytest -rA` output); may be given once per format",
    )
    ap.add_argument(
        "--quiet-ambiguous",
        action="store_true",
        help="count ambiguous keys without listing them",
    )
    args = ap.parse_args(argv)

    before_lines = (
        collect_ref(args.ref)
        if args.ref
        else args.before_ids.read_text(encoding="utf-8").splitlines()
    )
    after_lines = (
        args.after_ids.read_text(encoding="utf-8").splitlines()
        if args.after_ids
        else collect(ROOT)
    )
    rmap = (
        read_map(args.map.read_text(encoding="utf-8"))
        if args.map
        else RenameMap()
    )
    rep = compare(read_ids(before_lines), read_ids(after_lines), rmap)

    print(f"before: {rep.before} tests, after: {rep.after} tests")
    print(
        f"renamed by the map: {rep.renamed}, moved between files: {rep.moved}"
    )
    print_section("expected new (from the map)", rep.expected_new)
    print_section("expected removed (from the map)", rep.expected_removed)
    print_section("LOST", rep.lost)
    print_section("DUPLICATED", rep.duplicated)
    print_section("NEW (not in the map)", rep.new)
    print_section("UNUSED map entries", rep.unused)
    if args.quiet_ambiguous:
        print(f"ambiguous keys (count only proven): {len(rep.ambiguous)}")
    else:
        print_section("ambiguous keys (count only proven)", rep.ambiguous)
    failures = rep.failures
    for before_run, after_run in args.results or []:
        problems = compare_results(
            read_results(before_run), read_results(after_run), rmap
        )
        print(
            f"results {before_run.name} -> {after_run.name}: {len(problems)} differences"
        )
        print_section("RESULT differences", problems)
        failures += len(problems)
    print(f"unmapped differences: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

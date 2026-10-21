"""scripts/test_id_map.py - the proof that a test reorganization kept every test, checked on small made-up collections.

The tool is what a reorganization PR shows as its evidence, so a comparison that let a lost, doubled or new test through
would make that evidence worthless. These tests feed it collections and runs directly (no git, no pytest subprocess).

Run: uv run pytest -q tests/test_test_id_map.py
"""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "test_id_map_tool", ROOT / "scripts" / "test_id_map.py"
)
tim = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = (
    tim  # dataclasses look their module up while the file runs
)
spec.loader.exec_module(tim)

BEFORE = [
    "tests/test_a.py::Trash::test_restore",
    "tests/test_b.py::Trash::test_restore",
    "tests/test_a.py::Claim::test_claim",
    "tests/test_a.py::test_module_level",
    "",
    "3 tests collected in 0.01s",
]


def compare(before, after, map_text=""):
    """The report for two collections (lists of id lines) under a rename map text."""
    return tim.compare(
        tim.read_ids(before), tim.read_ids(after), tim.read_map(map_text)
    )


class Collections(unittest.TestCase):
    """Moves are free, renames need the map, and anything else is reported."""

    def test_a_move_between_files_is_not_a_difference(self):
        """The key drops the file: moving a class to another file changes nothing; the move is counted."""
        after = [
            ln.replace("tests/test_a.py::Claim", "tests/test_c.py::Claim")
            for ln in BEFORE
        ]
        rep = compare(BEFORE, after)
        self.assertEqual((rep.failures, rep.moved), (0, 1))

    def test_module_level_tests_are_keyed_by_their_module_stem(self):
        """Moving test_a.py to another directory changes nothing; the same name in another module is a different key."""
        before = ["tests/test_a.py::test_x", "tests/test_b.py::test_x"]
        moved = ["src/pkg/a/tests/test_a.py::test_x", "tests/test_b.py::test_x"]
        rep = compare(before, moved)
        self.assertEqual((rep.failures, rep.moved, rep.ambiguous), (0, 1, []))
        lost = compare(
            before, ["tests/test_b.py::test_x", "tests/test_c.py::test_x"]
        )
        self.assertEqual((len(lost.lost), len(lost.new)), (1, 1))
        renamed = ["tests/test_c.py::test_x", "tests/test_b.py::test_x"]
        self.assertEqual(
            compare(before, renamed, "test_a -> test_c").failures, 0
        )

    def test_a_file_qualified_rename_maps_only_that_files_class(self):
        """'tests/test_b.py::Trash -> TrashApi' renames the one Trash of test_b; the other Trash keeps its name."""
        after = [
            ln.replace("tests/test_b.py::Trash", "tests/test_b.py::TrashApi")
            for ln in BEFORE
        ]
        self.assertEqual(
            compare(
                BEFORE, after, "tests/test_b.py::Trash -> TrashApi"
            ).failures,
            0,
        )
        rep = compare(BEFORE, after)
        self.assertEqual((len(rep.lost), len(rep.new)), (1, 1))

    def test_lost_duplicated_and_new_tests_are_each_reported(self):
        """A dropped test is lost, a second copy of a key is duplicated, an unknown key is new."""
        after = [
            "tests/test_a.py::Trash::test_restore",
            "tests/test_b.py::Trash::test_restore",
            "tests/test_c.py::Trash::test_restore",
            "tests/test_a.py::test_module_level",
            "tests/test_a.py::Claim::test_other",
        ]
        rep = compare(BEFORE, after)
        self.assertEqual(
            [len(rep.lost), len(rep.duplicated), len(rep.new)], [1, 1, 1]
        )
        self.assertIn("Claim::test_claim", rep.lost[0])

    def test_declared_additions_pass_and_unused_map_entries_fail(self):
        """'+ Class' accepts that class's new tests; an entry that matches nothing is itself a failure."""
        after = [*BEFORE, "tests/test_d.py::NewTable::test_row"]
        self.assertEqual(
            compare(BEFORE, after, "+ tests/test_d.py::NewTable").failures, 0
        )
        rep = compare(BEFORE, BEFORE, "Nothing -> Something\n+ Missing")
        self.assertEqual((len(rep.unused), rep.failures), (2, 2))

    def test_a_malformed_map_line_is_a_usage_error(self):
        """A line that is neither a rename, +, - nor ~ entry stops the run with exit status 2."""
        with self.assertRaises(SystemExit) as cm:
            tim.read_map("Claim => Claims")
        self.assertEqual(cm.exception.code, 2)


class Collect(unittest.TestCase):
    """Collecting a tree reads the node ids at any verbosity and refuses an empty collection."""

    def test_ids_are_read_and_an_empty_tree_is_a_usage_error(self):
        """A tree with one test yields its id; a tree without tests stops with exit status 2, not 'no differences'."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "pytest.ini").write_text(
                "[pytest]\naddopts = -v\n", encoding="utf-8"
            )
            with self.assertRaises(SystemExit) as cm:
                tim.collect(root)
            self.assertEqual(cm.exception.code, 2)
            (root / "test_one.py").write_text(
                "def test_x():\n    pass\n", encoding="utf-8"
            )
            self.assertEqual(tim.collect(root), ["test_one.py::test_x"])


JUNIT = """<?xml version="1.0"?><testsuites><testsuite>
<testcase classname="tests.test_a.Trash" name="test_restore"/>
<testcase classname="tests.test_a.Claim" name="test_claim"><skipped/></testcase>
%s</testsuite></testsuites>"""


class Runs(unittest.TestCase):
    """Two runs agree test by test and in their totals, after the declared differences."""

    def write(self, text):
        """A temporary run file holding text."""
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name) / "run.txt"
        p.write_text(text, encoding="utf-8")
        return p

    def test_a_test_that_now_skips_is_named(self):
        """JUnit names every test: a pass turned skip is reported even though the totals of both runs are equal."""
        before = tim.read_results(self.write(JUNIT % ""))
        after = tim.read_results(
            self.write(
                JUNIT.replace(
                    'name="test_restore"/>',
                    'name="test_restore"><skipped/></testcase>',
                )
                % ""
            )
        )
        problems = tim.compare_results(before, after, tim.read_map(""))
        self.assertTrue(
            any(p.startswith("Trash::test_restore") for p in problems), problems
        )

    def test_expected_additions_and_declared_deltas_balance_the_totals(self):
        """A declared new test and a `~` subtest delta are the only totals that may move."""
        new = '<testcase classname="tests.test_d.NewTable" name="test_row"/>'
        junit = tim.compare_results(
            tim.read_results(self.write(JUNIT % "")),
            tim.read_results(self.write(JUNIT % new)),
            tim.read_map("+ tests/test_d.py::NewTable\n~ subtests passed +2"),
        )
        self.assertEqual(
            junit, []
        )  # a total the input does not carry (JUnit has no subtests) is not checked
        before = "PASSED tests/test_a.py::Trash::test_restore\n== 1 passed, 1 skipped, 3 subtests passed in 1.0s ==\n"
        after = before.replace("1 passed", "2 passed").replace(
            "3 subtests", "5 subtests"
        )
        after = "PASSED tests/test_d.py::NewTable::test_row\n" + after
        run = (
            tim.read_results(self.write(before)),
            tim.read_results(self.write(after)),
        )
        self.assertEqual(
            tim.compare_results(
                *run,
                tim.read_map(
                    "+ tests/test_d.py::NewTable\n~ subtests passed +2"
                ),
            ),
            [],
        )
        self.assertEqual(
            tim.compare_results(
                *run, tim.read_map("+ tests/test_d.py::NewTable")
            ),
            ["total subtests passed: expected 3, got 5"],
        )


if __name__ == "__main__":
    unittest.main()

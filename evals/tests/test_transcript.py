"""Finding the script an agent ran from its recorded Bash calls.

The commands are those of the 2026-11-22 sweep (#822), heredoc bodies cut.
"""

from __future__ import annotations

import pytest

from evals import shelltrace

T = "/private/var/folders/nq/2qwnl8nn4yg1g56zdvp1x7vh0000gn/T"
P = f"{T}/dmpl-eval-case-skill-p6ba2v7f"
BODY = "import matplotlib.pyplot as plt\nprint('a > b; c && d')"
UV = "uv run --with dartwork-mpl --with pandas python"

CASES = {
    "in the project": (
        ["ls && head data.csv", "python3 plot.py 2>&1 | tail -5"],
        (f"{P}/plot.py", (), P),
    ),
    "heredoc then absolute path, uv flags, a pipe": (
        [
            f"mkdir -p /tmp/work && cat > /tmp/work/plot.py <<'EOF'\n{BODY}\nEOF\n"
            f"{UV} /tmp/work/plot.py top_products.csv 2>&1 | tail -20"
        ],
        ("/tmp/work/plot.py", ("top_products.csv",), P),
    ),
    "cd there and back": (
        [
            'cd /tmp/work && sed -i \'s/"rev": 1.17/"rev": 1.16/\' plot.py && '
            f'cd - >/dev/null && {UV} /tmp/work/plot.py top_products.csv 2>&1 | grep -v "^dartwork-mpl"'
        ],
        ("/tmp/work/plot.py", ("top_products.csv",), P),
    ),
    "cd X && python plot.py": (
        [
            f"mkdir -p /tmp/work output && cat > /tmp/work/plot.py <<'E'\n{BODY}\nE\n"
            "cp recording.py /tmp/work/ && cd /tmp/work && mkdir -p output && python plot.py"
        ],
        ("/tmp/work/plot.py", (), "/tmp/work"),
    ),
    "a shell variable in the arguments": (
        [
            f"mkdir -p /tmp/lat && cat > /tmp/lat/plot.py <<'EOF'\n{BODY}\nEOF\n"
            f"cd /tmp/lat && P={P} && python3 -I /tmp/lat/plot.py $P/latency.csv $P/latency-distribution && ls $P"
        ],
        (
            "/tmp/lat/plot.py",
            (f"{P}/latency.csv", f"{P}/latency-distribution"),
            "/tmp/lat",
        ),
    ),
    "a patch through python - <<, then the script": (
        [
            f"cd /tmp/s && python3 - <<'E'\n{BODY}\nE\n"
            f"{UV} plot.py {P}/mix.csv 2>&1 | grep -v save: | tail"
        ],
        ("/tmp/s/plot.py", (f"{P}/mix.csv",), "/tmp/s"),
    ),
    "the shell is back in the project on the next call": (
        ["cd /tmp/s && ls -la; head -20 plot.py", "python3 plot.py"],
        (f"{P}/plot.py", (), P),
    ),
    "a subfolder of the project is kept between calls": (
        ["mkdir -p scripts && cd scripts", "python plot.py ../data.csv"],
        (f"{P}/scripts/plot.py", ("../data.csv",), f"{P}/scripts"),
    ),
    "a script beside the project": (
        [
            "mkdir -p ../scripts output 2>/dev/null; cat > /tmp/plot_outlook.py <<'EOF'\n"
            f"{BODY}\nEOF\nuv run python /tmp/plot_outlook.py outlook.csv",
            "cd ../scripts && python3 - <<'E'\n"
            f"{BODY}\nE\ncd ../project && uv run python ../scripts/plot.py rep.csv output/rep-levels-v2 2>&1 | tail",
            "mkdir -p output; uv run python ../scripts/plot_outlook.py outlook.csv",
        ],
        (f"{T}/scripts/plot_outlook.py", ("outlook.csv",), P),
    ),
    "$TMPDIR and ~ are the run's own": (
        ["cd ~ && python3 $TMPDIR/s/plot.py"],
        ("/run/tmp/s/plot.py", (), "/run/home"),
    ),
    "a path only the shell knew stays unresolved": (
        [
            f"D=$(mktemp -d) && cat > $D/stores_plot.py <<'E'\n{BODY}\nE\n"
            "python3 $D/stores_plot.py"
        ],
        ("$D/stores_plot.py", (), P),
    ),
}


@pytest.mark.parametrize("name", CASES)
def test_last_script_run(name: str):
    commands, (script, args, cwd) = CASES[name]
    variables = {"HOME": "/run/home", "TMPDIR": "/run/tmp"}
    run = shelltrace.runs(commands, P, variables)[-1]
    assert (run.script, run.args, run.cwd) == (script, args, cwd)
    assert run.resolved == ("$" not in script)


def test_inline_python_is_not_a_script_run():
    commands = [
        'python -c "import dartwork_mpl as dm; print(dm.__version__)"',
        f"python3 - <<'E'\n{BODY}\nE",
        "uv run dartwork-mpl path",
    ]
    assert shelltrace.runs(commands, P, {}) == []


def test_the_run_keeps_its_own_environment_and_added_packages():
    command = 'MPLBACKEND=Agg uv run --with scipy python plot.py 2>&1 | grep -v "^dartwork"'
    run = shelltrace.runs([command], P, {})[-1]
    assert run.env == (("MPLBACKEND", "Agg"),)
    assert run.packages == ("scipy",)

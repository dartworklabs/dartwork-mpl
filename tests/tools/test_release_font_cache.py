"""Release setup must isolate real mathtext rendering from shared font caches."""

import json
import os
import random
import subprocess
import sys
import textwrap
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _ROOT / ".github" / "workflows" / "release.yml"


def _python(
    code: str, environment: dict[str, str]
) -> subprocess.CompletedProcess:
    """Run real font discovery or rendering in a fresh interpreter."""
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        cwd=_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )


def _release_environment(environment: dict[str, str]) -> dict[str, str]:
    """Execute the release job's early environment setup with real Bash."""
    configured = environment.copy()
    github_env = Path(configured["GITHUB_ENV"])
    github_env.write_text("", encoding="utf-8")
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    for step in workflow["jobs"]["test"]["steps"]:
        script = step.get("run", "")
        if "uv sync" in script:
            break
        if "GITHUB_ENV" in script:
            result = subprocess.run(
                [
                    "bash",
                    "--noprofile",
                    "--norc",
                    "-eo",
                    "pipefail",
                    "-c",
                    script,
                ],
                cwd=_ROOT,
                env=configured,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=60,
                check=False,
            )
            assert result.returncode == 0, result.stderr
            for line in github_env.read_text(encoding="utf-8").splitlines():
                key, separator, value = line.partition("=")
                assert separator, line
                configured[key] = value
    return configured


def test_release_mathtext_uses_own_cache_when_shared_inventory_is_incomplete(
    tmp_path: Path,
) -> None:
    """The actual release setup keeps both original SVG gates off a stale cache."""
    runner_temp = tmp_path / "runner"
    runner_temp.mkdir()
    environment = {
        **os.environ,
        "GITHUB_ENV": str(tmp_path / "github-env"),
        "GITHUB_RUN_ID": "12345",
        "GITHUB_RUN_ATTEMPT": "2",
        "RUNNER_TEMP": str(runner_temp),
        "XDG_CACHE_HOME": str(tmp_path / "shared-cache"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "MPLBACKEND": "Agg",
    }
    environment.pop("MPLCONFIGDIR", None)
    seeded = _python(
        """
        import json
        from pathlib import Path
        import matplotlib
        from matplotlib import font_manager

        manager = font_manager.fontManager
        manager.ttflist = [
            entry for entry in manager.ttflist
            if not entry.name.startswith("STIX") and entry.name != "cmex10"
        ]
        cache = Path(matplotlib.get_cachedir()) / f"fontlist-v{manager.__version__}.json"
        font_manager.json_dump(manager, cache)
        print(json.dumps({"cache": str(cache), "stix": sum(
            entry.name.startswith("STIX") for entry in manager.ttflist
        )}))
        """,
        environment,
    )
    assert seeded.returncode == 0, seeded.stderr
    inventory = json.loads(seeded.stdout)
    assert inventory["stix"] == 0
    shared_cache = Path(inventory["cache"])
    original_cache = shared_cache.read_bytes()

    configured = _release_environment(environment)
    rendered = _python(
        """
        import json
        from pathlib import Path
        import runpy
        import matplotlib

        gates = runpy.run_path("tests/docs/test_font_invariants.py")
        gates["test_mathtext_scientific_matches_body_without_dejavu"]()
        matplotlib.rcdefaults()
        gates["test_mathtext_kr_stays_latin_without_dejavu"]()
        print(json.dumps({"cache": str(Path(matplotlib.get_cachedir()).resolve())}))
        """,
        configured,
    )
    assert rendered.returncode == 0, rendered.stderr
    used_cache = Path(json.loads(rendered.stdout)["cache"])
    assert used_cache.is_relative_to(runner_temp)
    assert used_cache != shared_cache.parent
    assert shared_cache.read_bytes() == original_cache

    # Repeated setup, including repeated job identities, never reuses a cache.
    generator = random.Random(0)
    used_caches = {used_cache}
    for _ in range(8):
        repeated = _release_environment(
            {
                **environment,
                "GITHUB_RUN_ID": str(generator.randint(1, 3)),
                "GITHUB_RUN_ATTEMPT": str(generator.randint(1, 3)),
            }
        )
        selected_cache = Path(repeated["MPLCONFIGDIR"])
        assert selected_cache.is_relative_to(runner_temp)
        assert selected_cache not in used_caches
        used_caches.add(selected_cache)

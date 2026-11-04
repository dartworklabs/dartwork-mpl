"""Installed wheels exercise the same native policy through Python and real MCP clients."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "tests" / "support" / "data_policy_probe.py"
SENTINEL = "DATA_POLICY_NATIVE_ACCEPTANCE_PASSED"


def _run(command, cwd, env):
    """Fail with complete child diagnostics; every child has a bounded lifetime."""
    result = subprocess.run(
        command, cwd=cwd, env=env, capture_output=True, text=True, timeout=180
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


@pytest.fixture(scope="module")
def wheel_runtime(tmp_path_factory):
    """Build actual package inputs once, without traversing repository docs.

    The aggregate's producer docs/_ext/build_hooks.py::_LLMS_FULL_SOURCES
    includes only consumer quickstart/recipes/migration/catalog/gallery sources,
    so copying its opaque bytes cannot copy a restricted design document.
    No aggregate text is inspected, altered or synthesized for this build.
    """
    root = tmp_path_factory.mktemp("data-policy-wheel")
    try:
        project = root / "project"
        project.mkdir()
        for name in (
            "pyproject.toml",
            "README.md",
            "LICENSE",
            "llms.txt",
            "llms-full.txt",
        ):
            shutil.copy2(ROOT / name, project / name)
        shutil.copytree(
            ROOT / "src" / "dartwork_mpl",
            project / "src" / "dartwork_mpl",
            ignore=shutil.ignore_patterns(
                "__pycache__", "tests", "test_*.py", "conftest.py"
            ),
        )
        env = dict(os.environ)
        for name in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
            env.pop(name, None)
        env.update(
            MPLBACKEND="Agg",
            MPLCONFIGDIR=str(root / "matplotlib"),
            DARTWORK_MPL_ARTIFACT_DIR=str(root / "artifacts"),
        )
        env.pop("DARTWORK_MPL_INPUT_POLICY", None)
        _run(
            [
                "uv",
                "build",
                "--wheel",
                "--quiet",
                "--out-dir",
                str(root / "dist"),
            ],
            project,
            env,
        )
        (wheel,) = (root / "dist").glob("*.whl")
        yield {"root": root, "wheel": wheel, "env": env}
    finally:
        shutil.rmtree(root)


@pytest.fixture(scope="module")
def basic_python(wheel_runtime):
    """Install only wheel core requirements in a fresh venv with no inherited packages."""
    root, env = wheel_runtime["root"], wheel_runtime["env"]
    venv = root / "basic"
    _run(["uv", "venv", "--python", sys.executable, str(venv)], root, env)
    python = venv / "bin" / "python"
    _run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            str(wheel_runtime["wheel"]),
        ],
        root,
        env,
    )
    return python


@pytest.fixture(scope="module")
def mcp_python(wheel_runtime):
    """Install MCP extra separately so core-only acceptance cannot inherit it."""
    root, env = wheel_runtime["root"], wheel_runtime["env"]
    venv = root / "mcp"
    _run(["uv", "venv", "--python", sys.executable, str(venv)], root, env)
    python = venv / "bin" / "python"
    _run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            f"{wheel_runtime['wheel']}[mcp]",
        ],
        root,
        env,
    )
    return python


def _check_basic_wheel(wheel_runtime, basic_python):
    """A noneditable core-only installation passes all native probes outside the checkout."""
    source = (
        "import importlib.util, json\n"
        "for optional in ('fastmcp', 'httpx', 'IPython', 'fastapi'):\n"
        "    assert importlib.util.find_spec(optional) is None, optional\n"
        + PROBE.read_text(encoding="utf-8")
        + "\nprint(json.dumps(probe()))\n"
    )
    output = _run(
        [str(basic_python), "-I", "-c", source],
        wheel_runtime["root"],
        wheel_runtime["env"],
    )
    observed = json.loads(output)
    assert observed["policies"] == ["strict", "preserve", "clean", "omitted"]
    assert not Path(observed["package"]).is_relative_to(ROOT)


def _check_installed_mcp(wheel_runtime, mcp_python, transport):
    """Real installed server execution proves assertions before its intentional error sentinel."""
    probe = (
        PROBE.read_text(encoding="utf-8")
        + f"\nprobe()\nraise RuntimeError({SENTINEL!r})\n"
    )
    source = f'''\
import asyncio, json, os, sys
from pathlib import Path
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
import dartwork_mpl as dm
assert Path(dm.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
from dartwork_mpl.mcp.server import mcp

async def observe():
    """Close each real transport and inspect discovery and the complete error framing."""
    transport = {transport!r}
    endpoint = mcp if transport == "inprocess" else StdioTransport(
        command=sys.executable, args=["-I", "-m", "dartwork_mpl.cli"],
        env=dict(os.environ), cwd={str(wheel_runtime["root"])!r}, keep_alive=False,
    )
    async with Client(endpoint) as client:
        before = [tool.model_dump(mode="json") for tool in await client.list_tools()]
        assert len(before) == 19
        result = await client.call_tool("render_plot", {{"code": {probe!r}}}, raise_on_error=False)
        after = [tool.model_dump(mode="json") for tool in await client.list_tools()]
        assert before == after
        payload = result.structured_content
        assert result.is_error is True, payload
        assert payload["schema_version"] == 1, payload
        assert payload["delivery_status"] == "error", payload
        assert payload["error_code"] == "exec_error", payload
        assert payload["message"] == "Plot execution did not complete.", payload
        report = payload["report"]
        assert report["status"] == "exec_error", report
        assert report["validation_complete"] is False, report
        assert report["failed_checks"] == [], report
        assert report["exc_type"] == "RuntimeError", report
        assert report["exc_msg"] == {SENTINEL!r}, report
        assert report["stderr"] == "", report
        assert [json.loads(block.text) for block in result.content if block.type == "text"] == [payload]
        return {{"transport": transport, "native_assertions": "passed", "package": dm.__file__}}

print(json.dumps(asyncio.run(observe())))
'''
    output = _run(
        [str(mcp_python), "-I", "-c", source],
        wheel_runtime["root"],
        wheel_runtime["env"],
    )
    observed = json.loads(output)
    assert observed["transport"] == transport
    assert observed["native_assertions"] == "passed"
    assert not Path(observed["package"]).is_relative_to(ROOT)


def test_installed_wheel_native_policy_across_python_and_mcp(
    wheel_runtime, basic_python, mcp_python
):
    """Run all three required environments on one worker, building the wheel once.

    CI's default xdist distribution may send separate test items to different
    workers; one journey preserves core-only, in-process and stdio scenarios
    without rebuilding or reinstalling the same wheel on three workers.
    """
    print("Runtime stage: core-only installed Python (no optional extras)")
    _check_basic_wheel(wheel_runtime, basic_python)
    print("Runtime stage: installed MCP with in-process client")
    _check_installed_mcp(wheel_runtime, mcp_python, "inprocess")
    print("Runtime stage: installed MCP CLI over stdio")
    _check_installed_mcp(wheel_runtime, mcp_python, "stdio")
    print("Runtime stages passed: core-only Python, MCP in-process, MCP stdio")

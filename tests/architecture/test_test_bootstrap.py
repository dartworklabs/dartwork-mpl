"""Concurrent pytest bootstraps cannot tear the version read by a worker."""

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def bootstrap_project(tmp_path: Path) -> Path:
    """Use the real bootstrap and package with only disposable metadata writes."""
    project = tmp_path / "project"
    project.mkdir()
    shutil.copy2(ROOT / "conftest.py", project / "conftest.py")
    shutil.copy2(ROOT / "pyproject.toml", project / "pyproject.toml")
    (project / "src").symlink_to(ROOT / "src", target_is_directory=True)
    return project


@pytest.mark.parametrize(
    "preexisting", [True, False], ids=["refresh", "first-publication"]
)
def test_concurrent_bootstrap_keeps_parent_and_child_version(
    bootstrap_project: Path, preexisting: bool
) -> None:
    """A worker imports complete metadata while a peer is publishing its copy.

    Pause the peer after its metadata file opens for writing, which truncates
    an existing destination. A real worker import must still agree with a
    fresh subprocess after publication finishes, including the source path.
    """
    project = bootstrap_project
    writer_code = textwrap.dedent(
        """
        import runpy
        import sys
        from pathlib import Path

        original = Path.write_text

        def paused_write(path, data, *args, **kwargs):
            "Pause the real write after opening its destination."
            if path.name != "METADATA":
                return original(path, data, *args, **kwargs)
            with path.open("w", encoding="utf-8") as stream:
                print("metadata-opened", flush=True)
                assert sys.stdin.readline() == "publish\\n"
                return stream.write(data)

        Path.write_text = paused_write
        runpy.run_path(sys.argv[1])
        """
    )
    probe = textwrap.dedent(
        """
        import importlib.metadata
        import json
        import runpy
        import shutil
        import subprocess
        import sys
        from pathlib import Path

        project = Path(sys.argv[1])
        bootstrap = runpy.run_path(str(project / "conftest.py"))
        metadata_path = bootstrap["_METADATA_PATH"]
        preexisting = sys.argv[2] == "True"
        if not preexisting:
            for entry in Path(metadata_path).glob("*.dist-info"):
                shutil.rmtree(entry)
        writer_code = WRITER_CODE
        writer = subprocess.Popen(
            [sys.executable, "-c", writer_code, str(project / "conftest.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            assert writer.stdout.readline() == "metadata-opened\\n"
            exposed = [
                dist.version
                for dist in importlib.metadata.distributions(path=[metadata_path])
            ]
            if preexisting:
                metadata_version = importlib.metadata.version("dartwork-mpl")
                import dartwork_mpl as dm
                parent = {"version": dm.__version__, "source": dm.__file__}
            _, error = writer.communicate("publish\\n", timeout=15)
            assert writer.returncode == 0, error
        finally:
            if writer.poll() is None:
                writer.kill()
                writer.communicate()

        if not preexisting:
            metadata_version = importlib.metadata.version("dartwork-mpl")
            import dartwork_mpl as dm
            parent = {"version": dm.__version__, "source": dm.__file__}
        child_code = (
            "import json; import dartwork_mpl as dm; "
            "print(json.dumps({'version': dm.__version__, 'source': dm.__file__}))"
        )
        child = subprocess.run(
            [sys.executable, "-c", child_code],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        print(json.dumps({
            "expected": bootstrap["_pyproject_version"](),
            "metadata": metadata_version,
            "exposed": exposed,
            "parent": parent,
            "child": json.loads(child.stdout),
        }))
        """
    ).replace("WRITER_CODE", repr(writer_code))
    result = subprocess.run(
        [sys.executable, "-c", probe, str(project), str(preexisting)],
        cwd=project,
        env={**os.environ, "MPLBACKEND": "Agg"},
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["exposed"] == (
        [observed["expected"]] if preexisting else []
    ), observed
    assert observed["metadata"] == observed["expected"], observed
    assert observed["parent"]["version"] == observed["expected"], observed
    assert observed["parent"] == observed["child"], observed


def test_concurrent_version_bump_bootstraps_exclude_stale_metadata(
    bootstrap_project: Path,
) -> None:
    """Two bootstraps survive the same retired version and import the current one."""
    project = bootstrap_project
    old = (
        project
        / ".pytest_cache/dartwork_mpl_metadata/dartwork_mpl-0.0.1.dist-info"
    )
    old.mkdir(parents=True)
    (old / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: dartwork-mpl\nVersion: 0.0.1\n",
        encoding="utf-8",
    )
    old_scoped = old.parent / "0.0.1" / old.name
    old_scoped.mkdir(parents=True)
    shutil.copy2(old / "METADATA", old_scoped / "METADATA")
    stale_pythonpath = os.pathsep.join(
        [str(old_scoped.parent), os.environ.get("PYTHONPATH", "")]
    )
    worker_code = textwrap.dedent(
        """
        import json
        import runpy
        import shutil
        import sys
        from pathlib import Path

        original = shutil.rmtree

        def paused_retirement(path, *args, **kwargs):
            "Let both bootstraps observe the old directory before either removes it."
            if Path(path).name == "dartwork_mpl-0.0.1.dist-info":
                print("retiring", flush=True)
                assert sys.stdin.readline() == "retire\\n"
            return original(path, *args, **kwargs)

        shutil.rmtree = paused_retirement
        bootstrap = runpy.run_path(sys.argv[1])
        import dartwork_mpl as dm
        print(json.dumps({"version": dm.__version__, "expected": bootstrap["_pyproject_version"]()}))
        """
    )
    workers = []
    observed = []
    try:
        for _ in range(2):
            workers.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        worker_code,
                        str(project / "conftest.py"),
                    ],
                    cwd=project,
                    env={
                        **os.environ,
                        "MPLBACKEND": "Agg",
                        "PYTHONPATH": stale_pythonpath,
                    },
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            )
        first_lines = []
        for worker in workers:
            assert worker.stdout is not None
            first_lines.append(worker.stdout.readline())
        for worker, first in zip(workers, first_lines, strict=True):
            output, error = worker.communicate("retire\n", timeout=15)
            assert worker.returncode == 0, error
            observed.append(
                json.loads(output if first == "retiring\n" else first)
            )
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.kill()
                worker.communicate()
    assert len(observed) == 2
    for item in observed:
        assert item["version"] == item["expected"], item
    assert (old / "METADATA").read_text(encoding="utf-8") == (
        "Metadata-Version: 2.1\nName: dartwork-mpl\nVersion: 0.0.1\n"
    )
    assert (old_scoped / "METADATA").read_bytes() == (
        old / "METADATA"
    ).read_bytes()


def test_failed_publication_preserves_metadata_and_peer_staging(
    bootstrap_project: Path,
) -> None:
    """A failed write removes only its staging tree, preserving published bytes."""
    probe = textwrap.dedent(
        """
        import runpy
        import sys
        from pathlib import Path

        bootstrap = runpy.run_path(sys.argv[1])
        root = Path(bootstrap["_METADATA_PATH"])
        metadata, = root.glob("*.dist-info/METADATA")
        published = metadata.read_bytes()
        peer = root / ".metadata-peer"
        peer.mkdir()
        (peer / "owned-by-peer").touch()
        previous = set(root.iterdir())
        original = Path.write_text

        def failed_write(path, data, *args, **kwargs):
            "Fail a real metadata write after partially filling its destination."
            if path.name != "METADATA":
                return original(path, data, *args, **kwargs)
            with path.open("w", encoding="utf-8") as stream:
                stream.write("partial")
            raise OSError("injected metadata publication failure")

        Path.write_text = failed_write
        try:
            runpy.run_path(sys.argv[1])
        except OSError as error:
            assert str(error) == "injected metadata publication failure"
        else:
            raise AssertionError("publication failure was swallowed")
        assert metadata.read_bytes() == published, "published metadata changed"
        assert set(root.iterdir()) == previous, "owned staging was not cleaned"
        assert (peer / "owned-by-peer").is_file(), "peer staging was removed"
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", probe, str(bootstrap_project / "conftest.py")],
        cwd=bootstrap_project,
        env={**os.environ, "MPLBACKEND": "Agg"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr

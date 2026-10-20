"""Repository-specific import gates protect artifact, execution and core surfaces."""

import ast
import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytest.importorskip("fastmcp")
ROOT = Path(__file__).resolve().parents[3] / "src" / "dartwork_mpl"
# Named retained edges: old MCP handlers/assets/prompts/resources and CLI wiring.
LEGACY = {
    "dartwork_mpl.mcp.tools",
    "dartwork_mpl.mcp.resources",
    "dartwork_mpl.mcp.prompts",
    "dartwork_mpl.mcp._assets",
}
ALLOWED = {
    ("artifacts", "execution"),
    ("legacy", "execution"),
    ("wiring", "artifacts"),
    ("wiring", "legacy"),
}
PURE = {
    "dartwork_mpl.mcp.artifacts.policy",
    "dartwork_mpl.mcp.artifacts.input_policy",
}


def slice_of(module):
    """Assign concrete repository modules to capability or existing-layer roles."""
    if module.startswith("dartwork_mpl.mcp.artifacts"):
        return "artifacts"
    if module == "dartwork_mpl.mcp.execution":
        return "execution"
    if module in LEGACY:
        return "legacy"
    if module in {
        "dartwork_mpl.mcp",
        "dartwork_mpl.mcp.server",
        "dartwork_mpl.cli",
    }:
        return "wiring"
    return "core"


def imports_and_surfaces():
    """Parse every production import and declared surface without importing MCP."""
    trees = {}
    for path in ROOT.rglob("*.py"):
        if "asset" in path.parts:
            continue
        relative = path.relative_to(ROOT.parent).with_suffix("")
        parts = (
            relative.parts[:-1]
            if relative.name == "__init__"
            else relative.parts
        )
        tree = ast.parse(path.read_text())
        if path.name == "execution.py":
            # The shared runner intentionally embeds Python for its one child.
            for node in tuple(ast.walk(tree)):
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and "matplotlib.use" in node.value
                ):
                    child = textwrap.dedent(node.value).format(
                        figure_var="fig", chart_type_hint=None, output_stem=None
                    )
                    tree.body.extend(ast.parse(child).body)
        trees[".".join(parts)] = tree
    surfaces = {}
    edges = []
    for module, tree in trees.items():
        exports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__"
                for t in node.targets
            ):
                exports.update(ast.literal_eval(node.value))
            if isinstance(node, ast.Import):
                edges.extend((module, alias.name, None) for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                package = (
                    module
                    if module in trees
                    and any(
                        isinstance(n, ast.ImportFrom) and n.level
                        for n in tree.body
                    )
                    and (
                        ROOT.parent.joinpath(*module.split(".")) / "__init__.py"
                    ).exists()
                    else module.rpartition(".")[0]
                )
                target = (
                    importlib.util.resolve_name(
                        "." * node.level + (node.module or ""), package
                    )
                    if node.level
                    else node.module or ""
                )
                for alias in node.names:
                    destination = target + "." + alias.name
                    edges.append(
                        (
                            module,
                            destination if destination in trees else target,
                            None if destination in trees else alias.name,
                        )
                    )
        surfaces[module] = exports
    return edges, surfaces


def assert_boundaries(edges, surfaces):
    """Count dependency paths, enforce public surfaces and reject decision leaks."""
    graph = {}
    for source, target, name in edges:
        if not target.startswith("dartwork_mpl"):
            if source in PURE:
                assert target.split(".")[0] in {
                    "hashlib",
                    "json",
                    "keyword",
                    "math",
                    "re",
                    "collections",
                    "dataclasses",
                    "datetime",
                    "enum",
                    "types",
                    "typing",
                }
            if slice_of(source) == "core":
                assert target.split(".")[0] not in {"fastmcp", "mcp"}
            continue
        first, second = slice_of(source), slice_of(target)
        graph.setdefault(source, set()).add(target)
        if source in PURE:
            assert target == "dartwork_mpl.mcp.artifacts.policy", (
                "decision dependency",
                source,
                target,
            )
        if first == second:
            continue
        if second == "core":
            # Existing public APIs used by execution and retained MCP handlers.
            if first in {"artifacts", "execution"}:
                assert target in {"dartwork_mpl", "dartwork_mpl.lint"}, (
                    source,
                    target,
                )
                assert name in surfaces.get(target, set()), (
                    source,
                    target,
                    name,
                )
            continue
        assert (first, second) in ALLOWED, (
            "unlisted dependency",
            source,
            target,
        )
        if second in {"artifacts", "execution"}:
            expected = (
                "dartwork_mpl.mcp.artifacts"
                if second == "artifacts"
                else "dartwork_mpl.mcp.execution"
            )
            assert target == expected and name in surfaces[target], (
                "private surface",
                source,
                target,
                name,
            )

    # Shared/core modules cannot reach a feature indirectly through another core.
    def visit(module, seen):
        """Walk complete paths, retaining core reachability through shared modules."""
        if module in seen:
            return
        seen.add(module)
        for target in graph.get(module, ()):
            assert slice_of(target) == "core", (
                "core reaches feature",
                module,
                target,
            )
            visit(target, seen)

    for module in graph:
        if slice_of(module) == "core":
            visit(module, set())
    feature_edges = {
        (slice_of(s), slice_of(t))
        for s, t, _ in edges
        if slice_of(s) != slice_of(t)
        and slice_of(s) in {"artifacts", "execution"}
        and slice_of(t) in {"artifacts", "execution"}
    }
    assert not (
        {("artifacts", "execution"), ("execution", "artifacts")}
        <= feature_edges
    ), "feature cycle"


def test_repository_imports_preserve_surfaces():
    """Every production module participates in the same import-path check."""
    assert_boundaries(*imports_and_surfaces())


@pytest.mark.parametrize(
    "edges",
    [
        [
            (
                "dartwork_mpl.mcp.tools",
                "dartwork_mpl.mcp.artifacts.store",
                "ArtifactStore",
            )
        ],
        [
            ("dartwork_mpl.shared", "dartwork_mpl.bridge", None),
            (
                "dartwork_mpl.bridge",
                "dartwork_mpl.mcp.execution",
                "validate_plot",
            ),
        ],
        [
            (
                "dartwork_mpl.mcp.artifacts.delivery",
                "dartwork_mpl.mcp.execution",
                "export_plot",
            ),
            (
                "dartwork_mpl.mcp.execution",
                "dartwork_mpl.mcp.artifacts",
                "render_artifact",
            ),
        ],
        [
            (
                "dartwork_mpl.mcp.resources",
                "dartwork_mpl.mcp.artifacts",
                "get_artifact",
            )
        ],
        [
            (
                "dartwork_mpl.mcp.artifacts.policy",
                "dartwork_mpl.mcp.execution",
                "validate_plot",
            )
        ],
    ],
)
def test_five_injected_boundary_violations_are_rejected(edges):
    """Private import, indirect shared path, cycle, missing edge and policy leak fail."""
    _, surfaces = imports_and_surfaces()
    with pytest.raises(AssertionError):
        assert_boundaries(edges, surfaces)


def test_legal_in_slice_import_is_accepted():
    """Private modules stay usable within their owning artifact slice."""
    assert_boundaries(
        [
            (
                "dartwork_mpl.mcp.artifacts.delivery",
                "dartwork_mpl.mcp.artifacts.policy",
                "RenderRequest",
            ),
            (
                "dartwork_mpl.mcp.artifacts.input_policy",
                "dartwork_mpl.mcp.artifacts.policy",
                "ArtifactId",
            ),
        ],
        {},
    )


def test_core_remains_importable_without_fastmcp():
    """A fresh interpreter refusing MCP can still load the complete core library."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys\nsys.modules['fastmcp'] = None\nimport dartwork_mpl\nprint('core imported')",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "core imported"


@pytest.mark.parametrize("module", ["policy", "input_policy"])
@pytest.mark.parametrize(
    "target",
    [
        "os",
        "pathlib",
        "subprocess",
        "io",
        "fastmcp",
        "dartwork_mpl.mcp.artifacts.store",
        "dartwork_mpl.mcp.execution",
    ],
)
def test_pure_policy_import_violations_are_rejected(module, target):
    """Both pure modules reject I/O and shell dependencies, even inside artifacts."""
    with pytest.raises(AssertionError):
        assert_boundaries(
            [(f"dartwork_mpl.mcp.artifacts.{module}", target, None)], {}
        )

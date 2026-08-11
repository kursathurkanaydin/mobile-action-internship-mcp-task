import ast
from pathlib import Path

import mcp_task.tools as tools_pkg

_TOOLS_DIR = Path(tools_pkg.__file__).parent

# charts.py files intentionally skip @handle_tool_errors and raise
# FastMCPToolError instead, since a chart with no data has nothing
# meaningful to return as a result dict (see errors.py's handle_tool_errors
# docstring and README's "Error handling" section).
_HANDLE_TOOL_ERRORS_EXEMPT_FILENAMES = {"charts.py"}


def _decorator_name(node: ast.expr) -> str | None:
    """Best-effort dotted name for a decorator, e.g. "mcp.tool" or "handle_tool_errors"."""
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute):
        base = _decorator_name(target.value)
        return f"{base}.{target.attr}" if base else target.attr
    if isinstance(target, ast.Name):
        return target.id
    return None


def _iter_mcp_tool_functions():
    """Yield (relative_path, function_name, decorator_names) for every @mcp.tool-decorated function."""
    for path in sorted(_TOOLS_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorator_names = {_decorator_name(deco) for deco in node.decorator_list}
            if "mcp.tool" not in decorator_names:
                continue
            yield path.relative_to(_TOOLS_DIR), node.name, decorator_names


class TestNoDuplicateToolNames:
    def test_every_mcp_tool_function_name_is_unique_across_the_project(self):
        # FastMCP tool names are global across the whole server, not
        # namespaced by module - two @mcp.tool functions with the same name
        # in different files silently overwrite each other in the registry
        # (only a runtime warning, easy to miss). This bit the project once
        # already (compare_keyword_ranking_history), hence this static check.
        seen: dict[str, Path] = {}
        collisions = []
        for relative_path, name, _decorators in _iter_mcp_tool_functions():
            if name in seen:
                collisions.append((name, seen[name], relative_path))
            else:
                seen[name] = relative_path

        assert not collisions, (
            "Duplicate @mcp.tool function name(s) found - each of these "
            "silently overwrites the other in FastMCP's registry: "
            + ", ".join(f"'{name}' in {first} and {second}" for name, first, second in collisions)
        )


class TestHandleToolErrorsCoverage:
    def test_every_mcp_tool_function_handles_its_own_errors(self):
        # Every data tool is expected to be wrapped with @handle_tool_errors
        # so an unanticipated exception can't leak a raw traceback to the
        # model instead of a clean error dict - see errors.py's
        # handle_tool_errors docstring. charts.py is the one deliberate
        # exception (see module docstring above).
        missing = [
            (relative_path, name)
            for relative_path, name, decorators in _iter_mcp_tool_functions()
            if "handle_tool_errors" not in decorators
            and relative_path.name not in _HANDLE_TOOL_ERRORS_EXEMPT_FILENAMES
        ]

        assert not missing, (
            "@mcp.tool function(s) missing @handle_tool_errors (and not in "
            f"a charts.py file): {', '.join(f'{name} in {path}' for path, name in missing)}"
        )


class TestWithCreditUsageCoverage:
    def test_every_mcp_tool_function_surfaces_credit_usage(self):
        # Every tool (data tool or chart tool) is expected to be wrapped
        # with @with_credit_usage so the credit_cost/credit_remaining spent
        # by the call is visible in the response, not just server logs -
        # see errors.py's with_credit_usage docstring. Unlike
        # @handle_tool_errors, there's no charts.py exemption here.
        missing = [
            (relative_path, name)
            for relative_path, name, decorators in _iter_mcp_tool_functions()
            if "with_credit_usage" not in decorators
        ]

        assert not missing, (
            "@mcp.tool function(s) missing @with_credit_usage: "
            f"{', '.join(f'{name} in {path}' for path, name in missing)}"
        )

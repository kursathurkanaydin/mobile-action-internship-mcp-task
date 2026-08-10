import pytest

from mcp_task.errors import ToolError, handle_tool_errors, to_error_response


class TestToolError:
    def test_message_and_status_code_are_stored(self):
        exc = ToolError("bad thing happened", status_code=429)
        assert exc.message == "bad thing happened"
        assert exc.status_code == 429

    def test_status_code_defaults_to_none(self):
        exc = ToolError("bad input")
        assert exc.status_code is None

    def test_is_a_regular_exception(self):
        assert isinstance(ToolError("x"), Exception)

    def test_error_type_defaults_to_internal(self):
        assert ToolError("x").error_type == "internal"

    def test_error_type_can_be_overridden_per_instance(self):
        assert ToolError("x", error_type="network").error_type == "network"

    def test_subclass_can_set_a_class_level_default(self):
        class CustomError(ToolError):
            error_type = "validation"

        assert CustomError("x").error_type == "validation"

    def test_per_instance_override_wins_over_class_default(self):
        class CustomError(ToolError):
            error_type = "validation"

        assert CustomError("x", error_type="network").error_type == "network"


class TestToErrorResponse:
    def test_shapes_message_status_code_and_error_type(self):
        exc = ToolError("rate limited", status_code=429, error_type="upstream_api")
        assert to_error_response(exc) == {"error": "rate limited", "status_code": 429, "error_type": "upstream_api"}

    def test_status_code_is_none_when_not_set(self):
        exc = ToolError("bad input")
        assert to_error_response(exc) == {"error": "bad input", "status_code": None, "error_type": "internal"}

    def test_works_for_subclasses(self):
        class CustomError(ToolError):
            error_type = "validation"

        exc = CustomError("custom failure")
        assert to_error_response(exc) == {"error": "custom failure", "status_code": None, "error_type": "validation"}


class TestHandleToolErrors:
    def test_successful_call_passes_through_unchanged(self):
        @handle_tool_errors
        def fn(x):
            return {"x": x}

        assert fn(5) == {"x": 5}

    def test_tool_error_is_converted_via_to_error_response(self):
        @handle_tool_errors
        def fn():
            raise ToolError("bad input", status_code=429, error_type="upstream_api")

        assert fn() == {"error": "bad input", "status_code": 429, "error_type": "upstream_api"}

    def test_unexpected_exception_is_caught_and_converted_too(self):
        # e.g. a KeyError from an unexpectedly-shaped API response, or a
        # third-party library raising something outside its documented
        # error types — must not leak a raw exception to the caller.
        @handle_tool_errors
        def fn():
            raise KeyError("trackId")

        result = fn()
        assert "error" in result
        assert "trackId" in result["error"]
        assert result["status_code"] is None
        assert result["error_type"] == "internal"

    def test_preserves_function_name_and_docstring(self):
        @handle_tool_errors
        def my_tool(x: int) -> dict:
            """My tool docstring."""
            return {"x": x}

        assert my_tool.__name__ == "my_tool"
        assert my_tool.__doc__ == "My tool docstring."

    def test_preserves_signature_for_introspection(self):
        # FastMCP inspects the wrapped function's signature to build the
        # tool's schema, so functools.wraps' __wrapped__ chain must hold.
        import inspect

        @handle_tool_errors
        def my_tool(x: int, y: str = "default") -> dict:
            return {"x": x, "y": y}

        sig = inspect.signature(my_tool)
        assert list(sig.parameters) == ["x", "y"]
        assert sig.parameters["y"].default == "default"

    def test_reraises_are_not_needed_args_and_kwargs_pass_through(self):
        @handle_tool_errors
        def fn(a, b, c=3):
            return a + b + c

        assert fn(1, 2) == 6
        assert fn(1, b=2, c=10) == 13


@pytest.mark.parametrize("bad_exc", [KeyError("k"), TypeError("t"), ValueError("v"), AttributeError("a")])
def test_handle_tool_errors_catches_any_exception_type(bad_exc):
    @handle_tool_errors
    def fn():
        raise bad_exc

    result = fn()
    assert result["error"].startswith("Unexpected internal error:")
    assert result["status_code"] is None

from mcp_task.errors import ToolError, to_error_response


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


class TestToErrorResponse:
    def test_shapes_message_and_status_code(self):
        exc = ToolError("rate limited", status_code=429)
        assert to_error_response(exc) == {"error": "rate limited", "status_code": 429}

    def test_status_code_is_none_when_not_set(self):
        exc = ToolError("bad input")
        assert to_error_response(exc) == {"error": "bad input", "status_code": None}

    def test_works_for_subclasses(self):
        class CustomError(ToolError):
            pass

        exc = CustomError("custom failure")
        assert to_error_response(exc) == {"error": "custom failure", "status_code": None}

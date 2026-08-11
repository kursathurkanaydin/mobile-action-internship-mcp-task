import logging

import pytest

from mcp_task import logging_config


class TestConfigureLogging:
    @pytest.fixture(autouse=True)
    def _restore_real_logging_after(self):
        yield
        logging_config.configure_logging()

    def test_creates_the_log_directory(self, tmp_path):
        log_dir = tmp_path / "logs"
        logging_config.configure_logging(log_dir=log_dir)
        assert log_dir.is_dir()

    def test_writes_a_log_line_to_the_file(self, tmp_path):
        log_dir = tmp_path / "logs"
        logging_config.configure_logging(log_dir=log_dir)

        logging.getLogger("mcp_task.test").info("hello from a test")

        assert "hello from a test" in (log_dir / "mcp_task.log").read_text()

    def test_info_level_messages_are_captured_not_suppressed(self, tmp_path):
        # the bug this whole feature fixes: without configure_logging(),
        # Python's default handler only surfaces WARNING and above, so an
        # info() call (e.g. the credit-cost log) was invisible everywhere.
        log_dir = tmp_path / "logs"
        logging_config.configure_logging(log_dir=log_dir, level="INFO")

        logging.getLogger("mcp_task.test").info("credit_cost=10")

        assert "credit_cost=10" in (log_dir / "mcp_task.log").read_text()

    def test_is_idempotent_does_not_stack_duplicate_handlers(self, tmp_path):
        log_dir = tmp_path / "logs"
        logging_config.configure_logging(log_dir=log_dir)
        logging_config.configure_logging(log_dir=log_dir)

        assert len(logging.getLogger("mcp_task").handlers) == 2

    def test_does_not_touch_the_root_or_third_party_loggers(self, tmp_path):
        # third-party libraries (httpx in particular) log full request URLs
        # at INFO, including the MobileAction API token as a query param -
        # only "mcp_task"'s own logger should be configured, not root,
        # or that would leak into the log file.
        log_dir = tmp_path / "logs"
        root_handlers_before = list(logging.getLogger().handlers)

        logging_config.configure_logging(log_dir=log_dir)

        assert logging.getLogger().handlers == root_handlers_before
        assert logging.getLogger("httpx").handlers == []

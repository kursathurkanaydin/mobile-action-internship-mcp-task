from mcp_task import credit_tracking


class TestCreditTracking:
    def test_pop_returns_none_when_nothing_recorded(self):
        credit_tracking.reset()
        assert credit_tracking.pop() is None

    def test_record_then_pop_returns_the_recorded_values_as_ints(self):
        credit_tracking.reset()
        credit_tracking.record(cost="10", remaining="48230")
        assert credit_tracking.pop() == {"credit_cost": 10, "credit_remaining": 48230}

    def test_reset_clears_a_previously_recorded_value(self):
        credit_tracking.record(cost="10", remaining="48230")
        credit_tracking.reset()
        assert credit_tracking.pop() is None

    def test_a_second_record_accumulates_cost_and_keeps_the_latest_remaining(self):
        # e.g. a tool that fans out to N apps makes N API calls - the total
        # cost paid is the sum of every call, but remaining is already a
        # running account balance, so only the latest snapshot is accurate.
        credit_tracking.reset()
        credit_tracking.record(cost="10", remaining="100")
        credit_tracking.record(cost="20", remaining="80")
        assert credit_tracking.pop() == {"credit_cost": 30, "credit_remaining": 80}

    def test_unparseable_cost_does_not_corrupt_the_running_total(self):
        credit_tracking.reset()
        credit_tracking.record(cost="10", remaining="100")
        credit_tracking.record(cost=None, remaining="90")
        assert credit_tracking.pop() == {"credit_cost": 10, "credit_remaining": 90}

    def test_unparseable_remaining_is_recorded_as_none(self):
        credit_tracking.reset()
        credit_tracking.record(cost="10", remaining=None)
        assert credit_tracking.pop() == {"credit_cost": 10, "credit_remaining": None}

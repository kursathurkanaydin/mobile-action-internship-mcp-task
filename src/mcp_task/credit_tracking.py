import contextvars

# Passes the credit_cost/credit_remaining spent during a tool call from
# clients/mobileaction.py (the producer) to errors.py's with_credit_usage
# decorator (the consumer) without either module knowing about the other.
# A contextvars.ContextVar rather than a plain module global, since FastMCP
# can run multiple tool calls concurrently as separate asyncio tasks - a
# plain global would let one call's credit info leak into another's
# response.
_last_credit_usage: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "_last_credit_usage", default=None
)


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def reset() -> None:
    """Clear any recorded credit usage - call before starting a new tool call."""
    _last_credit_usage.set(None)


def record(cost: str | None, remaining: str | None) -> None:
    """Record the credits spent by one MobileAction API call.

    credit_cost accumulates across every call made during the current tool
    invocation - a tool that fans out to several apps/stores (e.g.
    comparing 5 apps' ranking history makes one API call per app) actually
    spends the sum of each call's cost, not just the last one.
    credit_remaining is kept as the latest value instead: MobileAction
    already reports it as a running account balance rather than a per-call
    amount, so the most recent snapshot is the accurate one.
    """
    previous = _last_credit_usage.get()
    previous_cost = previous["credit_cost"] if previous else 0
    this_cost = _parse_int(cost)
    total_cost = previous_cost + this_cost if this_cost is not None else previous_cost

    _last_credit_usage.set({"credit_cost": total_cost, "credit_remaining": _parse_int(remaining)})


def pop() -> dict | None:
    """Return the credit usage accumulated so far, or None if no API call recorded any."""
    return _last_credit_usage.get()

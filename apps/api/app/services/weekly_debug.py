import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


def weekly_debug_enabled() -> bool:
    return os.getenv("NUTRIFLOW_WEEKLY_DEBUG", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def weekly_debug_verbose_enabled() -> bool:
    return weekly_debug_enabled() and os.getenv(
        "NUTRIFLOW_WEEKLY_DEBUG_VERBOSE",
        "",
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def weekly_debug(category: str, event: str, /, **fields: Any) -> None:
    if not weekly_debug_enabled():
        return
    details = " ".join(
        f"{key}={value}"
        for key, value in fields.items()
        if value is not None
    )
    suffix = f" {details}" if details else ""
    print(f"[{category}] {event}{suffix}", flush=True)


@contextmanager
def weekly_debug_span(
    category: str,
    event: str,
    /,
    **fields: Any,
) -> Iterator[None]:
    if not weekly_debug_enabled():
        yield
        return

    started = time.perf_counter()
    weekly_debug(category, f"START {event}", **fields)
    try:
        yield
    except Exception as exc:
        weekly_debug(
            category,
            f"ERROR {event}",
            elapsed_s=f"{time.perf_counter() - started:.3f}",
            error_type=type(exc).__name__,
            error=str(exc),
            **fields,
        )
        raise
    weekly_debug(
        category,
        f"END {event}",
        elapsed_s=f"{time.perf_counter() - started:.3f}",
        **fields,
    )

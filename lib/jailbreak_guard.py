"""Input guard: jailbreak detection via guardrails-ai hub://guardrails/detect_jailbreak.

The guard is initialised lazily on first use. If the validator is not installed
(e.g. `guardrails hub install` not yet run) the check is silently skipped so
the rest of the pipeline is unaffected.

Install steps:
    guardrails configure          # paste token from hub.guardrailsai.com/keys
    guardrails hub install hub://guardrails/detect_jailbreak
"""
from __future__ import annotations

import asyncio
from typing import Any

_guard: Any = None
_guard_available: bool | None = None  # None = not yet attempted


def _build_guard() -> Any:
    from guardrails import Guard
    from guardrails.hub import DetectJailbreak  # type: ignore[import]
    return Guard().use(DetectJailbreak(threshold=0.78, on_fail="exception"))


def _get_guard() -> Any | None:
    global _guard, _guard_available
    if _guard_available is False:
        return None
    if _guard is not None:
        return _guard
    try:
        _guard = _build_guard()
        _guard_available = True
        print("[JAILBREAK] Guard initialised")
    except Exception as exc:
        _guard_available = False
        print(f"[JAILBREAK] Guard unavailable — skipping (run 'guardrails hub install hub://guardrails/detect_jailbreak'): {exc}")
    return _guard


def warmup() -> None:
    """Pre-load the guard at startup so first-request latency is not affected."""
    _get_guard()


async def is_jailbreak(text: str) -> bool:
    """Return True if the text is detected as a jailbreak attempt.

    Runs the synchronous guardrails validate() in a thread-pool executor so the
    async event loop is not blocked.
    """
    guard = _get_guard()
    if guard is None:
        return False
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, lambda: guard.validate(text))
        return False
    except Exception:
        return True

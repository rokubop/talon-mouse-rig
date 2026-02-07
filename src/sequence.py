"""Sequence runner for chaining rig actions with async awareness"""

from talon import cron
from .builder import RigBuilder


class WaitHandle:
    """Handle returned by wait() that fires .then() after a delay"""

    def __init__(self, ms: float):
        self._callbacks = []
        cron.after(f"{int(ms)}ms", self._on_complete)

    def _on_complete(self):
        for cb in self._callbacks:
            try:
                cb()
            except Exception as e:
                print(f"Error in wait callback: {e}")

    def then(self, callback):
        self._callbacks.append(callback)
        return self


def _has_async_lifecycle(result):
    """Check if a RigBuilder has an async lifecycle (over/hold/revert > 0)"""
    if isinstance(result, RigBuilder):
        c = result.config
        return ((c.over_ms is not None and c.over_ms > 0) or
                (c.hold_ms is not None and c.hold_ms > 0) or
                (c.revert_ms is not None and c.revert_ms > 0))
    return False


def run_sequence(steps: list):
    """Run a sequence of steps, waiting for rig animations between steps.

    Each step is a callable (lambda/function). If a step returns a RigBuilder
    with an async lifecycle (over/hold/revert), the sequence waits for its
    animation to complete before running the next step. If a step returns a
    handle-like object with .then() (StopHandle, WaitHandle), it waits for
    that to complete. Otherwise continues immediately.
    """
    def run_step(i):
        if i >= len(steps):
            return
        result = steps[i]()
        if result is not None and hasattr(result, 'then'):
            if isinstance(result, RigBuilder):
                if _has_async_lifecycle(result):
                    result.then(lambda: run_step(i + 1))
                    result.run()
                else:
                    result.run()
                    run_step(i + 1)
            else:
                # Handle-like (StopHandle, WaitHandle, etc.) - already executing
                result.then(lambda: run_step(i + 1))
        else:
            run_step(i + 1)

    run_step(0)

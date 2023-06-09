import asyncio

import pytest

import wait_for2
from tests.common.constants import (
    BUILTIN_PREFERS_TIMEOUT_OVER_RESULT,
    BUILTIN_PREFERS_TIMEOUT_OVER_EXCEPTION,
    BUILTIN_PROPAGATES_CUSTOM_CANCEL,
)


async def _result_at_cancel(result, delay=0.0):
    # WARNING: this should not be something to do normally, but this reliably produces a race condition state.
    try:
        while True:
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        await asyncio.sleep(delay)
        return result


async def _exception_at_cancel(error, delay=0.0):
    # WARNING: this should not be something to do normally, but this reliably produces a race condition state.
    try:
        while True:
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        await asyncio.sleep(delay)
        raise error


@pytest.mark.asyncio
async def test_result_after_cancel_builtin():
    # 1. At natural timeout, a result or exception should be prioritized.
    sentinel = object()
    if BUILTIN_PREFERS_TIMEOUT_OVER_RESULT:
        # Builtin prioritizes timeout even if result is received.
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(_result_at_cancel(sentinel), timeout=0.5)
    else:
        # Builtin returns result instead of the timeout.
        assert await asyncio.wait_for(_result_at_cancel(sentinel), timeout=0.5) is sentinel
    sentinel_error = Exception()
    if BUILTIN_PREFERS_TIMEOUT_OVER_EXCEPTION:
        # Builtin prioritizes timeout even if error is raised.
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(_exception_at_cancel(sentinel_error), timeout=0.5)
    else:
        # Builtin propagates an error instead of the timeout.
        try:
            await asyncio.wait_for(_exception_at_cancel(sentinel_error), timeout=0.5)
        except Exception as e:
            assert sentinel_error is e
        else:
            assert False, "did not raise"

    # NOTE: At natural timeout, if an explicit cancellation occurs, the cancellation should have priority, even though
    # the result will be lost due to the lack of support for handling the race-condition.


@pytest.mark.asyncio
async def test_result_after_cancel_wf2():
    handled = []

    def race_handler(r, ex):
        handled.append((r, ex))

    def race_handler2(r, ex):
        handled.append((r, ex))
        raise Exception("This will be logged and not propagated.")

    sentinel = object()
    sentinel_error = Exception()

    # 1. At natural timeout, a result or exception is prioritized.
    assert await wait_for2.wait_for(_result_at_cancel(sentinel), timeout=0.5, race_handler=race_handler) is sentinel
    try:
        await wait_for2.wait_for(_exception_at_cancel(sentinel_error), timeout=0.5, race_handler=race_handler)
    except Exception as e:
        assert sentinel_error is e
    else:
        assert False, "did not raise"
    assert not handled

    for rh in [race_handler, race_handler2]:
        # 2. At natural timeout, if an explicit cancellation occurs, the cancellation will have priority.
        try:
            wf = asyncio.create_task(
                wait_for2.wait_for(_result_at_cancel(sentinel, delay=0.5), timeout=0.5, race_handler=rh)
            )
            await asyncio.sleep(0.75)
            wf.cancel()
            await wf
        except wait_for2.CancelledWithResultError:
            assert BUILTIN_PROPAGATES_CUSTOM_CANCEL, "task does not propagate the custom exception"
        except asyncio.CancelledError:
            assert not BUILTIN_PROPAGATES_CUSTOM_CANCEL, "custom exception should be propagated"
        else:
            assert False, "did not raise"
        assert handled == [(sentinel, False)]
        del handled[:]

        try:
            wf = asyncio.create_task(
                wait_for2.wait_for(_exception_at_cancel(sentinel_error, delay=0.5), timeout=0.5, race_handler=rh)
            )
            await asyncio.sleep(0.75)
            wf.cancel()
            await wf
        except wait_for2.CancelledWithResultError:
            assert BUILTIN_PROPAGATES_CUSTOM_CANCEL, "task does not propagate the custom exception"
        except asyncio.CancelledError:
            assert not BUILTIN_PROPAGATES_CUSTOM_CANCEL, "custom exception should be propagated"
        else:
            assert False, "did not raise"
        assert handled == [(sentinel_error, True)]
        del handled[:]

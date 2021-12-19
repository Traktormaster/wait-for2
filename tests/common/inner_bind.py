import asyncio
from typing import Optional


async def _inner_bind_behaviour_check(wait_for_impl, timeout, before_timeout: Optional[bool]):
    inner_running = asyncio.Event()
    inner_quiting = asyncio.Event()

    async def _inner():
        try:
            if not inner_running.is_set():
                inner_running.set()
            while True:
                try:
                    await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    # simulate long shutdown here to allow hitting timeout-handling edge cases
                    await asyncio.sleep(0.5)
                    raise
        finally:
            inner_quiting.set()

    async def _waiter():
        inner_ = asyncio.create_task(_inner())
        await inner_running.wait()  # ensure the inner task gets started
        await wait_for_impl(inner_, timeout=timeout)

    w = asyncio.create_task(_waiter())
    await inner_running.wait()
    await asyncio.sleep(0.001)  # ensure waiter enters wait-for impl
    if timeout is None:
        # before_timeout is not applicable in this case
        w.cancel()
        try:
            await w
        except asyncio.CancelledError:
            stop_behaviour = "cancelled"
            inner_bound = inner_quiting.is_set()
        except asyncio.TimeoutError:  # pragma: no cover
            assert False, "there is no timeout here"
        else:
            assert False, "cancellation shall not be ignored"
        if not inner_bound:
            await inner_quiting.wait()
    else:
        if before_timeout is not None:
            if timeout == 0:
                if not before_timeout:
                    await asyncio.sleep(0.1)
                    # w must be in timeout-handling because of the idle sleep here
            else:
                if not before_timeout:
                    await asyncio.sleep(0.2 + timeout)
                else:
                    await asyncio.sleep(0.5 * timeout)
            w.cancel()
        try:
            await w
        except asyncio.CancelledError:
            stop_behaviour = "cancelled"
            inner_bound = inner_quiting.is_set()
        except asyncio.TimeoutError:
            stop_behaviour = "timeout"
            inner_bound = inner_quiting.is_set()
        else:
            assert False, "w shall be guaranteed to raise cancellation, there is no timeout here"
        if not inner_bound:
            await inner_quiting.wait()

    return "%s %s" % (stop_behaviour, "bound" if inner_bound else "unbound")


async def inner_bind_behaviour_check(wait_for_impl):
    """
    Return a string describing the behaviour for each timeout-handling case, with the result of the wait-for
    implementation and if the inner future's life was bound to it.
    """
    return [
        "no timeout                 : " + await _inner_bind_behaviour_check(wait_for_impl, None, False),
        "no wait, cancel before     : " + await _inner_bind_behaviour_check(wait_for_impl, 0, True),
        "no wait, cancel after      : " + await _inner_bind_behaviour_check(wait_for_impl, 0, False),
        "no wait, no cancel         : " + await _inner_bind_behaviour_check(wait_for_impl, 0, None),
        "some timeout, cancel before: " + await _inner_bind_behaviour_check(wait_for_impl, 1.0, True),
        "some timeout, cancel after : " + await _inner_bind_behaviour_check(wait_for_impl, 1.0, False),
        "some timeout, no cancel    : " + await _inner_bind_behaviour_check(wait_for_impl, 1.0, None),
    ]

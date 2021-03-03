from asyncio import CancelledError, ensure_future, wait, get_event_loop, TimeoutError
from functools import partial


def _release_waiter(waiter, *args):  # copied from from asyncio.tasks
    if not waiter.done():
        waiter.set_result(None)


async def _cancel_and_wait(fut, loop):  # copied from from asyncio.tasks
    waiter = loop.create_future()
    cb = partial(_release_waiter, waiter)
    fut.add_done_callback(cb)
    try:
        fut.cancel()
        await waiter
    finally:
        fut.remove_done_callback(cb)


class CancelledWithResultError(CancelledError):
    def __init__(self, result):
        CancelledError.__init__(self, result)

    @property
    def result(self):
        return self.args[0]


async def wait_for(fut, timeout):
    """
    Alternate implementation of asyncio.wait_for() that does not eat cancellations.
    The CancelledWithResultError implementation works but is limited unfortunately. Wrapping futures and tasks raise
    their own CancelledError instances leaving the special one behind. So it is only usable when directly awaiting
    on this wait_for() coroutine.
    """
    fut = ensure_future(fut)
    try:
        done = bool((await wait((fut,), timeout=timeout))[0])
    except CancelledError:
        if fut.done():
            e = fut.exception()
            raise CancelledWithResultError(e if e else fut.result())
        await _cancel_and_wait(fut, get_event_loop())
        raise
    if done:
        return fut.result()
    await _cancel_and_wait(fut, get_event_loop())
    raise TimeoutError()

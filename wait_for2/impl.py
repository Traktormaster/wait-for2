"""
This implementation is mostly copied from asyncio.tasks (Python 3.8) while making the necessary changes.

:copyright: 2021 Nándor Mátravölgyi
:license: Apache2, see LICENSE for more details.
"""
import sys
from asyncio import CancelledError, ensure_future, TimeoutError
try:
    from asyncio import get_running_loop
except ImportError:
    from asyncio import get_event_loop as get_running_loop
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
        super(CancelledWithResultError, self).__init__(result)

    @property
    def result(self):
        return self.args[0]


async def wait_for(fut, timeout, *, loop=None):
    """
    Alternate implementation of asyncio.wait_for() based on the version from Python 3.8. It handles simultaneous
    cancellation of wait and completion of future differently and consistently across python versions 3.6+.

    Builtin asyncio.wait_for() behaviours:
        Python 3.6 and 3.7:
            Cancellation of wait_for could lose the completed future's result.
        Python 3.8+ and PyPy3:
            Cancellation of wait_for could lose the cancellation request.

    Whenever waiting for a future's result the user expects to either have the future completed or cancelled.
    Unfortunately due to technical details there is a chance that both will happen simultaneously. The builtin version
    of asyncio.wait_for() shipped with Python either handles one or the other only. If losing the future's result or
    ignoring the cancellation is critical to the application it may not be suitable for use.

    Using this implementation, in case both conditions occur at the same time a subclassed CancelledError will be
    raised which also contains the result of the future. The caller code must catch this exception and handle the
    result if it is important. Otherwise it can be used the same way as the builtin wait_for.

    NOTE: CancelledWithResultError is limited to the coroutine wait_for is invoked from!
    If this wait_for is wrapped in tasks those will not propagate the special exception, but raise their own
    CancelledError instances.
    """
    if loop is None:
        loop = get_running_loop()
    elif sys.version_info >= (3, 10):
        raise RuntimeError("loop parameter has been dropped since Python 3.10")

    if timeout is None:
        return await fut

    if timeout <= 0:
        fut = ensure_future(fut, loop=loop)

        if fut.done():
            return fut.result()

        await _cancel_and_wait(fut, loop=loop)
        try:
            fut.result()
        except CancelledError as exc:
            raise TimeoutError() from exc
        else:
            raise TimeoutError()

    waiter = loop.create_future()
    timeout_handle = loop.call_later(timeout, _release_waiter, waiter)
    cb = partial(_release_waiter, waiter)
    fut = ensure_future(fut, loop=loop)
    fut.add_done_callback(cb)

    try:
        try:
            await waiter
        except CancelledError:
            if fut.done():
                e = fut.exception()
                raise CancelledWithResultError(e if e else fut.result())
            else:
                fut.remove_done_callback(cb)
                fut.cancel()
                raise

        if fut.done():
            return fut.result()
        else:
            fut.remove_done_callback(cb)
            await _cancel_and_wait(fut, loop=loop)
            raise TimeoutError()
    finally:
        timeout_handle.cancel()

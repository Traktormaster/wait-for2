"""
This implementation is mostly copied from asyncio.tasks (Python 3.8) while making the necessary changes.

:copyright: 2021 Nándor Mátravölgyi
:license: Apache2, see LICENSE for more details.
"""
import asyncio
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


async def wait_for(fut, timeout, *, loop=None, cancel_handler=None):
    """
    Alternate implementation of asyncio.wait_for() based on the version from Python 3.8. It handles simultaneous
    cancellation of wait and completion of future differently and consistently across python versions 3.6+.

    The caller (when necessary) may give this construct a cleanup-callback to use when cancellation and inner task
    completion happens simultaneously.
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
            if fut.done() and cancel_handler:
                try:
                    fut_result = fut.exception()
                    if fut_result is None:
                        fut_result = fut.result()
                except asyncio.CancelledError:
                    pass  # inner future was also cancelled
                else:
                    try:
                        cancel_handler(fut_result)
                    except Exception:
                        # TODO: Log error from cancel_handler similarly to how add_callback does it...
                        #       It can be discussed, but the cancel-handler of the waiter should not be interrupted.
                        pass
            fut.remove_done_callback(cb)
            await _cancel_and_wait(fut, loop=loop)
            raise

        if fut.done():
            return fut.result()
        else:
            fut.remove_done_callback(cb)
            await _cancel_and_wait(fut, loop=loop)
            raise TimeoutError()
    finally:
        timeout_handle.cancel()


async def wait_for_special_raise(fut, timeout, *, loop=None):
    """
    Alternate implementation of asyncio.wait_for() based on the version from Python 3.8. It handles simultaneous
    cancellation of wait and completion of future differently and consistently across python versions 3.6+.

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


def _optionally_cancel_fut(fut, event):
    if not fut.done():
        event.set()
        fut.cancel()


async def wait_for_no_waiter(fut, timeout):
    """
    Alternative wait_for implementation structure proposed by Adam Liddell. (as-is)
    https://github.com/python/cpython/pull/26097#issuecomment-840497455

    This is a PoC, it does not work well as-is unfortunately.
    """
    loop = asyncio.get_running_loop()
    fut = ensure_future(fut, loop=loop)
    timeout_occurred = asyncio.Event()  # Likely not optimal
    if timeout is not None and timeout > 0:
        timeout_handle = loop.call_later(timeout, _optionally_cancel_fut, fut, timeout_occurred)
        fut.add_done_callback(lambda fut: timeout_handle.cancel())
    elif timeout is not None:
        # Timeout must be negative or zero, cancel immediately
        _optionally_cancel_fut(fut, timeout_occurred)

    try:
        return await fut
    except asyncio.CancelledError as exc:
        if timeout_occurred.is_set():
            raise asyncio.TimeoutError() from exc
        raise exc


async def wait_for_no_waiter_alt(fut, timeout, *, loop=None):
    """
    Alternative wait_for implementation structure proposed by Adam Liddell. (tried to improve it...)
    https://github.com/python/cpython/pull/26097#issuecomment-840497455

    I tried to improve the PoC version, but it is not right... I can't see what the problem is exactly.
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

    fut = ensure_future(fut, loop=loop)
    timeout_occurred = False

    def _handle_timeout():
        nonlocal timeout_occurred
        if fut.done():
            return  # task completed, timeout should not be handled
        timeout_occurred = True
        fut.cancel()  # NOTE: could utilize the msg parameter to signal timeout? (3.9+)

    timeout_handle = loop.call_later(timeout, _handle_timeout)

    try:
        return await fut
    except CancelledError as e:
        if timeout_occurred:
            raise TimeoutError() from e
        raise e
    finally:
        timeout_handle.cancel()

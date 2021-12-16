# from commit cb593779071a0baf92c550df8082c7dfc48b7467

import asyncio
import functools
from asyncio import ensure_future


def _release_waiter(waiter, *args):
    if not waiter.done():
        waiter.set_result(None)


async def wait_for(fut, timeout):
    """Wait for the single Future or coroutine to complete, with timeout.
    Coroutine will be wrapped in Task.
    Returns result of the Future or coroutine.  When a timeout occurs,
    it cancels the task and raises TimeoutError.  To avoid the task
    cancellation, wrap it in shield().
    If the wait is cancelled, the task is also cancelled.
    This function is a coroutine.
    """
    loop = asyncio.get_running_loop()

    if timeout is None:
        return await fut

    if timeout <= 0:
        fut = ensure_future(fut, loop=loop)

        if fut.done():
            return fut.result()

        await _cancel_and_wait(fut, loop=loop)
        try:
            return fut.result()
        except asyncio.CancelledError as exc:
            raise asyncio.TimeoutError() from exc

    waiter = loop.create_future()
    timeout_handle = loop.call_later(timeout, _release_waiter, waiter)
    cb = functools.partial(_release_waiter, waiter)

    fut = ensure_future(fut, loop=loop)
    fut.add_done_callback(cb)

    try:
        # wait until the future completes or the timeout
        try:
            await waiter
        except asyncio.CancelledError:
            if fut.done():
                return fut.result()
            else:
                fut.remove_done_callback(cb)
                # We must ensure that the task is not running
                # after wait_for() returns.
                # See https://bugs.python.org/issue32751
                await _cancel_and_wait(fut, loop=loop)
                return fut.result()

        if fut.done():
            return fut.result()
        else:
            fut.remove_done_callback(cb)
            # We must ensure that the task is not running
            # after wait_for() returns.
            # See https://bugs.python.org/issue32751
            await _cancel_and_wait(fut, loop=loop)
            # In case task cancellation failed with some
            # exception, we should re-raise it
            # See https://bugs.python.org/issue40607
            try:
                return fut.result()
            except asyncio.CancelledError as exc:
                raise asyncio.TimeoutError() from exc
    finally:
        timeout_handle.cancel()


async def _cancel_and_wait(fut, loop):
    """Cancel the *fut* future or task and wait until it completes."""

    waiter = loop.create_future()
    cb = functools.partial(_release_waiter, waiter)
    fut.add_done_callback(cb)

    try:
        fut.cancel()
        # We cannot wait on *fut* directly to make
        # sure _cancel_and_wait itself is reliably cancellable.
        await waiter
    finally:
        fut.remove_done_callback(cb)

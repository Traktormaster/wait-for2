"""
Test the behaviour of the new implementation while asserting the behaviour of the builtin one.

:copyright: 2021 Nándor Mátravölgyi
:license: Apache2, see LICENSE for more details.
"""
import asyncio
import sys

import pytest

import wait_for2


BUILTIN_PREFERS_CANCELLATION_OVER_RESULT = sys.version_info < (3, 8) or hasattr(sys, "pypy_version_info")


class JobError(Exception):
    pass


class StuckError(Exception):
    pass


class _AbstractEngine(object):
    def __init__(self):
        self.event = asyncio.Event()
        self.tasks = []

    async def job_error(self):
        await asyncio.sleep(1.0)
        try:
            raise JobError()
        finally:
            self.event.set()

    async def job_event(self):
        raise NotImplementedError()

    async def run(self):
        self.tasks = tasks = [asyncio.ensure_future(self.job_error()), asyncio.ensure_future(self.job_event())]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            # propagate first work task error to the main thread
            for t in done:
                e = t.exception()
                if e:
                    raise e
        finally:
            for t in tasks:
                t.cancel()
            try:
                # Detect stuck state for demonstration instead of naively waiting for the tasks.
                x = 0
                while not all(t.done() for t in tasks):
                    if x > 0:
                        raise StuckError()
                    await asyncio.sleep(1.0)
                    x += 1
            finally:
                for t in tasks:  # second cancellation will work in this case
                    t.cancel()
                # Gather tasks.
                await asyncio.gather(*tasks, return_exceptions=True)


class _WaitFor(_AbstractEngine):
    async def job_event(self):
        while True:
            try:
                await asyncio.wait_for(self.event.wait(), timeout=60.0)
                self.event.clear()
            except asyncio.TimeoutError:
                pass


class _WaitFor2(_AbstractEngine):
    def __init__(self):
        _AbstractEngine.__init__(self)
        self.result = object()

    async def job_event(self):
        while True:
            try:
                await wait_for2.wait_for(self.event.wait(), timeout=60.0)
                self.event.clear()
            except asyncio.TimeoutError:
                pass
            except wait_for2.CancelledWithResultError as e:
                self.result = e.result
                raise


class _Wait(_AbstractEngine):
    async def job_event(self):
        f = asyncio.ensure_future(self.event.wait())
        try:
            while True:
                if f.done():
                    f = asyncio.ensure_future(self.event.wait())
                d, _ = await asyncio.wait([f], timeout=60.0)
                if d:
                    self.event.clear()
        finally:
            f.cancel()
            await asyncio.gather(f, return_exceptions=True)


@pytest.mark.asyncio
async def test_wait_for2_basic():
    async def _wrapped(delay, result=None):
        await asyncio.sleep(delay)
        if isinstance(result, Exception):
            raise result
        return result

    sentinel0 = object()
    sentinel1 = object()
    exception0 = Exception()
    exception1 = Exception()

    # test timeout
    w0 = asyncio.ensure_future(_wrapped(2.0))
    w1 = asyncio.ensure_future(_wrapped(2.0))
    r0, r1 = await asyncio.gather(asyncio.wait_for(w0, 1.0), wait_for2.wait_for(w1, 1.0), return_exceptions=True)
    assert isinstance(r0, asyncio.TimeoutError)
    assert isinstance(r1, asyncio.TimeoutError)
    assert w0.cancelled()
    assert w0.done()
    assert w1.cancelled()
    assert w1.done()

    # test result
    w0 = asyncio.ensure_future(_wrapped(1.0, sentinel0))
    w1 = asyncio.ensure_future(_wrapped(1.0, sentinel1))
    r0, r1 = await asyncio.gather(asyncio.wait_for(w0, 2.0), wait_for2.wait_for(w1, 2.0), return_exceptions=True)
    assert r0 is sentinel0
    assert r1 is sentinel1
    assert not w0.cancelled()
    assert w0.done()
    assert not w1.cancelled()
    assert w1.done()

    # test exception
    w0 = asyncio.ensure_future(_wrapped(1.0, exception0))
    w1 = asyncio.ensure_future(_wrapped(1.0, exception1))
    t0 = asyncio.ensure_future(asyncio.wait_for(w0, 2.0))
    t1 = asyncio.ensure_future(wait_for2.wait_for(w1, 2.0))
    r0, r1 = await asyncio.gather(t0, t1, return_exceptions=True)
    assert r0 is exception0
    assert r1 is exception1
    assert not w0.cancelled()
    assert w0.done() is True
    assert not w1.cancelled()
    assert w1.done() is True
    assert t0.done() is True
    assert t1.done() is True
    assert t0.exception() is exception0
    assert t1.exception() is exception1

    # test cancelling
    w0 = asyncio.ensure_future(_wrapped(2.0))
    w1 = asyncio.ensure_future(_wrapped(2.0))
    t0 = asyncio.ensure_future(asyncio.wait_for(w0, 3.0))
    t1 = asyncio.ensure_future(wait_for2.wait_for(w1, 3.0))
    t = asyncio.gather(t0, t1, return_exceptions=True)
    await asyncio.sleep(0.1)
    assert t.done() is False
    assert w0.done() is False
    assert w1.done() is False
    assert t0.done() is False
    assert t1.done() is False
    t0.cancel()
    t1.cancel()
    r0, r1 = await t
    assert isinstance(r0, asyncio.CancelledError)
    assert isinstance(r1, asyncio.CancelledError)
    assert t0.cancelled()
    assert t1.cancelled()
    assert w0.cancelled()
    assert w0.done()
    assert w1.cancelled()
    assert w1.done()


@pytest.mark.asyncio
async def test_asyncio_wait_for_stuck():
    with pytest.raises(JobError if BUILTIN_PREFERS_CANCELLATION_OVER_RESULT else StuckError):
        await _WaitFor().run()


@pytest.mark.asyncio
async def test_asyncio_wait_pass():
    with pytest.raises(JobError):
        await _Wait().run()


@pytest.mark.asyncio
async def test_wait_for2_pass():
    w = _WaitFor2()
    with pytest.raises(JobError):
        await w.run()
    assert w.tasks[1].cancelled()
    assert w.tasks[1].done()
    assert w.result is True

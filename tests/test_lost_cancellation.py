import asyncio
from functools import partial

import pytest

import wait_for2
from tests.common.constants import BUILTIN_WAIT_FOR_BEHAVIOUR


async def _check_guard_cancellation_task(wait_for_impl, **wait_for_kwargs):
    race_timeout = 0.1
    run = True

    async def do_something():
        await asyncio.sleep(race_timeout)
        return object()

    async def work_coro():
        while run:
            await wait_for_impl(do_something(), timeout=5, **wait_for_kwargs)

    async def run_task_and_cancel_it():
        t = asyncio.create_task(work_coro())
        await asyncio.sleep(race_timeout)
        t.cancel()
        await asyncio.gather(t, return_exceptions=True)

    task = asyncio.create_task(run_task_and_cancel_it())
    done, _ = await asyncio.wait([task], timeout=3 * race_timeout)
    if not done:
        run = False
        await task
        return False
    return True


async def _check_guard_cancellation_future(wait_for_impl, **wait_for_kwargs):
    race_timeout = 0.1
    run = True
    loop = asyncio.get_running_loop()

    async def work_coro(f_):
        await wait_for_impl(f_, timeout=5, **wait_for_kwargs)
        while run:
            await asyncio.sleep(1)

    f = loop.create_future()
    loop.call_later(race_timeout, partial(f.set_result, object()))
    task = asyncio.create_task(work_coro(f))
    loop.call_later(race_timeout, partial(task.cancel))

    done, _ = await asyncio.wait([task], timeout=3 * race_timeout)
    if not done:
        run = False
        await task
        return False
    return True


@pytest.mark.asyncio
async def test_race_condition_by_timing_builtin():
    f = _check_guard_cancellation_task(asyncio.wait_for)
    if BUILTIN_WAIT_FOR_BEHAVIOUR["some timeout, cancel after "] == "cancelled bound":
        assert await f, "task result was lost by race-condition"
    else:
        assert not await f, "task cancellation was ignored by race-condition"
    f = _check_guard_cancellation_future(asyncio.wait_for)
    if BUILTIN_WAIT_FOR_BEHAVIOUR["some timeout, cancel after "] == "cancelled bound":
        assert await f, "future result was lost by race-condition"
    else:
        assert not await f, "future cancellation was ignored by race-condition"


@pytest.mark.asyncio
async def test_race_condition_by_timing_wf2():
    resource = []

    def race_handler(r, ie):
        assert not ie
        resource.append(r)

    assert await _check_guard_cancellation_task(wait_for2.wait_for, race_handler=race_handler)
    assert len(resource) == 1, "task result was not handled in race-condition"

    del resource[:]

    assert await _check_guard_cancellation_future(wait_for2.wait_for, race_handler=race_handler)
    assert len(resource) == 1, "future result was not handled in race-condition"

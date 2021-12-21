import asyncio

import pytest

import wait_for2
from tests.common.constants import BUILTIN_PREFERS_CANCELLATION_OVER_RESULT


async def _check_guard_cancellation(wait_for_impl, **wait_for_kwargs):
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


@pytest.mark.asyncio
async def test_race_condition_by_timing_builtin():
    if BUILTIN_PREFERS_CANCELLATION_OVER_RESULT:
        assert await _check_guard_cancellation(asyncio.wait_for), "result was lost by race-condition"
    else:
        assert not await _check_guard_cancellation(asyncio.wait_for), "cancellation was ignored by race-condition"


@pytest.mark.asyncio
async def test_race_condition_by_timing_wf2():
    resource = []

    def race_handler(r, ie):
        assert not ie
        resource.append(r)

    await _check_guard_cancellation(wait_for2.wait_for, race_handler=race_handler)

    assert len(resource) == 1, "result was not handled in race-condition"

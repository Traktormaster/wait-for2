import asyncio

import pytest

import wait_for2


async def _no_wait_result(wait_for_impl):
    loop = asyncio.get_running_loop()
    # result returned
    fut = loop.create_future()
    sentinel = object()
    fut.set_result(sentinel)
    assert await wait_for_impl(fut, timeout=0) == sentinel
    # exception raised
    fut = loop.create_future()
    sentinel_error = Exception()
    fut.set_exception(sentinel_error)
    try:
        await wait_for_impl(fut, timeout=0)
    except Exception as e:
        assert sentinel_error is e


@pytest.mark.asyncio
async def test_no_wait_result_builtin():
    await _no_wait_result(asyncio.wait_for)


@pytest.mark.asyncio
async def test_no_wait_result_wf2():
    await _no_wait_result(wait_for2.wait_for)

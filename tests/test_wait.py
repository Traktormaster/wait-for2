"""
Test the behaviour of the new implementation while asserting the behaviour of the builtin one.

:copyright: 2021 Nándor Mátravölgyi
:license: Apache2, see LICENSE for more details.
"""
import asyncio
import math
import sys

import pytest

import wait_for2
from wait_for2.impl28149 import wait_for as wait_for28149
from wait_for2.impl28149_2 import wait_for as wait_for28149_2

BUILTIN_PREFERS_CANCELLATION_OVER_RESULT = sys.version_info < (3, 8) or hasattr(sys, "pypy_version_info")
TASK_NUM = 10000  # may need to scale to CPU performance for the test to be effective

RESOURCES = set()
EXIT = False
WAIT_FOR_TIMED_OUT = False


def cleanup_resource(resource):
    RESOURCES.remove(resource)


async def create_resource():
    """
    Simulates a well-behaved coroutine that acquires some resource.
    Well-behaved means that it does not leak the resource if the coroutine is cancelled.
    """
    work = 1 + len(RESOURCES)
    for _ in range(int(math.log10(work))):
        await asyncio.sleep(0.0)
    resource = object()
    RESOURCES.add(resource)
    try:
        for _ in range(int(math.log10(work))):
            await asyncio.sleep(0.0)
        return resource
    except asyncio.CancelledError:
        cleanup_resource(resource)
        raise


async def resource_worker(wait_for_impl, use_special_raise=False, cancel_event=None, **wait_for_kwargs):
    try:
        resource = await wait_for_impl(create_resource(), timeout=99999.0, **wait_for_kwargs)
    except asyncio.TimeoutError:
        global WAIT_FOR_TIMED_OUT
        WAIT_FOR_TIMED_OUT = True
        raise
    except wait_for2.CancelledWithResultError as e:
        if use_special_raise:
            cleanup_resource(e.result)
        raise
    try:
        if not cancel_event.is_set() and len(RESOURCES) > TASK_NUM * 0.1:
            cancel_event.set()
        while not EXIT:
            await asyncio.sleep(1.0)
    finally:
        cleanup_resource(resource)


async def _resource_handling_test(wait_for_impl, **wait_for_kwargs):
    # reset for new test
    global EXIT
    RESOURCES.clear()
    EXIT = False

    tasks = []
    cancel_event = asyncio.Event()
    for i in range(TASK_NUM):  # scale to CPU
        tasks.append(asyncio.create_task(resource_worker(wait_for_impl, cancel_event=cancel_event, **wait_for_kwargs)))

    await cancel_event.wait()
    for t in tasks:
        t.cancel()

    try:
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 10.0)
    except asyncio.TimeoutError:
        EXIT = True
        await asyncio.gather(*tasks, return_exceptions=True)
        assert False, "wait_for within a task ignored the cancellation"
    finally:
        assert not WAIT_FOR_TIMED_OUT, "We should focus on the cancellation race right now"
        assert cancel_event.is_set(), "Cancellation was not initiated!"
        # to ensure different runs don't interfere
        assert all(task.done() for task in tasks), "Tasks were not terminated!"

    await asyncio.sleep(0.2)
    assert not RESOURCES, "resources were leaked: %s" % (len(RESOURCES),)


@pytest.mark.asyncio
async def test_resource_leakage_builtin():
    if BUILTIN_PREFERS_CANCELLATION_OVER_RESULT:
        with pytest.raises(AssertionError, match="resources were leaked"):
            await _resource_handling_test(asyncio.wait_for)
    else:
        with pytest.raises(AssertionError, match="wait_for within a task ignored the cancellation"):
            await _resource_handling_test(asyncio.wait_for)


@pytest.mark.asyncio
async def test_resource_leakage_wf2_callback():
    # handle the cancellation-completion race condition with a callback
    await _resource_handling_test(wait_for2.wait_for, race_handler=cleanup_resource)


@pytest.mark.asyncio
async def test_resource_leakage_wf2_except():
    # handle the cancellation-completion race condition as an exception
    await _resource_handling_test(wait_for2.wait_for, use_special_raise=True)


@pytest.mark.asyncio
async def test_resource_leakage_wf2_no_handle():
    # if we do not handle the race condition the alternate implementation is similar to the builtin
    with pytest.raises(AssertionError, match="resources were leaked"):
        await _resource_handling_test(wait_for2.wait_for)


@pytest.mark.asyncio
async def test_resource_leakage_28149():
    # retains the preferred cancellation behaviour
    with pytest.raises(AssertionError, match="resources were leaked"):
        await _resource_handling_test(wait_for28149)


@pytest.mark.asyncio
async def test_resource_leakage_28149_2():
    # retains the preferred cancellation behaviour
    with pytest.raises(AssertionError, match="wait_for within a task ignored the cancellation"):
        await _resource_handling_test(wait_for28149_2)

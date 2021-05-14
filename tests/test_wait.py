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

BUILTIN_PREFERS_CANCELLATION_OVER_RESULT = sys.version_info < (3, 8) or hasattr(sys, "pypy_version_info")
TASK_NUM = 10000  # may need to scale to CPU performance for the test to be effective

RESOURCES = set()
EXIT = False


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


async def resource_worker(wait_for_impl, use_special_raise=False, **wait_for_kwargs):
    try:
        resource = await wait_for_impl(create_resource(), timeout=0.1, **wait_for_kwargs)
    except wait_for2.CancelledWithResultError as e:
        if use_special_raise:
            cleanup_resource(e.result)
        raise
    try:
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
    for _ in range(TASK_NUM):  # scale to CPU
        tasks.append(asyncio.create_task(resource_worker(wait_for_impl, **wait_for_kwargs)))

    await asyncio.sleep(0.025)
    for task in tasks:
        task.cancel()

    try:
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 10.0)
    except asyncio.TimeoutError:
        EXIT = True
        await asyncio.gather(*tasks, return_exceptions=True)
        assert False, "wait_for within a task ignored the cancellation"
    finally:
        # to ensure different runs don't interfere
        assert all(task.done() for task in tasks), "Tasks were not terminated!"

    await asyncio.sleep(0.2)
    assert not RESOURCES, "resources were leaked: %s" % (len(RESOURCES),)


@pytest.mark.asyncio
async def test_resource_leakage():
    if BUILTIN_PREFERS_CANCELLATION_OVER_RESULT:
        with pytest.raises(AssertionError, match="resources were leaked"):
            await _resource_handling_test(asyncio.wait_for)
    else:
        with pytest.raises(AssertionError, match="wait_for within a task ignored the cancellation"):
            await _resource_handling_test(asyncio.wait_for)

    # handle the cancellation-completion race condition with a callback
    await _resource_handling_test(wait_for2.wait_for, race_handler=cleanup_resource)

    # handle the cancellation-completion race condition as an exception
    await _resource_handling_test(wait_for2.wait_for, use_special_raise=True)

    # if we do not handle the race condition the alternate implementation is similar to the builtin
    with pytest.raises(AssertionError, match="resources were leaked"):
        await _resource_handling_test(wait_for2.wait_for)

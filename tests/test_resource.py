"""
Test the behaviour of the new implementation while asserting the behaviour of the builtin one.

:copyright: 2021 Nándor Mátravölgyi
:license: Apache2, see LICENSE for more details.
"""

import asyncio

import pytest

import wait_for2
from .common.constants import BUILTIN_WAIT_FOR_BEHAVIOUR, GT_PY312
from .common.resource import ResourceWorkerWaitForTester


@pytest.mark.asyncio
async def test_resource_leakage_builtin():
    if BUILTIN_WAIT_FOR_BEHAVIOUR["some timeout, cancel after "] == "cancelled bound":
        await ResourceWorkerWaitForTester(asyncio.wait_for).run()
    else:
        with pytest.raises(AssertionError, match="wait_for within a task ignored the cancellation"):
            await ResourceWorkerWaitForTester(asyncio.wait_for).run()


@pytest.mark.asyncio
async def test_resource_leakage_wf2_callback():
    # handle the cancellation-completion race condition with a callback
    tester = ResourceWorkerWaitForTester(wait_for2.wait_for)
    await tester.run(race_handler=tester.cleanup_resource)


@pytest.mark.asyncio
async def test_resource_leakage_wf2_except():
    if GT_PY312:
        with pytest.raises(AssertionError, match="Special raise cleanup never called"):
            await ResourceWorkerWaitForTester(wait_for2.wait_for).run(use_special_raise=True)
    else:
        # handle the cancellation-completion race condition as an exception
        await ResourceWorkerWaitForTester(wait_for2.wait_for).run(use_special_raise=True)


@pytest.mark.asyncio
async def test_resource_leakage_wf2_no_handle():
    if GT_PY312:
        # since python 3.12 the builtin does not lose results (wait_for2 uses that automatically when no race_handler)
        await ResourceWorkerWaitForTester(wait_for2.wait_for).run()
    else:
        # if we do not handle the race condition the alternate implementation is similar to the builtin
        with pytest.raises(AssertionError, match="resources were leaked"):
            await ResourceWorkerWaitForTester(wait_for2.wait_for).run()

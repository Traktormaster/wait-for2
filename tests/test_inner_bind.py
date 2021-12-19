import asyncio

import pytest

import wait_for2
from .common.constants import BUILTIN_PREFERS_CANCELLATION_OVER_RESULT
from .common.inner_bind import inner_bind_behaviour_check


@pytest.mark.asyncio
async def test_inner_bound_builtin():
    x = await inner_bind_behaviour_check(asyncio.wait_for)
    if BUILTIN_PREFERS_CANCELLATION_OVER_RESULT:
        assert x == [
            "no timeout                 : cancelled bound",
            "no wait, cancel before     : timeout unbound",
            "no wait, cancel after      : timeout unbound",
            "no wait, no cancel         : timeout unbound",
            "some timeout, cancel before: cancelled unbound",
            "some timeout, cancel after : cancelled unbound",
            "some timeout, no cancel    : timeout bound",
        ], str(x)
    else:
        assert x == [
            "no timeout                 : cancelled bound",
            "no wait, cancel before     : cancelled unbound",
            "no wait, cancel after      : cancelled unbound",
            "no wait, no cancel         : timeout bound",
            "some timeout, cancel before: cancelled bound",
            "some timeout, cancel after : cancelled unbound",
            "some timeout, no cancel    : timeout bound",
        ], str(x)


@pytest.mark.asyncio
async def test_inner_bound_wf2():
    x = await inner_bind_behaviour_check(wait_for2.wait_for)
    assert x == [
        "no timeout                 : cancelled bound",
        "no wait, cancel before     : cancelled bound",
        "no wait, cancel after      : cancelled bound",
        "no wait, no cancel         : timeout bound",
        "some timeout, cancel before: cancelled bound",
        "some timeout, cancel after : cancelled bound",
        "some timeout, no cancel    : timeout bound",
    ], str(x)

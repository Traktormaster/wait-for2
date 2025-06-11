import asyncio

import pytest

import wait_for2
from .common.constants import BUILTIN_WAIT_FOR_BEHAVIOUR, BEST_WAIT_FOR_BEHAVIOUR, GT_PY312
from .common.inner_bind import inner_bind_behaviour_check


@pytest.mark.asyncio
async def test_inner_bound_builtin():
    x = await inner_bind_behaviour_check(asyncio.wait_for)
    assert x == BUILTIN_WAIT_FOR_BEHAVIOUR, str(x)


@pytest.mark.asyncio
async def test_inner_bound_wf2():
    x = await inner_bind_behaviour_check(wait_for2.wait_for)
    if GT_PY312:
        assert x == BUILTIN_WAIT_FOR_BEHAVIOUR, str(x)
        from wait_for2.impl import wait_for

        x = await inner_bind_behaviour_check(wait_for)
    assert x == BEST_WAIT_FOR_BEHAVIOUR, str(x)

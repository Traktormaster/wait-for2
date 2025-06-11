"""
wait_for2
Asyncio wait_for that can handle simultaneous cancellation and future completion.

:copyright: 2025 Nándor Mátravölgyi
:license: Apache2, see LICENSE for more details.
"""

__author__ = "Nándor Mátravölgyi"
__copyright__ = "Copyright 2021 Nándor Mátravölgyi"
__author_email__ = "nandor.matra@gmail.com"
__version__ = "0.4.0"

import sys

if sys.version_info >= (3, 12):
    from asyncio import wait_for as _builtin_wait_for
    from .impl import CancelledWithResultError, wait_for as _wf2

    async def wait_for(fut, timeout, *, loop=None, race_handler=None):
        if loop:
            raise RuntimeError("loop parameter has been dropped since Python 3.10")
        if race_handler is None:
            return await _builtin_wait_for(fut, timeout)
        return await _wf2(fut, timeout, race_handler=race_handler)

else:
    from .impl import CancelledWithResultError, wait_for

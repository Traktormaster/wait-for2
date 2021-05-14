"""
wait_for2
Asyncio wait_for that can handle simultaneous cancellation and future completion.

:copyright: 2021 Nándor Mátravölgyi
:license: Apache2, see LICENSE for more details.
"""

__author__ = "Nándor Mátravölgyi"
__copyright__ = "Copyright 2021 Nándor Mátravölgyi"
__author_email__ = "nandor.matra@gmail.com"
__version__ = "0.1.0"

from .impl import CancelledWithResultError, wait_for, wait_for_special_raise, wait_for_no_waiter, wait_for_no_waiter_alt

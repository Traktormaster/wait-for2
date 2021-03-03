"""
wait_for2
Asyncio wait_for with more control over cancellation.
"""

__author__ = "Nándor Mátravölgyi"
__copyright__ = "Copyright 2021 Nándor Mátravölgyi"
__author_email__ = "nandor.matra@gmail.com"
__version__ = "0.1.0"

from .impl import CancelledWithResultError, wait_for

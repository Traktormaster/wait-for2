import sys

BUILTIN_PREFERS_CANCELLATION_OVER_RESULT = sys.version_info < (3, 8) or hasattr(sys, "pypy_version_info")
BUILTIN_PREFERS_TIMEOUT_OVER_RESULT = sys.version_info < (3, 9) or hasattr(sys, "pypy_version_info")

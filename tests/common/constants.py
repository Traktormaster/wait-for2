import sys

_LT_PY38 = sys.version_info < (3, 8)
_LT_PY39 = sys.version_info < (3, 9)
_LT_PY3910 = sys.version_info < (3, 9, 10)
_GT_PY311 = sys.version_info >= (3, 11)


BUILTIN_PROPAGATES_CUSTOM_CANCEL = _GT_PY311
BUILTIN_PREFERS_CANCELLATION_OVER_RESULT = _LT_PY38
BUILTIN_PREFERS_TIMEOUT_OVER_RESULT = _LT_PY3910
BUILTIN_PREFERS_TIMEOUT_OVER_EXCEPTION = _LT_PY39

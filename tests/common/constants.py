import sys

_IS_PYPY = hasattr(sys, "pypy_version_info")
_LT_PY38 = sys.version_info < (3, 8)
_LT_PY39 = sys.version_info < (3, 9)
_LT_PY310 = sys.version_info < (3, 10)


BUILTIN_PREFERS_CANCELLATION_OVER_RESULT = _LT_PY38 or _IS_PYPY
BUILTIN_PREFERS_TIMEOUT_OVER_RESULT = _LT_PY39 or (not _LT_PY39 and _LT_PY310) or _IS_PYPY
BUILTIN_PREFERS_TIMEOUT_OVER_EXCEPTION = _LT_PY39 or _IS_PYPY

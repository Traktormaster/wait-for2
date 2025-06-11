import sys

_LT_PY39 = sys.version_info < (3, 9)
_LT_PY3910 = sys.version_info < (3, 9, 10)
_GT_PY311 = sys.version_info >= (3, 11)
GT_PY312 = sys.version_info >= (3, 12)


BUILTIN_PROPAGATES_CUSTOM_CANCEL = _GT_PY311
BUILTIN_PREFERS_TIMEOUT_OVER_RESULT = _LT_PY3910
BUILTIN_PREFERS_TIMEOUT_OVER_EXCEPTION = _LT_PY39

BUILTIN_WAIT_FOR_BEHAVIOUR = {
    "no timeout                 ": "cancelled bound",
    "no wait, cancel before     ": "cancelled unbound",
    "no wait, cancel after      ": "cancelled unbound",
    "no wait, no cancel         ": "timeout bound",
    "some timeout, cancel before": "cancelled bound",
    "some timeout, cancel after ": "cancelled bound" if GT_PY312 else "cancelled unbound",
    "some timeout, no cancel    ": "timeout bound",
}

BEST_WAIT_FOR_BEHAVIOUR = {
    "no timeout                 ": "cancelled bound",
    "no wait, cancel before     ": "cancelled bound",
    "no wait, cancel after      ": "cancelled bound",
    "no wait, no cancel         ": "timeout bound",
    "some timeout, cancel before": "cancelled bound",
    "some timeout, cancel after ": "cancelled bound",
    "some timeout, no cancel    ": "timeout bound",
}

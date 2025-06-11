# wait_for2

**If you only want to support Python 3.12+ then you should not need this library.**

Alternate implementation of `asyncio.wait_for()`. It handles several edge cases like simultaneous
cancellation of wait and completion of future differently and consistently across Python versions 3.7+.

## Updates

This library is pretty much unnecessary for Python 3.12+, the last primary race-condition was addressed: https://github.com/python/cpython/pull/28149#issuecomment-1560278644

If you need to support older Python versions you may still use it. Since version `0.4.0` the library will actually
use the builtin `asyncio.wait_for` when running in Python 3.12+, unless a `race_handler` parameter is passed. This
behaviour retains backwards compatibility with the library, but actually prefers a more correct implementation,
as the new `asyncio.wait_for` does not need a special race-condition handling.

The behavioural details below were made for Python 3.7-3.10 and have not been updated. For example a few more behaviour
variances have been introduced in Python 3.9.10. It changes the behaviour of simultaneous timeout and completion
compared to previous 3.9 releases. PyPy 3 used to mirror the 3.7 behaviour, but the current release have changed the
behaviour at some unspecified release to 3.9.10+, and even later Python 3.12+...

## Details
The tests in the repository are set up with TOX to cover and assert the following behaviours of `wait_for` and the
alternate implementation for each Python version.

### Cancellation behaviour with simultaneous result

Builtin `asyncio.wait_for()` behaviours:
  - Python 3.7:
    Cancellation of `wait_for` could lose the completed future's result.
  - Python 3.8+ and PyPy3:
    Cancellation of `wait_for` could lose the cancellation request.

Whenever waiting for a future's result the user expects to either have the future completed or cancelled.
Unfortunately due to technical details there is a chance that both will happen simultaneously. The builtin version
of `asyncio.wait_for()` shipped with Python either handles one or the other only. If losing the future's result or
ignoring the cancellation is critical to the application it may not be suitable for use.

Using this implementation, in case both conditions occur at the same time a subclassed `CancelledError` will be
raised which also contains the result of the future. The caller code must catch this exception and handle the
result if it is important. Otherwise, it can be used the same way as the builtin `wait_for`.

If the caller prefers to handle the race-condition with a callback, the `race_handler` argument may be provided.
It will be called with the result of the future when the waiter task is being cancelled. Even if this is provided,
the special error will be raised in the place of a normal CancelledError.

NOTE: `CancelledWithResultError` is limited to the coroutine `wait_for` is invoked from prior to Python 3.11!
If the `wait_for` is wrapped in tasks those will not propagate the special exception, but raise their own
`CancelledError` instances. The callback-based solution may be preferred as that will always work in all Python versions.

This table summarizes the behaviours in the race-condition cases.
The cross cells show what behaviour is observed:
- LR: looses result (returned result or raised exception)
- LC: looses cancellation request
- RH: race-condition handling supported, cancellation is never ignored by the wait-for

|                                    | Python 3.7 | Python 3.8+ and PyPy3 | wait_for2 |
|------------------------------------|------------|-----------------------|-----------|
| explicit cancel & result (or exc.) | LR         | LC                    | ***RH***  |


### Timeout handling behaviour with results

When the timeout is reached, the inner future is cancelled. This can also cause race condition where the result is lost.

The cross cells show what behaviour is observed:
- TE: prioritizes raising `TimeoutError`, looses result or exception
- PR: prioritizes returning or raising the result exception

|                                   | Python 3.7, 3.8 | Python 3.9 | Python 3.10+ and PyPy3 | wait_for2 |
|-----------------------------------|-----------------|------------|------------------------|-----------|
| result after cancel by timeout    | TE              | TE         | ***PR***               | ***PR***  |
| exception after cancel by timeout | TE              | ***PR***   | ***PR***               | ***PR***  |

### Cancellation behaviour with timeout handling

Additionally, this implementation will inherit the behaviour of the inner future when it comes to ignoring
cancellation. The builtin version prefers to always be cancellable, even if that means the wrapped future may
not be terminated with it. (behaviour of builtin _cancel_and_wait) This behaviour is also improved in
timeout-cancel edge cases, where the builtin would not wait for the termination of the inner future if the
waiter was cancelled after timeout handling had already started. This is more consistent as the inner future
must always be stopped for it to return.

The leftmost column describes the case where the behaviour is tested. It shows what timeout the wait-for is called with
and when the cancellation occurs relative to it.

The cross-cells show the raised result and if the inner future is terminated before the wait-for implementation returns:
- C/T: `CancelledError`/`TimeoutError` was raised
- B/U: `bound` means the inner future terminated before the wait-for returned/`unbound` means the inner future was still
  running when the wait-for returned

The cells where the desired behaviour is observed (IMO) are formatted to be bold-italic.

|                             | Python 3.7 | Python 3.8+ and PyPy3 | wait_for2 |
|-----------------------------|------------|-----------------------|-----------|
| no timeout, cancel          | ***C B***  | **C B**               | ***C B*** |
| zero timeout, cancel before | T U        | C U                   | ***C B*** |
| zero timeout, cancel after  | T U        | C U                   | ***C B*** |
| zero timeout, no cancel     | T U        | ***T B***             | ***T B*** |
| some timeout, cancel before | C U        | ***C B***             | ***C B*** |
| some timeout, cancel after  | C U        | C U                   | ***C B*** |
| some timeout, no cancel     | ***T B***  | ***T B***             | ***T B*** |

# Install & usage
A package is available on PyPI:

```console
$ python -m pip install wait_for2
```

```python
import asyncio
import wait_for2

task = asyncio.create_task(...)

def process_result(r, is_exc=False):
    print("processed:", r, is_exc)

...

try:
    process_result(await wait_for2.wait_for(task, 5.0))
except wait_for2.CancelledWithResultError as e:
    # NOTE: e.result could be an exception raised by the task; handling or ignoring it is up to the user code here
    process_result(e.result, e.is_exception)
    raise asyncio.CancelledError()

# alternatively with a callback:
process_result(await wait_for2.wait_for(task, 5.0, race_handler=process_result))

```

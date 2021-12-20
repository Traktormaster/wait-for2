# wait_for2
Alternate implementation of `asyncio.wait_for()` based on the version from Python 3.8. It handles simultaneous
cancellation of wait and completion of future differently and consistently across Python versions 3.6+.

## Details
Builtin `asyncio.wait_for()` behaviours:
  - Python 3.6, 3.7 and PyPy3:
    Cancellation of `wait_for` could lose the completed future's result.
  - Python 3.8+:
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

Additionally, this implementation will inherit the behaviour of the inner future when it comes to ignoring
cancellation. The builtin version prefers to always be cancellable, even if that means the wrapped future may
not be terminated with it. (behaviour of builtin _cancel_and_wait) This behaviour is also improved in
timeout-cancel edge cases, where the builtin would not wait for the termination of the inner future if the
waiter was cancelled after timeout handling had already started. This is more consistent as the inner future
must always be stopped for it to return.

NOTE: `CancelledWithResultError` is limited to the coroutine `wait_for` is invoked from!
If this `wait_for` is wrapped in tasks those will not propagate the special exception, but raise their own
`CancelledError` instances.

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

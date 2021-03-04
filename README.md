# wait_for2
Alternate implementation of `asyncio.wait_for()` based on the version from Python 3.8. It handles simultaneous
cancellation of wait and completion of future differently and consistently across Python versions 3.6+.

## Details
Builtin `asyncio.wait_for()` behaviours:
  - Python 3.6 and 3.7:
    Cancellation of `wait_for` could lose the completed future's result.
  - Python 3.8+ and PyPy3:
    Cancellation of `wait_for` could lose the cancellation request.

Whenever waiting for a future's result the user expects to either have the future completed or cancelled.
Unfortunately due to technical details there is a chance that both will happen simultaneously. The builtin version
of `asyncio.wait_for()` shipped with Python either handles one or the other only. If losing the future's result or
ignoring the cancellation is critical to the application it may not be suitable for use.

Using this implementation, in case both conditions occur at the same time a subclassed `CancelledError` will be
raised which also contains the result of the future. The caller code must catch this exception and handle the
result if it is important. Otherwise it can be used the same way as the builtin `wait_for`.

NOTE: `CancelledWithResultError` is limited to the coroutine `wait_for` is invoked from!
If this `wait_for` is wrapped in tasks those will not propagate the special exception, but raise their own
`CancelledError` instances.

# Install & usage
A source distribution is available on PyPI:

```console
$ python -m pip install wait_for2
```

```python
import asyncio
import wait_for2

task = asyncio.create_task(...)

async def process_result(r):
    print("processed:", r)

...

try:
    await process_result(await wait_for2.wait_for(task, 5.0))
except wait_for2.CancelledWithResultError as e:
    # NOTE: e.result could be an exception raised by the task; handling or ignoring it is up to the user code here
    await process_result(e.result)
    raise asyncio.CancelledError()
```

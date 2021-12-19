import asyncio
import time
from functools import partial

import wait_for2


class Resource(object):
    pass


class ResourceError(Exception):
    pass


class ResourceWorkerWaitForTester(object):
    CANCELLATION_TIME_LIMIT = 0.5

    def __init__(
        self,
        wait_for_impl,
        create_resource_sleeps: int = 2,
        create_resource_slow_sleeps: int = 10,
        task_num: int = 10000,
        cancel_after_task_percent: float = 0.1,
        wait_for_timeout: float = 999.0,
    ):
        self.exit = False
        self.waiting_finished = 0
        self.waiting_timed_out = 0
        self.cancelled_during_resource_creation = 0
        self.cancelled_before_resource_creation = 0
        self.cleanup_got_error = 0
        self.resources = set()
        self.cancel_event = asyncio.Event()
        # config that determines branch coverage and behaviour of this case
        self.wait_for_impl = wait_for_impl
        self.create_resource_sleeps = create_resource_sleeps
        self.create_resource_slow_sleeps = create_resource_slow_sleeps
        self.task_num = task_num
        self.cancel_after_task = int(task_num * cancel_after_task_percent)
        self.wait_for_timeout = wait_for_timeout

    async def run(self, **wait_for_kwargs):
        # Create a bunch of parallel tasks that will await using the wait_for impl being tested with different timings.
        tasks = []
        for i in range(self.task_num):
            t = asyncio.create_task(self._resource_worker(i, **wait_for_kwargs))
            t.add_done_callback(partial(self._task_done, i))
            tasks.append(t)

        # Cancel all tasks when prompted.
        await self.cancel_event.wait()
        for t in tasks:
            t.cancel()

        # Wait for all tasks to stop and evaluate the collected behaviour.
        cancel_start = time.perf_counter()
        try:
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 2 * self.CANCELLATION_TIME_LIMIT)
        except asyncio.TimeoutError:
            self.exit = True
            await asyncio.gather(*tasks, return_exceptions=True)
            assert False, "wait_for within a task ignored the cancellation"
        else:
            # NOTE: If this fails the CPU of the current machine is slow. Just raise the time limit.
            assert time.perf_counter() - cancel_start < self.CANCELLATION_TIME_LIMIT, "cancellation was slow"
        finally:
            assert all(task.done() for task in tasks), "Tasks were not terminated!"
        self._evaluate_behaviour()

    def _evaluate_behaviour(self):
        assert self.cancel_event.is_set(), "Cancellation was not initiated!"
        assert not self.resources, "resources were leaked: %s" % (len(self.resources),)
        assert self.cancelled_before_resource_creation > 0, "Cover this case"
        assert self.cancelled_during_resource_creation > 0, "Cover this case"
        assert self.waiting_timed_out == 0, "We should focus on the cancellation race right now"
        assert self.waiting_finished > 0, "Some must be successfully returned"
        assert self.cleanup_got_error > 0, "???"

    def _task_done(self, num, t):
        if not self.cancel_event.is_set() and num > self.cancel_after_task:
            self.cancel_event.set()

    async def _resource_worker(self, num: int, use_special_raise=False, **wait_for_kwargs):
        """
        This coroutine is run as a batch of tasks that acquire arbitrary resources using the wait_for_impl.
        """
        try:
            resource = await self.wait_for_impl(
                self.create_resource(num), timeout=self.wait_for_timeout, **wait_for_kwargs
            )
        except asyncio.TimeoutError:
            self.waiting_timed_out += 1
            raise
        except wait_for2.CancelledWithResultError as e:
            if use_special_raise:
                self.cleanup_resource(e.result, e.is_exception)
            raise
        except BaseException as e:
            raise
        else:
            self.waiting_finished += 1
        try:
            while not self.exit:
                await asyncio.sleep(1.0)
        finally:
            self._cleanup_resource(resource)

    def _cleanup_resource(self, resource):
        self.resources.remove(resource)

    def cleanup_resource(self, resource, exc):  # for use by race_handler
        # NOTE: If the waiting is cancelled or times out, while any result is made by the inner future, this will be
        # called. Including when the inner future raises a custom error, so the argument may be a ResourceError.
        if isinstance(resource, Resource):
            assert exc is False
            self.resources.remove(resource)
        elif isinstance(resource, ResourceError):
            assert exc is True
            self.cleanup_got_error += 1

    async def create_resource(self, num: int):
        """
        Simulates a well-behaved coroutine that acquires some resource.
        Well-behaved means that it does not leak the resource if the coroutine is cancelled or raises.
        """
        slow_before = num % 2 == 0
        slow_during = num % 4 >= 2
        period = (num // 4) % 10
        try:
            for _ in range(self.create_resource_slow_sleeps if slow_before else self.create_resource_sleeps):
                await asyncio.sleep(0.0)
            if period == 4:
                raise ResourceError("before")
            elif period == 3:
                raise asyncio.CancelledError()
        except asyncio.CancelledError:
            self.cancelled_before_resource_creation += 1
            raise
        resource = self._create_resource(num)
        try:
            for _ in range(self.create_resource_slow_sleeps if slow_during else self.create_resource_sleeps):
                await asyncio.sleep(0.0)
            if period == 9:
                raise ResourceError("during")
            elif period == 8:
                raise asyncio.CancelledError()
            return resource
        except asyncio.CancelledError:
            self.cancelled_during_resource_creation += 1
            self._cleanup_resource(resource)
            raise
        except Exception:
            self._cleanup_resource(resource)
            raise

    def _create_resource(self, num):
        # if not self.cancel_event.is_set() and num > self.cancel_after_task:
        #     self.cancel_event.set()
        resource = Resource()
        self.resources.add(resource)
        return resource

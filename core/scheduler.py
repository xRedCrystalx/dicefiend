import asyncio, logging, inspect
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, UTC
from typing import Callable, Any

logger = logging.getLogger("dicefiend.scheduler")


@dataclass
class ScheduledJob:
    id: str
    callable: Callable[..., Any]
    interval: int | timedelta | datetime
    repeat: bool = False

    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)

    on_complete: Callable[..., Any] | None = None
    on_error: Callable[..., Any] | None = None

    task: asyncio.Task[Any] | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


class TaskScheduler:
    def __init__(self) -> None:
        self.jobs: dict[str, ScheduledJob] = {}
        self.lock: asyncio.Lock = asyncio.Lock()
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()


    async def _execute_job(self, job: ScheduledJob) -> None:

        # NOTE: sanity check just in case
        if not (func := job.callable): # pyright: ignore[reportUnnecessaryComparison]
            logger.debug("TaskScheduler._execute_job > No callable")
            return

        try:
            if inspect.iscoroutinefunction(func):
                logger.debug("TaskScheduler._execute_job > Running async")
                await func(*job.args, **job.kwargs)
            else:
                logger.debug("TaskScheduler._execute_job > Running sync in thread")
                await asyncio.to_thread(func, *job.args, **job.kwargs)

            if job.on_complete:
                logger.debug("TaskScheduler._execute_job > Running running on_complete")

                if inspect.iscoroutinefunction(job.on_complete):
                    await job.on_complete()
                else:
                    await asyncio.to_thread(job.on_complete)

        except Exception as error:

            if job.on_error:
                logger.debug("TaskScheduler._execute_job > Has on_error, running it.")
                if inspect.iscoroutinefunction(job.on_error):
                    await job.on_error(error)
                else:
                    await asyncio.to_thread(job.on_error, error)

            else:
                # report only if no hook method provided
                logger.exception(f"TaskScheduler._execute_job > Error while executing {job.callable}:", error)

    async def _schedule_job(self, job: ScheduledJob, forced: bool = False) -> None:
        while True:
            try:
                if not forced:
                    delay: int = max(0, self._resolve_to_unix_timestamp(job.interval) - int(datetime.now().timestamp()))
                    logger.debug(f"TaskScheduler._schedule_job > Got delay {delay}")

                    await asyncio.sleep(delay)

                await self._execute_job(job)
                forced = False
                
                if not job.repeat:
                    logger.debug(f"TaskScheduler._schedule_job > Not repeating job - stopping")
                    break
            
            except asyncio.CancelledError:
                # ignore error if terminated by TaskScheduler.terminate
                logger.debug(f"TaskScheduler._schedule_job > Job forcefully cancelled.")
                break

            except Exception as error:
                logger.exception(f"TaskScheduler._schedule_job > Error while executing job {job.id}:", error)
                break


        async with self.lock:
            self.jobs.pop(job.id, None)
            logger.debug(f"TaskScheduler._schedule_job > Removed from jobs")

    def _resolve_to_unix_timestamp(self, value: datetime | timedelta | int) -> int:
        current_timestamp: int = int(datetime.now().timestamp())
        logger.debug(f"TaskScheduler._resolve_to_unix_timestamp > Current timestamp - {current_timestamp}")

        # resolving full datetime object
        if isinstance(value, datetime):
            logger.debug(f"TaskScheduler._resolve_to_unix_timestamp > Provided date type")
            datetime_timestamp = int(value.timestamp())

            if datetime_timestamp > current_timestamp:
                return datetime_timestamp

        # resolving timedelta
        elif isinstance(value, timedelta):
            logger.debug(f"TaskScheduler._resolve_to_unix_timestamp > Provided timedelta type")
            delta_timestamp: int = int(current_timestamp + value.total_seconds())

            if delta_timestamp > current_timestamp:
                return delta_timestamp

        # resolving provided int/float in seconds
        elif isinstance(value, int):
            logger.debug(f"TaskScheduler._resolve_to_unix_timestamp > Provided numerical type")
            if value > 0:
                return current_timestamp + int(value)

        return current_timestamp + 1 # adding one so it executes right after this

    async def _wait_till(self, time: time, job: ScheduledJob) -> None:
        current_datetime: datetime = datetime.now(tz=UTC)
        execution_date = current_datetime.date()

        # if passed, do it next day
        if current_datetime.timetz() >= time:
            logger.debug(f"TaskScheduler._wait_till > {job.id} ({job.callable}) cannot be executed today, scheduling for tomorrow")
            execution_date += timedelta(days=1)

        # combine
        execution_datetime: datetime = datetime.combine(execution_date, time, tzinfo=time.tzinfo)
        logger.debug(f"TaskScheduler._wait_till > Execution on - {execution_datetime}")

        # calculate and sleep
        sleep_time: int = max(0, int(execution_datetime.timestamp() - current_datetime.timestamp()))
        logger.debug(f"TaskScheduler._wait_till > Actual sleep time in seconds - {sleep_time}")
        await asyncio.sleep(sleep_time)

        job.task = self.loop.create_task(self._schedule_job(job, forced=True))

    async def _terminate_job_task(self, job: ScheduledJob) -> None:
        if not job.task:
            logger.debug(f"TaskScheduler._terminate_job_task > No job task found, quitting.")
            return

        job.task.cancel()
        await asyncio.sleep(0) # skips a frame to allow task cancellation

        logger.debug(f"TaskScheduler._terminate_job_task > Job cancelled.")

        # await it - memory cleanup
        try:
            await job.task
        except: pass


    async def run_in(self, id: str, when: int | timedelta, callable: Callable[..., Any], *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> None:
        logger.debug(f"TaskScheduler.run_in > Starting new job..")

        async with self.lock:
            if id in self.jobs:
                logger.debug(f"TaskScheduler.run_in > Found job with same id ({id}) - terminating it")
                await self.terminate(id)

            if not isinstance(when, timedelta | int):
                raise TypeError(f"Parameter `when` must be an int or timedelta object, not {type(when).__name__}!") # pyright: ignore[reportUnreachable]

            try:
                job = ScheduledJob(id=id, interval=when, callable=callable, args=args, kwargs=kwargs)
                job.task = self.loop.create_task(self._schedule_job(job))

                self.jobs[id] = job
                logger.debug(f"TaskScheduler.run_in > Sucessfully scheduled job.")

            except Exception as error:
                return logger.exception("TaskScheduler.run_in [<ID>] > Error while scheduling job:", error)

    async def run_at(self, id: str, when: int | datetime, callable: Callable[..., Any], *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> None:
        logger.debug(f"TaskScheduler.run_at > Starting new job..")

        async with self.lock:
            if id in self.jobs:
                logger.debug(f"TaskScheduler.run_at > Found job with same id ({id}) - terminating it")
                await self.terminate(id)

            if not isinstance(when, datetime | int):
                raise TypeError(f"Parameter `when` must be an int or datetime object, not {type(when).__name__}!") # pyright: ignore[reportUnreachable]

            try:
                when = when if isinstance(when, datetime) else datetime.fromtimestamp(when, UTC)

                job = ScheduledJob(id=id, interval=when, callable=callable, args=args, kwargs=kwargs)
                job.task = self.loop.create_task(self._schedule_job(job))

                self.jobs[id] = job
                logger.debug(f"TaskScheduler.run_at > Sucessfully scheduled job.")


            except Exception as error:
                return logger.exception("@RubyRexusSchedulerScheduler.run_at > Error while scheduling job:", error)

    async def run_every(self, id: str, interval: int | timedelta, callable: Callable[..., Any], _start: time | None = None, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> None:
        logger.debug(f"TaskScheduler.run_every > Starting new repeating job..")

        async with self.lock:
            if id in self.jobs:
                logger.debug(f"TaskScheduler.run_every > Found job with same id ({id}) - terminating it")
                await self.terminate(id)

            if isinstance(interval, datetime):
                raise TypeError("Parameter `interval` must be an int or datetime.timedelta, not datetime!")

            if not isinstance(_start, time | None):
                raise TypeError("Parameter `start` must be datetime.time or None.") # pyright: ignore[reportUnreachable]

            try:
                job = ScheduledJob(id=id, interval=interval, callable=callable, repeat=True, args=args, kwargs=kwargs)
                self.jobs[id] = job

                if _start:
                    self.loop.create_task(self._wait_till(_start, job))
                    logger.debug(f"TaskScheduler.run_every > Created background wait handler.")

                else:
                    job.task = self.loop.create_task(self._schedule_job(job))
                    logger.debug(f"TaskScheduler.run_every > Sucessfully scheduled job.")

            except Exception as error:
                return logger.exception("TaskScheduler.run_at > Error while scheduling job:", error)

    async def run_now(self, id: str) -> bool:
        async with self.lock:

            if (job := self.jobs.get(id)):
                logger.debug(f"TaskScheduler.run_now > Found job with provided ID. - {job.id}: {job.callable}")

                if job.task:
                    await self._terminate_job_task(job)
                    logger.debug(f"TaskScheduler.run_now > Terminating old task.")

                self.loop.create_task(
                    self._execute_job(job)
                )

                self.jobs.pop(id, None)
                logger.debug(f"TaskScheduler.run_now > Sucessfully executed requested job.")

                return True
            return False


    async def terminate(self, id: str) -> bool:
        async with self.lock:
            if job := self.jobs.get(id):
                logger.debug(f"TaskScheduler.terminate > Found job with provided ID.")

                await self._terminate_job_task(job)

                self.jobs.pop(id, None)
                logger.debug(f"TaskScheduler.terminate > Job terminated.")
                return True

            return False


    def is_scheduled(self, id: str) -> bool:
        return id in self.jobs

    def get_all_jobs(self) -> dict[str, ScheduledJob]:
        return self.jobs
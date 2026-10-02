from core import worker

from PySide6.QtCore import (
    QObject,
    QThread,
)

from typing import Optional, Callable

import asyncio
import functools


def threaded(func):
    """
    Run a blocking function in a QThread.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        callback = kwargs.pop(
            "callback",
            None,
        )

        def task():
            result = func(
                self,
                *args,
                **kwargs,
            )

            if callback is not None:
                callback(result)

            return result

        self.thread_manager.run(
            worker.GenericWorker,
            task,
        )

    return wrapper


def ejecutar_asincrono(coro):
    """
    Run an async coroutine inside a temporary QThread.
    """

    @functools.wraps(coro)
    def wrapper(self, *args, **kwargs):
        callback = kwargs.pop(
            "callback",
            None,
        )

        async def task():
            result = await coro(
                self,
                *args,
                **kwargs,
            )

            if callback is not None:
                callback(result)

            return result

        self.thread_manager.run(
            worker.AsyncRunnerWorker,
            task,
        )

    return wrapper


def ejecutar_protocolo_cdp(coro):
    """
    Run a coroutine on the application's persistent
    asyncio loop.

    This is used by CDP operations because aiohttp's
    WebSocket connection must remain associated with
    the same asyncio event loop.
    """

    @functools.wraps(coro)
    def wrapper(self, *args, **kwargs):
        callback = kwargs.pop(
            "callback",
            None,
        )

        loop = self.persistent_async.loop

        if loop is None or not loop.is_running():
            raise RuntimeError(
                "Persistent asyncio loop is not running."
            )

        future = asyncio.run_coroutine_threadsafe(
            coro(
                self,
                *args,
                **kwargs,
            ),
            loop,
        )

        if callback is not None:
            def completed(done):
                try:
                    callback(
                        done.result()
                    )
                except Exception as exc:
                    print(repr(exc))

            future.add_done_callback(
                completed
            )

        return future

    return wrapper


class ThreadManager:
    def __init__(self):
        self.threads = []
        self.workers = []

    def run(
        self,
        worker_class,
        *args,
        callback: Optional[Callable] = None,
        **kwargs,
    ):
        thread = QThread()

        worker_object = worker_class(
            *args,
            **kwargs,
        )

        worker_object.moveToThread(
            thread
        )

        thread.started.connect(
            worker_object.run
        )

        worker_object.finished.connect(
            thread.quit
        )
        worker_object.finished.connect(
            worker_object.deleteLater
        )

        thread.finished.connect(
            thread.deleteLater
        )

        if callback is not None:
            worker_object.result.connect(
                callback
            )

        def on_finished():
            if thread in self.threads:
                self.threads.remove(
                    thread
                )

            if worker_object in self.workers:
                self.workers.remove(
                    worker_object
                )

        thread.finished.connect(
            on_finished
        )

        self.threads.append(
            thread
        )
        self.workers.append(
            worker_object
        )

        thread.start()


class PersistentAsync(QObject):
    def __init__(self):
        super().__init__()

        self.thread_ = QThread()
        self.moveToThread(
            self.thread_
        )

        self.thread_.started.connect(
            self._run
        )

        self.loop = None

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(
            self.loop
        )

        self.loop.run_forever()

        self._cleanup_loop()

        self.thread_.quit()

    def _cleanup_loop(self):
        if self.loop is None:
            return

        try:
            pending = asyncio.all_tasks(
                self.loop
            )

            for task in pending:
                task.cancel()

            if pending:
                self.loop.run_until_complete(
                    asyncio.gather(
                        *pending,
                        return_exceptions=True,
                    )
                )

        except Exception as exc:
            print(repr(exc))

        finally:
            self.loop.close()
            self.loop = None

    def start(self):
        if not self.thread_.isRunning():
            self.thread_.start()

    def detener(self):
        loop = self.loop

        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(
                loop.detener
            )

            self.thread_.wait(3000)

        if self.thread_.isRunning():
            self.thread_.terminate()
            self.thread_.wait(1000)

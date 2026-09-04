import threading
from typing import Callable, Any, Optional


class Task:
    """Representa uma tarefa de segundo plano que pode ser monitorada e cancelada."""

    def __init__(
        self,
        name: str,
        target: Callable[..., Any],
        args: tuple = (),
        kwargs: dict = None,
        on_progress: Optional[Callable[[float, str], None]] = None,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        self.name = name
        self.target = target
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.on_progress = on_progress
        self.on_success = on_success
        self.on_error = on_error
        self.on_complete = on_complete

        self.cancel_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.is_running = False

    def start(self):
        """Inicia a tarefa em uma thread separada do pool."""
        self.is_running = True
        self.cancel_event.clear()

        # Injetar cancel_event e on_progress caso a função os receba
        self.kwargs["cancel_event"] = self.cancel_event
        self.kwargs["on_progress"] = self.on_progress

        def runner():
            try:
                result = self.target(*self.args, **self.kwargs)
                if not self.cancel_event.is_set() and self.on_success:
                    self.on_success(result)
            except Exception as e:
                if not self.cancel_event.is_set():
                    if self.on_error:
                        self.on_error(e)
                    else:
                        print(f"[Task Error] {self.name}: {e}")
            finally:
                self.is_running = False
                if self.on_complete:
                    self.on_complete()

        self.thread = threading.Thread(target=runner, name=f"Task-{self.name}", daemon=True)
        self.thread.start()

    def cancel(self):
        """Sinaliza para a tarefa abortar o processamento."""
        self.cancel_event.set()


class TaskManager:
    """Gerencia o ciclo de vida de tarefas assíncronas do aplicativo."""

    def __init__(self):
        self.active_tasks = {}

    def run_task(
        self,
        name: str,
        target: Callable[..., Any],
        args: tuple = (),
        kwargs: dict = None,
        on_progress: Optional[Callable[[float, str], None]] = None,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> Task:
        # Se já existir uma tarefa com esse nome ativa, cancela a anterior
        if name in self.active_tasks and self.active_tasks[name].is_running:
            self.active_tasks[name].cancel()

        def wrapped_complete():
            if name in self.active_tasks:
                del self.active_tasks[name]
            if on_complete:
                on_complete()

        task = Task(
            name=name,
            target=target,
            args=args,
            kwargs=kwargs,
            on_progress=on_progress,
            on_success=on_success,
            on_error=on_error,
            on_complete=wrapped_complete,
        )
        self.active_tasks[name] = task
        task.start()
        return task

    def cancel_task(self, name: str):
        if name in self.active_tasks:
            self.active_tasks[name].cancel()

    def cancel_all(self):
        for task in list(self.active_tasks.values()):
            task.cancel()


task_manager = TaskManager()

"""
Parallel Execution Scheduler for the Orchestrator Agent.

Implements dependency-aware parallel task execution with:
- Concurrent execution of independent tasks
- Dependency graph resolution (DAG)
- Synchronization for task handoffs
- Resource optimization (minimal idle time)
- Error handling and recovery
"""

import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError, as_completed
from dataclasses import dataclass
from typing import Any

from src.models.agent import Agent
from src.models.task import Subtask


@dataclass
class ExecutionResult:
    """Result of a task execution."""

    task_id: str
    status: str  # "completed", "failed", "timeout", "skipped"
    result: dict | None = None
    error: str | None = None
    duration: float = 0.0


@dataclass
class ExecutionStats:
    """Statistics about execution."""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    total_time: float = 0.0
    max_concurrent: int = 0


class ParallelExecutionScheduler:
    """
    Parallel execution scheduler with dependency-aware scheduling.

    Features:
    - Executes independent tasks concurrently
    - Respects task dependencies (DAG)
    - Synchronizes task handoffs between agents
    - Optimizes for minimal idle time
    - Handles errors gracefully
    """

    def __init__(
        self,
        agents: list[Agent],
        max_workers: int | None = None,
        task_timeout: float | None = None,
    ):
        """
        Initialize the parallel execution scheduler.

        Args:
            agents: List of available agents
            max_workers: Maximum number of concurrent tasks (default: number of agents)
            task_timeout: Timeout per task in seconds (default: None)
        """
        self.agents = agents
        self.max_workers = max_workers or len(agents)
        self.task_timeout = task_timeout
        self._stats = ExecutionStats()
        self._task_results: dict[str, Any] = {}
        self._active_count = 0
        self._max_concurrent_observed = 0

    def execute_tasks(
        self,
        tasks: list[Subtask],
        executor_func: Callable[[Subtask], dict],
        continue_on_error: bool = False,
    ) -> list[dict]:
        """
        Execute tasks in parallel while respecting dependencies.

        Args:
            tasks: List of subtasks to execute
            executor_func: Function that executes a single task
            continue_on_error: If True, continue executing independent tasks after failures

        Returns:
            List of execution results
        """
        start_time = time.time()

        # Build dependency graph
        task_map = {task.id: task for task in tasks}
        dependency_graph = self._build_dependency_graph(tasks)

        # Track task states
        pending: set[str] = set(task.id for task in tasks)
        completed: set[str] = set()
        failed: set[str] = set()
        in_progress: set[str] = set()

        results: list[dict] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures: dict[Future, str] = {}  # future -> task_id

            while pending or in_progress:
                # Find tasks ready to execute (all dependencies met)
                ready = self._get_ready_tasks(pending, completed, failed, dependency_graph)

                # Submit ready tasks
                for task_id in ready:
                    if len(futures) >= self.max_workers:
                        break  # Wait for some tasks to complete

                    task = task_map[task_id]
                    future = executor.submit(self._execute_task, task, executor_func)
                    futures[future] = task_id
                    pending.remove(task_id)
                    in_progress.add(task_id)

                    # Track concurrency
                    self._active_count += 1
                    self._max_concurrent_observed = max(
                        self._max_concurrent_observed, self._active_count
                    )

                # Wait for at least one task to complete or timeout
                if futures:
                    done_futures, timed_out_futures = self._wait_with_timeout(futures)

                    # Process completed futures
                    for future in done_futures:
                        task_id = futures.pop(future)
                        in_progress.remove(task_id)
                        self._active_count -= 1

                        try:
                            result = future.result(timeout=0.01)  # Should be immediate
                            completed.add(task_id)
                            self._task_results[task_id] = result
                            results.append(result)
                            self._stats.completed_tasks += 1
                        except Exception as e:
                            # Task raised an exception
                            failed.add(task_id)
                            error_result = {
                                "task_id": task_id,
                                "status": "failed",
                                "error": str(e),
                            }
                            results.append(error_result)
                            self._stats.failed_tasks += 1

                            if not continue_on_error:
                                # Cancel remaining futures
                                for f in futures:
                                    f.cancel()
                                break

                    # Process timed out futures
                    for future in timed_out_futures:
                        task_id = futures.pop(future)
                        in_progress.remove(task_id)
                        self._active_count -= 1

                        failed.add(task_id)
                        error_result = {
                            "task_id": task_id,
                            "status": "timeout",
                            "error": "Task exceeded timeout",
                        }
                        results.append(error_result)
                        self._stats.failed_tasks += 1

                        # Cancel the timed out future
                        future.cancel()

                        if not continue_on_error:
                            # Cancel remaining futures
                            for f in futures:
                                f.cancel()
                            break

                # If we can't make progress and continue_on_error is True,
                # skip tasks that depend on failed tasks
                if not ready and pending and continue_on_error:
                    # Find tasks that can never complete (depend on failed tasks)
                    skippable = self._find_skippable_tasks(
                        pending, completed, failed, dependency_graph
                    )
                    for task_id in skippable:
                        pending.remove(task_id)
                        results.append({
                            "task_id": task_id,
                            "status": "skipped",
                            "error": "Dependency failed",
                        })
                        self._stats.skipped_tasks += 1

        self._stats.total_tasks = len(tasks)
        self._stats.total_time = time.time() - start_time
        self._stats.max_concurrent = self._max_concurrent_observed

        return results

    def _execute_task(self, task: Subtask, executor_func: Callable[[Subtask], dict]) -> dict:
        """
        Execute a single task.

        Args:
            task: Subtask to execute
            executor_func: Function to execute the task

        Returns:
            Task result

        Raises:
            Exception: Any exception raised by executor_func
        """
        result = executor_func(task)

        # Ensure result has task_id
        if "task_id" not in result:
            result["task_id"] = task.id

        # Add status if not present
        if "status" not in result:
            result["status"] = "completed"

        return result

    def _build_dependency_graph(self, tasks: list[Subtask]) -> dict[str, list[str]]:
        """
        Build a dependency graph from tasks.

        Args:
            tasks: List of subtasks

        Returns:
            Dictionary mapping task_id -> list of dependency task_ids
        """
        graph = {}
        for task in tasks:
            graph[task.id] = task.dependencies if task.dependencies else []
        return graph

    def _get_ready_tasks(
        self,
        pending: set[str],
        completed: set[str],
        failed: set[str],
        dependency_graph: dict[str, list[str]],
    ) -> list[str]:
        """
        Get tasks that are ready to execute (all dependencies met).

        Args:
            pending: Set of pending task IDs
            completed: Set of completed task IDs
            failed: Set of failed task IDs
            dependency_graph: Dependency graph

        Returns:
            List of task IDs ready to execute
        """
        ready = []
        for task_id in pending:
            deps = dependency_graph.get(task_id, [])
            # Check if all dependencies are completed
            if all(dep in completed for dep in deps):
                ready.append(task_id)
        return ready

    def _find_skippable_tasks(
        self,
        pending: set[str],
        completed: set[str],
        failed: set[str],
        dependency_graph: dict[str, list[str]],
    ) -> list[str]:
        """
        Find tasks that should be skipped because dependencies failed.

        Args:
            pending: Set of pending task IDs
            completed: Set of completed task IDs
            failed: Set of failed task IDs
            dependency_graph: Dependency graph

        Returns:
            List of task IDs to skip
        """
        skippable = []
        for task_id in pending:
            deps = dependency_graph.get(task_id, [])
            # If any dependency failed, skip this task
            if any(dep in failed for dep in deps):
                skippable.append(task_id)
        return skippable

    def _wait_with_timeout(
        self, futures: dict[Future, str]
    ) -> tuple[set[Future], set[Future]]:
        """
        Wait for futures to complete or timeout.

        Args:
            futures: Dictionary of futures

        Returns:
            Tuple of (done futures, timed out futures)
        """
        done = set()
        timed_out = set()

        if self.task_timeout is None:
            # No timeout - wait for first completion
            for future in as_completed(futures.keys()):
                done.add(future)
                break
        else:
            # Wait with timeout
            try:
                for future in as_completed(futures.keys(), timeout=self.task_timeout):
                    done.add(future)
                    break
            except TimeoutError:
                # Find which future(s) timed out
                for future in futures.keys():
                    if not future.done():
                        timed_out.add(future)
                    elif future not in done:
                        done.add(future)

        return done, timed_out

    def get_execution_stats(self) -> dict:
        """
        Get execution statistics.

        Returns:
            Dictionary with execution stats
        """
        return {
            "total_tasks": self._stats.total_tasks,
            "completed_tasks": self._stats.completed_tasks,
            "failed_tasks": self._stats.failed_tasks,
            "skipped_tasks": self._stats.skipped_tasks,
            "total_time": self._stats.total_time,
            "max_concurrent": self._stats.max_concurrent,
        }

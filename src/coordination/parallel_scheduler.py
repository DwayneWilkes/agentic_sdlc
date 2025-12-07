"""Parallel Execution Scheduler for concurrent task execution.

Implements:
- Parallel task dispatching with concurrency limits
- Dependency-aware scheduling (respects task prerequisites)
- Task handoff synchronization between agents
- Idle time optimization for resource utilization
"""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.models.agent import Agent
from src.models.enums import TaskStatus
from src.models.task import Subtask


@dataclass
class TaskExecutionState:
    """Represents the execution state of a task."""

    task_id: str
    agent_id: str
    status: TaskStatus
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    result_data: dict[str, Any] = field(default_factory=dict)


class DependencyResolver:
    """Resolves task dependencies and determines execution order.

    Ensures tasks only execute after their prerequisites complete.
    Validates dependency graph for cycles and missing dependencies.
    """

    def __init__(self, tasks: list[Subtask]):
        """Initialize dependency resolver.

        Args:
            tasks: List of subtasks with dependency information
        """
        self.tasks = tasks
        self._task_map = {t.id: t for t in tasks}

    def validate_dependencies(self) -> None:
        """Validate that all dependencies exist and there are no cycles.

        Raises:
            ValueError: If circular dependencies or missing dependencies found
        """
        # Check for missing dependencies
        for task in self.tasks:
            for dep_id in task.dependencies:
                if dep_id not in self._task_map:
                    raise ValueError(
                        f"Missing dependency: task {task.id} depends on "
                        f"non-existent task {dep_id}"
                    )

        # Check for circular dependencies using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = self._task_map[task_id]
            for dep_id in task.dependencies:
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task in self.tasks:
            if task.id not in visited:
                if has_cycle(task.id):
                    raise ValueError(
                        f"Circular dependency detected involving task {task.id}"
                    )

    def get_ready_tasks(self, completed_task_ids: set[str]) -> list[Subtask]:
        """Get tasks that are ready to execute.

        A task is ready if:
        - It's not already completed
        - All its dependencies are completed

        Args:
            completed_task_ids: Set of task IDs that have completed

        Returns:
            List of tasks ready for execution
        """
        ready = []

        for task in self.tasks:
            # Skip if already completed
            if task.id in completed_task_ids:
                continue

            # Check if all dependencies are met
            deps_met = all(dep_id in completed_task_ids for dep_id in task.dependencies)

            if deps_met:
                ready.append(task)

        return ready


class ParallelTaskDispatcher:
    """Dispatches tasks for parallel execution with concurrency limits.

    Features:
    - Concurrent task execution with configurable limits
    - Dependency-aware scheduling
    - Async execution with proper error handling
    """

    def __init__(
        self,
        agents: list[Agent],
        tasks: list[Subtask],
        max_concurrent: int = 5,
    ):
        """Initialize parallel task dispatcher.

        Args:
            agents: Available agents for task execution
            tasks: Tasks to execute
            max_concurrent: Maximum number of concurrent tasks
        """
        self.agents = agents
        self.tasks = tasks
        self.max_concurrent = max_concurrent
        self.dependency_resolver = DependencyResolver(tasks)

        # Validate dependencies on creation
        self.dependency_resolver.validate_dependencies()

    async def dispatch_all(
        self,
        execute_fn: Callable[[Subtask, Agent], Awaitable[TaskExecutionState]],
    ) -> list[TaskExecutionState]:
        """Dispatch all tasks respecting dependencies and concurrency limits.

        Args:
            execute_fn: Async function to execute a task with an agent

        Returns:
            List of execution states for all tasks
        """
        completed_task_ids: set[str] = set()
        results: list[TaskExecutionState] = []
        running_tasks: dict[str, asyncio.Task] = {}  # task_id -> async Task

        while len(completed_task_ids) < len(self.tasks):
            # Get tasks ready to execute
            ready_tasks = self.dependency_resolver.get_ready_tasks(completed_task_ids)

            # Filter out tasks already running
            ready_tasks = [t for t in ready_tasks if t.id not in running_tasks]

            # Dispatch new tasks up to concurrency limit
            available_slots = self.max_concurrent - len(running_tasks)

            for task in ready_tasks[:available_slots]:
                # Find an available agent (simple round-robin for now)
                agent = self._get_available_agent()
                if not agent:
                    continue  # Skip if no agent available

                # Create async task
                async_task = asyncio.create_task(
                    self._execute_with_error_handling(task, agent, execute_fn)
                )
                running_tasks[task.id] = async_task

            # Wait for at least one task to complete
            if running_tasks:
                done, pending = await asyncio.wait(
                    running_tasks.values(),
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # Process completed tasks
                for async_task in done:
                    result = await async_task
                    results.append(result)
                    completed_task_ids.add(result.task_id)

                    # Remove from running tasks
                    running_tasks = {
                        tid: t for tid, t in running_tasks.items() if t not in done
                    }

            # If no tasks running and no tasks ready, we have a problem
            if not running_tasks and not ready_tasks:
                break

        return results

    async def _execute_with_error_handling(
        self,
        task: Subtask,
        agent: Agent,
        execute_fn: Callable[[Subtask, Agent], Awaitable[TaskExecutionState]],
    ) -> TaskExecutionState:
        """Execute a task with error handling.

        Args:
            task: Task to execute
            agent: Agent executing the task
            execute_fn: Execution function

        Returns:
            TaskExecutionState (either success or failure)
        """
        try:
            result = await execute_fn(task, agent)
            return result
        except Exception as e:
            # Return failed state
            return TaskExecutionState(
                task_id=task.id,
                agent_id=agent.id,
                status=TaskStatus.FAILED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                error=str(e),
            )

    def _get_available_agent(self) -> Agent | None:
        """Get an available agent (simple round-robin).

        Returns:
            An available agent or None if no agents available
        """
        # Simple implementation - just return first agent
        # In a real system, this would check agent status, workload, etc.
        return self.agents[0] if self.agents else None


@dataclass
class Handoff:
    """Represents a task handoff between agents."""

    id: str
    from_agent: str
    to_agent: str
    task_id: str
    data: dict[str, Any]
    created_at: datetime
    received_at: datetime | None = None
    acknowledged_at: datetime | None = None


class SynchronizationManager:
    """Manages task handoffs and synchronization between agents.

    Ensures clean state transfer when tasks transition between agents.
    Prevents race conditions and data loss during handoffs.
    """

    def __init__(self, timeout_seconds: float = 300.0):
        """Initialize synchronization manager.

        Args:
            timeout_seconds: How long before handoffs expire (default 5 min)
        """
        self.timeout_seconds = timeout_seconds
        self._handoffs: dict[str, Handoff] = {}

    def initiate_handoff(
        self,
        from_agent: str,
        to_agent: str,
        task_id: str,
        data: dict[str, Any],
    ) -> str:
        """Initiate a task handoff from one agent to another.

        Args:
            from_agent: Agent ID passing the task
            to_agent: Agent ID receiving the task
            task_id: ID of task being handed off
            data: Handoff data (results, state, etc.)

        Returns:
            Handoff ID for tracking
        """
        handoff_id = str(uuid.uuid4())

        handoff = Handoff(
            id=handoff_id,
            from_agent=from_agent,
            to_agent=to_agent,
            task_id=task_id,
            data=data,
            created_at=datetime.now(UTC),
        )

        self._handoffs[handoff_id] = handoff
        return handoff_id

    def receive_handoff(self, handoff_id: str, agent_id: str) -> dict[str, Any]:
        """Receive a handoff (must be the designated recipient).

        Args:
            handoff_id: ID of handoff to receive
            agent_id: Agent ID attempting to receive

        Returns:
            Handoff data

        Raises:
            ValueError: If handoff not found, expired, or wrong recipient
        """
        if handoff_id not in self._handoffs:
            raise ValueError(f"Handoff {handoff_id} not found")

        handoff = self._handoffs[handoff_id]

        # Check authorization
        if handoff.to_agent != agent_id:
            raise ValueError(
                f"Agent {agent_id} is not authorized to receive handoff {handoff_id}"
            )

        # Check timeout
        elapsed = (datetime.now(UTC) - handoff.created_at).total_seconds()
        if elapsed > self.timeout_seconds:
            raise ValueError(f"Handoff {handoff_id} has expired")

        # Mark as received
        handoff.received_at = datetime.now(UTC)

        return handoff.data

    def acknowledge_handoff(self, handoff_id: str, agent_id: str) -> None:
        """Acknowledge successful handoff receipt.

        Args:
            handoff_id: ID of handoff to acknowledge
            agent_id: Agent ID acknowledging

        Raises:
            ValueError: If handoff not found or wrong agent
        """
        if handoff_id not in self._handoffs:
            raise ValueError(f"Handoff {handoff_id} not found")

        handoff = self._handoffs[handoff_id]

        if handoff.to_agent != agent_id:
            raise ValueError(
                f"Agent {agent_id} cannot acknowledge handoff {handoff_id}"
            )

        handoff.acknowledged_at = datetime.now(UTC)

    def is_handoff_complete(self, handoff_id: str) -> bool:
        """Check if handoff is complete (acknowledged).

        Args:
            handoff_id: ID of handoff to check

        Returns:
            True if acknowledged, False otherwise
        """
        if handoff_id not in self._handoffs:
            return False

        handoff = self._handoffs[handoff_id]
        return handoff.acknowledged_at is not None


@dataclass
class AgentUtilization:
    """Tracks agent utilization for idle time optimization."""

    agent_id: str
    is_busy: bool = False
    current_task_id: str | None = None
    task_started_at: datetime | None = None
    total_busy_time: float = 0.0
    total_idle_time: float = 0.0


class IdleTimeOptimizer:
    """Optimizes agent utilization to minimize idle time.

    Tracks which agents are working vs. idle and provides
    suggestions for rebalancing workload.
    """

    def __init__(self, agents: list[Agent]):
        """Initialize idle time optimizer.

        Args:
            agents: List of agents to track
        """
        self.agents = agents
        self._utilization: dict[str, AgentUtilization] = {
            agent.id: AgentUtilization(agent_id=agent.id) for agent in agents
        }

    def mark_agent_busy(self, agent_id: str, task_id: str) -> None:
        """Mark an agent as busy working on a task.

        Args:
            agent_id: ID of agent
            task_id: ID of task being worked on
        """
        if agent_id not in self._utilization:
            return

        util = self._utilization[agent_id]
        util.is_busy = True
        util.current_task_id = task_id
        util.task_started_at = datetime.now(UTC)

    def mark_agent_idle(self, agent_id: str) -> None:
        """Mark an agent as idle (completed or waiting for work).

        Args:
            agent_id: ID of agent
        """
        if agent_id not in self._utilization:
            return

        util = self._utilization[agent_id]

        # Calculate busy time if was working
        if util.is_busy and util.task_started_at:
            busy_duration = (datetime.now(UTC) - util.task_started_at).total_seconds()
            util.total_busy_time += busy_duration

        util.is_busy = False
        util.current_task_id = None
        util.task_started_at = None

    def is_agent_busy(self, agent_id: str) -> bool:
        """Check if an agent is currently busy.

        Args:
            agent_id: ID of agent to check

        Returns:
            True if busy, False if idle
        """
        if agent_id not in self._utilization:
            return False

        return self._utilization[agent_id].is_busy

    def get_idle_agents(self) -> list[Agent]:
        """Get list of currently idle agents.

        Returns:
            List of idle agents
        """
        idle_agent_ids = [
            agent_id for agent_id, util in self._utilization.items() if not util.is_busy
        ]

        return [a for a in self.agents if a.id in idle_agent_ids]

    def get_utilization(self) -> float:
        """Calculate overall agent utilization percentage.

        Returns:
            Percentage of agents currently busy (0-100)
        """
        if not self.agents:
            return 0.0

        busy_count = sum(1 for util in self._utilization.values() if util.is_busy)
        return (busy_count / len(self.agents)) * 100.0

    def should_rebalance(self, threshold: float = 50.0) -> bool:
        """Check if workload should be rebalanced.

        Args:
            threshold: Utilization threshold below which rebalancing is suggested

        Returns:
            True if utilization is below threshold
        """
        return self.get_utilization() < threshold

    def record_idle_time(self, agent_id: str, duration_seconds: float) -> None:
        """Record idle time for an agent.

        Args:
            agent_id: ID of agent
            duration_seconds: Duration of idle period
        """
        if agent_id in self._utilization:
            self._utilization[agent_id].total_idle_time += duration_seconds


@dataclass
class SchedulerMetrics:
    """Tracks scheduler performance metrics."""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    in_progress_tasks: int = 0
    _task_durations: list[float] = field(default_factory=list)
    _task_start_times: dict[str, datetime] = field(default_factory=dict)
    _total_idle_time: float = 0.0

    def record_task_started(self, task_id: str) -> None:
        """Record that a task has started.

        Args:
            task_id: ID of started task
        """
        self.total_tasks += 1
        self.in_progress_tasks += 1
        self._task_start_times[task_id] = datetime.now(UTC)

    def record_task_completed(self, task_id: str, duration_seconds: float) -> None:
        """Record that a task completed successfully.

        Args:
            task_id: ID of completed task
            duration_seconds: How long the task took
        """
        self.completed_tasks += 1
        self.in_progress_tasks -= 1
        self._task_durations.append(duration_seconds)

        if task_id in self._task_start_times:
            del self._task_start_times[task_id]

    def record_task_failed(self, task_id: str) -> None:
        """Record that a task failed.

        Args:
            task_id: ID of failed task
        """
        self.failed_tasks += 1
        self.in_progress_tasks -= 1

        if task_id in self._task_start_times:
            del self._task_start_times[task_id]

    def get_average_duration(self) -> float:
        """Get average task duration.

        Returns:
            Average duration in seconds, or 0 if no tasks completed
        """
        if not self._task_durations:
            return 0.0

        return sum(self._task_durations) / len(self._task_durations)

    def record_idle_time(self, agent_id: str, duration_seconds: float) -> None:
        """Record idle time for metrics.

        Args:
            agent_id: ID of agent that was idle
            duration_seconds: Duration of idle period
        """
        self._total_idle_time += duration_seconds

    def get_total_idle_time(self) -> float:
        """Get total idle time across all agents.

        Returns:
            Total idle time in seconds
        """
        return self._total_idle_time

    def get_efficiency_score(self) -> float:
        """Calculate scheduler efficiency (work time / total time).

        Returns:
            Efficiency percentage (0-100)
        """
        total_work_time = sum(self._task_durations)
        total_time = total_work_time + self._total_idle_time

        if total_time == 0:
            return 0.0

        return (total_work_time / total_time) * 100.0

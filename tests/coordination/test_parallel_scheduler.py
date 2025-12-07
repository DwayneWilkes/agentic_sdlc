"""Tests for Parallel Execution Scheduler.

Tests the parallel task dispatch, dependency resolution, synchronization,
and idle time optimization components.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from src.coordination.parallel_scheduler import (
    DependencyResolver,
    IdleTimeOptimizer,
    ParallelTaskDispatcher,
    SchedulerMetrics,
    SynchronizationManager,
    TaskExecutionState,
)
from src.models.agent import Agent, AgentCapability, AgentStatus
from src.models.enums import TaskStatus
from src.models.task import Subtask


@pytest.fixture
def sample_agents():
    """Create sample agents for testing."""
    return [
        Agent(
            id="agent-1",
            role="developer",
            capabilities=[
                AgentCapability(
                    name="python",
                    description="Python development",
                    tools=["pytest", "mypy"],
                ),
                AgentCapability(
                    name="testing", description="Test writing", tools=["pytest"]
                ),
            ],
            status=AgentStatus.IDLE,
        ),
        Agent(
            id="agent-2",
            role="developer",
            capabilities=[
                AgentCapability(
                    name="python",
                    description="Python development",
                    tools=["pytest"],
                ),
                AgentCapability(
                    name="documentation",
                    description="Documentation writing",
                    tools=["mkdocs"],
                ),
            ],
            status=AgentStatus.IDLE,
        ),
        Agent(
            id="agent-3",
            role="tester",
            capabilities=[
                AgentCapability(
                    name="testing",
                    description="Advanced testing",
                    tools=["pytest", "coverage"],
                ),
            ],
            status=AgentStatus.IDLE,
        ),
    ]


@pytest.fixture
def independent_tasks():
    """Create independent tasks (no dependencies)."""
    return [
        Subtask(
            id="task-1",
            description="Write function A",
            dependencies=[],
            status=TaskStatus.PENDING,
        ),
        Subtask(
            id="task-2",
            description="Write function B",
            dependencies=[],
            status=TaskStatus.PENDING,
        ),
        Subtask(
            id="task-3",
            description="Write function C",
            dependencies=[],
            status=TaskStatus.PENDING,
        ),
    ]


@pytest.fixture
def dependent_tasks():
    """Create tasks with dependencies (DAG structure)."""
    return [
        Subtask(
            id="task-1",
            description="Design API",
            dependencies=[],
            status=TaskStatus.PENDING,
        ),
        Subtask(
            id="task-2",
            description="Implement API",
            dependencies=["task-1"],  # Depends on task-1
            status=TaskStatus.PENDING,
        ),
        Subtask(
            id="task-3",
            description="Write tests",
            dependencies=["task-2"],  # Depends on task-2
            status=TaskStatus.PENDING,
        ),
        Subtask(
            id="task-4",
            description="Write docs",
            dependencies=["task-1"],  # Also depends on task-1 (parallel with task-2)
            status=TaskStatus.PENDING,
        ),
    ]


class TestDependencyResolver:
    """Test dependency resolution for task scheduling."""

    def test_create_resolver(self):
        """Test creating a dependency resolver."""
        tasks = [
            Subtask(id="t1", description="Task 1", dependencies=[]),
            Subtask(id="t2", description="Task 2", dependencies=["t1"]),
        ]
        resolver = DependencyResolver(tasks)
        assert resolver is not None
        assert len(resolver.tasks) == 2

    def test_get_ready_tasks_no_dependencies(self, independent_tasks):
        """Test getting ready tasks when all are independent."""
        resolver = DependencyResolver(independent_tasks)
        completed = set()

        ready = resolver.get_ready_tasks(completed)

        # All tasks should be ready since none have dependencies
        assert len(ready) == 3
        assert set(t.id for t in ready) == {"task-1", "task-2", "task-3"}

    def test_get_ready_tasks_with_dependencies(self, dependent_tasks):
        """Test getting ready tasks with dependency constraints."""
        resolver = DependencyResolver(dependent_tasks)

        # Initially, only task-1 (no dependencies) should be ready
        ready = resolver.get_ready_tasks(set())
        assert len(ready) == 1
        assert ready[0].id == "task-1"

        # After task-1 completes, task-2 and task-4 should be ready
        ready = resolver.get_ready_tasks({"task-1"})
        assert len(ready) == 2
        assert set(t.id for t in ready) == {"task-2", "task-4"}

        # After task-2 completes, task-3 should be ready
        ready = resolver.get_ready_tasks({"task-1", "task-2"})
        assert len(ready) == 2  # task-3 and task-4
        assert "task-3" in [t.id for t in ready]
        assert "task-4" in [t.id for t in ready]

    def test_detect_circular_dependencies(self):
        """Test detection of circular dependencies."""
        circular_tasks = [
            Subtask(id="t1", description="Task 1", dependencies=["t2"]),
            Subtask(id="t2", description="Task 2", dependencies=["t1"]),
        ]

        with pytest.raises(ValueError, match="Circular dependency"):
            resolver = DependencyResolver(circular_tasks)
            resolver.validate_dependencies()

    def test_detect_missing_dependencies(self):
        """Test detection of missing dependency targets."""
        tasks = [
            Subtask(id="t1", description="Task 1", dependencies=["t-nonexistent"]),
        ]

        with pytest.raises(ValueError, match="Missing dependency"):
            resolver = DependencyResolver(tasks)
            resolver.validate_dependencies()

    def test_all_tasks_complete(self, dependent_tasks):
        """Test when all tasks are complete."""
        resolver = DependencyResolver(dependent_tasks)
        all_ids = {t.id for t in dependent_tasks}

        ready = resolver.get_ready_tasks(all_ids)
        assert len(ready) == 0  # No tasks ready when all complete


class TestParallelTaskDispatcher:
    """Test parallel task dispatching."""

    @pytest.mark.asyncio
    async def test_create_dispatcher(self, sample_agents, independent_tasks):
        """Test creating a parallel task dispatcher."""
        dispatcher = ParallelTaskDispatcher(
            agents=sample_agents,
            tasks=independent_tasks,
            max_concurrent=2,
        )
        assert dispatcher is not None
        assert len(dispatcher.agents) == 3
        assert len(dispatcher.tasks) == 3

    @pytest.mark.asyncio
    async def test_dispatch_independent_tasks(self, sample_agents, independent_tasks):
        """Test dispatching independent tasks runs them in parallel."""
        dispatcher = ParallelTaskDispatcher(
            agents=sample_agents,
            tasks=independent_tasks,
            max_concurrent=3,  # Allow all to run
        )

        # Mock task execution
        async def mock_execute(task: Subtask, agent: Agent):
            await asyncio.sleep(0.01)  # Simulate work
            return TaskExecutionState(
                task_id=task.id,
                agent_id=agent.id,
                status=TaskStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )

        results = await dispatcher.dispatch_all(execute_fn=mock_execute)

        # All tasks should complete
        assert len(results) == 3
        assert all(r.status == TaskStatus.COMPLETED for r in results)

    @pytest.mark.asyncio
    async def test_respect_max_concurrent_limit(self, sample_agents):
        """Test that max_concurrent limit is respected."""
        # Create many tasks
        many_tasks = [
            Subtask(id=f"task-{i}", description=f"Task {i}", dependencies=[])
            for i in range(10)
        ]

        dispatcher = ParallelTaskDispatcher(
            agents=sample_agents,
            tasks=many_tasks,
            max_concurrent=2,  # Only 2 at a time
        )

        concurrent_count = 0
        max_seen = 0

        async def mock_execute(task: Subtask, agent: Agent):
            nonlocal concurrent_count, max_seen
            concurrent_count += 1
            max_seen = max(max_seen, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return TaskExecutionState(
                task_id=task.id,
                agent_id=agent.id,
                status=TaskStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )

        await dispatcher.dispatch_all(execute_fn=mock_execute)

        # Should never exceed max_concurrent
        assert max_seen <= 2

    @pytest.mark.asyncio
    async def test_dispatch_with_dependencies(self, sample_agents, dependent_tasks):
        """Test dispatching tasks with dependencies respects order."""
        dispatcher = ParallelTaskDispatcher(
            agents=sample_agents,
            tasks=dependent_tasks,
            max_concurrent=4,
        )

        execution_order = []

        async def mock_execute(task: Subtask, agent: Agent):
            execution_order.append(task.id)
            await asyncio.sleep(0.01)
            return TaskExecutionState(
                task_id=task.id,
                agent_id=agent.id,
                status=TaskStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )

        await dispatcher.dispatch_all(execute_fn=mock_execute)

        # Verify execution order respects dependencies
        # task-1 must execute before task-2 and task-4
        task1_idx = execution_order.index("task-1")
        task2_idx = execution_order.index("task-2")
        task4_idx = execution_order.index("task-4")

        assert task1_idx < task2_idx, "task-1 must execute before task-2"
        assert task1_idx < task4_idx, "task-1 must execute before task-4"

        # task-2 must execute before task-3
        task3_idx = execution_order.index("task-3")
        assert task2_idx < task3_idx, "task-2 must execute before task-3"

    @pytest.mark.asyncio
    async def test_handle_task_failure(self, sample_agents, independent_tasks):
        """Test handling task failures doesn't block other tasks."""
        dispatcher = ParallelTaskDispatcher(
            agents=sample_agents,
            tasks=independent_tasks,
            max_concurrent=3,
        )

        async def mock_execute(task: Subtask, agent: Agent):
            if task.id == "task-2":
                # Fail task-2
                raise Exception("Task failed!")

            await asyncio.sleep(0.01)
            return TaskExecutionState(
                task_id=task.id,
                agent_id=agent.id,
                status=TaskStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )

        results = await dispatcher.dispatch_all(execute_fn=mock_execute)

        # task-1 and task-3 should still complete
        completed = [r for r in results if r.status == TaskStatus.COMPLETED]
        failed = [r for r in results if r.status == TaskStatus.FAILED]

        assert len(completed) == 2
        assert len(failed) == 1
        assert failed[0].task_id == "task-2"


class TestSynchronizationManager:
    """Test task handoff synchronization."""

    def test_create_sync_manager(self):
        """Test creating a synchronization manager."""
        manager = SynchronizationManager()
        assert manager is not None

    def test_handoff_simple(self):
        """Test simple task handoff between agents."""
        manager = SynchronizationManager()

        # Agent-1 completes task and hands off to agent-2
        handoff_data = {"result": "API implemented", "files": ["api.py"]}

        handoff_id = manager.initiate_handoff(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="task-1",
            data=handoff_data,
        )

        assert handoff_id is not None

        # Agent-2 receives handoff
        received = manager.receive_handoff(handoff_id, "agent-2")
        assert received == handoff_data

    def test_handoff_requires_receiver(self):
        """Test that only the intended receiver can get handoff data."""
        manager = SynchronizationManager()

        handoff_id = manager.initiate_handoff(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="task-1",
            data={"result": "done"},
        )

        # Wrong agent tries to receive
        with pytest.raises(ValueError, match="not authorized"):
            manager.receive_handoff(handoff_id, "agent-3")

    def test_handoff_timeout(self):
        """Test that handoffs expire after timeout."""
        manager = SynchronizationManager(timeout_seconds=0.1)

        handoff_id = manager.initiate_handoff(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="task-1",
            data={"result": "done"},
        )

        # Wait for timeout
        import time

        time.sleep(0.2)

        # Should be expired
        with pytest.raises(ValueError, match="expired"):
            manager.receive_handoff(handoff_id, "agent-2")

    def test_wait_for_handoff(self):
        """Test blocking wait for handoff completion."""
        manager = SynchronizationManager()

        handoff_id = manager.initiate_handoff(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="task-1",
            data={"result": "done"},
        )

        # Simulate agent-2 receiving handoff in another "thread"
        # (we'll just do it synchronously for testing)
        _ = manager.receive_handoff(handoff_id, "agent-2")

        # Mark as complete
        manager.acknowledge_handoff(handoff_id, "agent-2")

        # Should be marked complete
        assert manager.is_handoff_complete(handoff_id)


class TestIdleTimeOptimizer:
    """Test idle time optimization for agents."""

    def test_create_optimizer(self, sample_agents):
        """Test creating an idle time optimizer."""
        optimizer = IdleTimeOptimizer(agents=sample_agents)
        assert optimizer is not None

    def test_track_agent_utilization(self, sample_agents):
        """Test tracking agent utilization."""
        optimizer = IdleTimeOptimizer(agents=sample_agents)

        # Mark agent as working
        optimizer.mark_agent_busy("agent-1", "task-1")
        assert optimizer.is_agent_busy("agent-1")
        assert not optimizer.is_agent_busy("agent-2")

        # Mark agent as idle
        optimizer.mark_agent_idle("agent-1")
        assert not optimizer.is_agent_busy("agent-1")

    def test_get_idle_agents(self, sample_agents):
        """Test getting list of idle agents."""
        optimizer = IdleTimeOptimizer(agents=sample_agents)

        # Initially all idle
        idle = optimizer.get_idle_agents()
        assert len(idle) == 3

        # Mark one busy
        optimizer.mark_agent_busy("agent-1", "task-1")
        idle = optimizer.get_idle_agents()
        assert len(idle) == 2
        assert "agent-1" not in [a.id for a in idle]

    def test_calculate_utilization(self, sample_agents):
        """Test calculating overall utilization percentage."""
        optimizer = IdleTimeOptimizer(agents=sample_agents)

        # No agents busy
        assert optimizer.get_utilization() == 0.0

        # One agent busy (out of 3)
        optimizer.mark_agent_busy("agent-1", "task-1")
        assert optimizer.get_utilization() == pytest.approx(33.33, rel=0.1)

        # Two agents busy
        optimizer.mark_agent_busy("agent-2", "task-2")
        assert optimizer.get_utilization() == pytest.approx(66.67, rel=0.1)

        # All agents busy
        optimizer.mark_agent_busy("agent-3", "task-3")
        assert optimizer.get_utilization() == 100.0

    def test_suggest_rebalancing(self, sample_agents):
        """Test suggesting task rebalancing when agents idle."""
        optimizer = IdleTimeOptimizer(agents=sample_agents)

        # All agents busy - no rebalancing needed (100% utilization)
        optimizer.mark_agent_busy("agent-1", "task-1")
        optimizer.mark_agent_busy("agent-2", "task-2")
        optimizer.mark_agent_busy("agent-3", "task-3")

        assert not optimizer.should_rebalance()

        # One agent idle - 66% utilization, still above 50% threshold
        optimizer.mark_agent_idle("agent-3")
        assert not optimizer.should_rebalance()  # 66.67% > 50%

        # Two agents idle - 33% utilization, below 50% threshold
        optimizer.mark_agent_idle("agent-2")
        assert optimizer.should_rebalance()  # 33.33% < 50%


class TestSchedulerMetrics:
    """Test scheduler metrics collection."""

    def test_create_metrics(self):
        """Test creating scheduler metrics."""
        metrics = SchedulerMetrics()
        assert metrics is not None
        assert metrics.total_tasks == 0
        assert metrics.completed_tasks == 0

    def test_track_task_completion(self):
        """Test tracking task completion."""
        metrics = SchedulerMetrics()

        metrics.record_task_started("task-1")
        assert metrics.total_tasks == 1
        assert metrics.in_progress_tasks == 1

        metrics.record_task_completed("task-1", duration_seconds=5.0)
        assert metrics.completed_tasks == 1
        assert metrics.in_progress_tasks == 0

    def test_calculate_average_duration(self):
        """Test calculating average task duration."""
        metrics = SchedulerMetrics()

        metrics.record_task_started("task-1")
        metrics.record_task_completed("task-1", duration_seconds=10.0)

        metrics.record_task_started("task-2")
        metrics.record_task_completed("task-2", duration_seconds=20.0)

        assert metrics.get_average_duration() == 15.0

    def test_track_idle_time(self):
        """Test tracking total idle time."""
        metrics = SchedulerMetrics()

        # Record idle periods for agents
        metrics.record_idle_time("agent-1", duration_seconds=5.0)
        metrics.record_idle_time("agent-2", duration_seconds=3.0)

        assert metrics.get_total_idle_time() == 8.0

    def test_get_efficiency_score(self):
        """Test calculating efficiency score (work time / total time)."""
        metrics = SchedulerMetrics()

        # 10 seconds of work
        metrics.record_task_started("task-1")
        metrics.record_task_completed("task-1", duration_seconds=10.0)

        # 2 seconds of idle
        metrics.record_idle_time("agent-1", duration_seconds=2.0)

        # Efficiency = 10 / (10 + 2) = 83.33%
        assert metrics.get_efficiency_score() == pytest.approx(83.33, rel=0.1)

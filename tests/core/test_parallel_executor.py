"""Tests for parallel execution scheduler."""

import time

from src.models.agent import Agent
from src.models.task import Subtask


class TestBasicParallelExecution:
    """Test basic parallel execution capabilities."""

    def test_execute_independent_tasks_in_parallel(self):
        """Multiple tasks with no dependencies should run concurrently."""
        # Import will fail until we create the module
        from src.core.parallel_executor import ParallelExecutionScheduler

        # Create test agents
        agents = [
            Agent(id="agent-1", role="worker", capabilities=[]),
            Agent(id="agent-2", role="worker", capabilities=[]),
        ]

        # Create independent subtasks
        tasks = [
            Subtask(id="task-1", description="Task 1", dependencies=[]),
            Subtask(id="task-2", description="Task 2", dependencies=[]),
        ]

        scheduler = ParallelExecutionScheduler(agents=agents)

        # Mock executor function that sleeps briefly
        def mock_executor(task: Subtask) -> dict:
            time.sleep(0.1)
            return {"task_id": task.id, "status": "completed"}

        start = time.time()
        results = scheduler.execute_tasks(tasks, executor_func=mock_executor)
        elapsed = time.time() - start

        # Should complete in ~0.1s (parallel) not ~0.2s (sequential)
        assert elapsed < 0.15, "Tasks should run in parallel"
        assert len(results) == 2
        assert all(r["status"] == "completed" for r in results)

    def test_sequential_tasks_run_in_order(self):
        """Tasks with dependencies should execute sequentially."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [Agent(id="agent-1", role="worker", capabilities=[])]

        # Task 2 depends on Task 1
        tasks = [
            Subtask(id="task-1", description="Task 1", dependencies=[]),
            Subtask(id="task-2", description="Task 2", dependencies=["task-1"]),
        ]

        scheduler = ParallelExecutionScheduler(agents=agents)

        execution_order = []

        def mock_executor(task: Subtask) -> dict:
            execution_order.append(task.id)
            time.sleep(0.05)
            return {"task_id": task.id, "status": "completed"}

        scheduler.execute_tasks(tasks, executor_func=mock_executor)

        # Task 1 must complete before Task 2 starts
        assert execution_order == ["task-1", "task-2"]


class TestDependencyAwareScheduling:
    """Test dependency-aware scheduling."""

    def test_respects_task_dependencies(self):
        """Task only runs after dependencies complete."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [
            Agent(id="agent-1", role="worker", capabilities=[]),
            Agent(id="agent-2", role="worker", capabilities=[]),
        ]

        # Task B depends on Task A
        tasks = [
            Subtask(id="task-A", description="Task A", dependencies=[]),
            Subtask(id="task-B", description="Task B", dependencies=["task-A"]),
        ]

        scheduler = ParallelExecutionScheduler(agents=agents)

        completion_times = {}

        def mock_executor(task: Subtask) -> dict:
            time.sleep(0.1)
            completion_times[task.id] = time.time()
            return {"task_id": task.id, "status": "completed"}

        scheduler.execute_tasks(tasks, executor_func=mock_executor)

        # Task B should complete after Task A
        assert completion_times["task-B"] > completion_times["task-A"]

    def test_multi_level_dependencies(self):
        """A→B→C dependency chain executes in correct order."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [Agent(id=f"agent-{i}", role="worker", capabilities=[]) for i in range(3)]

        # Chain: A → B → C
        tasks = [
            Subtask(id="task-A", description="Task A", dependencies=[]),
            Subtask(id="task-B", description="Task B", dependencies=["task-A"]),
            Subtask(id="task-C", description="Task C", dependencies=["task-B"]),
        ]

        scheduler = ParallelExecutionScheduler(agents=agents)

        execution_order = []

        def mock_executor(task: Subtask) -> dict:
            execution_order.append(task.id)
            time.sleep(0.05)
            return {"task_id": task.id, "status": "completed"}

        scheduler.execute_tasks(tasks, executor_func=mock_executor)

        assert execution_order == ["task-A", "task-B", "task-C"]

    def test_diamond_dependencies(self):
        """Diamond pattern: A→B,C and B,C→D waits for both B and C."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [Agent(id=f"agent-{i}", role="worker", capabilities=[]) for i in range(3)]

        # Diamond: A → [B, C] → D
        tasks = [
            Subtask(id="task-A", description="Task A", dependencies=[]),
            Subtask(id="task-B", description="Task B", dependencies=["task-A"]),
            Subtask(id="task-C", description="Task C", dependencies=["task-A"]),
            Subtask(id="task-D", description="Task D", dependencies=["task-B", "task-C"]),
        ]

        scheduler = ParallelExecutionScheduler(agents=agents)

        completion_times = {}

        def mock_executor(task: Subtask) -> dict:
            time.sleep(0.1)
            completion_times[task.id] = time.time()
            return {"task_id": task.id, "status": "completed"}

        scheduler.execute_tasks(tasks, executor_func=mock_executor)

        # D must complete after both B and C
        assert completion_times["task-D"] > completion_times["task-B"]
        assert completion_times["task-D"] > completion_times["task-C"]


class TestSynchronizationAndHandoffs:
    """Test synchronization for task handoffs."""

    def test_task_handoff_synchronization(self):
        """Agent A completes task, Agent B receives result."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [
            Agent(id="agent-A", role="worker", capabilities=[]),
            Agent(id="agent-B", role="worker", capabilities=[]),
        ]

        tasks = [
            Subtask(id="task-1", description="Task 1", dependencies=[]),
            Subtask(id="task-2", description="Task 2", dependencies=["task-1"]),
        ]

        scheduler = ParallelExecutionScheduler(agents=agents)

        shared_state = {}

        def mock_executor(task: Subtask) -> dict:
            if task.id == "task-1":
                shared_state["result"] = "data_from_task_1"
                return {"task_id": task.id, "output": "data_from_task_1"}
            else:
                # Task 2 should be able to access task 1's output
                return {"task_id": task.id, "input": shared_state.get("result")}

        results = scheduler.execute_tasks(tasks, executor_func=mock_executor)

        # Verify handoff occurred
        task2_result = next(r for r in results if r["task_id"] == "task-2")
        assert task2_result["input"] == "data_from_task_1"

    def test_concurrent_handoffs(self):
        """Multiple handoffs happening simultaneously."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [Agent(id=f"agent-{i}", role="worker", capabilities=[]) for i in range(4)]

        # Two parallel chains: A1→B1 and A2→B2
        tasks = [
            Subtask(id="A1", description="A1", dependencies=[]),
            Subtask(id="A2", description="A2", dependencies=[]),
            Subtask(id="B1", description="B1", dependencies=["A1"]),
            Subtask(id="B2", description="B2", dependencies=["A2"]),
        ]

        scheduler = ParallelExecutionScheduler(agents=agents)

        def mock_executor(task: Subtask) -> dict:
            time.sleep(0.05)
            return {"task_id": task.id}

        results = scheduler.execute_tasks(tasks, executor_func=mock_executor)

        assert len(results) == 4


class TestResourceOptimization:
    """Test resource optimization and work distribution."""

    def test_minimal_idle_time(self):
        """Scheduler should minimize agent idle time."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [Agent(id=f"agent-{i}", role="worker", capabilities=[]) for i in range(2)]

        # 4 independent tasks with 2 agents
        tasks = [
            Subtask(id=f"task-{i}", description=f"Task {i}", dependencies=[])
            for i in range(4)
        ]

        scheduler = ParallelExecutionScheduler(agents=agents)

        def mock_executor(task: Subtask) -> dict:
            time.sleep(0.1)
            return {"task_id": task.id}

        start = time.time()
        scheduler.execute_tasks(tasks, executor_func=mock_executor)
        elapsed = time.time() - start

        # Should complete in ~0.2s (2 batches of 2) not ~0.4s (sequential)
        assert elapsed < 0.25, "Should minimize idle time with parallel batching"

    def test_max_parallelism_limit(self):
        """Scheduler respects max concurrent tasks limit."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [Agent(id=f"agent-{i}", role="worker", capabilities=[]) for i in range(10)]

        tasks = [
            Subtask(id=f"task-{i}", description=f"Task {i}", dependencies=[])
            for i in range(10)
        ]

        # Limit to 3 concurrent tasks
        scheduler = ParallelExecutionScheduler(agents=agents, max_workers=3)

        active_tasks = []
        max_concurrent = 0

        def mock_executor(task: Subtask) -> dict:
            active_tasks.append(task.id)
            max_concurrent_now = len(active_tasks)
            nonlocal max_concurrent
            max_concurrent = max(max_concurrent, max_concurrent_now)
            time.sleep(0.05)
            active_tasks.remove(task.id)
            return {"task_id": task.id}

        scheduler.execute_tasks(tasks, executor_func=mock_executor)

        # Should never exceed max_workers
        assert max_concurrent <= 3


class TestErrorHandling:
    """Test error handling and recovery."""

    def test_failed_task_doesnt_block_independents(self):
        """Failure in one task shouldn't block independent tasks."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [Agent(id=f"agent-{i}", role="worker", capabilities=[]) for i in range(3)]

        tasks = [
            Subtask(id="task-fail", description="Failing task", dependencies=[]),
            Subtask(id="task-ok-1", description="OK task 1", dependencies=[]),
            Subtask(id="task-ok-2", description="OK task 2", dependencies=[]),
        ]

        scheduler = ParallelExecutionScheduler(agents=agents)

        def mock_executor(task: Subtask) -> dict:
            if task.id == "task-fail":
                raise RuntimeError("Task failed")
            return {"task_id": task.id, "status": "completed"}

        results = scheduler.execute_tasks(
            tasks, executor_func=mock_executor, continue_on_error=True
        )

        # Should have results for successful tasks
        successful = [r for r in results if r.get("status") == "completed"]
        assert len(successful) == 2

    def test_failed_task_blocks_dependents(self):
        """Failed task should prevent dependent tasks from running."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [Agent(id=f"agent-{i}", role="worker", capabilities=[]) for i in range(2)]

        tasks = [
            Subtask(id="task-fail", description="Failing task", dependencies=[]),
            Subtask(id="task-dependent", description="Dependent task", dependencies=["task-fail"]),
        ]

        scheduler = ParallelExecutionScheduler(agents=agents)

        executed_tasks = []

        def mock_executor(task: Subtask) -> dict:
            executed_tasks.append(task.id)
            if task.id == "task-fail":
                raise RuntimeError("Task failed")
            return {"task_id": task.id}

        scheduler.execute_tasks(tasks, executor_func=mock_executor, continue_on_error=True)

        # Only the failed task should have been executed
        assert "task-fail" in executed_tasks
        assert "task-dependent" not in executed_tasks

    def test_timeout_handling(self):
        """Tasks that exceed time limit should timeout gracefully."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [Agent(id="agent-1", role="worker", capabilities=[])]

        tasks = [Subtask(id="task-slow", description="Slow task", dependencies=[])]

        scheduler = ParallelExecutionScheduler(agents=agents, task_timeout=0.1)

        def mock_executor(task: Subtask) -> dict:
            time.sleep(1.0)  # Exceeds timeout
            return {"task_id": task.id}

        results = scheduler.execute_tasks(
            tasks, executor_func=mock_executor, continue_on_error=True
        )

        # Should get timeout result
        assert len(results) == 1
        assert results[0].get("error") is not None or results[0].get("status") == "timeout"


class TestSchedulerConfiguration:
    """Test scheduler configuration and initialization."""

    def test_scheduler_initialization(self):
        """Scheduler initializes with correct configuration."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [Agent(id="agent-1", role="worker", capabilities=[])]

        scheduler = ParallelExecutionScheduler(
            agents=agents,
            max_workers=5,
            task_timeout=300,
        )

        assert scheduler.agents == agents
        assert scheduler.max_workers == 5
        assert scheduler.task_timeout == 300

    def test_get_execution_stats(self):
        """Scheduler provides execution statistics."""
        from src.core.parallel_executor import ParallelExecutionScheduler

        agents = [Agent(id=f"agent-{i}", role="worker", capabilities=[]) for i in range(2)]

        tasks = [
            Subtask(id=f"task-{i}", description=f"Task {i}", dependencies=[])
            for i in range(3)
        ]

        scheduler = ParallelExecutionScheduler(agents=agents)

        def mock_executor(task: Subtask) -> dict:
            time.sleep(0.05)
            return {"task_id": task.id}

        scheduler.execute_tasks(tasks, executor_func=mock_executor)

        stats = scheduler.get_execution_stats()

        assert "total_tasks" in stats
        assert "completed_tasks" in stats
        assert "total_time" in stats
        assert stats["total_tasks"] == 3
        assert stats["completed_tasks"] == 3

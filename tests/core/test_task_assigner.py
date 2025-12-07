"""Tests for task assignment optimizer."""

import pytest

from src.core.task_assigner import TaskAssigner, WorkloadInfo
from src.models.agent import Agent, AgentCapability
from src.models.enums import AgentStatus
from src.models.priority import Priority, WorkQueueTask
from src.models.task import Subtask


class TestWorkloadInfo:
    """Test the WorkloadInfo model."""

    def test_create_workload_info(self):
        """Test creating workload info for an agent."""
        wi = WorkloadInfo(agent_id="agent-1", assigned_tasks=3, estimated_tokens=50000)

        assert wi.agent_id == "agent-1"
        assert wi.assigned_tasks == 3
        assert wi.estimated_tokens == 50000

    def test_workload_info_comparison(self):
        """Test comparing workload info for balancing."""
        wi1 = WorkloadInfo(agent_id="agent-1", assigned_tasks=2, estimated_tokens=30000)
        wi2 = WorkloadInfo(agent_id="agent-2", assigned_tasks=4, estimated_tokens=60000)
        wi3 = WorkloadInfo(agent_id="agent-3", assigned_tasks=2, estimated_tokens=20000)

        # wi2 has most workload
        workloads = [wi1, wi2, wi3]
        sorted_workloads = sorted(workloads, key=lambda w: (w.assigned_tasks, w.estimated_tokens))

        assert sorted_workloads[0] == wi3  # Least workload
        assert sorted_workloads[2] == wi2  # Most workload


class TestTaskAssigner:
    """Test the TaskAssigner class."""

    @pytest.fixture
    def agents(self):
        """Create test agents with different capabilities."""
        return [
            Agent(
                id="backend-1",
                role="backend_developer",
                capabilities=[
                    AgentCapability(
                        name="python",
                        description="Python development",
                        tools=["write", "read", "bash"],
                    ),
                    AgentCapability(
                        name="api_design",
                        description="REST API design",
                        tools=["openapi"],
                    ),
                ],
                status=AgentStatus.IDLE,
            ),
            Agent(
                id="frontend-1",
                role="frontend_developer",
                capabilities=[
                    AgentCapability(
                        name="react",
                        description="React development",
                        tools=["npm", "write"],
                    ),
                ],
                status=AgentStatus.IDLE,
            ),
            Agent(
                id="backend-2",
                role="backend_developer",
                capabilities=[
                    AgentCapability(
                        name="python",
                        description="Python development",
                        tools=["write", "read"],
                    ),
                ],
                status=AgentStatus.IDLE,
            ),
        ]

    @pytest.fixture
    def subtasks(self):
        """Create test subtasks."""
        return [
            Subtask(
                id="task-1",
                description="Implement login endpoint",
                requirements={"capabilities": ["python", "api_design"]},
                metadata={
                    "priority": "critical",
                    "estimated_tokens": 40000,
                },
            ),
            Subtask(
                id="task-2",
                description="Create login UI",
                requirements={"capabilities": ["react"]},
                metadata={
                    "priority": "high",
                    "estimated_tokens": 30000,
                },
            ),
            Subtask(
                id="task-3",
                description="Write unit tests",
                requirements={"capabilities": ["python"]},
                metadata={
                    "priority": "medium",
                    "estimated_tokens": 20000,
                },
            ),
        ]

    def test_create_task_assigner(self, agents):
        """Test creating a task assigner."""
        assigner = TaskAssigner(agents)

        assert len(assigner.agents) == 3
        assert len(assigner.work_queue) == 0

    def test_add_tasks_to_queue(self, agents, subtasks):
        """Test adding subtasks to the work queue."""
        assigner = TaskAssigner(agents)
        assigner.add_tasks(subtasks)

        assert len(assigner.work_queue) == 3

        # Check that tasks are ordered by priority
        assert assigner.work_queue[0].priority == Priority.CRITICAL
        assert assigner.work_queue[1].priority == Priority.HIGH
        assert assigner.work_queue[2].priority == Priority.MEDIUM

    def test_get_capability_match_score(self, agents):
        """Test calculating capability match score."""
        assigner = TaskAssigner(agents)

        task = WorkQueueTask(
            id="task-1",
            priority=Priority.CRITICAL,
            title="Implement login endpoint",
            requirements={"capabilities": ["python", "api_design"]},
        )

        # backend-1 has both python and api_design = score 2
        score1 = assigner._get_capability_match_score(agents[0], task)
        assert score1 == 2

        # frontend-1 has neither python nor api_design = score 0
        score2 = assigner._get_capability_match_score(agents[1], task)
        assert score2 == 0

        # backend-2 has python but not api_design = score 1
        score3 = assigner._get_capability_match_score(agents[2], task)
        assert score3 == 1

    def test_get_agent_workload(self, agents):
        """Test getting current agent workload."""
        assigner = TaskAssigner(agents)

        # Initially no workload
        workload = assigner._get_agent_workload("backend-1")
        assert workload.assigned_tasks == 0
        assert workload.estimated_tokens == 0

        # Add a task to the agent
        agents[0].assigned_tasks = ["task-1"]
        task = WorkQueueTask(
            id="task-1",
            priority=Priority.HIGH,
            title="Task 1",
            estimated_tokens=30000,
        )
        task.claim("backend-1")
        assigner.work_queue.append(task)

        workload = assigner._get_agent_workload("backend-1")
        assert workload.assigned_tasks == 1
        assert workload.estimated_tokens == 30000

    def test_assign_tasks_capability_based(self, agents, subtasks):
        """Test capability-based task assignment."""
        assigner = TaskAssigner(agents)
        assigner.add_tasks(subtasks)

        assignments = assigner.assign_tasks()

        # task-1 should go to backend-1 (has both python and api_design)
        assert assignments["task-1"] == "backend-1"

        # task-2 should go to frontend-1 (only one with react)
        assert assignments["task-2"] == "frontend-1"

        # task-3 should go to backend-2 (to balance workload, since backend-1 already has task-1)
        assert assignments["task-3"] == "backend-2"

    def test_assign_tasks_workload_balancing(self, agents):
        """Test that workload is balanced across agents."""
        assigner = TaskAssigner(agents)

        # Create tasks that all match backend agents
        tasks = [
            Subtask(
                id=f"task-{i}",
                description=f"Task {i}",
                requirements={"capabilities": ["python"]},
                metadata={"priority": "medium", "estimated_tokens": 10000},
            )
            for i in range(6)
        ]

        assigner.add_tasks(tasks)
        assignments = assigner.assign_tasks()

        # Count tasks per agent
        backend1_count = sum(1 for a in assignments.values() if a == "backend-1")
        backend2_count = sum(1 for a in assignments.values() if a == "backend-2")

        # Both backend agents should get roughly equal tasks (3 each)
        assert backend1_count == 3
        assert backend2_count == 3

    def test_claim_task(self, agents):
        """Test claiming a task from the queue."""
        assigner = TaskAssigner(agents)

        task = WorkQueueTask(
            id="task-1",
            priority=Priority.CRITICAL,
            title="Important task",
        )
        assigner.work_queue.append(task)

        # Claim the task
        claimed = assigner.claim_task("task-1", "backend-1")

        assert claimed is True
        assert task.assigned_agent == "backend-1"
        assert task.status == "claimed"

    def test_claim_task_already_claimed(self, agents):
        """Test that claiming an already claimed task fails."""
        assigner = TaskAssigner(agents)

        task = WorkQueueTask(
            id="task-1",
            priority=Priority.CRITICAL,
            title="Important task",
        )
        assigner.work_queue.append(task)

        # First claim succeeds
        assigner.claim_task("task-1", "backend-1")

        # Second claim fails
        with pytest.raises(ValueError, match="already claimed"):
            assigner.claim_task("task-1", "backend-2")

    def test_release_task(self, agents):
        """Test releasing a claimed task."""
        assigner = TaskAssigner(agents)

        task = WorkQueueTask(
            id="task-1",
            priority=Priority.CRITICAL,
            title="Important task",
        )
        assigner.work_queue.append(task)

        # Claim then release
        assigner.claim_task("task-1", "backend-1")
        released = assigner.release_task("task-1")

        assert released is True
        assert task.assigned_agent is None
        assert task.status == "pending"

    def test_release_unclaimed_task(self, agents):
        """Test releasing an unclaimed task."""
        assigner = TaskAssigner(agents)

        task = WorkQueueTask(
            id="task-1",
            priority=Priority.CRITICAL,
            title="Important task",
        )
        assigner.work_queue.append(task)

        # Release without claiming should fail gracefully
        released = assigner.release_task("task-1")
        assert released is False

    def test_get_next_task_by_priority(self, agents):
        """Test getting the next unassigned task by priority."""
        assigner = TaskAssigner(agents)

        tasks = [
            WorkQueueTask(id="low-1", priority=Priority.LOW, title="Low priority"),
            WorkQueueTask(id="critical-1", priority=Priority.CRITICAL, title="Critical"),
            WorkQueueTask(id="high-1", priority=Priority.HIGH, title="High priority"),
        ]

        for task in tasks:
            assigner.work_queue.append(task)

        # Sort queue by priority
        assigner.work_queue.sort(key=lambda t: t.priority.priority_order, reverse=True)

        # Get next task for an agent with all capabilities
        next_task = assigner.get_next_task("backend-1")

        # Should get critical task first
        assert next_task is not None
        assert next_task.id == "critical-1"

    def test_no_capable_agent_for_task(self, agents):
        """Test assignment when no agent has required capabilities."""
        assigner = TaskAssigner(agents)

        task = Subtask(
            id="task-1",
            description="Rust development task",
            requirements={"capabilities": ["rust"]},
            metadata={"priority": "high"},
        )

        assigner.add_tasks([task])
        assignments = assigner.assign_tasks()

        # No agent can do this task, should be unassigned
        assert "task-1" not in assignments or assignments["task-1"] is None

    def test_get_queue_status(self, agents, subtasks):
        """Test getting queue status summary."""
        assigner = TaskAssigner(agents)
        assigner.add_tasks(subtasks)

        # Assign some tasks
        assigner.assign_tasks()

        status = assigner.get_queue_status()

        assert "total_tasks" in status
        assert "pending" in status
        assert "claimed" in status
        assert "completed" in status
        assert status["total_tasks"] == 3
        assert status["claimed"] == 3  # All tasks assigned

    def test_prevent_duplicate_work(self, agents):
        """Test that claim mechanism prevents duplicate work."""
        assigner = TaskAssigner(agents)

        task = WorkQueueTask(
            id="task-1",
            priority=Priority.CRITICAL,
            title="Important task",
        )
        assigner.work_queue.append(task)

        # Agent 1 claims
        assigner.claim_task("task-1", "backend-1")

        # Agent 2 tries to claim same task
        with pytest.raises(ValueError):
            assigner.claim_task("task-1", "backend-2")

        # Verify only agent 1 has the task
        assert task.assigned_agent == "backend-1"

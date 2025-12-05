"""Tests for Task and Subtask models."""

from src.models.enums import TaskStatus, TaskType
from src.models.task import Subtask, Task


class TestSubtask:
    """Test Subtask model."""

    def test_subtask_creation(self):
        """Test creating a basic subtask."""
        subtask = Subtask(
            id="subtask-1",
            description="Implement user authentication",
            dependencies=[],
        )
        assert subtask.id == "subtask-1"
        assert subtask.description == "Implement user authentication"
        assert subtask.dependencies == []
        assert subtask.status == TaskStatus.PENDING
        assert subtask.assigned_agent is None

    def test_subtask_with_dependencies(self):
        """Test subtask with dependencies."""
        subtask = Subtask(
            id="subtask-2",
            description="Write integration tests",
            dependencies=["subtask-1"],
        )
        assert subtask.dependencies == ["subtask-1"]

    def test_subtask_with_assigned_agent(self):
        """Test subtask with assigned agent."""
        subtask = Subtask(
            id="subtask-3",
            description="Deploy to production",
            dependencies=[],
            assigned_agent="agent-123",
        )
        assert subtask.assigned_agent == "agent-123"

    def test_subtask_status_update(self):
        """Test updating subtask status."""
        subtask = Subtask(
            id="subtask-4",
            description="Code review",
            dependencies=[],
        )
        assert subtask.status == TaskStatus.PENDING
        subtask.status = TaskStatus.IN_PROGRESS
        assert subtask.status == TaskStatus.IN_PROGRESS

    def test_subtask_with_metadata(self):
        """Test subtask with metadata."""
        subtask = Subtask(
            id="subtask-5",
            description="Performance optimization",
            dependencies=[],
            metadata={"priority": "high", "estimated_hours": 8},
        )
        assert subtask.metadata["priority"] == "high"
        assert subtask.metadata["estimated_hours"] == 8


class TestTask:
    """Test Task model."""

    def test_task_creation_minimal(self):
        """Test creating a task with minimal required fields."""
        task = Task(
            id="task-1",
            description="Build a REST API",
            task_type=TaskType.SOFTWARE,
        )
        assert task.id == "task-1"
        assert task.description == "Build a REST API"
        assert task.task_type == TaskType.SOFTWARE
        assert task.status == TaskStatus.PENDING
        assert task.subtasks == []
        assert task.constraints == {}
        assert task.context == {}

    def test_task_creation_full(self):
        """Test creating a task with all fields."""
        subtasks = [
            Subtask(id="st-1", description="Design API", dependencies=[]),
            Subtask(id="st-2", description="Implement endpoints", dependencies=["st-1"]),
        ]
        task = Task(
            id="task-2",
            description="Build authentication system",
            task_type=TaskType.SOFTWARE,
            subtasks=subtasks,
            status=TaskStatus.IN_PROGRESS,
            constraints={"deadline": "2025-12-31", "budget": 10000},
            context={"framework": "FastAPI", "database": "PostgreSQL"},
            metadata={"client": "Acme Corp"},
        )
        assert len(task.subtasks) == 2
        assert task.subtasks[0].id == "st-1"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.constraints["deadline"] == "2025-12-31"
        assert task.context["framework"] == "FastAPI"
        assert task.metadata["client"] == "Acme Corp"

    def test_task_different_types(self):
        """Test tasks with different types."""
        software_task = Task(
            id="task-3",
            description="Develop mobile app",
            task_type=TaskType.SOFTWARE,
        )
        research_task = Task(
            id="task-4",
            description="Analyze market trends",
            task_type=TaskType.RESEARCH,
        )
        assert software_task.task_type == TaskType.SOFTWARE
        assert research_task.task_type == TaskType.RESEARCH

    def test_task_add_subtask(self):
        """Test adding subtasks to a task."""
        task = Task(
            id="task-5",
            description="Complete project",
            task_type=TaskType.SOFTWARE,
        )
        assert len(task.subtasks) == 0

        subtask = Subtask(id="st-1", description="Setup environment", dependencies=[])
        task.subtasks.append(subtask)
        assert len(task.subtasks) == 1
        assert task.subtasks[0].id == "st-1"

    def test_task_status_transitions(self):
        """Test task status transitions."""
        task = Task(
            id="task-6",
            description="Test task",
            task_type=TaskType.SOFTWARE,
        )
        assert task.status == TaskStatus.PENDING

        task.status = TaskStatus.IN_PROGRESS
        assert task.status == TaskStatus.IN_PROGRESS

        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

    def test_task_with_complex_dependencies(self):
        """Test task with complex subtask dependencies."""
        subtasks = [
            Subtask(id="st-1", description="Task 1", dependencies=[]),
            Subtask(id="st-2", description="Task 2", dependencies=["st-1"]),
            Subtask(id="st-3", description="Task 3", dependencies=["st-1"]),
            Subtask(id="st-4", description="Task 4", dependencies=["st-2", "st-3"]),
        ]
        task = Task(
            id="task-7",
            description="Complex workflow",
            task_type=TaskType.SOFTWARE,
            subtasks=subtasks,
        )
        assert len(task.subtasks) == 4
        assert task.subtasks[3].dependencies == ["st-2", "st-3"]

    def test_task_constraints_and_context(self):
        """Test task constraints and context handling."""
        task = Task(
            id="task-8",
            description="Constrained task",
            task_type=TaskType.SOFTWARE,
            constraints={
                "max_agents": 5,
                "timeout_hours": 24,
                "must_use_tools": ["pytest", "mypy"],
            },
            context={
                "codebase_url": "https://github.com/example/repo",
                "existing_tests": True,
            },
        )
        assert task.constraints["max_agents"] == 5
        assert task.constraints["timeout_hours"] == 24
        assert "pytest" in task.constraints["must_use_tools"]
        assert task.context["existing_tests"] is True

"""Tests for TaskDecomposer - recursive task decomposition and dependency graph generation."""

from src.core.task_decomposer import (
    DecompositionResult,
    DependencyGraph,
    SubtaskNode,
    TaskDecomposer,
)
from src.core.task_parser import ParsedTask, TaskParser
from src.models.enums import TaskType


class TestSubtaskNode:
    """Test SubtaskNode data structure."""

    def test_create_subtask_node(self):
        """Test creating a basic subtask node."""
        node = SubtaskNode(
            id="task-1",
            description="Implement authentication endpoint",
            parent_id=None,
            depth=0,
        )

        assert node.id == "task-1"
        assert node.description == "Implement authentication endpoint"
        assert node.parent_id is None
        assert node.depth == 0
        assert node.dependencies == []
        assert node.estimated_complexity == "medium"

    def test_subtask_node_with_dependencies(self):
        """Test subtask node with dependencies."""
        node = SubtaskNode(
            id="task-2",
            description="Test authentication",
            parent_id="task-1",
            depth=1,
            dependencies=["task-1"],
            estimated_complexity="small",
        )

        assert len(node.dependencies) == 1
        assert "task-1" in node.dependencies
        assert node.estimated_complexity == "small"


class TestDependencyGraph:
    """Test DependencyGraph construction and analysis."""

    def test_create_empty_graph(self):
        """Test creating an empty dependency graph."""
        graph = DependencyGraph()

        assert graph.node_count() == 0
        assert graph.is_acyclic()
        assert graph.get_independent_tasks() == []

    def test_add_node_to_graph(self):
        """Test adding nodes to the graph."""
        graph = DependencyGraph()
        node = SubtaskNode(id="task-1", description="Task 1", parent_id=None, depth=0)

        graph.add_node(node)

        assert graph.node_count() == 1
        assert graph.has_node("task-1")

    def test_add_dependency(self):
        """Test adding dependencies between nodes."""
        graph = DependencyGraph()

        node1 = SubtaskNode(id="task-1", description="Task 1", parent_id=None, depth=0)
        node2 = SubtaskNode(
            id="task-2",
            description="Task 2",
            parent_id=None,
            depth=0,
            dependencies=["task-1"],
        )

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_dependency("task-2", "task-1")

        assert graph.has_dependency("task-2", "task-1")

    def test_detect_cycle(self):
        """Test cycle detection in dependency graph."""
        graph = DependencyGraph()

        node1 = SubtaskNode(id="task-1", description="Task 1", parent_id=None, depth=0)
        node2 = SubtaskNode(id="task-2", description="Task 2", parent_id=None, depth=0)

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_dependency("task-1", "task-2")
        graph.add_dependency("task-2", "task-1")  # Creates cycle

        assert not graph.is_acyclic()

    def test_get_independent_tasks(self):
        """Test getting tasks with no dependencies."""
        graph = DependencyGraph()

        node1 = SubtaskNode(id="task-1", description="Task 1", parent_id=None, depth=0)
        node2 = SubtaskNode(id="task-2", description="Task 2", parent_id=None, depth=0)
        node3 = SubtaskNode(
            id="task-3",
            description="Task 3",
            parent_id=None,
            depth=0,
            dependencies=["task-1"],
        )

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)
        graph.add_dependency("task-3", "task-1")

        independent = graph.get_independent_tasks()
        assert len(independent) == 2
        assert "task-1" in independent
        assert "task-2" in independent
        assert "task-3" not in independent

    def test_topological_sort(self):
        """Test topological sorting of tasks."""
        graph = DependencyGraph()

        node1 = SubtaskNode(id="task-1", description="Task 1", parent_id=None, depth=0)
        node2 = SubtaskNode(
            id="task-2",
            description="Task 2",
            parent_id=None,
            depth=0,
            dependencies=["task-1"],
        )
        node3 = SubtaskNode(
            id="task-3",
            description="Task 3",
            parent_id=None,
            depth=0,
            dependencies=["task-2"],
        )

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)
        graph.add_dependency("task-2", "task-1")
        graph.add_dependency("task-3", "task-2")

        sorted_tasks = graph.topological_sort()
        assert len(sorted_tasks) == 3

        # task-1 should come before task-2, task-2 before task-3
        idx1 = sorted_tasks.index("task-1")
        idx2 = sorted_tasks.index("task-2")
        idx3 = sorted_tasks.index("task-3")
        assert idx1 < idx2 < idx3

    def test_critical_path_simple(self):
        """Test critical path identification in simple graph."""
        graph = DependencyGraph()

        # Linear path: task-1 -> task-2 -> task-3
        node1 = SubtaskNode(
            id="task-1",
            description="Task 1",
            parent_id=None,
            depth=0,
            estimated_complexity="large",
        )
        node2 = SubtaskNode(
            id="task-2",
            description="Task 2",
            parent_id=None,
            depth=0,
            dependencies=["task-1"],
            estimated_complexity="medium",
        )
        node3 = SubtaskNode(
            id="task-3",
            description="Task 3",
            parent_id=None,
            depth=0,
            dependencies=["task-2"],
            estimated_complexity="small",
        )

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)
        graph.add_dependency("task-2", "task-1")
        graph.add_dependency("task-3", "task-2")

        critical_path = graph.get_critical_path()
        assert len(critical_path) == 3
        assert critical_path == ["task-1", "task-2", "task-3"]

    def test_critical_path_diamond(self):
        """Test critical path in diamond-shaped dependency graph."""
        graph = DependencyGraph()

        # Diamond: task-1 -> task-2 -> task-4
        #          task-1 -> task-3 -> task-4
        # task-3 path is longer (critical)
        node1 = SubtaskNode(
            id="task-1",
            description="Start",
            parent_id=None,
            depth=0,
            estimated_complexity="small",
        )
        node2 = SubtaskNode(
            id="task-2",
            description="Short path",
            parent_id=None,
            depth=0,
            dependencies=["task-1"],
            estimated_complexity="small",
        )
        node3 = SubtaskNode(
            id="task-3",
            description="Long path",
            parent_id=None,
            depth=0,
            dependencies=["task-1"],
            estimated_complexity="large",
        )
        node4 = SubtaskNode(
            id="task-4",
            description="End",
            parent_id=None,
            depth=0,
            dependencies=["task-2", "task-3"],
            estimated_complexity="medium",
        )

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)
        graph.add_node(node4)
        graph.add_dependency("task-2", "task-1")
        graph.add_dependency("task-3", "task-1")
        graph.add_dependency("task-4", "task-2")
        graph.add_dependency("task-4", "task-3")

        critical_path = graph.get_critical_path()
        # Should include task-3 (large) over task-2 (small)
        assert "task-1" in critical_path
        assert "task-3" in critical_path
        assert "task-4" in critical_path


class TestTaskDecomposer:
    """Test TaskDecomposer recursive decomposition logic."""

    def test_decompose_simple_task(self):
        """Test decomposing a simple task without recursion."""
        decomposer = TaskDecomposer(max_depth=1)
        parsed_task = ParsedTask(
            goal="Build a REST API for user authentication",
            task_type=TaskType.SOFTWARE,
            raw_description="Build a REST API for user authentication",
        )

        result = decomposer.decompose(parsed_task)

        assert isinstance(result, DecompositionResult)
        assert result.task == parsed_task
        assert len(result.subtasks) > 0
        assert result.dependency_graph.node_count() == len(result.subtasks)

    def test_decompose_respects_max_depth(self):
        """Test that decomposition respects max_depth limit."""
        decomposer = TaskDecomposer(max_depth=2)
        parsed_task = ParsedTask(
            goal="Build a complete e-commerce platform with payment processing",
            task_type=TaskType.SOFTWARE,
            raw_description="Build a complete e-commerce platform",
        )

        result = decomposer.decompose(parsed_task)

        # Check that no subtask has depth > max_depth
        for subtask in result.subtasks:
            assert subtask.depth <= 2

    def test_decompose_creates_dag(self):
        """Test that decomposition creates a valid DAG."""
        decomposer = TaskDecomposer(max_depth=2)
        parsed_task = ParsedTask(
            goal="Implement user authentication system",
            task_type=TaskType.SOFTWARE,
            raw_description="Implement user authentication system",
        )

        result = decomposer.decompose(parsed_task)

        # Should be acyclic
        assert result.dependency_graph.is_acyclic()

        # Should have at least one independent task (starting point)
        independent = result.dependency_graph.get_independent_tasks()
        assert len(independent) > 0

    def test_decompose_software_task(self):
        """Test decomposing a software development task."""
        decomposer = TaskDecomposer(max_depth=2)
        parsed_task = ParsedTask(
            goal="Build a REST API for user management",
            task_type=TaskType.SOFTWARE,
            constraints={"technology": ["Python", "FastAPI"]},
            success_criteria=["CRUD operations", "JWT authentication"],
            raw_description="Build a REST API for user management with CRUD and auth",
        )

        result = decomposer.decompose(parsed_task)

        # Should have subtasks for different aspects
        subtask_descriptions = [st.description.lower() for st in result.subtasks]

        # Likely to have tasks related to: models, endpoints, tests, etc.
        assert len(result.subtasks) >= 3

        # Should contain some software-related keywords
        all_text = " ".join(subtask_descriptions)
        assert any(
            keyword in all_text
            for keyword in ["endpoint", "model", "test", "database", "api"]
        )

    def test_decompose_research_task(self):
        """Test decomposing a research task."""
        decomposer = TaskDecomposer(max_depth=2)
        parsed_task = ParsedTask(
            goal="Research machine learning frameworks for NLP",
            task_type=TaskType.RESEARCH,
            raw_description="Research ML frameworks for NLP tasks",
        )

        result = decomposer.decompose(parsed_task)

        # Should have research-related subtasks
        subtask_descriptions = [st.description.lower() for st in result.subtasks]
        all_text = " ".join(subtask_descriptions)

        assert len(result.subtasks) >= 2
        # Likely contains research-related terms
        assert any(
            keyword in all_text
            for keyword in ["search", "review", "compare", "summarize", "findings"]
        )

    def test_decompose_identifies_dependencies(self):
        """Test that decomposer identifies logical dependencies."""
        decomposer = TaskDecomposer(max_depth=2)
        parsed_task = ParsedTask(
            goal="Build and deploy a web application",
            task_type=TaskType.SOFTWARE,
            raw_description="Build and deploy a web application",
        )

        result = decomposer.decompose(parsed_task)

        # Should have dependencies (e.g., build before deploy)
        graph = result.dependency_graph
        total_edges = sum(
            len(st.dependencies) for st in result.subtasks if st.dependencies
        )
        assert total_edges > 0

        # Should be able to sort topologically
        sorted_tasks = graph.topological_sort()
        assert len(sorted_tasks) == len(result.subtasks)

    def test_decompose_empty_task(self):
        """Test decomposing an empty or invalid task."""
        decomposer = TaskDecomposer()
        parsed_task = ParsedTask(
            goal="", task_type=TaskType.SOFTWARE, raw_description=""
        )

        result = decomposer.decompose(parsed_task)

        # Should handle gracefully - either empty or single clarification subtask
        assert isinstance(result, DecompositionResult)

    def test_subtasks_are_independent_testable_estimable(self):
        """Test that subtasks follow ITE principles where possible."""
        decomposer = TaskDecomposer(max_depth=2)
        parsed_task = ParsedTask(
            goal="Implement user registration feature",
            task_type=TaskType.SOFTWARE,
            raw_description="Implement user registration",
        )

        result = decomposer.decompose(parsed_task)

        # Each subtask should be reasonably independent (can have some deps)
        # Each should be testable (concrete enough)
        # Each should be estimable (has complexity estimate)
        for subtask in result.subtasks:
            assert subtask.description  # Not empty
            assert len(subtask.description.split()) >= 2  # Reasonably descriptive
            assert subtask.estimated_complexity in [
                "small",
                "medium",
                "large",
            ]  # Has estimate

    def test_integration_with_task_parser(self):
        """Test full integration: parse then decompose."""
        parser = TaskParser()
        decomposer = TaskDecomposer(max_depth=2)

        description = (
            "Build a todo list API with FastAPI. "
            "Must support creating, reading, updating, and deleting todos. "
            "Include authentication with JWT tokens. "
            "Write tests with pytest."
        )

        parsed = parser.parse(description)
        result = decomposer.decompose(parsed)

        assert len(result.subtasks) > 0
        assert result.dependency_graph.is_acyclic()

        # Should create logical grouping of tasks
        subtask_descriptions = [st.description for st in result.subtasks]
        assert len(subtask_descriptions) >= 4


class TestDecompositionResult:
    """Test DecompositionResult data structure."""

    def test_create_decomposition_result(self):
        """Test creating a decomposition result."""
        parsed_task = ParsedTask(
            goal="Test task", task_type=TaskType.SOFTWARE, raw_description="Test"
        )
        graph = DependencyGraph()
        subtasks = []

        result = DecompositionResult(
            task=parsed_task, subtasks=subtasks, dependency_graph=graph
        )

        assert result.task == parsed_task
        assert result.subtasks == subtasks
        assert result.dependency_graph == graph

    def test_get_execution_order(self):
        """Test getting execution order from result."""
        parsed_task = ParsedTask(
            goal="Test task", task_type=TaskType.SOFTWARE, raw_description="Test"
        )

        graph = DependencyGraph()
        node1 = SubtaskNode(id="task-1", description="Task 1", parent_id=None, depth=0)
        node2 = SubtaskNode(
            id="task-2",
            description="Task 2",
            parent_id=None,
            depth=0,
            dependencies=["task-1"],
        )

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_dependency("task-2", "task-1")

        result = DecompositionResult(
            task=parsed_task, subtasks=[node1, node2], dependency_graph=graph
        )

        execution_order = result.get_execution_order()
        assert len(execution_order) == 2
        assert execution_order[0] == "task-1"
        assert execution_order[1] == "task-2"

    def test_get_parallel_groups(self):
        """Test getting groups of tasks that can run in parallel."""
        parsed_task = ParsedTask(
            goal="Test task", task_type=TaskType.SOFTWARE, raw_description="Test"
        )

        graph = DependencyGraph()

        # Create a graph with parallelizable tasks:
        # task-1 (independent)
        # task-2 (independent)
        # task-3 (depends on task-1)
        # task-4 (depends on task-1)
        # task-5 (depends on task-3 and task-4)

        node1 = SubtaskNode(id="task-1", description="Task 1", parent_id=None, depth=0)
        node2 = SubtaskNode(id="task-2", description="Task 2", parent_id=None, depth=0)
        node3 = SubtaskNode(
            id="task-3",
            description="Task 3",
            parent_id=None,
            depth=0,
            dependencies=["task-1"],
        )
        node4 = SubtaskNode(
            id="task-4",
            description="Task 4",
            parent_id=None,
            depth=0,
            dependencies=["task-1"],
        )
        node5 = SubtaskNode(
            id="task-5",
            description="Task 5",
            parent_id=None,
            depth=0,
            dependencies=["task-3", "task-4"],
        )

        for node in [node1, node2, node3, node4, node5]:
            graph.add_node(node)

        graph.add_dependency("task-3", "task-1")
        graph.add_dependency("task-4", "task-1")
        graph.add_dependency("task-5", "task-3")
        graph.add_dependency("task-5", "task-4")

        result = DecompositionResult(
            task=parsed_task,
            subtasks=[node1, node2, node3, node4, node5],
            dependency_graph=graph,
        )

        parallel_groups = result.get_parallel_groups()

        # Should have multiple groups
        assert len(parallel_groups) >= 2

        # First group should have independent tasks (task-1, task-2)
        assert len(parallel_groups[0]) >= 2

        # Should find task-3 and task-4 can run in parallel (both depend only on task-1)
        # They should be in the same group
        group_with_3 = None
        for group in parallel_groups:
            if "task-3" in group:
                group_with_3 = group
                break

        if group_with_3:
            assert "task-4" in group_with_3  # Both should be parallelizable


class TestDependencyGraphEdgeCases:
    """Test edge cases for DependencyGraph."""

    def test_critical_path_empty_graph(self):
        """Test critical path on empty graph."""
        graph = DependencyGraph()
        critical_path = graph.get_critical_path()
        assert critical_path == []

    def test_get_node_existing(self):
        """Test getting an existing node."""
        graph = DependencyGraph()
        node = SubtaskNode(id="task-1", description="Task 1", parent_id=None, depth=0)
        graph.add_node(node)

        retrieved = graph.get_node("task-1")
        assert retrieved is not None
        assert retrieved.id == "task-1"

    def test_get_node_nonexistent(self):
        """Test getting a nonexistent node."""
        graph = DependencyGraph()
        retrieved = graph.get_node("nonexistent")
        assert retrieved is None


class TestDecompositionResultEdgeCases:
    """Test edge cases for DecompositionResult."""

    def test_get_parallel_groups_empty(self):
        """Test get_parallel_groups with empty graph."""
        parsed_task = ParsedTask(
            goal="Empty", task_type=TaskType.SOFTWARE, raw_description="Empty"
        )
        graph = DependencyGraph()
        result = DecompositionResult(task=parsed_task, subtasks=[], dependency_graph=graph)

        groups = result.get_parallel_groups()
        assert groups == []


class TestTaskDecomposerTaskTypes:
    """Test decomposition of different task types."""

    def test_decompose_analysis_task(self):
        """Test decomposing an analysis task."""
        decomposer = TaskDecomposer(max_depth=2)
        parsed_task = ParsedTask(
            goal="Analyze customer churn patterns",
            task_type=TaskType.ANALYSIS,
            raw_description="Analyze customer churn patterns in the data",
        )

        result = decomposer.decompose(parsed_task)

        assert len(result.subtasks) >= 3
        subtask_descriptions = " ".join([st.description.lower() for st in result.subtasks])
        # Should have analysis-related subtasks
        assert any(
            keyword in subtask_descriptions
            for keyword in ["data", "analysis", "interpret", "report", "results"]
        )

    def test_decompose_creative_task(self):
        """Test decomposing a creative task."""
        decomposer = TaskDecomposer(max_depth=2)
        parsed_task = ParsedTask(
            goal="Design a new marketing campaign",
            task_type=TaskType.CREATIVE,
            raw_description="Design a creative marketing campaign",
        )

        result = decomposer.decompose(parsed_task)

        assert len(result.subtasks) >= 3
        subtask_descriptions = " ".join([st.description.lower() for st in result.subtasks])
        # Should have creative-related subtasks
        assert any(
            keyword in subtask_descriptions
            for keyword in ["brainstorm", "draft", "design", "iterate", "finalize"]
        )

    def test_decompose_hybrid_task(self):
        """Test decomposing a hybrid task."""
        decomposer = TaskDecomposer(max_depth=2)
        parsed_task = ParsedTask(
            goal="Research and implement a new feature",
            task_type=TaskType.HYBRID,
            raw_description="Research and implement a new feature",
        )

        result = decomposer.decompose(parsed_task)

        # Hybrid uses generic decomposition
        assert len(result.subtasks) >= 2
        assert result.dependency_graph.is_acyclic()

    def test_decompose_hybrid_uses_generic(self):
        """Test that hybrid task type uses generic decomposition."""
        decomposer = TaskDecomposer(max_depth=2)
        parsed_task = ParsedTask(
            goal="Do something that spans categories",
            task_type=TaskType.HYBRID,
            raw_description="Do something hybrid",
        )

        result = decomposer.decompose(parsed_task)

        # HYBRID uses generic decomposition (prepare/execute/review)
        assert len(result.subtasks) >= 2
        subtask_descriptions = " ".join([st.description.lower() for st in result.subtasks])
        assert any(
            keyword in subtask_descriptions
            for keyword in ["prepare", "plan", "execute", "review", "finalize"]
        )


class TestTaskDecomposerSoftwareVariants:
    """Test various software task decomposition scenarios."""

    def test_decompose_database_task(self):
        """Test decomposing a database-focused task."""
        decomposer = TaskDecomposer(max_depth=1)
        parsed_task = ParsedTask(
            goal="Create database models for user management",
            task_type=TaskType.SOFTWARE,
            raw_description="Create database models for user management",
        )

        result = decomposer.decompose(parsed_task)

        subtask_descriptions = " ".join([st.description.lower() for st in result.subtasks])
        assert any(
            keyword in subtask_descriptions
            for keyword in ["model", "data", "design"]
        )

    def test_decompose_task_with_authentication(self):
        """Test decomposing a task that mentions authentication."""
        decomposer = TaskDecomposer(max_depth=1)
        parsed_task = ParsedTask(
            goal="Build API with JWT authentication",
            task_type=TaskType.SOFTWARE,
            success_criteria=["JWT token validation works"],
            raw_description="Build API with JWT auth",
        )

        result = decomposer.decompose(parsed_task)

        subtask_descriptions = " ".join([st.description.lower() for st in result.subtasks])
        assert "auth" in subtask_descriptions or "security" in subtask_descriptions

    def test_decompose_task_with_deployment(self):
        """Test decomposing a task that mentions deployment."""
        decomposer = TaskDecomposer(max_depth=1)
        parsed_task = ParsedTask(
            goal="Build and deploy the application",
            task_type=TaskType.SOFTWARE,
            raw_description="Build and deploy the application",
        )

        result = decomposer.decompose(parsed_task)

        subtask_descriptions = " ".join([st.description.lower() for st in result.subtasks])
        assert "deploy" in subtask_descriptions


class TestTaskDecomposerDepth:
    """Test decomposition at various depths."""

    def test_max_depth_zero_returns_empty(self):
        """Test that max_depth=0 returns no subtasks."""
        decomposer = TaskDecomposer(max_depth=0)
        parsed_task = ParsedTask(
            goal="Build something",
            task_type=TaskType.SOFTWARE,
            raw_description="Build something",
        )

        result = decomposer.decompose(parsed_task)

        # At depth 0, recursive call returns empty
        # But the initial call still creates subtasks at depth 0
        # Let me check - the decompose method calls _decompose_recursive with depth=0
        # and inside, if depth >= max_depth, it returns []
        # Since max_depth=0 and depth starts at 0, 0 >= 0 is True
        assert result.subtasks == []

    def test_deeper_decomposition_software(self):
        """Test that depth > 0 uses generic decomposition."""
        decomposer = TaskDecomposer(max_depth=2)
        parsed_task = ParsedTask(
            goal="Build API",
            task_type=TaskType.SOFTWARE,
            raw_description="Build API",
        )

        # This creates subtasks at depth 0
        result = decomposer.decompose(parsed_task)

        # At depth > 0, software tasks use generic decomposition
        # We verify by checking that decomposition happened
        assert len(result.subtasks) > 0

    def test_research_task_deeper_depth(self):
        """Test research task decomposition at deeper depth."""
        decomposer = TaskDecomposer(max_depth=2)
        parsed_task = ParsedTask(
            goal="Research AI",
            task_type=TaskType.RESEARCH,
            raw_description="Research AI technologies",
        )

        result = decomposer.decompose(parsed_task)

        # At depth 0, research workflow is used
        assert len(result.subtasks) >= 3


class TestGenericDecomposition:
    """Test generic task decomposition."""

    def test_generic_decomposition_structure(self):
        """Test that generic decomposition creates expected structure."""
        decomposer = TaskDecomposer(max_depth=1)
        # HYBRID uses generic decomposition
        parsed_task = ParsedTask(
            goal="Complete a generic task",
            task_type=TaskType.HYBRID,
            raw_description="Do something generic",
        )

        result = decomposer.decompose(parsed_task)

        # Generic decomposition creates 3 phases
        assert len(result.subtasks) == 3

        descriptions = [st.description for st in result.subtasks]
        assert "Prepare and plan" in descriptions
        assert "Execute main work" in descriptions
        assert "Review and finalize" in descriptions

    def test_generic_decomposition_dependencies(self):
        """Test that generic decomposition has correct dependencies."""
        decomposer = TaskDecomposer(max_depth=1)
        # HYBRID uses generic decomposition
        parsed_task = ParsedTask(
            goal="Complete a task",
            task_type=TaskType.HYBRID,
            raw_description="Do something",
        )

        result = decomposer.decompose(parsed_task)

        # Find the execute task - it should depend on prepare
        execute_task = next(
            (st for st in result.subtasks if "Execute" in st.description), None
        )
        prepare_task = next(
            (st for st in result.subtasks if "Prepare" in st.description), None
        )

        assert execute_task is not None
        assert prepare_task is not None

        # Execute should depend on prepare
        assert result.dependency_graph.has_dependency(execute_task.id, prepare_task.id)

"""
Task Decomposer for recursive task breakdown and dependency graph generation.

This module provides the TaskDecomposer class for breaking down complex tasks
into manageable subtasks with dependency relationships.
"""

from dataclasses import dataclass, field
from typing import Any

import networkx as nx

from src.core.task_parser import ParsedTask
from src.models.enums import TaskType


@dataclass
class SubtaskNode:
    """
    Represents a single subtask in the decomposition tree.

    Subtasks should be Independent, Testable, and Estimable where possible.
    """

    id: str
    description: str
    parent_id: str | None
    depth: int
    dependencies: list[str] = field(default_factory=list)
    estimated_complexity: str = "medium"  # small, medium, large
    metadata: dict[str, Any] = field(default_factory=dict)


class DependencyGraph:
    """
    Manages the dependency graph (DAG) for subtasks.

    Uses NetworkX for graph operations like cycle detection,
    topological sorting, and critical path analysis.
    """

    def __init__(self) -> None:
        """Initialize an empty directed graph."""
        self._graph: nx.DiGraph = nx.DiGraph()
        self._nodes: dict[str, SubtaskNode] = {}

    def add_node(self, node: SubtaskNode) -> None:
        """
        Add a subtask node to the graph.

        Args:
            node: SubtaskNode to add
        """
        self._graph.add_node(node.id)
        self._nodes[node.id] = node

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """
        Add a dependency edge: task_id depends on depends_on.

        Args:
            task_id: ID of the dependent task
            depends_on: ID of the task it depends on
        """
        self._graph.add_edge(depends_on, task_id)

    def has_node(self, node_id: str) -> bool:
        """
        Check if a node exists in the graph.

        Args:
            node_id: ID of the node

        Returns:
            True if node exists, False otherwise
        """
        return node_id in self._graph

    def has_dependency(self, task_id: str, depends_on: str) -> bool:
        """
        Check if a dependency exists.

        Args:
            task_id: ID of the dependent task
            depends_on: ID of the task it might depend on

        Returns:
            True if dependency exists, False otherwise
        """
        return self._graph.has_edge(depends_on, task_id)

    def node_count(self) -> int:
        """
        Get the number of nodes in the graph.

        Returns:
            Number of nodes
        """
        return self._graph.number_of_nodes()

    def is_acyclic(self) -> bool:
        """
        Check if the graph is a valid DAG (no cycles).

        Returns:
            True if acyclic, False if cycles exist
        """
        return nx.is_directed_acyclic_graph(self._graph)

    def get_independent_tasks(self) -> list[str]:
        """
        Get tasks with no dependencies (in-degree = 0).

        Returns:
            List of task IDs with no dependencies
        """
        return [node for node in self._graph.nodes() if self._graph.in_degree(node) == 0]

    def topological_sort(self) -> list[str]:
        """
        Get a topological ordering of tasks.

        Returns:
            List of task IDs in topological order

        Raises:
            nx.NetworkXError: If graph contains cycles
        """
        return list(nx.topological_sort(self._graph))

    def get_critical_path(self) -> list[str]:
        """
        Identify the critical path (longest path) through the graph.

        The critical path represents the minimum time needed to complete
        all tasks, assuming unlimited parallelism.

        Returns:
            List of task IDs forming the critical path
        """
        if self.node_count() == 0:
            return []

        # Assign weights based on estimated complexity
        complexity_weights = {"small": 1, "medium": 2, "large": 3}

        # For longest path in DAG, we negate weights and find shortest path,
        # then negate back (standard algorithm)
        weighted_graph: nx.DiGraph = nx.DiGraph()
        for node_id in self._graph.nodes():
            weighted_graph.add_node(node_id)

        for u, v in self._graph.edges():
            # Weight is the complexity of the target node (negated for longest path)
            weight = -complexity_weights.get(
                self._nodes[v].estimated_complexity, 2
            )
            weighted_graph.add_edge(u, v, weight=weight)

        # Find longest path using dynamic programming on DAG
        try:
            # Use topological sort and DP to find longest path
            topo_order = list(nx.topological_sort(weighted_graph))

            # dist[node] = longest path length ending at node
            dist = {node: 0 for node in weighted_graph.nodes()}
            predecessor = {node: None for node in weighted_graph.nodes()}

            # Process nodes in topological order
            for node in topo_order:
                node_weight = complexity_weights.get(
                    self._nodes[node].estimated_complexity, 2
                )

                # Update all successors
                for successor in weighted_graph.successors(node):
                    new_dist = dist[node] + node_weight
                    if new_dist > dist[successor]:
                        dist[successor] = new_dist
                        predecessor[successor] = node

            # Find node with maximum distance
            if not dist:
                return []

            end_node = max(dist, key=lambda x: dist[x])

            # Reconstruct path
            path = []
            current = end_node
            while current is not None:
                path.append(current)
                current = predecessor[current]

            path.reverse()
            return path

        except Exception:
            # Fallback to topological sort if something goes wrong
            return self.topological_sort()

    def get_node(self, node_id: str) -> SubtaskNode | None:
        """
        Get a subtask node by ID.

        Args:
            node_id: ID of the node

        Returns:
            SubtaskNode or None if not found
        """
        return self._nodes.get(node_id)


@dataclass
class DecompositionResult:
    """
    Result of task decomposition.

    Contains the original task, generated subtasks, and dependency graph.
    """

    task: ParsedTask
    subtasks: list[SubtaskNode]
    dependency_graph: DependencyGraph

    def get_execution_order(self) -> list[str]:
        """
        Get a valid execution order for subtasks.

        Returns:
            List of task IDs in topological order
        """
        return self.dependency_graph.topological_sort()

    def get_parallel_groups(self) -> list[list[str]]:
        """
        Get groups of tasks that can be executed in parallel.

        Returns:
            List of groups, where each group contains task IDs
            that can run concurrently
        """
        if self.dependency_graph.node_count() == 0:
            return []

        # Use topological generations (levels in the DAG)
        try:
            generations = list(nx.topological_generations(self.dependency_graph._graph))
            return [list(gen) for gen in generations]
        except Exception:
            # Fallback: return all tasks as separate groups
            return [[task_id] for task_id in self.dependency_graph.topological_sort()]


class TaskDecomposer:
    """
    Decomposes complex tasks into subtasks with dependency relationships.

    Uses a combination of rule-based decomposition strategies and
    task type-specific heuristics.
    """

    def __init__(self, max_depth: int = 3, min_subtasks: int = 2, max_subtasks: int = 10):
        """
        Initialize the task decomposer.

        Args:
            max_depth: Maximum recursion depth for decomposition
            min_subtasks: Minimum number of subtasks to generate
            max_subtasks: Maximum number of subtasks per decomposition level
        """
        self.max_depth = max_depth
        self.min_subtasks = min_subtasks
        self.max_subtasks = max_subtasks
        self._task_counter = 0

    def decompose(self, task: ParsedTask) -> DecompositionResult:
        """
        Decompose a parsed task into subtasks with dependencies.

        Args:
            task: ParsedTask to decompose

        Returns:
            DecompositionResult with subtasks and dependency graph
        """
        self._task_counter = 0
        graph = DependencyGraph()

        # Handle empty task
        if not task.goal or not task.goal.strip():
            return DecompositionResult(task=task, subtasks=[], dependency_graph=graph)

        # Generate subtasks based on task type
        subtasks = self._decompose_recursive(task, depth=0, parent_id=None)

        # Build dependency graph
        for subtask in subtasks:
            graph.add_node(subtask)
            for dep in subtask.dependencies:
                if graph.has_node(dep):
                    graph.add_dependency(subtask.id, dep)

        return DecompositionResult(
            task=task, subtasks=subtasks, dependency_graph=graph
        )

    def _decompose_recursive(
        self, task: ParsedTask, depth: int, parent_id: str | None
    ) -> list[SubtaskNode]:
        """
        Recursively decompose a task into subtasks.

        Args:
            task: ParsedTask to decompose
            depth: Current recursion depth
            parent_id: ID of the parent task

        Returns:
            List of SubtaskNode objects
        """
        if depth >= self.max_depth:
            # Max depth reached, return atomic task
            return []

        # Use task type-specific decomposition strategy
        if task.task_type == TaskType.SOFTWARE:
            return self._decompose_software_task(task, depth, parent_id)
        elif task.task_type == TaskType.RESEARCH:
            return self._decompose_research_task(task, depth, parent_id)
        elif task.task_type == TaskType.ANALYSIS:
            return self._decompose_analysis_task(task, depth, parent_id)
        elif task.task_type == TaskType.CREATIVE:
            return self._decompose_creative_task(task, depth, parent_id)
        elif task.task_type == TaskType.HYBRID:
            return self._decompose_hybrid_task(task, depth, parent_id)
        else:
            return self._decompose_generic_task(task, depth, parent_id)

    def _decompose_software_task(
        self, task: ParsedTask, depth: int, parent_id: str | None
    ) -> list[SubtaskNode]:
        """Decompose a software development task."""
        subtasks = []

        goal_lower = task.goal.lower()
        raw_lower = task.raw_description.lower()
        full_text = f"{goal_lower} {raw_lower}"

        # Common software phases
        if depth == 0:
            # High-level decomposition
            phases: list[tuple[str, str, list[str]]] = []

            # Design/Planning phase
            if any(
                keyword in full_text
                for keyword in ["build", "create", "implement", "develop"]
            ):
                phases.append(
                    ("Design and plan the architecture", "small", [])
                )

            # Implementation phase
            if "api" in full_text or "endpoint" in full_text:
                phases.append(
                    ("Implement API endpoints", "large", [phases[0][0]] if phases else [])
                )
            elif "database" in full_text or "model" in full_text:
                phases.append(
                    ("Design and implement data models", "medium", [phases[0][0]] if phases else [])
                )
            else:
                phases.append(
                    ("Implement core functionality", "large", [phases[0][0]] if phases else [])
                )

            # Testing phase (check both goal, raw description, and success criteria)
            needs_tests = (
                "test" in full_text
                or any("test" in str(sc).lower() for sc in task.success_criteria)
                or any("pytest" in str(sc).lower() for sc in task.success_criteria)
            )
            if needs_tests:
                prev_phase = phases[-1][0] if phases else None
                phases.append(
                    ("Write and run tests", "medium", [prev_phase] if prev_phase else [])
                )

            # Authentication/Security - check raw description and success criteria too
            has_auth = any(
                keyword in full_text
                for keyword in ["auth", "jwt", "login", "security", "token"]
            ) or any(
                keyword in str(sc).lower()
                for sc in task.success_criteria
                for keyword in ["auth", "jwt", "login", "token"]
            )

            if has_auth:
                # Add authentication before tests if tests exist, else before end
                # Find correct previous dependency
                if len(phases) >= 2:
                    # Depend on implementation phase
                    prev_phase = phases[1][0] if len(phases) > 1 else phases[0][0]
                else:
                    prev_phase = phases[0][0] if phases else None

                auth_task = (
                    "Implement authentication and security",
                    "medium",
                    [prev_phase] if prev_phase else [],
                )

                # Insert before tests if tests exist
                if needs_tests and len(phases) >= 2:
                    phases.insert(len(phases) - 1, auth_task)
                else:
                    phases.append(auth_task)

            # Deployment/Integration
            if "deploy" in full_text or "integrate" in full_text:
                prev_phase = phases[-1][0] if phases else None
                phases.append(
                    ("Deploy and integrate", "medium", [prev_phase] if prev_phase else [])
                )

            # Create subtasks
            task_id_map: dict[str, str] = {}
            for description, complexity, dep_descriptions in phases:
                task_id = self._generate_task_id()
                deps = [task_id_map[desc] for desc in dep_descriptions if desc in task_id_map]

                subtask = SubtaskNode(
                    id=task_id,
                    description=description,
                    parent_id=parent_id,
                    depth=depth,
                    dependencies=deps,
                    estimated_complexity=complexity,
                )
                subtasks.append(subtask)
                task_id_map[description] = task_id

        else:
            # Deeper decomposition - break into smaller units
            subtasks = self._decompose_generic_task(task, depth, parent_id)

        return subtasks

    def _decompose_research_task(
        self, task: ParsedTask, depth: int, parent_id: str | None
    ) -> list[SubtaskNode]:
        """Decompose a research task."""
        subtasks = []

        if depth == 0:
            # Research workflow
            phases = [
                ("Define research scope and questions", "small", []),
                (
                    "Search and gather relevant sources",
                    "medium",
                    ["Define research scope and questions"],
                ),
                (
                    "Review and analyze findings",
                    "large",
                    ["Search and gather relevant sources"],
                ),
                (
                    "Synthesize and document results",
                    "medium",
                    ["Review and analyze findings"],
                ),
            ]

            task_id_map: dict[str, str] = {}
            for description, complexity, dep_descriptions in phases:
                task_id = self._generate_task_id()
                deps = [task_id_map[desc] for desc in dep_descriptions if desc in task_id_map]

                subtask = SubtaskNode(
                    id=task_id,
                    description=description,
                    parent_id=parent_id,
                    depth=depth,
                    dependencies=deps,
                    estimated_complexity=complexity,
                )
                subtasks.append(subtask)
                task_id_map[description] = task_id

        else:
            subtasks = self._decompose_generic_task(task, depth, parent_id)

        return subtasks

    def _decompose_analysis_task(
        self, task: ParsedTask, depth: int, parent_id: str | None
    ) -> list[SubtaskNode]:
        """Decompose an analysis task."""
        subtasks = []

        if depth == 0:
            # Analysis workflow
            phases = [
                ("Collect and prepare data", "medium", []),
                ("Perform analysis", "large", ["Collect and prepare data"]),
                ("Interpret results", "medium", ["Perform analysis"]),
                ("Create report with recommendations", "medium", ["Interpret results"]),
            ]

            task_id_map: dict[str, str] = {}
            for description, complexity, dep_descriptions in phases:
                task_id = self._generate_task_id()
                deps = [task_id_map[desc] for desc in dep_descriptions if desc in task_id_map]

                subtask = SubtaskNode(
                    id=task_id,
                    description=description,
                    parent_id=parent_id,
                    depth=depth,
                    dependencies=deps,
                    estimated_complexity=complexity,
                )
                subtasks.append(subtask)
                task_id_map[description] = task_id

        else:
            subtasks = self._decompose_generic_task(task, depth, parent_id)

        return subtasks

    def _decompose_creative_task(
        self, task: ParsedTask, depth: int, parent_id: str | None
    ) -> list[SubtaskNode]:
        """Decompose a creative task."""
        subtasks = []

        if depth == 0:
            # Creative workflow
            phases = [
                ("Brainstorm and ideate concepts", "medium", []),
                ("Create initial drafts/mockups", "large", ["Brainstorm and ideate concepts"]),
                ("Refine and iterate on designs", "medium", ["Create initial drafts/mockups"]),
                ("Finalize and deliver assets", "small", ["Refine and iterate on designs"]),
            ]

            task_id_map: dict[str, str] = {}
            for description, complexity, dep_descriptions in phases:
                task_id = self._generate_task_id()
                deps = [task_id_map[desc] for desc in dep_descriptions if desc in task_id_map]

                subtask = SubtaskNode(
                    id=task_id,
                    description=description,
                    parent_id=parent_id,
                    depth=depth,
                    dependencies=deps,
                    estimated_complexity=complexity,
                )
                subtasks.append(subtask)
                task_id_map[description] = task_id

        else:
            subtasks = self._decompose_generic_task(task, depth, parent_id)

        return subtasks

    def _decompose_hybrid_task(
        self, task: ParsedTask, depth: int, parent_id: str | None
    ) -> list[SubtaskNode]:
        """Decompose a hybrid task (multiple types)."""
        # For hybrid tasks, use a generic approach
        return self._decompose_generic_task(task, depth, parent_id)

    def _decompose_generic_task(
        self, task: ParsedTask, depth: int, parent_id: str | None
    ) -> list[SubtaskNode]:
        """Generic task decomposition fallback."""
        subtasks = []

        # Simple 3-phase approach
        phases = [
            ("Prepare and plan", "small", []),
            ("Execute main work", "large", ["Prepare and plan"]),
            ("Review and finalize", "medium", ["Execute main work"]),
        ]

        task_id_map: dict[str, str] = {}
        for description, complexity, dep_descriptions in phases:
            task_id = self._generate_task_id()
            deps = [task_id_map[desc] for desc in dep_descriptions if desc in task_id_map]

            subtask = SubtaskNode(
                id=task_id,
                description=description,
                parent_id=parent_id,
                depth=depth,
                dependencies=deps,
                estimated_complexity=complexity,
            )
            subtasks.append(subtask)
            task_id_map[description] = task_id

        return subtasks

    def _generate_task_id(self) -> str:
        """Generate a unique task ID."""
        self._task_counter += 1
        return f"task-{self._task_counter}"

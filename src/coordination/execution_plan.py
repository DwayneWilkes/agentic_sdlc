"""Execution Plan Generator - Creates execution plans with parallelism analysis.

Generates execution plans that:
- Show parallel execution opportunities
- Identify critical paths
- Detect bottlenecks
- Estimate completion time
"""

from dataclasses import dataclass, field

from src.models.task import Subtask


@dataclass
class ExecutionStage:
    """A group of tasks that can execute in parallel.

    Represents one stage in the execution plan where all tasks
    can run concurrently without violating dependencies.
    """

    stage_number: int
    tasks: list[str]  # Task IDs that can run in parallel
    estimated_duration: int  # Complexity units for this stage


@dataclass
class ExecutionPlan:
    """Represents an execution plan for a set of tasks.

    Contains:
    - Sequential stages of parallel tasks
    - Critical path (longest dependency chain)
    - Bottlenecks (tasks with high fan-out)
    - Time estimates
    """

    stages: list[ExecutionStage] = field(default_factory=list)
    critical_path: list[str] = field(default_factory=list)
    bottlenecks: list[str] = field(default_factory=list)
    total_estimated_time: int = 0
    max_parallelism: int = 0


class ExecutionPlanGenerator:
    """Generates execution plans from task DAGs.

    Analyzes task dependencies to create an execution plan that:
    1. Groups tasks into parallel execution stages
    2. Identifies the critical path
    3. Detects bottlenecks
    4. Estimates completion time
    """

    # Complexity weights for time estimation
    COMPLEXITY_WEIGHTS = {
        "small": 1,
        "medium": 2,
        "large": 3,
    }

    def generate(self, tasks: list[Subtask]) -> ExecutionPlan:
        """Generate an execution plan from a list of subtasks.

        Args:
            tasks: List of subtasks with dependency information

        Returns:
            ExecutionPlan with stages, critical path, and estimates

        Raises:
            ValueError: If circular dependencies or missing dependencies found
        """
        if not tasks:
            return ExecutionPlan()

        # Validate dependencies
        self._validate_dependencies(tasks)

        # Build task map for quick lookup
        task_map = {t.id: t for t in tasks}

        # Calculate execution stages
        stages = self._calculate_stages(tasks, task_map)

        # Identify critical path
        critical_path = self._calculate_critical_path(tasks, task_map)

        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(tasks)

        # Calculate max parallelism
        max_parallelism = max((len(stage.tasks) for stage in stages), default=0)

        # Estimate total time (sum of stage durations)
        total_time = sum(stage.estimated_duration for stage in stages)

        return ExecutionPlan(
            stages=stages,
            critical_path=critical_path,
            bottlenecks=bottlenecks,
            total_estimated_time=total_time,
            max_parallelism=max_parallelism,
        )

    def format_plan_text(self, plan: ExecutionPlan) -> str:
        """Format execution plan as human-readable text.

        Args:
            plan: ExecutionPlan to format

        Returns:
            Formatted text representation
        """
        if not plan.stages:
            return "No tasks to execute"

        lines = []
        lines.append("=== Execution Plan ===\n")

        # Show stages
        lines.append("Execution Stages:")
        for stage in plan.stages:
            task_list = ", ".join(stage.tasks)
            lines.append(
                f"  Stage {stage.stage_number}: [{task_list}] "
                f"(~{stage.estimated_duration} units)"
            )

        # Show critical path
        lines.append(f"\nCritical Path: {' -> '.join(plan.critical_path)}")

        # Show bottlenecks
        if plan.bottlenecks:
            lines.append(f"Bottlenecks: {', '.join(plan.bottlenecks)}")

        # Show summary
        lines.append(f"\nTotal Estimated Time: {plan.total_estimated_time} units")
        lines.append(f"Max Parallelism: {plan.max_parallelism} tasks")

        return "\n".join(lines)

    def _validate_dependencies(self, tasks: list[Subtask]) -> None:
        """Validate that all dependencies exist and there are no cycles.

        Args:
            tasks: List of subtasks to validate

        Raises:
            ValueError: If circular dependencies or missing dependencies found
        """
        task_ids = {t.id for t in tasks}

        # Check for missing dependencies
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    raise ValueError(
                        f"Task '{task.id}' depends on missing task '{dep_id}'"
                    )

        # Check for circular dependencies using DFS
        visited = set()
        rec_stack = set()
        task_map = {t.id: t for t in tasks}

        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = task_map[task_id]
            for dep_id in task.dependencies:
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task in tasks:
            if task.id not in visited:
                if has_cycle(task.id):
                    raise ValueError(
                        f"Circular dependency detected involving task '{task.id}'"
                    )

    def _calculate_stages(
        self, tasks: list[Subtask], task_map: dict[str, Subtask]
    ) -> list[ExecutionStage]:
        """Calculate execution stages using topological layering.

        Args:
            tasks: List of all tasks
            task_map: Dictionary mapping task IDs to tasks

        Returns:
            List of execution stages in order
        """
        if not tasks:
            return []

        # Calculate the "level" of each task (longest path from a root)
        levels: dict[str, int] = {}

        def calculate_level(task_id: str) -> int:
            if task_id in levels:
                return levels[task_id]

            task = task_map[task_id]
            if not task.dependencies:
                levels[task_id] = 0
                return 0

            # Level is 1 + max level of dependencies
            max_dep_level = max(
                calculate_level(dep_id) for dep_id in task.dependencies
            )
            levels[task_id] = max_dep_level + 1
            return levels[task_id]

        # Calculate levels for all tasks
        for task in tasks:
            calculate_level(task.id)

        # Group tasks by level
        max_level = max(levels.values()) if levels else 0
        stages = []

        for level in range(max_level + 1):
            task_ids = [tid for tid, lv in levels.items() if lv == level]

            if task_ids:
                # Calculate stage duration (max complexity in this stage)
                durations = []
                for tid in task_ids:
                    task = task_map[tid]
                    complexity = task.metadata.get("estimated_complexity", "medium")
                    duration = self.COMPLEXITY_WEIGHTS.get(complexity, 2)
                    durations.append(duration)

                stage_duration = max(durations) if durations else 0

                stages.append(
                    ExecutionStage(
                        stage_number=level,
                        tasks=sorted(task_ids),  # Sort for determinism
                        estimated_duration=stage_duration,
                    )
                )

        return stages

    def _calculate_critical_path(
        self, tasks: list[Subtask], task_map: dict[str, Subtask]
    ) -> list[str]:
        """Calculate the critical path (longest path) through the DAG.

        Args:
            tasks: List of all tasks
            task_map: Dictionary mapping task IDs to tasks

        Returns:
            List of task IDs forming the critical path
        """
        if not tasks:
            return []

        # Calculate longest path to each node
        dist: dict[str, int] = {}
        predecessor: dict[str, str | None] = {}

        def calculate_distance(task_id: str) -> int:
            if task_id in dist:
                return dist[task_id]

            task = task_map[task_id]
            complexity = task.metadata.get("estimated_complexity", "medium")
            task_weight = self.COMPLEXITY_WEIGHTS.get(complexity, 2)

            if not task.dependencies:
                dist[task_id] = task_weight
                predecessor[task_id] = None
                return task_weight

            # Find max distance through dependencies
            max_dist = 0
            max_pred = None

            for dep_id in task.dependencies:
                dep_dist = calculate_distance(dep_id)
                if dep_dist > max_dist:
                    max_dist = dep_dist
                    max_pred = dep_id

            dist[task_id] = max_dist + task_weight
            predecessor[task_id] = max_pred
            return dist[task_id]

        # Calculate distances for all tasks
        for task in tasks:
            calculate_distance(task.id)

        # Find task with maximum distance (end of critical path)
        if not dist:
            return []

        end_task = max(dist, key=lambda x: dist[x])

        # Reconstruct path
        path = []
        current: str | None = end_task
        while current is not None:
            path.append(current)
            current = predecessor.get(current)

        path.reverse()
        return path

    def _identify_bottlenecks(self, tasks: list[Subtask]) -> list[str]:
        """Identify bottleneck tasks with high fan-out.

        A bottleneck is a task that many other tasks depend on.

        Args:
            tasks: List of all tasks

        Returns:
            List of task IDs that are bottlenecks
        """
        # Count how many tasks depend on each task
        dependents: dict[str, int] = {t.id: 0 for t in tasks}

        for task in tasks:
            for dep_id in task.dependencies:
                dependents[dep_id] = dependents.get(dep_id, 0) + 1

        # Tasks with >= 3 dependents are bottlenecks
        bottlenecks = [
            task_id for task_id, count in dependents.items() if count >= 3
        ]

        return sorted(bottlenecks)

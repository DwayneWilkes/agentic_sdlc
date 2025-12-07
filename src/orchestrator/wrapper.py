"""
Orchestrator Wrapper - Smart dispatcher for natural language requests.

This module provides the OrchestratorWrapper class that accepts ANY natural
language request and routes it appropriately:
- Simple tasks → single agent
- Complex tasks → decompose → parallel coordinated team
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.role_registry import RoleRegistry
from src.core.task_decomposer import DecompositionResult, TaskDecomposer
from src.core.task_parser import ParsedTask, TaskParser


class ComplexityLevel(str, Enum):
    """Complexity level of a task."""

    SIMPLE = "simple"  # Single straightforward action
    MEDIUM = "medium"  # A few related steps
    COMPLEX = "complex"  # Multiple subtasks with dependencies


class ExecutionMode(str, Enum):
    """Execution mode for a task."""

    SINGLE_AGENT = "single_agent"  # Run with a single agent
    COORDINATED_TEAM = "coordinated_team"  # Run with coordinated team


@dataclass
class ComplexityAssessment:
    """
    Assessment of task complexity.

    Attributes:
        level: The assessed complexity level
        estimated_subtasks: Estimated number of subtasks needed
        reasoning: Explanation of the assessment
    """

    level: ComplexityLevel
    estimated_subtasks: int = 1
    reasoning: str = ""


@dataclass
class ExecutionResult:
    """
    Result of processing a request.

    Attributes:
        request: Original natural language request
        parsed_task: Parsed task structure
        mode: Execution mode used
        success: Whether execution was successful
        decomposition: Task decomposition (for complex tasks)
        clarifications: Clarification questions (if ambiguities found)
        error: Error message (if failed)
        metadata: Additional execution metadata
    """

    request: str
    parsed_task: ParsedTask
    mode: ExecutionMode
    success: bool
    decomposition: DecompositionResult | None = None
    clarifications: list[str] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class OrchestratorWrapper:
    """
    Smart dispatcher that accepts natural language requests and routes them.

    Flow:
    1. User provides natural language request
    2. TaskParser extracts goal, constraints, context, task_type
    3. Assess complexity:
       - Simple: Spawn single Claude Code agent directly
       - Complex: Decompose → Assign roles → Spawn parallel agents
    4. Coordinate execution via NATS
    5. Integrate outputs and return result

    Example:
        >>> wrapper = OrchestratorWrapper()
        >>> result = wrapper.process_request("Fix the typo in README.md")
        >>> print(result.mode)
        ExecutionMode.SINGLE_AGENT
    """

    def __init__(self, dry_run: bool = False):
        """
        Initialize the orchestrator wrapper.

        Args:
            dry_run: If True, don't actually spawn agents (for testing)
        """
        self.dry_run = dry_run
        self.task_parser = TaskParser()
        self.task_decomposer = TaskDecomposer()
        self.role_registry = RoleRegistry.create_standard_registry()

    def process_request(self, request: str) -> ExecutionResult:
        """
        Process a natural language request.

        Args:
            request: Natural language task description

        Returns:
            ExecutionResult with execution details and results
        """
        # Phase 1: Parse the request
        parsed = self.task_parser.parse(request)

        # Phase 2: Check for ambiguities
        clarifications = parsed.generate_clarification_requests()

        # Phase 3: Assess complexity
        assessment = self.assess_complexity(parsed)

        # Phase 4: Select execution mode
        mode = self.select_execution_mode(parsed)

        # Phase 5: Execute based on mode
        if mode == ExecutionMode.SINGLE_AGENT:
            return self._execute_single_agent(
                request, parsed, clarifications, assessment
            )
        else:
            return self._execute_coordinated_team(
                request, parsed, clarifications, assessment
            )

    def assess_complexity(self, parsed: ParsedTask) -> ComplexityAssessment:
        """
        Assess the complexity of a parsed task.

        Heuristics:
        - SIMPLE: Single-file edit, typo fix, simple refactor, single command
        - MEDIUM: Multiple related steps, moderate refactoring, research task
        - COMPLEX: Multiple independent components, system design, full features

        Args:
            parsed: Parsed task to assess

        Returns:
            ComplexityAssessment with level and reasoning
        """
        # Count complexity indicators
        num_success_criteria = len(parsed.success_criteria)
        num_constraint_types = len(parsed.constraints)
        num_context_types = len(parsed.context)

        # Check for complexity keywords in goal
        goal_lower = parsed.goal.lower()
        complex_keywords = [
            "build",
            "create",
            "implement",
            "system",
            "full",
            "complete",
            "multiple",
            "integrate",
        ]
        simple_keywords = ["fix", "update", "change", "add", "remove", "single"]

        complex_score = sum(1 for kw in complex_keywords if kw in goal_lower)
        simple_score = sum(1 for kw in simple_keywords if kw in goal_lower)

        # Calculate total complexity score
        total_score = (
            num_success_criteria * 2  # Weight success criteria more heavily
            + num_constraint_types
            + num_context_types
            + complex_score * 2  # Weight complex keywords more
            - simple_score
        )

        # Determine level
        if total_score <= 2:
            level = ComplexityLevel.SIMPLE
            estimated = 1
            reasoning = (
                f"Single straightforward action (score: {total_score}). "
                f"Success criteria: {num_success_criteria}, "
                f"Constraints: {num_constraint_types}"
            )
        elif total_score <= 6:
            level = ComplexityLevel.MEDIUM
            estimated = 3
            reasoning = (
                f"A few related steps needed (score: {total_score}). "
                f"Success criteria: {num_success_criteria}, "
                f"Constraints: {num_constraint_types}"
            )
        else:
            level = ComplexityLevel.COMPLEX
            estimated = max(4, num_success_criteria)
            reasoning = (
                f"Multiple subtasks with dependencies (score: {total_score}). "
                f"Success criteria: {num_success_criteria}, "
                f"Constraints: {num_constraint_types}, "
                f"Complex keywords: {complex_score}"
            )

        return ComplexityAssessment(
            level=level, estimated_subtasks=estimated, reasoning=reasoning
        )

    def select_execution_mode(self, parsed: ParsedTask) -> ExecutionMode:
        """
        Select execution mode based on task complexity.

        Args:
            parsed: Parsed task to evaluate

        Returns:
            ExecutionMode to use
        """
        assessment = self.assess_complexity(parsed)

        if assessment.level == ComplexityLevel.SIMPLE:
            return ExecutionMode.SINGLE_AGENT
        else:
            return ExecutionMode.COORDINATED_TEAM

    def _execute_single_agent(
        self,
        request: str,
        parsed: ParsedTask,
        clarifications: list[str],
        assessment: ComplexityAssessment,
    ) -> ExecutionResult:
        """
        Execute a simple task with a single agent.

        Args:
            request: Original request
            parsed: Parsed task
            clarifications: Clarification questions
            assessment: Complexity assessment

        Returns:
            ExecutionResult
        """
        if self.dry_run:
            # In dry run mode, just return success
            return ExecutionResult(
                request=request,
                parsed_task=parsed,
                mode=ExecutionMode.SINGLE_AGENT,
                success=True,
                clarifications=clarifications if clarifications else None,
                metadata={
                    "dry_run": True,
                    "assessment": {
                        "level": assessment.level.value,
                        "reasoning": assessment.reasoning,
                    },
                },
            )

        # TODO: Actually spawn a single Claude Code agent
        # For now, return a placeholder result
        return ExecutionResult(
            request=request,
            parsed_task=parsed,
            mode=ExecutionMode.SINGLE_AGENT,
            success=False,
            error="Single agent execution not yet implemented",
            clarifications=clarifications if clarifications else None,
        )

    def _execute_coordinated_team(
        self,
        request: str,
        parsed: ParsedTask,
        clarifications: list[str],
        assessment: ComplexityAssessment,
    ) -> ExecutionResult:
        """
        Execute a complex task with a coordinated team.

        Args:
            request: Original request
            parsed: Parsed task
            clarifications: Clarification questions
            assessment: Complexity assessment

        Returns:
            ExecutionResult with decomposition
        """
        # Decompose the task
        decomposition = self.task_decomposer.decompose(parsed)

        if self.dry_run:
            # In dry run mode, return success with decomposition
            return ExecutionResult(
                request=request,
                parsed_task=parsed,
                mode=ExecutionMode.COORDINATED_TEAM,
                success=True,
                decomposition=decomposition,
                clarifications=clarifications if clarifications else None,
                metadata={
                    "dry_run": True,
                    "assessment": {
                        "level": assessment.level.value,
                        "reasoning": assessment.reasoning,
                    },
                    "subtask_count": decomposition.dependency_graph.node_count(),
                },
            )

        # TODO: Actually spawn coordinated team
        # For now, return a placeholder result
        return ExecutionResult(
            request=request,
            parsed_task=parsed,
            mode=ExecutionMode.COORDINATED_TEAM,
            success=False,
            decomposition=decomposition,
            error="Coordinated team execution not yet implemented",
            clarifications=clarifications if clarifications else None,
        )

"""
Output Integration Engine - Phase 6.3

Combines agent outputs into coherent final results and validates against original goals.

Features:
1. Combine outputs from multiple subtasks
2. Validate integrated output against original goal/requirements
3. Detect and report inconsistencies between agent outputs
4. Verify requirement coverage completeness

Usage:
    from src.coordination.output_integration import OutputIntegrationEngine

    engine = OutputIntegrationEngine()
    result = engine.integrate_outputs(task, subtasks)

    if result.success:
        print(f"Integration successful: {result.combined_output}")
        val = result.validation_result
        print(f"Requirements met: {val.requirements_met}/{val.requirements_total}")

    if result.inconsistencies:
        print(f"Found {len(result.inconsistencies)} inconsistencies")
        for inc in result.inconsistencies:
            print(f"  - {inc.description}")
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.models.enums import TaskStatus
from src.models.task import Subtask, Task

# =============================================================================
# Enums
# =============================================================================


class InconsistencyType(str, Enum):
    """Types of inconsistencies that can occur between agent outputs."""

    SCHEMA_CONFLICT = "schema_conflict"  # Conflicting data structures
    DUPLICATE_WORK = "duplicate_work"  # Duplicate implementations
    MISSING_INTEGRATION = "missing_integration"  # Missing links between dependent outputs
    CONFLICTING_LOGIC = "conflicting_logic"  # Contradictory business logic
    INCOMPATIBLE_VERSIONS = "incompatible_versions"  # Version mismatches


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SubtaskOutput:
    """Represents the output from a single subtask."""

    subtask_id: str
    agent_id: str | None
    status: TaskStatus
    output: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class InconsistencyReport:
    """Report of an inconsistency between agent outputs."""

    inconsistency_type: InconsistencyType
    affected_subtasks: list[str]
    description: str
    severity: str = "medium"  # low, medium, high, critical
    suggested_resolution: str | None = None


@dataclass
class ValidationResult:
    """Result of validating integrated output against goal."""

    is_valid: bool
    requirements_met: int
    requirements_total: int
    missing_requirements: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class IntegrationResult:
    """Result of integrating agent outputs."""

    success: bool
    subtask_outputs: list[SubtaskOutput] = field(default_factory=list)
    combined_output: dict[str, Any] | None = None
    validation_result: ValidationResult = field(
        default_factory=lambda: ValidationResult(
            is_valid=False, requirements_met=0, requirements_total=0
        )
    )
    inconsistencies: list[InconsistencyReport] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# Output Integration Engine
# =============================================================================


class OutputIntegrationEngine:
    """
    Integrates outputs from multiple agents into a coherent final result.

    Responsibilities:
    1. Collect and combine agent outputs
    2. Validate against original task goals
    3. Detect inconsistencies and conflicts
    4. Verify requirement coverage
    """

    def integrate_outputs(self, task: Task, subtasks: list[Subtask]) -> IntegrationResult:
        """
        Integrate outputs from all subtasks into a final result.

        Args:
            task: Original task with goals and requirements
            subtasks: List of subtasks (some may be completed, others not)

        Returns:
            IntegrationResult with combined output and validation
        """
        # Extract outputs from completed subtasks
        subtask_outputs = self.extract_subtask_outputs(subtasks)

        # Check if we have any outputs to integrate
        if not subtask_outputs:
            return IntegrationResult(
                success=False,
                validation_result=ValidationResult(
                    is_valid=False,
                    requirements_met=0,
                    requirements_total=self._count_requirements(task),
                    message="No completed subtasks to integrate",
                ),
            )

        # Combine the outputs
        combined = self._combine_outputs(subtask_outputs)

        # Detect inconsistencies
        inconsistencies = self.detect_inconsistencies(subtasks)

        # Validate against task goal
        validation = self._validate_against_goal(task, subtask_outputs, subtasks)

        # Check for incomplete work
        incomplete_count = sum(
            1
            for st in subtasks
            if st.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
        )
        if incomplete_count > 0:
            validation.message = (
                f"{validation.message} Note: {incomplete_count} subtask(s) still incomplete."
            )

        return IntegrationResult(
            success=len(subtask_outputs) > 0 and len(inconsistencies) == 0,
            subtask_outputs=subtask_outputs,
            combined_output=combined,
            validation_result=validation,
            inconsistencies=inconsistencies,
        )

    def extract_subtask_outputs(self, subtasks: list[Subtask]) -> list[SubtaskOutput]:
        """
        Extract outputs from completed subtasks.

        Args:
            subtasks: List of subtasks

        Returns:
            List of SubtaskOutput objects from completed tasks
        """
        outputs = []

        for subtask in subtasks:
            # Only process completed subtasks
            if subtask.status != TaskStatus.COMPLETED:
                continue

            # Extract output from metadata
            if subtask.metadata and "output" in subtask.metadata:
                output_data = subtask.metadata["output"]
            else:
                # No output metadata - use empty dict
                output_data = {}

            outputs.append(
                SubtaskOutput(
                    subtask_id=subtask.id,
                    agent_id=subtask.assigned_agent,
                    status=subtask.status,
                    output=output_data,
                )
            )

        return outputs

    def detect_inconsistencies(self, subtasks: list[Subtask]) -> list[InconsistencyReport]:
        """
        Detect inconsistencies and conflicts between agent outputs.

        Args:
            subtasks: List of subtasks to analyze

        Returns:
            List of detected inconsistencies
        """
        inconsistencies: list[InconsistencyReport] = []

        # Get only completed subtasks
        completed = [st for st in subtasks if st.status == TaskStatus.COMPLETED]

        if len(completed) < 2:
            # Need at least 2 outputs to detect conflicts
            return inconsistencies

        # Check for schema conflicts
        schema_conflicts = self._detect_schema_conflicts(completed)
        inconsistencies.extend(schema_conflicts)

        # Check for duplicate work
        duplicates = self._detect_duplicate_work(completed)
        inconsistencies.extend(duplicates)

        # Check for missing integration points
        missing_integrations = self._detect_missing_integrations(completed)
        inconsistencies.extend(missing_integrations)

        return inconsistencies

    def verify_requirement_coverage(
        self, task: Task, outputs: list[SubtaskOutput]
    ) -> dict[str, Any]:
        """
        Verify that outputs cover all task requirements.

        Args:
            task: Original task with requirements
            outputs: Integrated subtask outputs

        Returns:
            Dictionary with coverage metrics
        """
        requirements = self._extract_requirements(task)
        total_count = len(requirements)

        if total_count == 0:
            # No explicit requirements - consider fully covered
            return {
                "coverage_percentage": 100.0,
                "met_count": 0,
                "total_count": 0,
                "missing_requirements": [],
            }

        # Check which requirements are met by outputs
        met_requirements = []
        missing_requirements = []

        for requirement in requirements:
            if self._is_requirement_met(requirement, outputs):
                met_requirements.append(requirement)
            else:
                missing_requirements.append(requirement)

        met_count = len(met_requirements)
        coverage_percentage = (met_count / total_count) * 100

        return {
            "coverage_percentage": coverage_percentage,
            "met_count": met_count,
            "total_count": total_count,
            "missing_requirements": missing_requirements,
        }

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _combine_outputs(self, outputs: list[SubtaskOutput]) -> dict[str, Any]:
        """
        Combine multiple subtask outputs into a single unified result.

        Args:
            outputs: List of subtask outputs

        Returns:
            Combined output dictionary
        """
        combined = {
            "subtasks": {},
            "metadata": {
                "total_subtasks": len(outputs),
                "combined_at": datetime.now().isoformat(),
            },
        }

        for output in outputs:
            combined["subtasks"][output.subtask_id] = {
                "agent_id": output.agent_id,
                "output": output.output,
                "timestamp": output.timestamp.isoformat(),
            }

        return combined

    def _validate_against_goal(
        self, task: Task, outputs: list[SubtaskOutput], all_subtasks: list[Subtask]
    ) -> ValidationResult:
        """
        Validate that integrated outputs satisfy the original task goal.

        Args:
            task: Original task
            outputs: Integrated outputs
            all_subtasks: All subtasks (completed and incomplete)

        Returns:
            ValidationResult
        """
        # Get coverage metrics
        coverage = self.verify_requirement_coverage(task, outputs)

        is_valid = coverage["coverage_percentage"] == 100.0
        message = f"Requirements met: {coverage['met_count']}/{coverage['total_count']}"

        if not is_valid:
            message = f"{message} - Missing {len(coverage['missing_requirements'])} requirement(s)"

        return ValidationResult(
            is_valid=is_valid,
            requirements_met=coverage["met_count"],
            requirements_total=coverage["total_count"],
            missing_requirements=coverage["missing_requirements"],
            message=message,
        )

    def _extract_requirements(self, task: Task) -> list[str]:
        """
        Extract requirements from task constraints.

        Args:
            task: Task to extract requirements from

        Returns:
            List of requirement strings
        """
        requirements = []

        # Check for explicit requirements field
        if "requirements" in task.constraints:
            requirements.extend(task.constraints["requirements"])

        # Check for acceptance criteria
        if "acceptance_criteria" in task.constraints:
            requirements.extend(task.constraints["acceptance_criteria"])

        return requirements

    def _is_requirement_met(self, requirement: str, outputs: list[SubtaskOutput]) -> bool:
        """
        Check if a requirement is met by any of the outputs.

        Uses keyword matching in output content with flexible matching criteria.
        Supports exact matches, partial matches (substrings), and compound words.

        Args:
            requirement: Requirement string to check
            outputs: List of subtask outputs

        Returns:
            True if requirement appears to be met
        """
        # Extract keywords from requirement (lowercase)
        req_lower = requirement.lower()

        # Split into words and filter out common stop words
        stop_words = {
            "the", "and", "or", "with", "for", "must",
            "be", "to", "in", "on", "a", "an", "of"
        }

        # Extract words, but also split on hyphens to get components
        # E.g., "JWT-based" -> ["jwt", "based"]
        all_words = []
        for word in req_lower.replace("-", " ").split():
            if len(word) > 2 and word not in stop_words:
                all_words.append(word)

        # Also keep original hyphenated words for exact matching
        keywords = [
            word
            for word in req_lower.split()
            if len(word) > 2 and word not in stop_words
        ]

        # Combine both sets for more flexible matching
        all_keywords = list(set(all_words + keywords))

        if not all_keywords:
            # If no keywords, consider it met (edge case)
            return True

        # Check if any output mentions these keywords
        for output in outputs:
            output_str = str(output.output).lower()

            # Count how many keywords match (exact or substring)
            matched_keywords = sum(1 for keyword in all_keywords if keyword in output_str)

            # More flexible matching: if ANY significant keywords match, consider it met
            # Use 25% threshold for more lenient matching (at least 1 keyword must match)
            threshold = max(1, len(all_keywords) * 0.25)
            if matched_keywords >= threshold:
                return True

        return False

    def _count_requirements(self, task: Task) -> int:
        """Count total requirements in task."""
        return len(self._extract_requirements(task))

    def _detect_schema_conflicts(self, subtasks: list[Subtask]) -> list[InconsistencyReport]:
        """
        Detect conflicts in data schemas between outputs.

        Args:
            subtasks: Completed subtasks to check

        Returns:
            List of schema conflict reports
        """
        conflicts = []

        # Look for schema/schema_used fields
        schemas = {}
        for subtask in subtasks:
            if not subtask.metadata or "output" not in subtask.metadata:
                continue

            output = subtask.metadata["output"]

            # Check for schema definitions
            if "schema" in output:
                schemas[subtask.id] = ("schema", output["schema"])
            elif "schema_used" in output:
                schemas[subtask.id] = ("schema_used", output["schema_used"])

        # Compare schemas
        if len(schemas) >= 2:
            schema_list = list(schemas.items())
            for i in range(len(schema_list)):
                for j in range(i + 1, len(schema_list)):
                    st1_id, (field1, schema1) = schema_list[i]
                    st2_id, (field2, schema2) = schema_list[j]

                    # Check for conflicts in common fields
                    if isinstance(schema1, dict) and isinstance(schema2, dict):
                        common_fields = set(schema1.keys()) & set(schema2.keys())

                        for field in common_fields:
                            if schema1[field] != schema2[field]:
                                conflicts.append(
                                    InconsistencyReport(
                                        inconsistency_type=InconsistencyType.SCHEMA_CONFLICT,
                                        affected_subtasks=[st1_id, st2_id],
                                        description=(
                                            f"Schema conflict in field '{field}': "
                                            f"{schema1[field]} vs {schema2[field]}"
                                        ),
                                        severity="high",
                                        suggested_resolution=(
                                            f"Align on a single type for field '{field}'"
                                        ),
                                    )
                                )

        return conflicts

    def _detect_duplicate_work(self, subtasks: list[Subtask]) -> list[InconsistencyReport]:
        """
        Detect duplicate implementations between subtasks.

        Args:
            subtasks: Completed subtasks to check

        Returns:
            List of duplicate work reports
        """
        duplicates: list[InconsistencyReport] = []

        # Track function/module/implementation names
        implementations: dict[Any, str] = {}

        for subtask in subtasks:
            if not subtask.metadata or "output" not in subtask.metadata:
                continue

            output = subtask.metadata["output"]

            # Check for common duplicate indicators
            duplicate_keys = ["function", "module", "implementation", "route"]

            for key in duplicate_keys:
                if key in output:
                    value = output[key]

                    if value in implementations:
                        # Duplicate found
                        duplicates.append(
                            InconsistencyReport(
                                inconsistency_type=InconsistencyType.DUPLICATE_WORK,
                                affected_subtasks=[implementations[value], subtask.id],
                                description=(
                                    f"Duplicate {key}: '{value}' "
                                    f"implemented by multiple subtasks"
                                ),
                                severity="medium",
                                suggested_resolution=(
                                    f"Remove duplicate {key} and use single implementation"
                                ),
                            )
                        )
                    else:
                        implementations[value] = subtask.id

        return duplicates

    def _detect_missing_integrations(
        self, subtasks: list[Subtask]
    ) -> list[InconsistencyReport]:
        """
        Detect missing integration points between dependent subtasks.

        Args:
            subtasks: Completed subtasks to check

        Returns:
            List of missing integration reports
        """
        missing = []

        for subtask in subtasks:
            if not subtask.dependencies:
                continue

            # This subtask depends on others - check if integration exists
            if not subtask.metadata or "output" not in subtask.metadata:
                continue

            output = subtask.metadata["output"]

            # Check if output references dependencies (via imports, modules, etc.)
            has_integration = False

            # Look for integration indicators
            if "imports" in output and isinstance(output["imports"], list):
                if len(output["imports"]) > 0:
                    has_integration = True

            if "dependencies" in output and isinstance(output["dependencies"], list):
                if len(output["dependencies"]) > 0:
                    has_integration = True

            # If has dependencies but no integration found, report it
            if not has_integration and len(subtask.dependencies) > 0:
                missing.append(
                    InconsistencyReport(
                        inconsistency_type=InconsistencyType.MISSING_INTEGRATION,
                        affected_subtasks=[subtask.id] + subtask.dependencies,
                        description=(
                            f"Subtask {subtask.id} depends on "
                            f"{len(subtask.dependencies)} other subtask(s) "
                            f"but shows no integration"
                        ),
                        severity="medium",
                        suggested_resolution=(
                            "Add explicit imports or references to dependency outputs"
                        ),
                    )
                )

        return missing


# =============================================================================
# Singleton and Convenience Functions
# =============================================================================

_engine_instance: OutputIntegrationEngine | None = None


def get_integration_engine() -> OutputIntegrationEngine:
    """Get the singleton integration engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = OutputIntegrationEngine()
    return _engine_instance


def integrate_task_outputs(task: Task, subtasks: list[Subtask]) -> IntegrationResult:
    """Convenience function to integrate task outputs."""
    return get_integration_engine().integrate_outputs(task, subtasks)

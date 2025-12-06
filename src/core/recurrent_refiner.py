"""
Recurrent Refiner for multi-pass task understanding.

This module implements recurrent refinement (RPT-1/2) - processing tasks
through multiple passes to achieve deeper understanding before acting.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.task_parser import ParsedTask


class PassType(Enum):
    """Type of refinement pass."""

    INITIAL = "initial"  # Rough understanding, identify key elements
    CONTEXTUAL = "contextual"  # Integrate with context, refine interpretation
    COHERENCE = "coherence"  # Check coherence, resolve contradictions


@dataclass
class RefinementPass:
    """
    Data from a single refinement pass.

    Tracks what was learned and the confidence level after this pass.
    """

    pass_type: PassType
    confidence: float  # 0.0 to 1.0
    key_insights: list[str] = field(default_factory=list)
    ambiguities_noted: list[str] = field(default_factory=list)
    findings: dict[str, Any] = field(default_factory=dict)


@dataclass
class RefinedTask:
    """
    Result of multi-pass refinement.

    Contains the original task, all passes performed, and final confidence.
    """

    original_task: ParsedTask
    passes: list[RefinementPass]
    final_confidence: float

    def get_summary(self) -> str:
        """
        Get a summary of the refinement process.

        Returns:
            Human-readable summary string
        """
        num_passes = len(self.passes)
        insights = sum(len(p.key_insights) for p in self.passes)
        ambiguities = sum(len(p.ambiguities_noted) for p in self.passes)

        return (
            f"Refined task through {num_passes} passes. "
            f"Final confidence: {self.final_confidence:.2f}. "
            f"Insights: {insights}, Ambiguities: {ambiguities}"
        )


class RecurrentRefiner:
    """
    Multi-pass task understanding and refinement.

    Implements recurrent processing to achieve deeper understanding:
    1. Initial scan: Extract key entities and relationships
    2. Contextual integration: Integrate with broader context
    3. Coherence check: Verify understanding is self-consistent

    Stops early if confidence threshold reached or diminishing returns detected.
    """

    def __init__(self, max_passes: int = 3, confidence_threshold: float = 0.85):
        """
        Initialize the recurrent refiner.

        Args:
            max_passes: Maximum number of refinement passes
            confidence_threshold: Stop if confidence reaches this level
        """
        self.max_passes = max_passes
        self.confidence_threshold = confidence_threshold

    def refine(self, task: ParsedTask) -> RefinedTask:
        """
        Refine a parsed task through multiple passes.

        Args:
            task: ParsedTask to refine

        Returns:
            RefinedTask with all passes and final confidence
        """
        passes: list[RefinementPass] = []

        # Handle empty task
        if not task.goal or not task.goal.strip():
            return RefinedTask(
                original_task=task,
                passes=[],
                final_confidence=0.0,
            )

        # Pass 1: Initial scan
        initial_pass = self._initial_scan(task)
        passes.append(initial_pass)

        # Check if we should continue
        if self._should_stop(passes):
            return RefinedTask(
                original_task=task,
                passes=passes,
                final_confidence=initial_pass.confidence,
            )

        # Pass 2: Contextual integration
        contextual_pass = self._contextual_integration(task, passes)
        passes.append(contextual_pass)

        # Check if we should continue
        if self._should_stop(passes):
            return RefinedTask(
                original_task=task,
                passes=passes,
                final_confidence=contextual_pass.confidence,
            )

        # Pass 3: Coherence check
        if len(passes) < self.max_passes:
            coherence_pass = self._coherence_check(task, passes)
            passes.append(coherence_pass)

        # Additional passes if needed (up to max_passes)
        while len(passes) < self.max_passes and not self._should_stop(passes):
            # Re-run coherence check with accumulated insights
            additional_pass = self._coherence_check(task, passes)
            passes.append(additional_pass)

        final_confidence = passes[-1].confidence if passes else 0.0

        return RefinedTask(
            original_task=task,
            passes=passes,
            final_confidence=final_confidence,
        )

    def _initial_scan(self, task: ParsedTask) -> RefinementPass:
        """
        Pass 1: Initial scan for rough understanding.

        Extract key entities, relationships, and task type.

        Args:
            task: ParsedTask to scan

        Returns:
            RefinementPass with initial findings
        """
        insights: list[str] = []
        ambiguities: list[str] = []
        findings: dict[str, Any] = {}

        # Extract key elements from goal
        goal_lower = task.goal.lower()
        raw_lower = task.raw_description.lower()

        # Identify key entities (simplified heuristic)
        key_entities = []
        entity_keywords = ["api", "database", "user", "authentication", "oauth", "jwt", "token"]
        for keyword in entity_keywords:
            if keyword in goal_lower or keyword in raw_lower:
                key_entities.append(keyword)

        findings["entities"] = key_entities
        if key_entities:
            insights.append(f"Identified key entities: {', '.join(key_entities)}")

        # Note task type
        insights.append(f"Task type: {task.task_type.value}")

        # Note existing ambiguities from parser
        if task.ambiguities:
            ambiguities.extend(task.ambiguities)
            insights.append(f"Parser identified {len(task.ambiguities)} ambiguities")

        # Note constraints
        if task.constraints:
            findings["constraints"] = task.constraints
            insights.append(f"Found {len(task.constraints)} constraints")

        # Calculate initial confidence
        # Base confidence on clarity of goal and presence of ambiguities
        confidence = self._calculate_initial_confidence(task, key_entities, ambiguities)

        return RefinementPass(
            pass_type=PassType.INITIAL,
            confidence=confidence,
            key_insights=insights,
            ambiguities_noted=ambiguities,
            findings=findings,
        )

    def _contextual_integration(
        self, task: ParsedTask, previous_passes: list[RefinementPass]
    ) -> RefinementPass:
        """
        Pass 2: Contextual integration.

        Integrate task understanding with broader context and refine interpretation.

        Args:
            task: ParsedTask being refined
            previous_passes: Previous refinement passes

        Returns:
            RefinementPass with contextual insights
        """
        insights: list[str] = []
        ambiguities: list[str] = []
        findings: dict[str, Any] = {}

        # Get entities from initial pass
        initial_findings = previous_passes[0].findings
        entities = initial_findings.get("entities", [])

        # Identify relationships and dependencies
        goal_lower = task.goal.lower()
        raw_lower = task.raw_description.lower()
        full_text = f"{goal_lower} {raw_lower}"

        dependencies = []
        dependency_markers = ["after", "before", "once", "when", "requires", "needs"]
        for marker in dependency_markers:
            if marker in full_text:
                dependencies.append(marker)

        if dependencies:
            findings["dependencies"] = dependencies
            insights.append(f"Detected dependency markers: {', '.join(dependencies)}")

        # Check for implicit requirements based on entities
        implicit_requirements = []
        if "authentication" in entities or "auth" in entities:
            implicit_requirements.append("security considerations")
            implicit_requirements.append("user management")

        if "api" in entities:
            implicit_requirements.append("endpoint design")
            implicit_requirements.append("error handling")

        if "database" in entities:
            implicit_requirements.append("data modeling")
            implicit_requirements.append("migrations")

        if implicit_requirements:
            findings["implicit_requirements"] = implicit_requirements
            insights.append(f"Inferred requirements: {', '.join(implicit_requirements)}")

        # Check for scope clarity
        if len(task.goal.split()) < 5:
            ambiguities.append("Task description is very brief, may lack detail")

        # Integrate with success criteria
        if task.success_criteria:
            findings["success_criteria"] = task.success_criteria
            insights.append(f"Success criteria specified: {len(task.success_criteria)}")
        else:
            ambiguities.append("No explicit success criteria defined")

        # Calculate confidence improvement
        prev_confidence = previous_passes[-1].confidence
        confidence = self._calculate_contextual_confidence(
            task, prev_confidence, ambiguities, implicit_requirements
        )

        return RefinementPass(
            pass_type=PassType.CONTEXTUAL,
            confidence=confidence,
            key_insights=insights,
            ambiguities_noted=ambiguities,
            findings=findings,
        )

    def _coherence_check(
        self, task: ParsedTask, previous_passes: list[RefinementPass]
    ) -> RefinementPass:
        """
        Pass 3: Coherence check.

        Verify understanding is self-consistent and resolve contradictions.

        Args:
            task: ParsedTask being refined
            previous_passes: Previous refinement passes

        Returns:
            RefinementPass with coherence analysis
        """
        insights: list[str] = []
        ambiguities: list[str] = []
        findings: dict[str, Any] = {}

        # Check for contradictions in requirements
        goal_lower = task.goal.lower()
        raw_lower = task.raw_description.lower()
        full_text = f"{goal_lower} {raw_lower}"

        # Common contradictions
        contradictions = []

        # Stateless vs stateful
        if "stateless" in full_text and any(
            word in full_text for word in ["session", "cookie", "state"]
        ):
            contradictions.append("Stateless requirement conflicts with session/state usage")

        # Simple vs complex
        if "simple" in full_text and any(
            word in full_text for word in ["oauth2", "microservice", "distributed"]
        ):
            contradictions.append("Simple requirement conflicts with complex technologies")

        # Fast vs thorough
        if "quick" in full_text or "fast" in full_text:
            if any(word in full_text for word in ["comprehensive", "thorough", "extensive"]):
                contradictions.append("Speed requirement may conflict with thoroughness")

        if contradictions:
            findings["contradictions"] = contradictions
            for contradiction in contradictions:
                ambiguities.append(contradiction)
                insights.append(f"Detected contradiction: {contradiction}")

        # Verify all entities have coverage
        all_entities = []
        for prev_pass in previous_passes:
            all_entities.extend(prev_pass.findings.get("entities", []))

        unique_entities = list(set(all_entities))
        findings["all_entities"] = unique_entities

        if unique_entities:
            insights.append(f"Tracking {len(unique_entities)} unique entities")

        # Check if implicit requirements are addressed
        all_implicit = []
        for prev_pass in previous_passes:
            all_implicit.extend(prev_pass.findings.get("implicit_requirements", []))

        if all_implicit:
            findings["all_implicit_requirements"] = list(set(all_implicit))
            insights.append(f"Verified {len(set(all_implicit))} implicit requirements")

        # Calculate final confidence
        prev_confidence = previous_passes[-1].confidence
        confidence = self._calculate_coherence_confidence(
            task, prev_confidence, contradictions, ambiguities
        )

        return RefinementPass(
            pass_type=PassType.COHERENCE,
            confidence=confidence,
            key_insights=insights,
            ambiguities_noted=ambiguities,
            findings=findings,
        )

    def _calculate_initial_confidence(
        self, task: ParsedTask, entities: list[str], ambiguities: list[str]
    ) -> float:
        """Calculate confidence for initial pass."""
        # Start with base confidence
        confidence = 0.5

        # Increase confidence for clear, specific goals
        if len(task.goal.split()) >= 5:
            confidence += 0.1

        # Increase confidence for identified entities
        confidence += min(0.2, len(entities) * 0.05)

        # Decrease confidence for ambiguities
        confidence -= min(0.3, len(ambiguities) * 0.1)

        # Increase confidence if success criteria specified
        if task.success_criteria:
            confidence += 0.1

        # Increase confidence if constraints specified
        if task.constraints:
            confidence += 0.05

        return max(0.0, min(1.0, confidence))

    def _calculate_contextual_confidence(
        self,
        task: ParsedTask,
        prev_confidence: float,
        ambiguities: list[str],
        implicit_requirements: list[str],
    ) -> float:
        """Calculate confidence for contextual pass."""
        confidence = prev_confidence

        # Increase confidence for identified implicit requirements
        confidence += min(0.15, len(implicit_requirements) * 0.03)

        # Decrease confidence for new ambiguities
        confidence -= min(0.2, len(ambiguities) * 0.08)

        # Increase slightly for deeper understanding
        confidence += 0.05

        return max(0.0, min(1.0, confidence))

    def _calculate_coherence_confidence(
        self,
        task: ParsedTask,
        prev_confidence: float,
        contradictions: list[str],
        ambiguities: list[str],
    ) -> float:
        """Calculate confidence for coherence pass."""
        confidence = prev_confidence

        # Decrease confidence for contradictions
        confidence -= min(0.25, len(contradictions) * 0.15)

        # If no contradictions found, increase confidence slightly
        if not contradictions and not ambiguities:
            confidence += 0.05

        # Small increase for completing coherence check
        confidence += 0.02

        return max(0.0, min(1.0, confidence))

    def _should_stop(self, passes: list[RefinementPass]) -> bool:
        """
        Determine if refinement should stop.

        Stops if:
        - Confidence threshold reached
        - Diminishing returns detected
        - Max passes reached

        Args:
            passes: List of completed passes

        Returns:
            True if should stop, False otherwise
        """
        if not passes:
            return False

        # Check confidence threshold
        if passes[-1].confidence >= self.confidence_threshold:
            return True

        # Check max passes
        if len(passes) >= self.max_passes:
            return True

        # Check diminishing returns (confidence not improving much)
        if len(passes) >= 2:
            confidence_delta = passes[-1].confidence - passes[-2].confidence
            # If improvement is very small, stop
            if confidence_delta < 0.02:
                return True

        return False

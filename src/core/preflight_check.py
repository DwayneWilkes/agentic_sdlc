"""Pre-flight check framework for the orchestrator system.

This module provides comprehensive pre-flight checks for agents before they
start tasks. Agents perform honest self-assessment, identify risks, document
assumptions, and determine if they should proceed.

The pre-flight check answers:
- Do I understand this task?
- Can I do this successfully?
- What could go wrong?
- What am I assuming?
- When should I stop and ask for help?
"""

from dataclasses import asdict, dataclass
from enum import Enum


class Recommendation(str, Enum):
    """Recommendations for whether to proceed with a task."""

    PROCEED = "proceed"
    PROCEED_WITH_CAUTION = "proceed_with_caution"
    ASK_FOR_CLARIFICATION = "ask_for_clarification"
    DECLINE = "decline"


@dataclass
class Assumption:
    """
    An assumption being made about the task or environment.

    Assumptions should be explicitly stated upfront for human review.
    Critical assumptions need verification before proceeding.
    """

    description: str
    needs_verification: bool = False
    confidence: float = 1.0  # 0.0 to 1.0
    impact_if_false: str = ""


@dataclass
class RiskAssessment:
    """
    Assessment of a specific risk.

    Identifies what could go wrong, how likely it is, how severe,
    and what mitigation strategies are available.
    """

    risk: str
    likelihood: float  # 0.0 to 1.0
    severity: str = "medium"  # low, medium, high, critical
    mitigation: str = ""
    blast_radius: str = ""  # What's affected if this risk materializes


@dataclass
class AbortCondition:
    """
    A condition that should cause the agent to stop and ask for help.

    These are defined upfront to prevent agents from continuing when
    they encounter situations they cannot handle.
    """

    condition: str
    reasoning: str = ""
    alternative_action: str = ""


@dataclass
class UnderstandingCheck:
    """
    Assessment of the agent's understanding of the task.

    Includes restating the goal, identifying ambiguities, and
    assessing whether sufficient context is available.
    """

    goal_in_own_words: str
    has_ambiguities: bool
    ambiguities: list[str]
    has_sufficient_context: bool
    missing_context: list[str]
    understanding_confidence: float  # 0.0 to 1.0


@dataclass
class CapabilityAssessment:
    """
    Assessment of the agent's capability to complete the task.

    Compares task requirements against agent's track record,
    available tools, and complexity estimate.
    """

    has_done_similar: bool
    similar_tasks: list[str]
    has_required_tools: bool
    required_tools: list[str]
    missing_tools: list[str]
    complexity_estimate: int  # 1-10 scale
    capability_match: float  # 0.0 to 1.0


@dataclass
class PreFlightCheck:
    """
    Complete pre-flight check result.

    Contains all assessments, risks, assumptions, and a final
    recommendation on whether to proceed.
    """

    task_description: str
    understanding: UnderstandingCheck
    capability: CapabilityAssessment
    assumptions: list[Assumption]
    risks: list[RiskAssessment]
    abort_conditions: list[AbortCondition]
    estimated_success: float  # 0.0 to 1.0
    recommendation: Recommendation
    reasoning: str

    def to_dict(self) -> dict:
        """Convert pre-flight check to dictionary for serialization."""
        return asdict(self)


class PreFlightChecker:
    """
    Performs pre-flight checks for agents before starting tasks.

    Implements honest self-assessment to determine if the agent
    understands the task, has the capability to complete it, and
    should proceed.
    """

    def __init__(self, agent_id: str) -> None:
        """
        Initialize the pre-flight checker.

        Args:
            agent_id: ID of the agent performing checks
        """
        self._agent_id = agent_id
        self._check_history: list[PreFlightCheck] = []

    def perform_check(
        self,
        task_description: str,
        task_context: dict | None = None,
    ) -> PreFlightCheck:
        """
        Perform a complete pre-flight check on a task.

        Args:
            task_description: Description of the task to assess
            task_context: Optional context about the task

        Returns:
            Complete pre-flight check result
        """
        if task_context is None:
            task_context = {}

        # Step 1: Understanding check
        understanding = self._check_understanding(task_description, task_context)

        # Step 2: Capability assessment
        capability = self._assess_capability(task_description, task_context)

        # Step 3: Identify assumptions
        assumptions = self._identify_assumptions(task_description, task_context)

        # Step 4: Risk assessment
        risks = self._assess_risks(task_description, task_context)

        # Step 5: Define abort conditions
        abort_conditions = self._define_abort_conditions(task_description, task_context)

        # Step 6: Estimate success probability
        estimated_success = self._estimate_success(
            understanding, capability, risks, task_context
        )

        # Step 7: Make recommendation
        recommendation, reasoning = self._make_recommendation(
            understanding, capability, estimated_success, risks
        )

        # Create complete check
        check = PreFlightCheck(
            task_description=task_description,
            understanding=understanding,
            capability=capability,
            assumptions=assumptions,
            risks=risks,
            abort_conditions=abort_conditions,
            estimated_success=estimated_success,
            recommendation=recommendation,
            reasoning=reasoning,
        )

        # Track in history
        self._check_history.append(check)

        return check

    def get_check_history(self) -> list[PreFlightCheck]:
        """
        Get the history of all checks performed.

        Returns:
            List of all pre-flight checks performed
        """
        return self._check_history.copy()

    def _check_understanding(
        self,
        task_description: str,
        task_context: dict,
    ) -> UnderstandingCheck:
        """
        Check if the task is understood.

        Args:
            task_description: Task description
            task_context: Task context

        Returns:
            Understanding check result
        """
        # Detect ambiguities
        ambiguities = []
        has_ambiguities = False

        # Very vague tasks
        vague_terms = ["better", "improve", "make", "do", "thing"]
        words = task_description.lower().split()

        if len(words) < 4:
            has_ambiguities = True
            ambiguities.append("Task description is very brief - may lack detail")

        # Check for vague terms without specific details
        task_lower = task_description.lower()
        if any(vague in task_lower for vague in vague_terms):
            # Need sufficient detail to clarify vague terms
            # But if task is long (>15 words), it probably has detail
            if len(words) < 8 and len(words) > 3:
                has_ambiguities = True
                ambiguities.append("Task uses vague terms without specific details")

        # "Fix" is okay if it has specific target (like "Fix typo")
        if "fix" in task_lower and len(words) >= 4:
            # Specific fix is clear
            pass

        # Check for missing context
        missing_context = []
        has_sufficient_context = True

        # Tasks that mention unknowns
        if "unknown" in task_context.values() or not task_context:
            if "add" in task_description.lower() or "integrate" in task_description.lower():
                has_sufficient_context = False
                missing_context.append("Implementation details not specified")

        # Restate goal (simple extraction for now)
        goal_in_own_words = task_description

        # Calculate understanding confidence
        confidence = 1.0
        if has_ambiguities:
            confidence -= 0.3
        if not has_sufficient_context:
            confidence -= 0.2

        # Very complex tasks should have some uncertainty even if clear
        # because there are likely hidden complexities
        if len(words) >= 15:
            # Long descriptions suggest complex task
            confidence -= 0.15

        confidence = max(0.0, min(1.0, confidence))

        return UnderstandingCheck(
            goal_in_own_words=goal_in_own_words,
            has_ambiguities=has_ambiguities,
            ambiguities=ambiguities,
            has_sufficient_context=has_sufficient_context,
            missing_context=missing_context,
            understanding_confidence=confidence,
        )

    def _assess_capability(
        self,
        task_description: str,
        task_context: dict,
    ) -> CapabilityAssessment:
        """
        Assess capability to complete the task.

        Args:
            task_description: Task description
            task_context: Task context

        Returns:
            Capability assessment
        """
        # Determine if similar tasks have been done
        # (In a real implementation, would check agent's memory/history)
        has_done_similar = False
        similar_tasks = []

        # Check for required tools
        required_tools = []
        missing_tools = []
        has_required_tools = True

        if "test" in task_description.lower():
            required_tools.append("pytest")
            if task_context.get("has_pytest", True):
                pass
            else:
                missing_tools.append("pytest")
                has_required_tools = False

        # Estimate complexity (1-10)
        complexity = 5  # Default medium

        # Simple tasks
        if any(
            simple in task_description.lower()
            for simple in ["comment", "typo", "formatting", "rename"]
        ):
            complexity = 2
            has_done_similar = True
            similar_tasks.append("Similar simple edits")

        # Complex tasks
        if any(
            complex_term in task_description.lower()
            for complex_term in [
                "refactor entire",
                "rewrite",
                "architecture",
                "microservices",
                "distributed",
            ]
        ):
            complexity = 9

        # Very long descriptions suggest complexity
        if len(task_description.split()) > 30:
            complexity = min(10, complexity + 2)

        # Calculate capability match
        capability_match = 0.5  # Default neutral

        if has_done_similar:
            capability_match += 0.3
        if has_required_tools:
            capability_match += 0.2
        if complexity <= 5:
            capability_match += 0.1
        else:
            capability_match -= (complexity - 5) * 0.05

        capability_match = max(0.0, min(1.0, capability_match))

        return CapabilityAssessment(
            has_done_similar=has_done_similar,
            similar_tasks=similar_tasks,
            has_required_tools=has_required_tools,
            required_tools=required_tools,
            missing_tools=missing_tools,
            complexity_estimate=complexity,
            capability_match=capability_match,
        )

    def _identify_assumptions(
        self,
        task_description: str,
        task_context: dict,
    ) -> list[Assumption]:
        """
        Identify assumptions being made.

        Args:
            task_description: Task description
            task_context: Task context

        Returns:
            List of assumptions
        """
        assumptions = []

        # Integration/addition tasks assume existing infrastructure
        if any(
            keyword in task_description.lower()
            for keyword in ["integrate", "add", "connect"]
        ):
            assumptions.append(
                Assumption(
                    description="Required integration points/APIs exist",
                    needs_verification=True,
                    confidence=0.7,
                    impact_if_false="Will need to implement missing infrastructure first",
                )
            )

        # Caching assumes no existing cache conflict
        if "cach" in task_description.lower():
            assumptions.append(
                Assumption(
                    description="No conflicting cache implementation exists",
                    needs_verification=True,
                    confidence=0.6,
                    impact_if_false="May need to refactor existing cache first",
                )
            )

        # Testing assumes test infrastructure exists
        if "test" in task_description.lower():
            assumptions.append(
                Assumption(
                    description="Test infrastructure is set up",
                    needs_verification=False,
                    confidence=0.9,
                    impact_if_false="Will need to set up testing framework",
                )
            )

        return assumptions

    def _assess_risks(
        self,
        task_description: str,
        task_context: dict,
    ) -> list[RiskAssessment]:
        """
        Assess risks of the task.

        Args:
            task_description: Task description
            task_context: Task context

        Returns:
            List of risk assessments
        """
        risks = []

        # Deletion/removal is high risk
        if any(
            dangerous in task_description.lower()
            for dangerous in ["delete", "remove", "drop"]
        ):
            risks.append(
                RiskAssessment(
                    risk="Accidentally delete data or code still in use",
                    likelihood=0.4,
                    severity="high",
                    mitigation="Check for dependencies before deletion",
                    blast_radius="Dependent systems may break",
                )
            )

        # Refactoring is medium risk
        if "refactor" in task_description.lower():
            risks.append(
                RiskAssessment(
                    risk="Break existing functionality",
                    likelihood=0.3,
                    severity="medium",
                    mitigation="Comprehensive test coverage before refactoring",
                    blast_radius="Affected module and its callers",
                )
            )

        # Authentication/security is high risk
        if any(
            security in task_description.lower()
            for security in ["auth", "security", "permission", "credential"]
        ):
            risks.append(
                RiskAssessment(
                    risk="Introduce security vulnerability",
                    likelihood=0.3,
                    severity="critical",
                    mitigation="Security review required",
                    blast_radius="All users and data",
                )
            )

        # Large-scale tasks have resource risks
        if any(
            large in task_description.lower()
            for large in ["million", "all", "entire", "rewrite"]
        ):
            risks.append(
                RiskAssessment(
                    risk="Exceed resource limits (time, tokens, memory)",
                    likelihood=0.5,
                    severity="medium",
                    mitigation="Break into smaller chunks",
                    blast_radius="Task may not complete",
                )
            )

        return risks

    def _define_abort_conditions(
        self,
        task_description: str,
        task_context: dict,
    ) -> list[AbortCondition]:
        """
        Define conditions that should trigger stopping and asking for help.

        Args:
            task_description: Task description
            task_context: Task context

        Returns:
            List of abort conditions
        """
        abort_conditions = []

        # Integration tasks
        if "integrat" in task_description.lower():
            abort_conditions.append(
                AbortCondition(
                    condition="Required API/service is not available or documented",
                    reasoning="Cannot integrate without knowing the interface",
                    alternative_action="Ask user for API documentation or service details",
                )
            )

        # Complex tasks
        if any(
            complex_term in task_description.lower()
            for complex_term in ["architecture", "microservices", "distributed"]
        ):
            abort_conditions.append(
                AbortCondition(
                    condition="Requirements are unclear after clarification attempt",
                    reasoning="Architecture decisions need clear requirements",
                    alternative_action="Request detailed requirements document",
                )
            )

        # Security-sensitive tasks
        if any(
            security in task_description.lower()
            for security in ["auth", "security", "credential"]
        ):
            abort_conditions.append(
                AbortCondition(
                    condition="No security review process is defined",
                    reasoning="Security changes need expert review",
                    alternative_action="Request security review before implementation",
                )
            )

        # If no specific abort conditions, add a general one
        if not abort_conditions:
            abort_conditions.append(
                AbortCondition(
                    condition="Stuck for more than 30 minutes without progress",
                    reasoning="Prolonged stuck state indicates need for help",
                    alternative_action="Escalate to human with context summary",
                )
            )

        return abort_conditions

    def _estimate_success(
        self,
        understanding: UnderstandingCheck,
        capability: CapabilityAssessment,
        risks: list[RiskAssessment],
        task_context: dict,
    ) -> float:
        """
        Estimate probability of successful task completion.

        Args:
            understanding: Understanding check result
            capability: Capability assessment
            risks: List of identified risks
            task_context: Task context

        Returns:
            Success probability (0.0 to 1.0)
        """
        # Start with understanding and capability
        success = (understanding.understanding_confidence + capability.capability_match) / 2

        # Reduce for high-severity risks
        high_risk_count = sum(
            1 for r in risks if r.severity in ["high", "critical"]
        )
        success -= high_risk_count * 0.1

        # Reduce for resource constraints
        if "token_budget" in task_context or "time_limit_minutes" in task_context:
            success -= 0.1

        # Ensure in valid range
        return max(0.0, min(1.0, success))

    def _make_recommendation(
        self,
        understanding: UnderstandingCheck,
        capability: CapabilityAssessment,
        estimated_success: float,
        risks: list[RiskAssessment],
    ) -> tuple[Recommendation, str]:
        """
        Make a recommendation on whether to proceed.

        Args:
            understanding: Understanding check result
            capability: Capability assessment
            estimated_success: Estimated success probability
            risks: List of identified risks

        Returns:
            Tuple of (recommendation, reasoning)
        """
        # Decline if understanding is too low
        if understanding.understanding_confidence < 0.4:
            return (
                Recommendation.DECLINE,
                "Understanding confidence too low - task is unclear",
            )

        # Ask for clarification if there are ambiguities
        if understanding.has_ambiguities and understanding.understanding_confidence < 0.8:
            return (
                Recommendation.ASK_FOR_CLARIFICATION,
                "Task has ambiguities that need clarification",
            )

        # Decline if capability is very low
        if capability.capability_match < 0.3:
            return (
                Recommendation.DECLINE,
                "Capability match too low - task is beyond current abilities",
            )

        # Proceed with caution if there are high risks
        if any(r.severity in ["high", "critical"] for r in risks):
            return (
                Recommendation.PROCEED_WITH_CAUTION,
                "High-risk task requires careful handling",
            )

        # Proceed with caution if success is moderate
        if 0.5 <= estimated_success < 0.75:
            return (
                Recommendation.PROCEED_WITH_CAUTION,
                "Moderate success probability - proceed carefully",
            )

        # Decline if success is very low
        if estimated_success < 0.5:
            return (
                Recommendation.DECLINE,
                "Success probability too low",
            )

        # Otherwise proceed
        return (
            Recommendation.PROCEED,
            "Good understanding and capability match, proceed with task",
        )

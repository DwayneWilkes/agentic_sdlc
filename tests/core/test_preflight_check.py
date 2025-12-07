"""Tests for pre-flight check framework."""

from src.core.preflight_check import (
    AbortCondition,
    Assumption,
    CapabilityAssessment,
    PreFlightCheck,
    PreFlightChecker,
    Recommendation,
    RiskAssessment,
    UnderstandingCheck,
)


class TestAssumption:
    """Test the Assumption dataclass."""

    def test_create_assumption(self) -> None:
        """Test creating an assumption."""
        assumption = Assumption(
            description="Backend supports OAuth2 endpoints",
            needs_verification=True,
            confidence=0.8,
            impact_if_false="Will need to implement OAuth2 on backend first",
        )
        assert assumption.description == "Backend supports OAuth2 endpoints"
        assert assumption.needs_verification is True
        assert assumption.confidence == 0.8
        assert assumption.impact_if_false == "Will need to implement OAuth2 on backend first"

    def test_assumption_defaults(self) -> None:
        """Test assumption with defaults."""
        assumption = Assumption(description="Simple assumption")
        assert assumption.needs_verification is False
        assert assumption.confidence == 1.0
        assert assumption.impact_if_false == ""


class TestRiskAssessment:
    """Test the RiskAssessment dataclass."""

    def test_create_risk_assessment(self) -> None:
        """Test creating a risk assessment."""
        risk = RiskAssessment(
            risk="Break existing logins",
            likelihood=0.3,
            severity="high",
            mitigation="Feature flag for gradual rollout",
            blast_radius="All authentication flows",
        )
        assert risk.risk == "Break existing logins"
        assert risk.likelihood == 0.3
        assert risk.severity == "high"
        assert risk.mitigation == "Feature flag for gradual rollout"
        assert risk.blast_radius == "All authentication flows"

    def test_risk_defaults(self) -> None:
        """Test risk assessment with defaults."""
        risk = RiskAssessment(risk="Something might fail", likelihood=0.2)
        assert risk.severity == "medium"
        assert risk.mitigation == ""
        assert risk.blast_radius == ""


class TestAbortCondition:
    """Test the AbortCondition dataclass."""

    def test_create_abort_condition(self) -> None:
        """Test creating an abort condition."""
        condition = AbortCondition(
            condition="Cannot find OAuth2 library compatible with current stack",
            reasoning="Without OAuth2 library, cannot implement the feature",
            alternative_action="Ask user for library recommendations",
        )
        assert condition.condition == "Cannot find OAuth2 library compatible with current stack"
        assert condition.reasoning == "Without OAuth2 library, cannot implement the feature"
        assert condition.alternative_action == "Ask user for library recommendations"

    def test_abort_condition_defaults(self) -> None:
        """Test abort condition with defaults."""
        condition = AbortCondition(condition="Something is blocking")
        assert condition.reasoning == ""
        assert condition.alternative_action == ""


class TestUnderstandingCheck:
    """Test the UnderstandingCheck dataclass."""

    def test_create_understanding_check(self) -> None:
        """Test creating an understanding check."""
        check = UnderstandingCheck(
            goal_in_own_words="Implement user authentication using OAuth2",
            has_ambiguities=True,
            ambiguities=["Which OAuth2 provider?", "Session storage location?"],
            has_sufficient_context=False,
            missing_context=["OAuth2 client credentials", "Redirect URLs"],
            understanding_confidence=0.6,
        )
        assert check.goal_in_own_words == "Implement user authentication using OAuth2"
        assert check.has_ambiguities is True
        assert len(check.ambiguities) == 2
        assert check.has_sufficient_context is False
        assert len(check.missing_context) == 2
        assert check.understanding_confidence == 0.6

    def test_understanding_check_clear_task(self) -> None:
        """Test understanding check for a clear task."""
        check = UnderstandingCheck(
            goal_in_own_words="Fix the null pointer exception in user.py line 42",
            has_ambiguities=False,
            ambiguities=[],
            has_sufficient_context=True,
            missing_context=[],
            understanding_confidence=0.95,
        )
        assert check.understanding_confidence == 0.95
        assert check.has_ambiguities is False
        assert check.has_sufficient_context is True


class TestCapabilityAssessment:
    """Test the CapabilityAssessment dataclass."""

    def test_create_capability_assessment(self) -> None:
        """Test creating a capability assessment."""
        assessment = CapabilityAssessment(
            has_done_similar=True,
            similar_tasks=["Implemented JWT authentication", "Added API security"],
            has_required_tools=True,
            required_tools=["pytest", "OAuth2 library"],
            missing_tools=[],
            complexity_estimate=7,
            capability_match=0.75,
        )
        assert assessment.has_done_similar is True
        assert len(assessment.similar_tasks) == 2
        assert assessment.has_required_tools is True
        assert assessment.complexity_estimate == 7
        assert assessment.capability_match == 0.75

    def test_capability_assessment_unfamiliar(self) -> None:
        """Test capability assessment for unfamiliar task."""
        assessment = CapabilityAssessment(
            has_done_similar=False,
            similar_tasks=[],
            has_required_tools=False,
            required_tools=["blockchain-sdk"],
            missing_tools=["blockchain-sdk"],
            complexity_estimate=9,
            capability_match=0.3,
        )
        assert assessment.capability_match == 0.3
        assert assessment.has_done_similar is False
        assert len(assessment.missing_tools) == 1


class TestRecommendation:
    """Test the Recommendation enum."""

    def test_recommendation_values(self) -> None:
        """Test that all recommendations are defined."""
        assert Recommendation.PROCEED == "proceed"
        assert Recommendation.PROCEED_WITH_CAUTION == "proceed_with_caution"
        assert Recommendation.ASK_FOR_CLARIFICATION == "ask_for_clarification"
        assert Recommendation.DECLINE == "decline"


class TestPreFlightCheck:
    """Test the PreFlightCheck dataclass."""

    def test_create_complete_preflight_check(self) -> None:
        """Test creating a complete pre-flight check."""
        understanding = UnderstandingCheck(
            goal_in_own_words="Add OAuth2 authentication",
            has_ambiguities=False,
            ambiguities=[],
            has_sufficient_context=True,
            missing_context=[],
            understanding_confidence=0.85,
        )

        capability = CapabilityAssessment(
            has_done_similar=True,
            similar_tasks=["JWT auth"],
            has_required_tools=True,
            required_tools=["pytest"],
            missing_tools=[],
            complexity_estimate=5,
            capability_match=0.8,
        )

        assumptions = [
            Assumption(description="Backend has OAuth2 endpoints", confidence=0.9)
        ]

        risks = [
            RiskAssessment(
                risk="Break existing logins",
                likelihood=0.2,
                severity="high",
                mitigation="Feature flag",
            )
        ]

        abort_conditions = [
            AbortCondition(
                condition="OAuth2 library not compatible",
                reasoning="Cannot implement without library",
            )
        ]

        check = PreFlightCheck(
            task_description="Implement OAuth2 authentication",
            understanding=understanding,
            capability=capability,
            assumptions=assumptions,
            risks=risks,
            abort_conditions=abort_conditions,
            estimated_success=0.7,
            recommendation=Recommendation.PROCEED_WITH_CAUTION,
            reasoning="Good understanding but high-risk change needs careful handling",
        )

        assert check.task_description == "Implement OAuth2 authentication"
        assert check.estimated_success == 0.7
        assert check.recommendation == Recommendation.PROCEED_WITH_CAUTION
        assert len(check.assumptions) == 1
        assert len(check.risks) == 1
        assert len(check.abort_conditions) == 1

    def test_preflight_check_to_dict(self) -> None:
        """Test serializing pre-flight check to dictionary."""
        understanding = UnderstandingCheck(
            goal_in_own_words="Fix bug",
            has_ambiguities=False,
            ambiguities=[],
            has_sufficient_context=True,
            missing_context=[],
            understanding_confidence=0.9,
        )

        capability = CapabilityAssessment(
            has_done_similar=True,
            similar_tasks=["Similar bug fix"],
            has_required_tools=True,
            required_tools=["pytest"],
            missing_tools=[],
            complexity_estimate=3,
            capability_match=0.85,
        )

        check = PreFlightCheck(
            task_description="Fix null pointer bug",
            understanding=understanding,
            capability=capability,
            assumptions=[],
            risks=[],
            abort_conditions=[],
            estimated_success=0.85,
            recommendation=Recommendation.PROCEED,
            reasoning="Clear task, good capability match",
        )

        check_dict = check.to_dict()
        assert isinstance(check_dict, dict)
        assert check_dict["task_description"] == "Fix null pointer bug"
        assert check_dict["estimated_success"] == 0.85
        assert check_dict["recommendation"] == "proceed"


class TestPreFlightChecker:
    """Test the PreFlightChecker class."""

    def test_create_preflight_checker(self) -> None:
        """Test creating a pre-flight checker."""
        checker = PreFlightChecker(agent_id="test-agent-1")
        assert checker._agent_id == "test-agent-1"

    def test_perform_check_simple_task(self) -> None:
        """Test performing a check on a simple, clear task."""
        checker = PreFlightChecker(agent_id="test-agent-1")

        check = checker.perform_check(
            task_description="Fix typo in README.md",
            task_context={"file": "README.md", "line": 42},
        )

        assert isinstance(check, PreFlightCheck)
        assert check.task_description == "Fix typo in README.md"
        assert check.understanding.understanding_confidence > 0.7
        assert check.estimated_success > 0.5
        assert check.recommendation in [
            Recommendation.PROCEED,
            Recommendation.PROCEED_WITH_CAUTION,
        ]

    def test_perform_check_complex_task(self) -> None:
        """Test performing a check on a complex task."""
        checker = PreFlightChecker(agent_id="test-agent-1")

        task_desc = (
            "Refactor the entire authentication system to use microservices "
            "architecture with OAuth2, RBAC, and distributed session management"
        )
        check = checker.perform_check(
            task_description=task_desc,
            task_context={},
        )

        assert isinstance(check, PreFlightCheck)
        # Complex tasks should have lower confidence
        assert check.understanding.understanding_confidence < 0.9
        # Should have some risks identified
        assert len(check.risks) > 0
        # Should have abort conditions
        assert len(check.abort_conditions) > 0

    def test_perform_check_with_ambiguities(self) -> None:
        """Test check when task has ambiguities."""
        checker = PreFlightChecker(agent_id="test-agent-1")

        check = checker.perform_check(
            task_description="Make it better",
            task_context={},
        )

        assert check.understanding.has_ambiguities is True
        assert len(check.understanding.ambiguities) > 0
        assert check.recommendation in [
            Recommendation.ASK_FOR_CLARIFICATION,
            Recommendation.DECLINE,
        ]

    def test_perform_check_identifies_assumptions(self) -> None:
        """Test that pre-flight check identifies assumptions."""
        checker = PreFlightChecker(agent_id="test-agent-1")

        check = checker.perform_check(
            task_description="Add caching to the API endpoints",
            task_context={"existing_cache": "unknown"},
        )

        # Should make assumptions about cache implementation
        assert len(check.assumptions) > 0
        # At least one assumption should need verification
        assert any(a.needs_verification for a in check.assumptions)

    def test_perform_check_identifies_risks(self) -> None:
        """Test that pre-flight check identifies risks."""
        checker = PreFlightChecker(agent_id="test-agent-1")

        check = checker.perform_check(
            task_description="Delete all deprecated API endpoints",
            task_context={},
        )

        # Deletion should identify risks
        assert len(check.risks) > 0
        # Should have high severity risks
        assert any(r.severity in ["high", "critical"] for r in check.risks)

    def test_perform_check_sets_abort_conditions(self) -> None:
        """Test that pre-flight check sets abort conditions."""
        checker = PreFlightChecker(agent_id="test-agent-1")

        check = checker.perform_check(
            task_description="Integrate with third-party payment API",
            task_context={},
        )

        # Integration tasks should have abort conditions
        assert len(check.abort_conditions) > 0

    def test_perform_check_capability_assessment(self) -> None:
        """Test capability assessment in pre-flight check."""
        checker = PreFlightChecker(agent_id="test-agent-1")

        # Provide some past experience
        check = checker.perform_check(
            task_description="Write unit tests for the user module",
            task_context={"has_pytest": True},
        )

        assert check.capability.complexity_estimate > 0
        assert 0.0 <= check.capability.capability_match <= 1.0

    def test_estimated_success_calculation(self) -> None:
        """Test that estimated success is calculated reasonably."""
        checker = PreFlightChecker(agent_id="test-agent-1")

        # Simple, clear task should have high success estimate
        simple_check = checker.perform_check(
            task_description="Add a comment to explain function X",
            task_context={},
        )
        assert simple_check.estimated_success > 0.7

        # Complex, ambiguous task should have lower success estimate
        complex_check = checker.perform_check(
            task_description="Rewrite everything to be better",
            task_context={},
        )
        assert complex_check.estimated_success < simple_check.estimated_success

    def test_recommendation_logic(self) -> None:
        """Test that recommendations are logical."""
        checker = PreFlightChecker(agent_id="test-agent-1")

        # High success estimate → PROCEED or PROCEED_WITH_CAUTION
        check1 = checker.perform_check(
            task_description="Fix formatting in config.py",
            task_context={},
        )
        assert check1.recommendation in [
            Recommendation.PROCEED,
            Recommendation.PROCEED_WITH_CAUTION,
        ]

        # Very vague → ASK_FOR_CLARIFICATION or DECLINE
        check2 = checker.perform_check(
            task_description="Do the thing",
            task_context={},
        )
        assert check2.recommendation in [
            Recommendation.ASK_FOR_CLARIFICATION,
            Recommendation.DECLINE,
        ]

    def test_multiple_checks_tracked(self) -> None:
        """Test that checker tracks multiple checks."""
        checker = PreFlightChecker(agent_id="test-agent-1")

        checker.perform_check(
            task_description="Task 1",
            task_context={},
        )
        checker.perform_check(
            task_description="Task 2",
            task_context={},
        )

        history = checker.get_check_history()
        assert len(history) == 2
        assert history[0].task_description == "Task 1"
        assert history[1].task_description == "Task 2"

    def test_check_with_resource_constraints(self) -> None:
        """Test pre-flight check considers resource constraints."""
        checker = PreFlightChecker(agent_id="test-agent-1")

        check = checker.perform_check(
            task_description="Process 1 million records and generate reports",
            task_context={"token_budget": 10000, "time_limit_minutes": 30},
        )

        # Should identify resource concerns
        assert len(check.risks) > 0 or len(check.abort_conditions) > 0
        # Success estimate should account for constraints
        assert check.estimated_success < 1.0

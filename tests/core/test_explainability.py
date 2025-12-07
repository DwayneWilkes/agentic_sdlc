"""Tests for explainability framework (Phase 7.3)."""


from src.core.explainability import (
    AgentSelectionExplanation,
    DecompositionExplanation,
    ExplainabilityTracker,
    FailureDiagnostics,
    InteractionLog,
    TeamDesignExplanation,
)


class TestDecompositionExplanation:
    """Test decomposition explanation tracking."""

    def test_create_explanation(self):
        """Test creating decomposition explanation."""
        exp = DecompositionExplanation(
            task_id="task-1",
            original_task="Build API",
            num_subtasks=3,
            strategy="component-based",
            reasons=["Complex task", "Parallel execution"],
        )
        assert exp.task_id == "task-1"
        assert exp.num_subtasks == 3
        assert len(exp.reasons) == 2

    def test_to_dict(self):
        """Test converting to dictionary."""
        exp = DecompositionExplanation(
            task_id="task-1", original_task="Test", num_subtasks=2
        )
        data = exp.to_dict()
        assert "task_id" in data
        assert "timestamp" in data


class TestTeamDesignExplanation:
    """Test team design explanation tracking."""

    def test_create_explanation(self):
        """Test creating team design explanation."""
        exp = TeamDesignExplanation(
            team_id="team-1",
            team_size=3,
            roles=["coder", "tester", "reviewer"],
            role_justifications={"coder": "Write code", "tester": "Test code"},
        )
        assert exp.team_id == "team-1"
        assert exp.team_size == 3
        assert len(exp.roles) == 3


class TestAgentSelectionExplanation:
    """Test agent selection explanation tracking."""

    def test_create_explanation(self):
        """Test creating agent selection explanation."""
        exp = AgentSelectionExplanation(
            agent_name="Alice",
            task_id="task-1",
            selection_reasons=["Expert", "Available"],
            affinity_score=0.9,
        )
        assert exp.agent_name == "Alice"
        assert exp.affinity_score == 0.9


class TestInteractionLog:
    """Test interaction logging."""

    def test_create_log(self):
        """Test creating interaction log."""
        log = InteractionLog(
            from_agent="Alice",
            to_agent="Bob",
            interaction_type="handoff",
            message="Task complete",
        )
        assert log.from_agent == "Alice"
        assert log.to_agent == "Bob"


class TestFailureDiagnostics:
    """Test failure diagnostics."""

    def test_create_diagnostics(self):
        """Test creating failure diagnostics."""
        diag = FailureDiagnostics(
            task_id="task-1",
            failure_type="timeout",
            error_message="Task timed out",
            agent_name="Alice",
            recovery_suggestions=["Retry", "Increase timeout"],
        )
        assert diag.task_id == "task-1"
        assert diag.failure_type == "timeout"
        assert len(diag.recovery_suggestions) == 2


class TestExplainabilityTracker:
    """Test the main explainability tracker."""

    def test_record_decomposition(self):
        """Test recording decomposition."""
        tracker = ExplainabilityTracker()
        tracker.record_decomposition(
            "task-1", "Build API", 3, ["Complex", "Parallel work possible"]
        )
        decompositions = tracker.get_decompositions()
        assert len(decompositions) == 1
        assert decompositions[0].task_id == "task-1"

    def test_record_team_design(self):
        """Test recording team design."""
        tracker = ExplainabilityTracker()
        tracker.record_team_design("team-1", 2, ["coder", "tester"])
        designs = tracker.get_team_designs()
        assert len(designs) == 1
        assert designs[0].team_size == 2

    def test_record_agent_selection(self):
        """Test recording agent selection."""
        tracker = ExplainabilityTracker()
        tracker.record_agent_selection("Alice", "task-1", ["Expert"], affinity_score=0.9)
        selections = tracker.get_agent_selections()
        assert len(selections) == 1
        assert selections[0].agent_name == "Alice"

    def test_record_interaction(self):
        """Test recording interaction."""
        tracker = ExplainabilityTracker()
        tracker.record_interaction("Alice", "Bob", "message", "Hello")
        interactions = tracker.get_interactions()
        assert len(interactions) == 1
        assert interactions[0].from_agent == "Alice"

    def test_record_failure(self):
        """Test recording failure."""
        tracker = ExplainabilityTracker()
        tracker.record_failure("task-1", "error", "Failed", "Alice")
        failures = tracker.get_failures()
        assert len(failures) == 1
        assert failures[0].task_id == "task-1"

    def test_get_interactions_by_agent(self):
        """Test filtering interactions by agent."""
        tracker = ExplainabilityTracker()
        tracker.record_interaction("Alice", "Bob", "msg", "Hi")
        tracker.record_interaction("Bob", "Carol", "msg", "Hello")
        tracker.record_interaction("Alice", "Carol", "msg", "Hey")

        alice_interactions = tracker.get_interactions_by_agent("Alice")
        assert len(alice_interactions) == 2

    def test_get_failures_by_task(self):
        """Test filtering failures by task."""
        tracker = ExplainabilityTracker()
        tracker.record_failure("task-1", "error", "E1", "Alice")
        tracker.record_failure("task-2", "error", "E2", "Bob")
        tracker.record_failure("task-1", "timeout", "E3", "Carol")

        task1_failures = tracker.get_failures_by_task("task-1")
        assert len(task1_failures) == 2

    def test_export_all(self):
        """Test exporting all data."""
        tracker = ExplainabilityTracker()
        tracker.record_decomposition("task-1", "Test", 2, ["Reason"])
        tracker.record_interaction("Alice", "Bob", "msg", "Hi")

        export = tracker.export_all()
        assert "decompositions" in export
        assert "interactions" in export
        assert len(export["decompositions"]) == 1

    def test_generate_report(self):
        """Test generating summary report."""
        tracker = ExplainabilityTracker()
        tracker.record_decomposition("task-1", "Test", 2, ["Reason"])
        tracker.record_team_design("team-1", 1, ["coder"])

        report = tracker.generate_report()
        assert "Decompositions: 1" in report
        assert "Team Designs: 1" in report

    def test_clear(self):
        """Test clearing all data."""
        tracker = ExplainabilityTracker()
        tracker.record_decomposition("task-1", "Test", 2, ["Reason"])
        tracker.record_interaction("Alice", "Bob", "msg", "Hi")

        tracker.clear()

        assert len(tracker.get_decompositions()) == 0
        assert len(tracker.get_interactions()) == 0

    def test_full_workflow(self):
        """Test complete workflow with all explanation types."""
        tracker = ExplainabilityTracker()

        # Record decomposition
        tracker.record_decomposition(
            "task-1",
            "Build authentication system",
            4,
            ["Complex task", "Multiple components"],
            strategy="component-based",
        )

        # Record team design
        tracker.record_team_design(
            "team-1",
            3,
            ["backend", "security", "tester"],
            role_justifications={
                "backend": "API implementation",
                "security": "Auth protocols",
            },
        )

        # Record agent selection
        tracker.record_agent_selection(
            "Alice", "subtask-1", ["Backend expert"], affinity_score=0.9
        )

        # Record interaction
        tracker.record_interaction("Alice", "Bob", "handoff", "Security review needed")

        # Verify all recorded
        assert len(tracker.get_decompositions()) == 1
        assert len(tracker.get_team_designs()) == 1
        assert len(tracker.get_agent_selections()) == 1
        assert len(tracker.get_interactions()) == 1

        # Generate report
        report = tracker.generate_report()
        assert "authentication system" not in report  # Summary doesn't include details
        assert "Decompositions: 1" in report

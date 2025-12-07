"""Tests for the undo awareness framework."""

import json

from src.core.error_detection import ErrorContext, ErrorSeverity, ErrorType
from src.core.undo_awareness import (
    ActionSnapshot,
    RiskLevel,
    UndoAction,
    UndoAwarenessEngine,
    UndoChain,
)


class TestUndoAction:
    """Tests for UndoAction dataclass."""

    def test_create_undo_action(self) -> None:
        """Test creating a basic undo action."""
        action = UndoAction(
            action="Edit file",
            undo_command="git checkout -- src/file.py",
            description="Refactor authentication module",
            risk_level=RiskLevel.MEDIUM,
        )

        assert action.action == "Edit file"
        assert action.undo_command == "git checkout -- src/file.py"
        assert action.description == "Refactor authentication module"
        assert action.risk_level == RiskLevel.MEDIUM
        assert action.files_affected == []

    def test_undo_action_with_files(self) -> None:
        """Test undo action with affected files."""
        action = UndoAction(
            action="Delete files",
            undo_command="git checkout HEAD -- src/auth/*.ts",
            description="Remove deprecated auth code",
            risk_level=RiskLevel.HIGH,
            files_affected=["src/auth/old_auth.ts", "src/auth/legacy.ts"],
        )

        assert len(action.files_affected) == 2
        assert "src/auth/old_auth.ts" in action.files_affected

    def test_undo_action_with_metadata(self) -> None:
        """Test undo action with additional metadata."""
        action = UndoAction(
            action="Database migration",
            undo_command="npm run migration:rollback",
            description="Add user preferences table",
            risk_level=RiskLevel.CRITICAL,
            metadata={"migration_version": "20231205_001", "reversible": True},
        )

        assert action.metadata["migration_version"] == "20231205_001"
        assert action.metadata["reversible"] is True


class TestActionSnapshot:
    """Tests for ActionSnapshot dataclass."""

    def test_create_snapshot(self) -> None:
        """Test creating a snapshot before a risky operation."""
        snapshot = ActionSnapshot(
            action_description="Refactor auth module",
            files_affected=["src/auth/auth.py"],
            snapshot_data={"git_hash": "abc123", "file_contents": "..."},
            risk_level=RiskLevel.HIGH,
        )

        assert snapshot.action_description == "Refactor auth module"
        assert "src/auth/auth.py" in snapshot.files_affected
        assert snapshot.snapshot_data["git_hash"] == "abc123"
        assert snapshot.risk_level == RiskLevel.HIGH
        assert snapshot.verified is False

    def test_verify_snapshot(self) -> None:
        """Test marking a snapshot as verified."""
        snapshot = ActionSnapshot(
            action_description="Deploy API",
            files_affected=["config/api.yaml"],
            snapshot_data={"previous_version": "v1.2.0"},
            risk_level=RiskLevel.CRITICAL,
        )

        # Initially not verified
        assert snapshot.verified is False

        # Mark as verified
        snapshot.verified = True
        assert snapshot.verified is True


class TestUndoChain:
    """Tests for UndoChain class."""

    def test_create_empty_chain(self) -> None:
        """Test creating an empty undo chain."""
        chain = UndoChain()
        assert chain.depth() == 0
        assert chain.is_empty()

    def test_add_action(self) -> None:
        """Test adding an action to the chain."""
        chain = UndoChain()

        action = UndoAction(
            action="Create file",
            undo_command="rm src/new_file.py",
            description="Add new module",
            risk_level=RiskLevel.LOW,
        )

        chain.add(action)
        assert chain.depth() == 1
        assert not chain.is_empty()

    def test_get_last_action(self) -> None:
        """Test retrieving the last action in the chain."""
        chain = UndoChain()

        action1 = UndoAction(
            action="Edit file A",
            undo_command="git checkout -- a.py",
            description="First edit",
            risk_level=RiskLevel.LOW,
        )
        action2 = UndoAction(
            action="Edit file B",
            undo_command="git checkout -- b.py",
            description="Second edit",
            risk_level=RiskLevel.LOW,
        )

        chain.add(action1)
        chain.add(action2)

        last = chain.get_last()
        assert last is not None
        assert last.action == "Edit file B"

    def test_get_last_from_empty_chain(self) -> None:
        """Test getting last action from empty chain returns None."""
        chain = UndoChain()
        assert chain.get_last() is None

    def test_pop_action(self) -> None:
        """Test removing the last action from the chain."""
        chain = UndoChain()

        action1 = UndoAction(
            action="Action 1",
            undo_command="undo 1",
            description="First",
            risk_level=RiskLevel.LOW,
        )
        action2 = UndoAction(
            action="Action 2",
            undo_command="undo 2",
            description="Second",
            risk_level=RiskLevel.LOW,
        )

        chain.add(action1)
        chain.add(action2)
        assert chain.depth() == 2

        popped = chain.pop()
        assert popped is not None
        assert popped.action == "Action 2"
        assert chain.depth() == 1

    def test_get_all_actions(self) -> None:
        """Test retrieving all actions in the chain."""
        chain = UndoChain()

        for i in range(3):
            action = UndoAction(
                action=f"Action {i}",
                undo_command=f"undo {i}",
                description=f"Description {i}",
                risk_level=RiskLevel.LOW,
            )
            chain.add(action)

        all_actions = chain.get_all()
        assert len(all_actions) == 3
        assert all_actions[0].action == "Action 0"
        assert all_actions[2].action == "Action 2"

    def test_clear_chain(self) -> None:
        """Test clearing the entire chain."""
        chain = UndoChain()

        for i in range(5):
            action = UndoAction(
                action=f"Action {i}",
                undo_command=f"undo {i}",
                description="Test",
                risk_level=RiskLevel.LOW,
            )
            chain.add(action)

        assert chain.depth() == 5

        chain.clear()
        assert chain.depth() == 0
        assert chain.is_empty()

    def test_chain_max_depth(self) -> None:
        """Test undo chain respects maximum depth."""
        max_depth = 10
        chain = UndoChain(max_depth=max_depth)

        # Add more actions than max_depth
        for i in range(15):
            action = UndoAction(
                action=f"Action {i}",
                undo_command=f"undo {i}",
                description="Test",
                risk_level=RiskLevel.LOW,
            )
            chain.add(action)

        # Chain should not exceed max_depth
        assert chain.depth() == max_depth

        # Oldest actions should be removed (0-4), keeping 5-14
        all_actions = chain.get_all()
        assert all_actions[0].action == "Action 5"
        assert all_actions[-1].action == "Action 14"


class TestUndoAwarenessEngine:
    """Tests for UndoAwarenessEngine class."""

    def test_create_engine(self) -> None:
        """Test creating an undo awareness engine."""
        engine = UndoAwarenessEngine()
        assert engine.get_chain_depth() == 0

    def test_record_action(self) -> None:
        """Test recording an action with undo capability."""
        engine = UndoAwarenessEngine()

        engine.record_action(
            action="Edit file",
            undo_command="git checkout -- file.py",
            description="Update function",
            risk_level=RiskLevel.LOW,
        )

        assert engine.get_chain_depth() == 1

    def test_record_action_with_files(self) -> None:
        """Test recording an action with affected files."""
        engine = UndoAwarenessEngine()

        engine.record_action(
            action="Refactor module",
            undo_command="git checkout -- src/module/",
            description="Restructure",
            risk_level=RiskLevel.MEDIUM,
            files_affected=["src/module/a.py", "src/module/b.py"],
        )

        last_action = engine.get_last_action()
        assert last_action is not None
        assert len(last_action.files_affected) == 2

    def test_get_undo_command(self) -> None:
        """Test retrieving the undo command for the last action."""
        engine = UndoAwarenessEngine()

        engine.record_action(
            action="Create file",
            undo_command="rm new_file.py",
            description="Add new file",
            risk_level=RiskLevel.LOW,
        )

        undo_cmd = engine.get_undo_command()
        assert undo_cmd == "rm new_file.py"

    def test_get_undo_command_empty(self) -> None:
        """Test getting undo command when no actions exist."""
        engine = UndoAwarenessEngine()
        assert engine.get_undo_command() is None

    def test_create_snapshot(self) -> None:
        """Test creating a snapshot before a risky operation."""
        engine = UndoAwarenessEngine()

        snapshot = engine.create_snapshot(
            action_description="Deploy to production",
            files_affected=["config/prod.yaml"],
            snapshot_data={"git_hash": "abc123"},
            risk_level=RiskLevel.CRITICAL,
        )

        assert snapshot.action_description == "Deploy to production"
        assert snapshot.risk_level == RiskLevel.CRITICAL
        assert not snapshot.verified

    def test_verify_snapshot(self) -> None:
        """Test verifying a snapshot after operation succeeds."""
        engine = UndoAwarenessEngine()

        snapshot = engine.create_snapshot(
            action_description="Risky operation",
            files_affected=["file.py"],
            snapshot_data={"backup": "data"},
            risk_level=RiskLevel.HIGH,
        )

        engine.verify_snapshot(snapshot)
        assert snapshot.verified

    def test_generate_rollback_plan(self) -> None:
        """Test generating a rollback plan from action history."""
        engine = UndoAwarenessEngine()

        # Record multiple actions
        engine.record_action(
            action="Edit file A",
            undo_command="git checkout -- a.py",
            description="First edit",
            risk_level=RiskLevel.LOW,
        )
        engine.record_action(
            action="Edit file B",
            undo_command="git checkout -- b.py",
            description="Second edit",
            risk_level=RiskLevel.MEDIUM,
        )

        plan = engine.generate_rollback_plan()

        assert "Rollback Plan" in plan
        assert "git checkout -- b.py" in plan
        assert "git checkout -- a.py" in plan
        # Commands should be in reverse order
        assert plan.index("b.py") < plan.index("a.py")

    def test_rollback_plan_empty(self) -> None:
        """Test generating rollback plan when no actions exist."""
        engine = UndoAwarenessEngine()
        plan = engine.generate_rollback_plan()

        assert "No actions" in plan or "Empty" in plan

    def test_can_rollback(self) -> None:
        """Test checking if rollback is possible."""
        engine = UndoAwarenessEngine()

        # Initially cannot rollback (no actions)
        assert not engine.can_rollback()

        # After recording an action, can rollback
        engine.record_action(
            action="Test",
            undo_command="undo test",
            description="Test action",
            risk_level=RiskLevel.LOW,
        )
        assert engine.can_rollback()

    def test_rollback_integration_with_error_context(self) -> None:
        """Test rollback plan includes error context when available."""
        engine = UndoAwarenessEngine()

        engine.record_action(
            action="Deploy",
            undo_command="rollback deployment",
            description="Deploy new version",
            risk_level=RiskLevel.HIGH,
        )

        error = ErrorContext(
            error_type=ErrorType.VALIDATION_FAILURE,
            severity=ErrorSeverity.CRITICAL,
            message="Deployment failed validation",
            agent_id="deployer-1",
            task_id="deploy-123",
        )

        plan = engine.generate_rollback_plan(error_context=error)

        assert "validation_failure" in plan
        assert "Deployment failed validation" in plan
        assert "rollback deployment" in plan

    def test_export_to_handoff_format(self) -> None:
        """Test exporting rollback plan in handoff document format."""
        engine = UndoAwarenessEngine()

        engine.record_action(
            action="Refactor auth",
            undo_command="git checkout -- src/auth/",
            description="Refactor authentication",
            risk_level=RiskLevel.HIGH,
            files_affected=["src/auth/auth.py"],
        )

        handoff_data = engine.export_to_handoff()

        assert "rollback_plan" in handoff_data
        assert "action_count" in handoff_data
        assert handoff_data["action_count"] == 1
        assert handoff_data["can_rollback"] is True

    def test_auto_rollback_on_critical_error(self) -> None:
        """Test automatic rollback when critical error detected."""
        engine = UndoAwarenessEngine()

        # Record an action
        engine.record_action(
            action="Critical operation",
            undo_command="revert operation",
            description="Risky change",
            risk_level=RiskLevel.CRITICAL,
        )

        # Simulate a critical error
        error = ErrorContext(
            error_type=ErrorType.CRASH,
            severity=ErrorSeverity.CRITICAL,
            message="System crash detected",
            agent_id="agent-1",
            task_id="task-1",
        )

        # Check if rollback should be triggered
        should_rollback = engine.should_auto_rollback(error)
        assert should_rollback

    def test_no_auto_rollback_on_low_severity(self) -> None:
        """Test no automatic rollback for low severity errors."""
        engine = UndoAwarenessEngine()

        engine.record_action(
            action="Minor change",
            undo_command="revert change",
            description="Small edit",
            risk_level=RiskLevel.LOW,
        )

        error = ErrorContext(
            error_type=ErrorType.VALIDATION_FAILURE,
            severity=ErrorSeverity.LOW,
            message="Minor validation issue",
            agent_id="agent-1",
            task_id="task-1",
        )

        should_rollback = engine.should_auto_rollback(error)
        assert not should_rollback

    def test_rollback_decision_based_on_risk_level(self) -> None:
        """Test rollback decision considers both error severity and risk level."""
        engine = UndoAwarenessEngine()

        # High risk action with medium severity error should rollback
        engine.record_action(
            action="High risk operation",
            undo_command="undo operation",
            description="Critical change",
            risk_level=RiskLevel.HIGH,
        )

        error_medium = ErrorContext(
            error_type=ErrorType.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            message="Operation timed out",
            agent_id="agent-1",
            task_id="task-1",
        )

        # High risk + medium severity = should rollback
        assert engine.should_auto_rollback(error_medium)

    def test_multiple_rollback_steps(self) -> None:
        """Test rolling back multiple steps in correct order."""
        engine = UndoAwarenessEngine()

        # Record multiple actions
        actions = [
            ("Step 1", "undo step 1"),
            ("Step 2", "undo step 2"),
            ("Step 3", "undo step 3"),
        ]

        for action, undo in actions:
            engine.record_action(
                action=action,
                undo_command=undo,
                description=f"Description for {action}",
                risk_level=RiskLevel.MEDIUM,
            )

        # Get rollback plan - should be in reverse order
        plan = engine.generate_rollback_plan()

        # Step 3 should appear before Step 2, which should appear before Step 1
        step3_pos = plan.index("undo step 3")
        step2_pos = plan.index("undo step 2")
        step1_pos = plan.index("undo step 1")

        assert step3_pos < step2_pos < step1_pos

    def test_export_to_json(self) -> None:
        """Test exporting undo chain to JSON format."""
        engine = UndoAwarenessEngine()

        engine.record_action(
            action="Deploy",
            undo_command="rollback",
            description="Production deployment",
            risk_level=RiskLevel.CRITICAL,
            files_affected=["dist/app.js"],
        )

        json_data = engine.export_to_json()
        parsed = json.loads(json_data)

        assert parsed["action_count"] == 1
        assert parsed["can_rollback"] is True
        assert len(parsed["actions"]) == 1
        assert parsed["actions"][0]["action"] == "Deploy"

    def test_clear_history(self) -> None:
        """Test clearing the undo chain history."""
        engine = UndoAwarenessEngine()

        # Add several actions
        for i in range(5):
            engine.record_action(
                action=f"Action {i}",
                undo_command=f"undo {i}",
                description=f"Test {i}",
                risk_level=RiskLevel.LOW,
            )

        assert engine.get_chain_depth() == 5

        # Clear history
        engine.clear_history()
        assert engine.get_chain_depth() == 0
        assert not engine.can_rollback()

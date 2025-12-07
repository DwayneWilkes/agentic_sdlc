"""Tests for stuck detection and escape strategies."""

from datetime import datetime, timedelta

from src.core.stuck_detection import (
    EscapeStrategy,
    EscapeStrategyEngine,
    ProgressMetrics,
    ProgressSnapshot,
    StuckDetector,
    StuckPattern,
    StuckSignal,
)


class TestProgressSnapshot:
    """Test the ProgressSnapshot dataclass."""

    def test_create_snapshot(self) -> None:
        """Test creating a progress snapshot."""
        snapshot = ProgressSnapshot(
            timestamp=datetime.now(),
            lines_changed=10,
            tests_passing=5,
            tests_failing=2,
            goals_met=1,
            files_modified={"file1.py", "file2.py"},
        )
        assert snapshot.lines_changed == 10
        assert snapshot.tests_passing == 5
        assert snapshot.tests_failing == 2
        assert snapshot.goals_met == 1
        assert len(snapshot.files_modified) == 2


class TestProgressMetrics:
    """Test the ProgressMetrics class."""

    def test_initialization(self) -> None:
        """Test ProgressMetrics initializes with empty history."""
        metrics = ProgressMetrics()
        assert len(metrics.get_history()) == 0

    def test_record_progress(self) -> None:
        """Test recording a progress snapshot."""
        metrics = ProgressMetrics()
        snapshot = ProgressSnapshot(
            timestamp=datetime.now(),
            lines_changed=10,
            tests_passing=5,
            tests_failing=2,
            goals_met=1,
            files_modified={"file1.py"},
        )
        metrics.record_progress(snapshot)
        assert len(metrics.get_history()) == 1

    def test_has_progress_with_changes(self) -> None:
        """Test detecting progress when changes are made."""
        metrics = ProgressMetrics()
        # Record initial state
        snapshot1 = ProgressSnapshot(
            timestamp=datetime.now() - timedelta(minutes=5),
            lines_changed=0,
            tests_passing=5,
            tests_failing=2,
            goals_met=0,
            files_modified=set(),
        )
        metrics.record_progress(snapshot1)

        # Record progress
        snapshot2 = ProgressSnapshot(
            timestamp=datetime.now(),
            lines_changed=10,
            tests_passing=6,
            tests_failing=1,
            goals_met=1,
            files_modified={"file1.py"},
        )
        metrics.record_progress(snapshot2)

        assert metrics.has_progress(time_window_minutes=10)

    def test_has_progress_no_changes(self) -> None:
        """Test detecting no progress when nothing changes."""
        metrics = ProgressMetrics()
        snapshot1 = ProgressSnapshot(
            timestamp=datetime.now() - timedelta(minutes=5),
            lines_changed=0,
            tests_passing=5,
            tests_failing=2,
            goals_met=0,
            files_modified=set(),
        )
        metrics.record_progress(snapshot1)

        snapshot2 = ProgressSnapshot(
            timestamp=datetime.now(),
            lines_changed=0,
            tests_passing=5,
            tests_failing=2,
            goals_met=0,
            files_modified=set(),
        )
        metrics.record_progress(snapshot2)

        assert not metrics.has_progress(time_window_minutes=10)

    def test_get_tests_trend_improving(self) -> None:
        """Test detecting improving test trend."""
        metrics = ProgressMetrics()
        # Create snapshots from oldest to newest with improving scores
        # i=2 (oldest): pass=3, fail=7, score=-4
        # i=1:          pass=4, fail=6, score=-2
        # i=0 (newest): pass=5, fail=5, score=0
        snapshots = [
            ProgressSnapshot(
                timestamp=datetime.now() - timedelta(minutes=2 - i),
                lines_changed=0,
                tests_passing=3 + i,
                tests_failing=7 - i,
                goals_met=0,
                files_modified=set(),
            )
            for i in range(3)
        ]
        for snapshot in snapshots:
            metrics.record_progress(snapshot)

        trend = metrics.get_tests_trend()
        assert trend == "improving"

    def test_get_tests_trend_degrading(self) -> None:
        """Test detecting degrading test trend."""
        metrics = ProgressMetrics()
        # Create snapshots from oldest to newest with degrading scores
        # i=0 (oldest): pass=5, fail=5, score=0
        # i=1:          pass=4, fail=6, score=-2
        # i=2 (newest): pass=3, fail=7, score=-4
        snapshots = [
            ProgressSnapshot(
                timestamp=datetime.now() - timedelta(minutes=2 - i),
                lines_changed=0,
                tests_passing=5 - i,
                tests_failing=5 + i,
                goals_met=0,
                files_modified=set(),
            )
            for i in range(3)
        ]
        for snapshot in snapshots:
            metrics.record_progress(snapshot)

        trend = metrics.get_tests_trend()
        assert trend == "degrading"

    def test_get_tests_trend_stable(self) -> None:
        """Test detecting stable test trend."""
        metrics = ProgressMetrics()
        for i in range(3):
            snapshot = ProgressSnapshot(
                timestamp=datetime.now() - timedelta(minutes=i),
                lines_changed=0,
                tests_passing=5,
                tests_failing=2,
                goals_met=0,
                files_modified=set(),
            )
            metrics.record_progress(snapshot)

        trend = metrics.get_tests_trend()
        assert trend == "stable"


class TestStuckDetector:
    """Test the StuckDetector class."""

    def test_initialization(self) -> None:
        """Test StuckDetector initializes with empty history."""
        detector = StuckDetector()
        assert len(detector.get_error_history()) == 0
        assert len(detector.get_action_history()) == 0

    def test_detect_retry_loop_below_threshold(self) -> None:
        """Test retry loop detection below threshold."""
        detector = StuckDetector()
        # Record same error twice (below threshold of 3)
        detector.record_error("agent-1", "task-1", "Error: null pointer")
        detector.record_error("agent-1", "task-1", "Error: null pointer")

        signal = detector.detect_retry_loop(agent_id="agent-1", task_id="task-1")
        assert signal is None

    def test_detect_retry_loop_at_threshold(self) -> None:
        """Test retry loop detection at threshold."""
        detector = StuckDetector()
        # Record same error 3 times
        for _ in range(3):
            detector.record_error("agent-1", "task-1", "Error: null pointer")

        signal = detector.detect_retry_loop(agent_id="agent-1", task_id="task-1")
        assert signal is not None
        assert signal.pattern == StuckPattern.RETRY_LOOP
        assert signal.severity == "high"
        assert "3 times" in signal.description

    def test_detect_retry_loop_different_errors(self) -> None:
        """Test retry loop not detected with different errors."""
        detector = StuckDetector()
        detector.record_error("agent-1", "task-1", "Error: null pointer")
        detector.record_error("agent-1", "task-1", "Error: timeout")
        detector.record_error("agent-1", "task-1", "Error: invalid input")

        signal = detector.detect_retry_loop(agent_id="agent-1", task_id="task-1")
        assert signal is None

    def test_detect_thrashing_pattern(self) -> None:
        """Test thrashing detection with A→B→A→B pattern."""
        detector = StuckDetector()
        # Simulate thrashing: approach A, then B, then A again, then B again
        detector.record_action("agent-1", "task-1", "approach_A")
        detector.record_action("agent-1", "task-1", "approach_B")
        detector.record_action("agent-1", "task-1", "approach_A")
        detector.record_action("agent-1", "task-1", "approach_B")

        signal = detector.detect_thrashing(agent_id="agent-1", task_id="task-1")
        assert signal is not None
        assert signal.pattern == StuckPattern.THRASHING
        assert signal.severity == "high"

    def test_detect_thrashing_no_pattern(self) -> None:
        """Test thrashing not detected without pattern."""
        detector = StuckDetector()
        # Different approaches, no repetition
        detector.record_action("agent-1", "task-1", "approach_A")
        detector.record_action("agent-1", "task-1", "approach_B")
        detector.record_action("agent-1", "task-1", "approach_C")

        signal = detector.detect_thrashing(agent_id="agent-1", task_id="task-1")
        assert signal is None

    def test_detect_no_progress_with_metrics(self) -> None:
        """Test no progress detection with ProgressMetrics."""
        detector = StuckDetector()
        metrics = ProgressMetrics()

        # Record snapshots with no progress
        for i in range(3):
            snapshot = ProgressSnapshot(
                timestamp=datetime.now() - timedelta(minutes=5 - i),
                lines_changed=0,
                tests_passing=5,
                tests_failing=2,
                goals_met=0,
                files_modified=set(),
            )
            metrics.record_progress(snapshot)

        signal = detector.detect_no_progress(
            agent_id="agent-1",
            task_id="task-1",
            progress_metrics=metrics,
            time_threshold_minutes=10,
        )
        assert signal is not None
        assert signal.pattern == StuckPattern.NO_PROGRESS
        assert signal.severity == "medium"

    def test_detect_no_progress_with_progress(self) -> None:
        """Test no progress not detected when progress is made."""
        detector = StuckDetector()
        metrics = ProgressMetrics()

        # Record snapshots with progress
        snapshot1 = ProgressSnapshot(
            timestamp=datetime.now() - timedelta(minutes=5),
            lines_changed=0,
            tests_passing=5,
            tests_failing=2,
            goals_met=0,
            files_modified=set(),
        )
        metrics.record_progress(snapshot1)

        snapshot2 = ProgressSnapshot(
            timestamp=datetime.now(),
            lines_changed=10,
            tests_passing=6,
            tests_failing=1,
            goals_met=1,
            files_modified={"file1.py"},
        )
        metrics.record_progress(snapshot2)

        signal = detector.detect_no_progress(
            agent_id="agent-1",
            task_id="task-1",
            progress_metrics=metrics,
            time_threshold_minutes=10,
        )
        assert signal is None

    def test_is_stuck_multiple_signals(self) -> None:
        """Test is_stuck returns true when multiple signals detected."""
        detector = StuckDetector()
        metrics = ProgressMetrics()

        # Create retry loop
        for _ in range(3):
            detector.record_error("agent-1", "task-1", "Error: same error")

        # Create no progress
        snapshot = ProgressSnapshot(
            timestamp=datetime.now() - timedelta(minutes=5),
            lines_changed=0,
            tests_passing=5,
            tests_failing=2,
            goals_met=0,
            files_modified=set(),
        )
        metrics.record_progress(snapshot)

        is_stuck, signals = detector.is_stuck(
            agent_id="agent-1", task_id="task-1", progress_metrics=metrics
        )
        assert is_stuck
        assert len(signals) >= 1

    def test_is_stuck_no_signals(self) -> None:
        """Test is_stuck returns false when no signals detected."""
        detector = StuckDetector()
        metrics = ProgressMetrics()

        # Create baseline snapshot
        baseline = ProgressSnapshot(
            timestamp=datetime.now() - timedelta(minutes=5),
            lines_changed=0,
            tests_passing=3,
            tests_failing=2,
            goals_met=0,
            files_modified=set(),
        )
        metrics.record_progress(baseline)

        # Create progress snapshot showing improvement
        progress = ProgressSnapshot(
            timestamp=datetime.now(),
            lines_changed=10,
            tests_passing=5,
            tests_failing=0,
            goals_met=1,
            files_modified={"file1.py"},
        )
        metrics.record_progress(progress)

        is_stuck, signals = detector.is_stuck(
            agent_id="agent-1", task_id="task-1", progress_metrics=metrics
        )
        assert not is_stuck
        assert len(signals) == 0


class TestEscapeStrategyEngine:
    """Test the EscapeStrategyEngine class."""

    def test_initialization(self):
        """Test EscapeStrategyEngine initializes correctly."""
        engine = EscapeStrategyEngine()
        strategies = engine.get_available_strategies()
        assert len(strategies) == 5
        assert EscapeStrategy.REFRAME in strategies
        assert EscapeStrategy.REDUCE in strategies
        assert EscapeStrategy.RESEARCH in strategies
        assert EscapeStrategy.ESCALATE in strategies
        assert EscapeStrategy.HANDOFF in strategies

    def test_recommend_strategy_for_retry_loop(self):
        """Test strategy recommendation for retry loop."""
        engine = EscapeStrategyEngine()
        signal = StuckSignal(
            pattern=StuckPattern.RETRY_LOOP,
            severity="high",
            description="Same error 3 times",
            agent_id="agent-1",
            task_id="task-1",
            detected_at=datetime.now(),
        )
        strategy = engine.recommend_strategy(signal)
        assert strategy == EscapeStrategy.REFRAME

    def test_recommend_strategy_for_thrashing(self):
        """Test strategy recommendation for thrashing."""
        engine = EscapeStrategyEngine()
        signal = StuckSignal(
            pattern=StuckPattern.THRASHING,
            severity="high",
            description="Switching approaches",
            agent_id="agent-1",
            task_id="task-1",
            detected_at=datetime.now(),
        )
        strategy = engine.recommend_strategy(signal)
        assert strategy == EscapeStrategy.REDUCE

    def test_recommend_strategy_for_no_progress(self):
        """Test strategy recommendation for no progress."""
        engine = EscapeStrategyEngine()
        signal = StuckSignal(
            pattern=StuckPattern.NO_PROGRESS,
            severity="medium",
            description="No progress in 10 minutes",
            agent_id="agent-1",
            task_id="task-1",
            detected_at=datetime.now(),
        )
        strategy = engine.recommend_strategy(signal)
        assert strategy in [
            EscapeStrategy.RESEARCH,
            EscapeStrategy.REFRAME,
        ]

    def test_generate_reframe_action(self):
        """Test generating REFRAME action plan."""
        engine = EscapeStrategyEngine()
        signal = StuckSignal(
            pattern=StuckPattern.RETRY_LOOP,
            severity="high",
            description="Same error 3 times",
            agent_id="agent-1",
            task_id="task-1",
            detected_at=datetime.now(),
        )
        action = engine.generate_action_plan(signal, EscapeStrategy.REFRAME)
        assert "Try a completely different approach" in action
        assert "agent-1" in action
        assert "task-1" in action

    def test_generate_reduce_action(self):
        """Test generating REDUCE action plan."""
        engine = EscapeStrategyEngine()
        signal = StuckSignal(
            pattern=StuckPattern.THRASHING,
            severity="high",
            description="Switching approaches",
            agent_id="agent-1",
            task_id="task-1",
            detected_at=datetime.now(),
        )
        action = engine.generate_action_plan(signal, EscapeStrategy.REDUCE)
        assert "minimal reproducing case" in action.lower()

    def test_generate_research_action(self):
        """Test generating RESEARCH action plan."""
        engine = EscapeStrategyEngine()
        signal = StuckSignal(
            pattern=StuckPattern.NO_PROGRESS,
            severity="medium",
            description="No progress",
            agent_id="agent-1",
            task_id="task-1",
            detected_at=datetime.now(),
        )
        action = engine.generate_action_plan(signal, EscapeStrategy.RESEARCH)
        assert "search" in action.lower() or "research" in action.lower()

    def test_generate_escalate_action(self):
        """Test generating ESCALATE action plan."""
        engine = EscapeStrategyEngine()
        signal = StuckSignal(
            pattern=StuckPattern.RETRY_LOOP,
            severity="high",
            description="Same error 5 times",
            agent_id="agent-1",
            task_id="task-1",
            detected_at=datetime.now(),
        )
        action = engine.generate_action_plan(signal, EscapeStrategy.ESCALATE)
        assert "human" in action.lower() or "help" in action.lower()

    def test_generate_handoff_action(self):
        """Test generating HANDOFF action plan."""
        engine = EscapeStrategyEngine()
        signal = StuckSignal(
            pattern=StuckPattern.THRASHING,
            severity="high",
            description="Switching approaches",
            agent_id="agent-1",
            task_id="task-1",
            detected_at=datetime.now(),
        )
        action = engine.generate_action_plan(signal, EscapeStrategy.HANDOFF)
        assert "different agent" in action.lower() or "handoff" in action.lower()

    def test_execute_escape_strategy(self):
        """Test executing an escape strategy."""
        engine = EscapeStrategyEngine()
        signal = StuckSignal(
            pattern=StuckPattern.RETRY_LOOP,
            severity="high",
            description="Same error 3 times",
            agent_id="agent-1",
            task_id="task-1",
            detected_at=datetime.now(),
        )
        result = engine.execute_escape_strategy(signal)
        assert result["strategy"] in [s.value for s in EscapeStrategy]
        assert "action_plan" in result
        assert "signal" in result
        assert result["signal"]["pattern"] == StuckPattern.RETRY_LOOP.value

"""
Tests for Recurrent Refiner module.

Tests the multi-pass understanding and refinement of parsed tasks.
"""


from src.core.recurrent_refiner import (
    PassType,
    RecurrentRefiner,
    RefinedTask,
    RefinementPass,
)
from src.core.task_parser import ParsedTask, TaskParser
from src.models.enums import TaskType


def test_refiner_initialization():
    """Test that RecurrentRefiner initializes with correct defaults."""
    refiner = RecurrentRefiner()
    assert refiner.max_passes == 3
    assert refiner.confidence_threshold == 0.85


def test_refiner_custom_config():
    """Test RecurrentRefiner with custom configuration."""
    refiner = RecurrentRefiner(max_passes=5, confidence_threshold=0.9)
    assert refiner.max_passes == 5
    assert refiner.confidence_threshold == 0.9


def test_refine_simple_task():
    """Test refinement of a simple task description."""
    parser = TaskParser()
    task = parser.parse("Build a REST API for user authentication")

    refiner = RecurrentRefiner()
    refined = refiner.refine(task)

    assert isinstance(refined, RefinedTask)
    assert refined.original_task == task
    assert len(refined.passes) > 0
    assert len(refined.passes) <= refiner.max_passes
    assert 0.0 <= refined.final_confidence <= 1.0


def test_refine_tracks_passes():
    """Test that refinement tracks all processing passes."""
    parser = TaskParser()
    task = parser.parse("Analyze performance bottlenecks in the authentication module")

    refiner = RecurrentRefiner()
    refined = refiner.refine(task)

    # Should have at least 2 passes (initial + contextual)
    assert len(refined.passes) >= 2

    # Each pass should have required fields
    for pass_data in refined.passes:
        assert isinstance(pass_data, RefinementPass)
        assert pass_data.pass_type in [PassType.INITIAL, PassType.CONTEXTUAL, PassType.COHERENCE]
        assert 0.0 <= pass_data.confidence <= 1.0
        assert len(pass_data.key_insights) >= 0


def test_first_pass_is_initial_scan():
    """Test that first pass is always INITIAL scan."""
    parser = TaskParser()
    task = parser.parse("Create a caching layer for database queries")

    refiner = RecurrentRefiner()
    refined = refiner.refine(task)

    assert refined.passes[0].pass_type == PassType.INITIAL
    assert "entities" in refined.passes[0].findings or "key_elements" in refined.passes[0].findings


def test_confidence_increases_across_passes():
    """Test that confidence generally increases with each pass."""
    parser = TaskParser()
    task = parser.parse(
        "Build a REST API for user authentication with JWT tokens. "
        "Include login, logout, and token refresh endpoints. "
        "Use OAuth2 for third-party authentication."
    )

    refiner = RecurrentRefiner()
    refined = refiner.refine(task)

    # Confidence should increase or stay stable (never decrease significantly)
    for i in range(1, len(refined.passes)):
        # Allow small decreases due to discovering ambiguities
        assert refined.passes[i].confidence >= refined.passes[i-1].confidence - 0.1


def test_refinement_identifies_ambiguities():
    """Test that refinement can identify ambiguous requirements."""
    parser = TaskParser()
    # Intentionally ambiguous task
    task = parser.parse("Fix the authentication system")

    refiner = RecurrentRefiner()
    refined = refiner.refine(task)

    # Should identify ambiguities in one of the passes
    ambiguities_found = any(
        len(pass_data.ambiguities_noted) > 0
        for pass_data in refined.passes
    )
    assert ambiguities_found or refined.final_confidence < 0.7


def test_refinement_detects_dependencies():
    """Test that refinement identifies task dependencies."""
    parser = TaskParser()
    task = parser.parse(
        "Implement user authentication with database storage. "
        "Add API endpoints after the database models are ready. "
        "Write tests once the API is complete."
    )

    refiner = RecurrentRefiner()
    refined = refiner.refine(task)

    # Should identify dependencies in contextual or coherence pass
    deps_found = any(
        "dependencies" in pass_data.findings
        for pass_data in refined.passes
    )
    assert deps_found


def test_refinement_stops_early_if_confident():
    """Test that refinement stops early if confidence threshold reached."""
    parser = TaskParser()
    # Very clear, unambiguous task
    task = parser.parse("Add 2 + 2")

    refiner = RecurrentRefiner(max_passes=5, confidence_threshold=0.8)
    refined = refiner.refine(task)

    # Should stop before max passes due to high confidence
    # (simple task should be understood quickly)
    assert (
        refined.final_confidence >= refiner.confidence_threshold
        or len(refined.passes) < refiner.max_passes
    )


def test_refinement_detects_contradictions():
    """Test that coherence check detects contradictions."""
    parser = TaskParser()
    # Task with internal contradiction
    task = parser.parse(
        "Build a stateless authentication system using session cookies. "
        "Ensure the API is fully RESTful and stateless."
    )

    refiner = RecurrentRefiner()
    refined = refiner.refine(task)

    # Should note contradiction in coherence pass
    coherence_passes = [p for p in refined.passes if p.pass_type == PassType.COHERENCE]
    if coherence_passes:
        # Either ambiguities noted or confidence decreased
        assert (
            len(coherence_passes[0].ambiguities_noted) > 0
            or coherence_passes[0].confidence < 0.8
        )


def test_refined_task_summary():
    """Test that refined task provides a useful summary."""
    parser = TaskParser()
    task = parser.parse("Implement OAuth2 authentication with JWT tokens")

    refiner = RecurrentRefiner()
    refined = refiner.refine(task)

    summary = refined.get_summary()
    assert isinstance(summary, str)
    assert len(summary) > 0
    assert "confidence" in summary.lower() or str(refined.final_confidence) in summary


def test_refinement_key_insights_accumulate():
    """Test that key insights accumulate across passes."""
    parser = TaskParser()
    task = parser.parse(
        "Build a REST API for user management. "
        "Include CRUD operations for users. "
        "Add role-based access control. "
        "Implement rate limiting for API endpoints."
    )

    refiner = RecurrentRefiner()
    refined = refiner.refine(task)

    # Key insights should accumulate
    total_insights = sum(len(p.key_insights) for p in refined.passes)
    assert total_insights > 0


def test_refinement_handles_empty_task():
    """Test that refiner handles empty task gracefully."""
    task = ParsedTask(
        goal="",
        constraints=[],
        context={},
        task_type=TaskType.SOFTWARE,
        success_criteria=[],
        ambiguities=[],
        raw_description=""
    )

    refiner = RecurrentRefiner()
    refined = refiner.refine(task)

    assert isinstance(refined, RefinedTask)
    assert refined.final_confidence == 0.0  # No content = no confidence


def test_diminishing_returns_detection():
    """Test that refiner detects when additional passes don't help."""
    parser = TaskParser()
    task = parser.parse("List all files in the current directory")

    refiner = RecurrentRefiner(max_passes=5)
    refined = refiner.refine(task)

    # Simple task should trigger diminishing returns before max passes
    # (confidence should stabilize)
    if len(refined.passes) >= 2:
        confidence_deltas = [
            refined.passes[i].confidence - refined.passes[i-1].confidence
            for i in range(1, len(refined.passes))
        ]
        # Last delta should be small (diminishing returns)
        if len(confidence_deltas) > 0:
            assert confidence_deltas[-1] < 0.15  # Small improvement


def test_refinement_preserves_original_task():
    """Test that refinement doesn't modify the original task."""
    parser = TaskParser()
    task = parser.parse("Build a REST API")
    original_goal = task.goal
    original_type = task.task_type

    refiner = RecurrentRefiner()
    refined = refiner.refine(task)

    # Original task unchanged
    assert task.goal == original_goal
    assert task.task_type == original_type
    assert refined.original_task == task


def test_multiple_refinements_independent():
    """Test that multiple refinements don't interfere with each other."""
    parser = TaskParser()
    task1 = parser.parse("Build API")
    task2 = parser.parse("Analyze data")

    refiner = RecurrentRefiner()
    refined1 = refiner.refine(task1)
    refined2 = refiner.refine(task2)

    # Should be independent results
    assert refined1 != refined2
    assert refined1.original_task != refined2.original_task

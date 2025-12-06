"""Tests for the goal interpreter."""

import pytest
from pathlib import Path

from src.orchestrator.goal_interpreter import (
    interpret_goal,
    InterpretedGoal,
    format_interpretation,
)


class TestInterpretGoal:
    """Tests for goal interpretation."""

    @pytest.fixture
    def sample_roadmap(self, tmp_path):
        """Create a sample roadmap file."""
        roadmap = tmp_path / "roadmap.md"
        roadmap.write_text("""# Roadmap

## Batch 1

### Phase 1.2: Task Parser and Goal Extraction
- **Status:** ⚪ Not Started
- **Tasks:**
  - [ ] Implement TaskParser
- **Effort:** M

### Phase 1.3: Task Decomposition Engine
- **Status:** ⚪ Not Started
- **Tasks:**
  - [ ] Implement decomposition
- **Effort:** M

### Phase 1.4: Agent Role Registry
- **Status:** ⚪ Not Started
- **Tasks:**
  - [ ] Define roles
- **Effort:** S

## Batch 2

### Phase 2.1: Team Composition
- **Status:** 🔴 Blocked
- **Depends On:** Phase 1.4
- **Effort:** S
""")
        return roadmap

    def test_interpret_parser_goal(self, sample_roadmap):
        """Test interpreting a parser-related goal."""
        result = interpret_goal("I want to build the task parser", sample_roadmap)

        assert result.original_goal == "I want to build the task parser"
        assert len(result.matched_work_streams) > 0
        assert any(ws.id == "1.2" for ws in result.matched_work_streams)

    def test_interpret_all_goal(self, sample_roadmap):
        """Test interpreting 'run everything' goal."""
        result = interpret_goal("Run everything available", sample_roadmap)

        assert result.suggested_action == "run_batch"
        assert len(result.matched_work_streams) == 3  # All non-blocked

    def test_interpret_next_goal(self, sample_roadmap):
        """Test interpreting 'next' goal."""
        result = interpret_goal("Start the next work stream", sample_roadmap)

        assert result.suggested_action == "run_single"
        assert len(result.matched_work_streams) == 1

    def test_interpret_decomposition_goal(self, sample_roadmap):
        """Test interpreting decomposition goal."""
        result = interpret_goal("Work on task decomposition", sample_roadmap)

        assert any(ws.id == "1.3" for ws in result.matched_work_streams)

    def test_interpret_specific_phase(self, sample_roadmap):
        """Test interpreting role registry goal."""
        result = interpret_goal("Work on the agent role registry", sample_roadmap)

        assert any(ws.id == "1.4" for ws in result.matched_work_streams)

    def test_interpret_no_match(self, sample_roadmap):
        """Test interpreting unrelated goal."""
        result = interpret_goal("Make coffee", sample_roadmap)

        # Should still return something (low confidence suggestions)
        assert result.confidence < 0.5

    def test_confidence_high_for_exact_match(self, sample_roadmap):
        """Test that exact matches have high confidence."""
        result = interpret_goal("parser", sample_roadmap)

        assert result.confidence >= 0.5

    def test_suggested_action_single_vs_parallel(self, sample_roadmap):
        """Test correct action suggestion based on matches."""
        single = interpret_goal("Just the parser", sample_roadmap)
        assert single.suggested_action in ("run_single", "suggest")

        multi = interpret_goal("foundation work", sample_roadmap)
        # Foundation matches multiple phases
        if len(multi.matched_work_streams) > 1:
            assert multi.suggested_action in ("run_parallel", "suggest")


class TestFormatInterpretation:
    """Tests for formatting interpretation results."""

    def test_format_basic(self, tmp_path):
        """Test basic formatting."""
        roadmap = tmp_path / "roadmap.md"
        roadmap.write_text("""# Roadmap
## Batch 1
### Phase 1.2: Task Parser
- **Status:** ⚪ Not Started
- **Effort:** M
""")
        result = interpret_goal("parser", roadmap)
        formatted = format_interpretation(result)

        assert "parser" in formatted.lower()
        assert "1.2" in formatted
        assert "Confidence" in formatted

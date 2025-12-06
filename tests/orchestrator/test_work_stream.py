"""Tests for the work stream parser."""

import pytest
from pathlib import Path
from unittest.mock import patch

from src.orchestrator.work_stream import (
    WorkStream,
    WorkStreamStatus,
    parse_roadmap,
    get_available_work_streams,
    get_blocked_work_streams,
)


class TestWorkStreamStatus:
    """Tests for WorkStreamStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert WorkStreamStatus.NOT_STARTED.value == "not_started"
        assert WorkStreamStatus.IN_PROGRESS.value == "in_progress"
        assert WorkStreamStatus.COMPLETE.value == "complete"
        assert WorkStreamStatus.BLOCKED.value == "blocked"


class TestWorkStream:
    """Tests for WorkStream dataclass."""

    def test_create_work_stream(self):
        """Test creating a work stream."""
        ws = WorkStream(
            id="1.2",
            name="Task Parser",
            status=WorkStreamStatus.NOT_STARTED,
        )
        assert ws.id == "1.2"
        assert ws.name == "Task Parser"
        assert ws.status == WorkStreamStatus.NOT_STARTED

    def test_is_available(self):
        """Test is_available property."""
        ws_not_started = WorkStream(
            id="1.2",
            name="Test",
            status=WorkStreamStatus.NOT_STARTED,
        )
        assert ws_not_started.is_available is True

        ws_blocked = WorkStream(
            id="1.3",
            name="Test",
            status=WorkStreamStatus.BLOCKED,
        )
        assert ws_blocked.is_available is False

    def test_is_claimable_not_started(self):
        """Test is_claimable for not started work streams."""
        ws = WorkStream(
            id="1.2",
            name="Test",
            status=WorkStreamStatus.NOT_STARTED,
        )
        assert ws.is_claimable is True

    def test_is_claimable_in_progress_unassigned(self):
        """Test is_claimable for unassigned in-progress work streams."""
        ws = WorkStream(
            id="1.2",
            name="Test",
            status=WorkStreamStatus.IN_PROGRESS,
            assigned_to=None,
        )
        assert ws.is_claimable is True

    def test_is_claimable_in_progress_assigned(self):
        """Test is_claimable for assigned in-progress work streams."""
        ws = WorkStream(
            id="1.2",
            name="Test",
            status=WorkStreamStatus.IN_PROGRESS,
            assigned_to="Aurora",
        )
        assert ws.is_claimable is False

    def test_str_representation(self):
        """Test string representation."""
        ws = WorkStream(
            id="1.2",
            name="Task Parser",
            status=WorkStreamStatus.NOT_STARTED,
        )
        assert "1.2" in str(ws)
        assert "Task Parser" in str(ws)


class TestParseRoadmap:
    """Tests for roadmap parsing."""

    @pytest.fixture
    def sample_roadmap(self, tmp_path):
        """Create a sample roadmap file."""
        roadmap = tmp_path / "roadmap.md"
        roadmap.write_text("""# Roadmap

## Batch 1 (Foundation)

### Phase 1.1: Core Data Models
- **Status:** ✅ Complete
- **Assigned To:** Aurora
- **Tasks:**
  - [✅] Create project structure
  - [✅] Define core models
- **Effort:** S
- **Done When:** Models exist

### Phase 1.2: Task Parser
- **Status:** ⚪ Not Started
- **Tasks:**
  - [ ] Implement TaskParser
  - [ ] Add classification
- **Effort:** M
- **Done When:** Parser works

## Batch 2 (Blocked)

### Phase 2.1: Team Composition
- **Status:** 🔴 Blocked
- **Depends On:** Phase 1.4
- **Tasks:**
  - [ ] Team sizing
- **Effort:** S
""")
        return roadmap

    def test_parse_roadmap_basic(self, sample_roadmap):
        """Test basic roadmap parsing."""
        streams = parse_roadmap(sample_roadmap)
        assert len(streams) == 3

    def test_parse_roadmap_statuses(self, sample_roadmap):
        """Test status parsing."""
        streams = parse_roadmap(sample_roadmap)
        by_id = {ws.id: ws for ws in streams}

        assert by_id["1.1"].status == WorkStreamStatus.COMPLETE
        assert by_id["1.2"].status == WorkStreamStatus.NOT_STARTED
        assert by_id["2.1"].status == WorkStreamStatus.BLOCKED

    def test_parse_roadmap_assigned(self, sample_roadmap):
        """Test assigned_to parsing."""
        streams = parse_roadmap(sample_roadmap)
        by_id = {ws.id: ws for ws in streams}

        assert by_id["1.1"].assigned_to == "Aurora"
        assert by_id["1.2"].assigned_to is None

    def test_parse_roadmap_tasks(self, sample_roadmap):
        """Test task parsing."""
        streams = parse_roadmap(sample_roadmap)
        by_id = {ws.id: ws for ws in streams}

        assert len(by_id["1.1"].tasks) == 2
        assert "Create project structure" in by_id["1.1"].tasks[0]

    def test_parse_roadmap_effort(self, sample_roadmap):
        """Test effort parsing."""
        streams = parse_roadmap(sample_roadmap)
        by_id = {ws.id: ws for ws in streams}

        assert by_id["1.1"].effort == "S"
        assert by_id["1.2"].effort == "M"

    def test_get_available_work_streams(self, sample_roadmap):
        """Test getting available work streams."""
        available = get_available_work_streams(sample_roadmap)
        assert len(available) == 1
        assert available[0].id == "1.2"

    def test_get_blocked_work_streams(self, sample_roadmap):
        """Test getting blocked work streams."""
        blocked = get_blocked_work_streams(sample_roadmap)
        assert len(blocked) == 1
        assert blocked[0].id == "2.1"

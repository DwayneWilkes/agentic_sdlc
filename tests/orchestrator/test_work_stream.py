"""Tests for the work stream parser."""


import pytest

from src.orchestrator.work_stream import (
    WorkStream,
    WorkStreamStatus,
    get_available_work_streams,
    get_blocked_work_streams,
    get_bootstrap_phases,
    get_prioritized_work_streams,
    parse_roadmap,
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


class TestPriorityParsing:
    """Tests for priority tag parsing and prioritization."""

    @pytest.fixture
    def priority_roadmap(self, tmp_path):
        """Create a roadmap with BOOTSTRAP priority tags."""
        roadmap = tmp_path / "roadmap.md"
        roadmap.write_text("""# Roadmap

## Batch 1 (Foundation)

### Phase 1.1: Core Data Models
- **Status:** ✅ Complete
- **Tasks:**
  - [✅] Create models
- **Effort:** S

### Phase 1.2: Task Parser
- **Status:** ⚪ Not Started
- **Tasks:**
  - [ ] Implement parser
- **Effort:** M

## Batch 2 (Development)

### Phase 2.3: Error Detection ⭐ BOOTSTRAP
- **Status:** ⚪ Not Started
- **Depends On:** Phase 1.1 ✅
- **Tasks:**
  - [ ] Detect errors
- **Effort:** S

### Phase 2.6: QA Verifier ⭐ BOOTSTRAP
- **Status:** ⚪ Not Started
- **Depends On:** Phase 1.1 ✅
- **Tasks:**
  - [ ] Verify quality
- **Effort:** M

### Phase 2.8: Stuck Detection ⭐ BOOTSTRAP
- **Status:** 🔴 Blocked
- **Depends On:** Phase 2.3
- **Tasks:**
  - [ ] Detect stuck agents
- **Effort:** M

## Batch 3 (Normal)

### Phase 3.1: Team Composition
- **Status:** ⚪ Not Started
- **Tasks:**
  - [ ] Compose teams
- **Effort:** S
""")
        return roadmap

    def test_parse_bootstrap_priority(self, priority_roadmap):
        """Test that BOOTSTRAP tag is parsed correctly."""
        streams = parse_roadmap(priority_roadmap)
        by_id = {ws.id: ws for ws in streams}

        # Bootstrap phases
        assert by_id["2.3"].priority == "bootstrap"
        assert by_id["2.3"].is_bootstrap is True
        assert by_id["2.6"].priority == "bootstrap"
        assert by_id["2.6"].is_bootstrap is True
        assert by_id["2.8"].priority == "bootstrap"
        assert by_id["2.8"].is_bootstrap is True

        # Normal phases (no tag)
        assert by_id["1.1"].priority == "normal"
        assert by_id["1.1"].is_bootstrap is False
        assert by_id["1.2"].priority == "normal"
        assert by_id["3.1"].priority == "normal"

    def test_str_shows_bootstrap_marker(self, priority_roadmap):
        """Test that __str__ shows star for bootstrap phases."""
        streams = parse_roadmap(priority_roadmap)
        by_id = {ws.id: ws for ws in streams}

        # Bootstrap phase should show star
        assert "⭐" in str(by_id["2.3"])

        # Normal phase should not show star
        assert "⭐" not in str(by_id["1.2"])

    def test_get_bootstrap_phases(self, priority_roadmap):
        """Test getting claimable bootstrap phases."""
        bootstrap = get_bootstrap_phases(priority_roadmap)

        # Should only include claimable bootstrap phases (not blocked 2.8)
        assert len(bootstrap) == 2
        ids = [ws.id for ws in bootstrap]
        assert "2.3" in ids
        assert "2.6" in ids
        assert "2.8" not in ids  # Blocked

    def test_get_prioritized_work_streams(self, priority_roadmap):
        """Test that prioritized work streams puts bootstrap first."""
        prioritized = get_prioritized_work_streams(priority_roadmap)

        # Should have bootstrap phases first, then normal
        ids = [ws.id for ws in prioritized]

        # Bootstrap phases (2.3, 2.6) should come before normal phases (1.2, 3.1)
        bootstrap_indices = [ids.index("2.3"), ids.index("2.6")]
        normal_indices = [ids.index("1.2"), ids.index("3.1")]

        assert max(bootstrap_indices) < min(normal_indices), \
            f"Bootstrap phases should come first. Got order: {ids}"

    def test_prioritized_maintains_batch_order_within_priority(self, priority_roadmap):
        """Test that within same priority, phases are sorted by batch then ID."""
        prioritized = get_prioritized_work_streams(priority_roadmap)
        ids = [ws.id for ws in prioritized]

        # Within bootstrap: 2.3 should come before 2.6 (same batch, lower ID)
        assert ids.index("2.3") < ids.index("2.6")

        # Within normal: 1.2 should come before 3.1 (lower batch)
        assert ids.index("1.2") < ids.index("3.1")

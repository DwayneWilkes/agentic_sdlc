"""Tests for the RoadmapGardener module."""

import pytest
from unittest.mock import patch, MagicMock

from src.orchestrator.roadmap_gardener import (
    RoadmapGardener,
    get_gardener,
    garden_roadmap,
    check_roadmap_health,
)
from src.orchestrator.work_stream import (
    clear_roadmap_cache,
)


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure with roadmap."""
    plans_dir = tmp_path / "plans"
    plans_dir.mkdir()
    completed_dir = plans_dir / "completed"
    completed_dir.mkdir()

    return tmp_path


@pytest.fixture
def sample_roadmap_content():
    """Sample roadmap content for testing."""
    return """\
# Implementation Roadmap

## Batch 1 - Foundation

### Phase 1.1: Core Data Models
- **Status:** ✅ Complete
- **Assigned To:** Alice
- **Depends On:** -
- **Effort:** M
- **Done When:** Tests pass
- **Tasks:**
  - [x] Create Task model
  - [x] Create Agent model

### Phase 1.2: Task Parser
- **Status:** ✅ Complete
- **Assigned To:** Bob
- **Depends On:** Phase 1.1
- **Effort:** M
- **Done When:** Parser works
- **Tasks:**
  - [x] Implement parser
  - [x] Add tests

### Phase 1.3: Task Decomposer
- **Status:** 🔄 In Progress
- **Assigned To:** Carol
- **Depends On:** Phase 1.2
- **Effort:** L
- **Done When:** Decomposer works
- **Tasks:**
  - [ ] Implement decomposer
  - [ ] Add tests

### Phase 1.4: Team Composition
- **Status:** 🔴 Blocked
- **Assigned To:** -
- **Depends On:** Phase 1.3
- **Effort:** M
- **Done When:** Team composition works
- **Tasks:**
  - [ ] Design team structure
  - [ ] Implement selection

## Batch 2 - Advanced

### Phase 2.1: Parallel Execution
- **Status:** 🔴 Blocked
- **Assigned To:** -
- **Depends On:** Phase 1.2, Phase 1.3
- **Effort:** L
- **Done When:** Parallel works
- **Tasks:**
  - [ ] Implement parallel execution

### Phase 2.2: Coordination
- **Status:** ⚪ Not Started
- **Assigned To:** -
- **Depends On:** -
- **Effort:** M
- **Done When:** Coordination works
- **Tasks:**
  - [ ] Implement coordination
"""


@pytest.fixture
def roadmap_with_blocked_no_deps():
    """Roadmap with a blocked phase that has no dependencies."""
    return """\
# Roadmap

## Batch 1

### Phase 1.1: First Phase
- **Status:** ✅ Complete
- **Assigned To:** Alice
- **Depends On:** -
- **Effort:** M
- **Tasks:**
  - [x] Task 1

### Phase 1.2: Blocked No Deps
- **Status:** 🔴 Blocked
- **Assigned To:** -
- **Depends On:** -
- **Effort:** M
- **Tasks:**
  - [ ] Task 1
"""


@pytest.fixture
def roadmap_with_satisfied_deps():
    """Roadmap with a blocked phase whose dependencies are satisfied."""
    return """\
# Roadmap

## Batch 1

### Phase 1.1: First Phase
- **Status:** ✅ Complete
- **Assigned To:** Alice
- **Depends On:** -
- **Effort:** M
- **Tasks:**
  - [x] Task 1

### Phase 1.2: Second Phase
- **Status:** ✅ Complete
- **Assigned To:** Bob
- **Depends On:** Phase 1.1
- **Effort:** M
- **Tasks:**
  - [x] Task 1

### Phase 1.3: Should Unblock
- **Status:** 🔴 Blocked
- **Assigned To:** -
- **Depends On:** Phase 1.1, Phase 1.2
- **Effort:** M
- **Tasks:**
  - [ ] Task 1
"""


class TestRoadmapGardenerInit:
    """Tests for RoadmapGardener initialization."""

    def test_init_with_default_path(self):
        """Test initialization with default project root."""
        gardener = RoadmapGardener()
        assert gardener.project_root.exists()
        assert gardener.roadmap_path.name == "roadmap.md"
        assert gardener.archive_path.name == "roadmap-archive.md"

    def test_init_with_custom_path(self, temp_project):
        """Test initialization with custom project root."""
        gardener = RoadmapGardener(project_root=temp_project)
        assert gardener.project_root == temp_project
        assert gardener.roadmap_path == temp_project / "plans" / "roadmap.md"
        assert gardener.archive_path == temp_project / "plans" / "completed" / "roadmap-archive.md"


class TestParseDependencies:
    """Tests for _parse_dependencies method."""

    def test_parse_single_dependency(self, temp_project, sample_roadmap_content):
        """Test parsing a single dependency."""
        (temp_project / "plans" / "roadmap.md").write_text(sample_roadmap_content)
        gardener = RoadmapGardener(project_root=temp_project)

        deps = gardener._parse_dependencies("Phase 1.1")
        assert deps == ["1.1"]

    def test_parse_multiple_dependencies_comma(self, temp_project, sample_roadmap_content):
        """Test parsing multiple dependencies separated by comma."""
        (temp_project / "plans" / "roadmap.md").write_text(sample_roadmap_content)
        gardener = RoadmapGardener(project_root=temp_project)

        deps = gardener._parse_dependencies("Phase 1.1, Phase 1.2")
        assert deps == ["1.1", "1.2"]

    def test_parse_multiple_dependencies_semicolon(self, temp_project, sample_roadmap_content):
        """Test parsing multiple dependencies separated by semicolon."""
        (temp_project / "plans" / "roadmap.md").write_text(sample_roadmap_content)
        gardener = RoadmapGardener(project_root=temp_project)

        deps = gardener._parse_dependencies("Phase 1.1; Phase 1.2")
        assert deps == ["1.1", "1.2"]

    def test_parse_dependency_with_checkmark(self, temp_project, sample_roadmap_content):
        """Test parsing dependency with checkmark symbol."""
        (temp_project / "plans" / "roadmap.md").write_text(sample_roadmap_content)
        gardener = RoadmapGardener(project_root=temp_project)

        deps = gardener._parse_dependencies("Phase 1.1 ✅")
        assert deps == ["1.1"]

    def test_parse_dependency_without_phase_prefix(self, temp_project, sample_roadmap_content):
        """Test parsing dependency without 'Phase' prefix."""
        (temp_project / "plans" / "roadmap.md").write_text(sample_roadmap_content)
        gardener = RoadmapGardener(project_root=temp_project)

        deps = gardener._parse_dependencies("1.1, 1.2")
        assert deps == ["1.1", "1.2"]

    def test_parse_empty_dependencies(self, temp_project, sample_roadmap_content):
        """Test parsing empty dependency string."""
        (temp_project / "plans" / "roadmap.md").write_text(sample_roadmap_content)
        gardener = RoadmapGardener(project_root=temp_project)

        deps = gardener._parse_dependencies("")
        assert deps == []


class TestGarden:
    """Tests for the garden method."""

    def test_garden_unblocks_phase_with_no_deps(self, temp_project):
        """Test that garden unblocks phases with no dependencies (None, not '-')."""
        # Create roadmap where depends_on is truly None (no Depends On line parsed)
        roadmap_content = """\
# Roadmap

## Batch 1

### Phase 1.1: First Phase
- **Status:** ✅ Complete
- **Assigned To:** Alice
- **Effort:** M
- **Tasks:**
  - [x] Task 1

### Phase 1.2: Blocked No Deps
- **Status:** 🔴 Blocked
- **Assigned To:** -
- **Effort:** M
- **Tasks:**
  - [ ] Task 1
"""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_content)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        results = gardener.garden()

        assert len(results["unblocked"]) == 1
        assert results["unblocked"][0]["id"] == "1.2"
        assert results["unblocked"][0]["reason"] == "No dependencies listed"

        # Verify roadmap was updated
        updated_content = roadmap_path.read_text()
        assert "⚪ Not Started" in updated_content
        assert "🔴 Blocked" not in updated_content

    def test_garden_unblocks_phase_with_dash_deps(self, temp_project, roadmap_with_blocked_no_deps):
        """Test that garden unblocks phases with '-' as dependencies (treated as empty)."""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_with_blocked_no_deps)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        results = gardener.garden()

        # '-' parses to empty deps list, so all deps are "satisfied"
        assert len(results["unblocked"]) == 1
        assert results["unblocked"][0]["id"] == "1.2"
        assert results["unblocked"][0]["reason"] == "All dependencies completed"

        # Verify roadmap was updated
        updated_content = roadmap_path.read_text()
        assert "⚪ Not Started" in updated_content
        assert "🔴 Blocked" not in updated_content

    def test_garden_unblocks_phase_with_satisfied_deps(self, temp_project, roadmap_with_satisfied_deps):
        """Test that garden unblocks phases whose dependencies are complete."""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_with_satisfied_deps)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        results = gardener.garden()

        assert len(results["unblocked"]) == 1
        assert results["unblocked"][0]["id"] == "1.3"
        assert results["unblocked"][0]["reason"] == "All dependencies completed"

    def test_garden_keeps_phase_blocked_with_unmet_deps(self, temp_project, sample_roadmap_content):
        """Test that garden keeps phases blocked when dependencies aren't met."""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(sample_roadmap_content)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        results = gardener.garden()

        # Phase 1.4 depends on 1.3 which is in progress
        still_blocked = [b for b in results["still_blocked"] if b["id"] == "1.4"]
        assert len(still_blocked) == 1
        assert "1.3" in still_blocked[0]["pending_deps"]

    def test_garden_returns_empty_when_no_blocked(self, temp_project):
        """Test garden with no blocked phases."""
        roadmap_content = """\
# Roadmap

## Batch 1

### Phase 1.1: First Phase
- **Status:** ✅ Complete
- **Assigned To:** Alice
- **Depends On:** -
- **Effort:** M
- **Tasks:**
  - [x] Task 1

### Phase 1.2: Second Phase
- **Status:** ⚪ Not Started
- **Assigned To:** -
- **Depends On:** Phase 1.1
- **Effort:** M
- **Tasks:**
  - [ ] Task 1
"""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_content)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        results = gardener.garden()

        assert results["unblocked"] == []
        assert results["still_blocked"] == []
        assert results["errors"] == []


class TestApplyUnblocks:
    """Tests for the _apply_unblocks method."""

    def test_apply_unblocks_updates_roadmap(self, temp_project, roadmap_with_blocked_no_deps):
        """Test that _apply_unblocks correctly updates the roadmap file."""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_with_blocked_no_deps)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)

        unblocked = [{"id": "1.2", "name": "Blocked No Deps", "reason": "No deps"}]
        gardener._apply_unblocks(unblocked)

        updated = roadmap_path.read_text()
        assert "⚪ Not Started" in updated
        assert "🔴 Blocked" not in updated


class TestCheckHealth:
    """Tests for the check_health method."""

    def test_check_health_returns_status_counts(self, temp_project, sample_roadmap_content):
        """Test that check_health returns correct status counts."""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(sample_roadmap_content)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        health = gardener.check_health()

        assert health["total_phases"] == 6
        assert "complete" in health["by_status"]
        assert len(health["by_status"]["complete"]) == 2  # 1.1 and 1.2 are complete
        assert "in_progress" in health["by_status"]
        assert len(health["by_status"]["in_progress"]) == 1  # 1.3 is in progress

    def test_check_health_detects_blocked_no_deps_issue(self, temp_project):
        """Test that check_health detects phases blocked with no dependencies (None)."""
        # Create roadmap where depends_on is truly None (no Depends On line)
        roadmap_content = """\
# Roadmap

## Batch 1

### Phase 1.1: First Phase
- **Status:** ✅ Complete
- **Assigned To:** Alice
- **Effort:** M
- **Tasks:**
  - [x] Task 1

### Phase 1.2: Blocked No Deps
- **Status:** 🔴 Blocked
- **Assigned To:** -
- **Effort:** M
- **Tasks:**
  - [ ] Task 1
"""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_content)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        health = gardener.check_health()

        assert any("1.2" in issue and "no dependencies" in issue for issue in health["issues"])

    def test_check_health_detects_should_be_unblocked(self, temp_project, roadmap_with_satisfied_deps):
        """Test that check_health detects phases that should be unblocked."""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_with_satisfied_deps)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        health = gardener.check_health()

        assert any("1.3" in issue and "should be unblocked" in issue for issue in health["issues"])

    def test_check_health_reports_available_for_work(self, temp_project, sample_roadmap_content):
        """Test that check_health reports available work streams."""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(sample_roadmap_content)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        health = gardener.check_health()

        # Phase 2.2 is not started with no deps
        assert health["available_for_work"] >= 1


class TestGetNextPhases:
    """Tests for the get_next_phases method."""

    def test_get_next_phases_gardens_first(self, temp_project, roadmap_with_satisfied_deps):
        """Test that get_next_phases gardens the roadmap before returning."""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_with_satisfied_deps)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)

        # Phase 1.3 should be unblocked and returned
        next_phases = gardener.get_next_phases()

        # Should have at least Phase 1.3 available now
        phase_ids = [ws.id for ws in next_phases]
        assert "1.3" in phase_ids

    def test_get_next_phases_returns_prioritized(self, temp_project):
        """Test that get_next_phases returns bootstrap phases first."""
        roadmap_content = """\
# Roadmap

## Batch 1

### Phase 1.1: Normal Phase
- **Status:** ⚪ Not Started
- **Assigned To:** -
- **Depends On:** -
- **Effort:** M
- **Tasks:**
  - [ ] Task 1

### Phase 1.2: Bootstrap Phase ⭐ BOOTSTRAP
- **Status:** ⚪ Not Started
- **Assigned To:** -
- **Depends On:** -
- **Effort:** M
- **Tasks:**
  - [ ] Task 1
"""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_content)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        next_phases = gardener.get_next_phases()

        # Bootstrap should come first
        assert len(next_phases) >= 2
        assert next_phases[0].id == "1.2"  # Bootstrap first
        assert next_phases[0].is_bootstrap


class TestSingletonAndConvenienceFunctions:
    """Tests for get_gardener and convenience functions."""

    def test_get_gardener_returns_singleton(self):
        """Test that get_gardener returns the same instance."""
        # Reset the singleton
        import src.orchestrator.roadmap_gardener as module
        module._gardener = None

        gardener1 = get_gardener()
        gardener2 = get_gardener()

        assert gardener1 is gardener2

    def test_garden_roadmap_convenience(self, temp_project, roadmap_with_blocked_no_deps):
        """Test the garden_roadmap convenience function."""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_with_blocked_no_deps)

        clear_roadmap_cache()

        # Use a mocked gardener
        import src.orchestrator.roadmap_gardener as module

        mock_gardener = MagicMock()
        mock_gardener.garden.return_value = {"unblocked": [], "still_blocked": [], "errors": []}

        with patch.object(module, '_gardener', mock_gardener):
            garden_roadmap()  # Result intentionally unused - testing side effect

        mock_gardener.garden.assert_called_once()

    def test_check_roadmap_health_convenience(self):
        """Test the check_roadmap_health convenience function."""
        import src.orchestrator.roadmap_gardener as module

        mock_gardener = MagicMock()
        mock_gardener.check_health.return_value = {
            "total_phases": 5,
            "by_status": {},
            "issues": [],
            "available_for_work": 2,
        }

        with patch.object(module, '_gardener', mock_gardener):
            result = check_roadmap_health()

        mock_gardener.check_health.assert_called_once()
        assert result["total_phases"] == 5


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_garden_with_dependency_checkmark_in_string(self, temp_project):
        """Test garden correctly handles ✅ in dependency string."""
        roadmap_content = """\
# Roadmap

## Batch 1

### Phase 1.1: First Phase
- **Status:** ✅ Complete
- **Assigned To:** Alice
- **Depends On:** -
- **Effort:** M
- **Tasks:**
  - [x] Task 1

### Phase 1.2: Second Phase
- **Status:** 🔴 Blocked
- **Assigned To:** -
- **Depends On:** Phase 1.1 ✅
- **Effort:** M
- **Tasks:**
  - [ ] Task 1
"""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_content)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        results = gardener.garden()

        # Should unblock because ✅ indicates dependency is satisfied
        assert len(results["unblocked"]) == 1
        assert results["unblocked"][0]["id"] == "1.2"

    def test_garden_with_mixed_dependency_formats(self, temp_project):
        """Test garden handles mixed dependency formats."""
        roadmap_content = """\
# Roadmap

## Batch 1

### Phase 1.1: First Phase
- **Status:** ✅ Complete
- **Assigned To:** Alice
- **Depends On:** -
- **Effort:** M
- **Tasks:**
  - [x] Task 1

### Phase 1.2: Second Phase
- **Status:** ✅ Complete
- **Assigned To:** Bob
- **Depends On:** 1.1
- **Effort:** M
- **Tasks:**
  - [x] Task 1

### Phase 1.3: Third Phase
- **Status:** 🔴 Blocked
- **Assigned To:** -
- **Depends On:** Phase 1.1; 1.2
- **Effort:** M
- **Tasks:**
  - [ ] Task 1
"""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_content)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        results = gardener.garden()

        # Both deps are complete, should unblock
        assert len(results["unblocked"]) == 1
        assert results["unblocked"][0]["id"] == "1.3"

    def test_check_health_with_empty_roadmap(self, temp_project):
        """Test check_health with minimal roadmap."""
        roadmap_content = """\
# Roadmap

No phases defined yet.
"""
        roadmap_path = temp_project / "plans" / "roadmap.md"
        roadmap_path.write_text(roadmap_content)

        clear_roadmap_cache()
        gardener = RoadmapGardener(project_root=temp_project)
        health = gardener.check_health()

        assert health["total_phases"] == 0
        assert health["available_for_work"] == 0
        assert health["issues"] == []

"""
Roadmap Gardener - Maintains roadmap health by auto-updating blockers.

Responsibilities:
- Check dependency completion status
- Unblock phases when dependencies are met
- Archive completed phases (optional)
- Validate roadmap consistency
"""

import re
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.orchestrator.work_stream import (
    parse_roadmap,
    clear_roadmap_cache,
    WorkStream,
    WorkStreamStatus,
)


class RoadmapGardener:
    """
    Maintains roadmap health by auto-updating blockers and archiving completed phases.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the roadmap gardener.

        Args:
            project_root: Root of the project. Defaults to auto-detect.
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent

        self.project_root = project_root
        self.roadmap_path = project_root / "plans" / "roadmap.md"
        self.archive_path = project_root / "plans" / "completed" / "roadmap-archive.md"

    def garden(self) -> dict:
        """
        Perform all gardening tasks on the roadmap.

        Returns:
            Dictionary with results of gardening actions
        """
        results = {
            "unblocked": [],
            "still_blocked": [],
            "errors": [],
        }

        # Refresh cache
        clear_roadmap_cache()

        # Get all work streams
        all_streams = parse_roadmap(self.roadmap_path)

        # Build completion map
        completed_phases = {
            ws.id for ws in all_streams
            if ws.status == WorkStreamStatus.COMPLETE
        }

        # Check blocked phases
        blocked_streams = [
            ws for ws in all_streams
            if ws.status == WorkStreamStatus.BLOCKED
        ]

        for ws in blocked_streams:
            if not ws.depends_on:
                # No dependencies listed but blocked - unblock it
                results["unblocked"].append({
                    "id": ws.id,
                    "name": ws.name,
                    "reason": "No dependencies listed",
                })
                continue

            # Parse dependencies
            deps = self._parse_dependencies(ws.depends_on)
            all_satisfied = all(
                dep in completed_phases or "✅" in dep
                for dep in deps
            )

            if all_satisfied:
                results["unblocked"].append({
                    "id": ws.id,
                    "name": ws.name,
                    "dependencies": deps,
                    "reason": "All dependencies completed",
                })
            else:
                pending = [d for d in deps if d not in completed_phases and "✅" not in d]
                results["still_blocked"].append({
                    "id": ws.id,
                    "name": ws.name,
                    "pending_deps": pending,
                })

        # Apply changes to roadmap
        if results["unblocked"]:
            self._apply_unblocks(results["unblocked"])

        return results

    def _parse_dependencies(self, depends_on: str) -> list[str]:
        """Parse dependencies string into list of phase IDs."""
        # Handle formats like "Phase 1.4", "Phase 1.4 ✅", "Phase 1.4, Phase 2.1"
        deps = []
        parts = re.split(r"[,;]", depends_on)
        for part in parts:
            part = part.strip()
            # Extract phase ID
            match = re.search(r"(?:Phase\s+)?(\d+\.\d+)", part)
            if match:
                deps.append(match.group(1))
        return deps

    def _apply_unblocks(self, unblocked: list[dict]) -> None:
        """Apply unblock changes to roadmap file."""
        content = self.roadmap_path.read_text()

        for item in unblocked:
            phase_id = item["id"]

            # Find and replace status for this phase
            # Pattern: After "### Phase X.X:" find "- **Status:** 🔴 Blocked"
            pattern = rf"(### Phase {re.escape(phase_id)}:.*?- \*\*Status:\*\*) 🔴 Blocked"
            replacement = r"\1 ⚪ Not Started"
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        self.roadmap_path.write_text(content)
        clear_roadmap_cache()

    def check_health(self) -> dict:
        """
        Check roadmap health without making changes.

        Returns:
            Dictionary with health report
        """
        clear_roadmap_cache()
        all_streams = parse_roadmap(self.roadmap_path)

        by_status = {}
        for ws in all_streams:
            status = ws.status.value
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(ws.id)

        # Check for issues
        issues = []

        # Issue: Blocked with no dependencies
        for ws in all_streams:
            if ws.status == WorkStreamStatus.BLOCKED and not ws.depends_on:
                issues.append(f"Phase {ws.id} is blocked but has no dependencies listed")

        # Issue: Dependencies satisfied but still blocked
        completed = {ws.id for ws in all_streams if ws.status == WorkStreamStatus.COMPLETE}
        for ws in all_streams:
            if ws.status == WorkStreamStatus.BLOCKED and ws.depends_on:
                deps = self._parse_dependencies(ws.depends_on)
                all_met = all(d in completed or "✅" in ws.depends_on for d in deps)
                if all_met:
                    issues.append(f"Phase {ws.id} should be unblocked - dependencies satisfied")

        return {
            "total_phases": len(all_streams),
            "by_status": by_status,
            "issues": issues,
            "available_for_work": len([ws for ws in all_streams if ws.is_claimable]),
        }

    def get_next_phases(self) -> list[WorkStream]:
        """
        Get phases that are ready to work on.

        Returns:
            List of claimable work streams
        """
        # First, garden the roadmap
        self.garden()

        # Then return available work
        all_streams = parse_roadmap(self.roadmap_path)
        return [ws for ws in all_streams if ws.is_claimable]


# Singleton instance
_gardener: Optional[RoadmapGardener] = None


def get_gardener() -> RoadmapGardener:
    """Get the global roadmap gardener instance."""
    global _gardener
    if _gardener is None:
        _gardener = RoadmapGardener()
    return _gardener


def garden_roadmap() -> dict:
    """Convenience function to garden the roadmap."""
    return get_gardener().garden()


def check_roadmap_health() -> dict:
    """Convenience function to check roadmap health."""
    return get_gardener().check_health()

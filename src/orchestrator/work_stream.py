"""
Work Stream Parser - Extracts work streams from roadmap.md

Parses the roadmap to identify:
- Available work streams (not started, not blocked)
- In-progress work streams
- Completed work streams
- Blocked work streams and their dependencies

Optimizations:
- Caches parsed roadmap with file modification time check
- Pre-compiled regex patterns
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Pre-compiled regex patterns for efficiency
_BATCH_PATTERN = re.compile(r"^## Batch (\d+)")
# Captures phase ID, name, and optional priority tag (e.g., "⭐ BOOTSTRAP")
_PHASE_PATTERN = re.compile(r"^### Phase (\d+\.\d+): (.+?)(?:\s+⭐\s*(\w+))?$")
_TASK_PATTERN = re.compile(r"\s*-\s*\[(.?)\]\s*(.+)")

# Cache for parsed roadmap
_roadmap_cache: dict[Path, tuple[float, list["WorkStream"]]] = {}


class WorkStreamStatus(str, Enum):
    """Status of a work stream."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"


@dataclass
class WorkStream:
    """A work stream from the roadmap."""

    id: str  # e.g., "1.2", "2.1"
    name: str  # e.g., "Task Parser and Goal Extraction"
    status: WorkStreamStatus
    tasks: list[str] = field(default_factory=list)
    assigned_to: str | None = None
    depends_on: str | None = None
    effort: str = "M"
    done_when: str | None = None
    batch: int = 1
    priority: str = "normal"  # "bootstrap" for force-multiplier phases, "normal" otherwise

    @property
    def is_bootstrap(self) -> bool:
        """Check if this is a bootstrap (force-multiplier) phase."""
        return self.priority.lower() == "bootstrap"

    @property
    def is_available(self) -> bool:
        """Check if work stream can be claimed."""
        return self.status == WorkStreamStatus.NOT_STARTED

    @property
    def is_claimable(self) -> bool:
        """Check if work stream can be claimed (not started or in progress but unassigned)."""
        if self.status == WorkStreamStatus.NOT_STARTED:
            return True
        if self.status == WorkStreamStatus.IN_PROGRESS and not self.assigned_to:
            return True
        return False

    def __str__(self) -> str:
        status_emoji = {
            WorkStreamStatus.NOT_STARTED: "⚪",
            WorkStreamStatus.IN_PROGRESS: "🔄",
            WorkStreamStatus.COMPLETE: "✅",
            WorkStreamStatus.BLOCKED: "🔴",
        }
        priority_marker = " ⭐" if self.is_bootstrap else ""
        return f"[{status_emoji[self.status]}] Phase {self.id}: {self.name}{priority_marker}"


def parse_roadmap(roadmap_path: Path | None = None, use_cache: bool = True) -> list[WorkStream]:
    """
    Parse the roadmap.md file to extract work streams.

    Args:
        roadmap_path: Path to roadmap.md. Defaults to plans/roadmap.md
        use_cache: Whether to use cached results if available

    Returns:
        List of WorkStream objects
    """
    if roadmap_path is None:
        project_root = Path(__file__).parent.parent.parent
        roadmap_path = project_root / "plans" / "roadmap.md"

    roadmap_path = roadmap_path.resolve()

    if not roadmap_path.exists():
        raise FileNotFoundError(f"Roadmap not found: {roadmap_path}")

    # Check cache
    mtime = roadmap_path.stat().st_mtime
    if use_cache and roadmap_path in _roadmap_cache:
        cached_mtime, cached_streams = _roadmap_cache[roadmap_path]
        if cached_mtime == mtime:
            return cached_streams

    content = roadmap_path.read_text()
    work_streams = []
    current_batch = 1

    # Split into sections by "## Batch" or "### Phase"
    lines = content.split("\n")
    current_stream: dict | None = None
    in_tasks = False

    for line in lines:
        # Detect batch headers (use pre-compiled pattern)
        batch_match = _BATCH_PATTERN.match(line)
        if batch_match:
            current_batch = int(batch_match.group(1))
            continue

        # Detect phase headers (use pre-compiled pattern)
        phase_match = _PHASE_PATTERN.match(line)
        if phase_match:
            # Save previous stream if exists
            if current_stream:
                work_streams.append(_create_work_stream(current_stream))

            # Extract priority tag if present (group 3 captures "BOOTSTRAP", "PRIORITY", etc.)
            priority_tag = phase_match.group(3)
            priority = priority_tag.lower() if priority_tag else "normal"

            current_stream = {
                "id": phase_match.group(1),
                "name": phase_match.group(2).strip(),
                "batch": current_batch,
                "tasks": [],
                "status": WorkStreamStatus.NOT_STARTED,
                "assigned_to": None,
                "depends_on": None,
                "effort": "M",
                "done_when": None,
                "priority": priority,
            }
            in_tasks = False
            continue

        if not current_stream:
            continue

        # Parse status
        if line.startswith("- **Status:**"):
            status_text = line.split(":**")[1].strip()
            if "✅" in status_text or "Complete" in status_text:
                current_stream["status"] = WorkStreamStatus.COMPLETE
            elif "🔄" in status_text or "In Progress" in status_text:
                current_stream["status"] = WorkStreamStatus.IN_PROGRESS
            elif "🔴" in status_text or "Blocked" in status_text:
                current_stream["status"] = WorkStreamStatus.BLOCKED
            else:
                current_stream["status"] = WorkStreamStatus.NOT_STARTED
            continue

        # Parse assigned to
        if line.startswith("- **Assigned To:**"):
            assigned = line.split(":**")[1].strip()
            if assigned and assigned != "-":
                current_stream["assigned_to"] = assigned
            continue

        # Parse depends on
        if line.startswith("- **Depends On:**"):
            depends = line.split(":**")[1].strip()
            if depends:
                current_stream["depends_on"] = depends
            continue

        # Parse effort
        if line.startswith("- **Effort:**"):
            effort = line.split(":**")[1].strip()
            current_stream["effort"] = effort
            continue

        # Parse done when
        if line.startswith("- **Done When:**"):
            done_when = line.split(":**")[1].strip()
            current_stream["done_when"] = done_when
            continue

        # Parse tasks section
        if line.startswith("- **Tasks:**"):
            in_tasks = True
            continue

        # Parse individual tasks (use pre-compiled pattern)
        if in_tasks and line.strip().startswith("- ["):
            task_match = _TASK_PATTERN.match(line)
            if task_match:
                task_text = task_match.group(2).strip()
                current_stream["tasks"].append(task_text)
            continue

        # End of tasks section
        if in_tasks and line.startswith("- **"):
            in_tasks = False

    # Don't forget the last stream
    if current_stream:
        work_streams.append(_create_work_stream(current_stream))

    # Update cache
    _roadmap_cache[roadmap_path] = (mtime, work_streams)

    return work_streams


def clear_roadmap_cache() -> None:
    """Clear the roadmap cache (useful for testing or after edits)."""
    _roadmap_cache.clear()


def _create_work_stream(data: dict) -> WorkStream:
    """Create a WorkStream from parsed data."""
    return WorkStream(
        id=data["id"],
        name=data["name"],
        status=data["status"],
        tasks=data["tasks"],
        assigned_to=data["assigned_to"],
        depends_on=data["depends_on"],
        effort=data["effort"],
        done_when=data["done_when"],
        batch=data["batch"],
        priority=data.get("priority", "normal"),
    )


def get_available_work_streams(roadmap_path: Path | None = None) -> list[WorkStream]:
    """
    Get work streams that are available to be claimed.

    Returns work streams that are:
    - Not started and not blocked
    - In progress but not assigned
    """
    all_streams = parse_roadmap(roadmap_path)
    return [ws for ws in all_streams if ws.is_claimable]


def get_blocked_work_streams(roadmap_path: Path | None = None) -> list[WorkStream]:
    """Get work streams that are blocked."""
    all_streams = parse_roadmap(roadmap_path)
    return [ws for ws in all_streams if ws.status == WorkStreamStatus.BLOCKED]


def get_in_progress_work_streams(roadmap_path: Path | None = None) -> list[WorkStream]:
    """Get work streams that are in progress."""
    all_streams = parse_roadmap(roadmap_path)
    return [ws for ws in all_streams if ws.status == WorkStreamStatus.IN_PROGRESS]


def get_completed_work_streams(roadmap_path: Path | None = None) -> list[WorkStream]:
    """Get completed work streams."""
    all_streams = parse_roadmap(roadmap_path)
    return [ws for ws in all_streams if ws.status == WorkStreamStatus.COMPLETE]


def get_bootstrap_phases(roadmap_path: Path | None = None) -> list[WorkStream]:
    """
    Get BOOTSTRAP phases that are available to work on.

    Returns claimable bootstrap phases sorted by batch number.
    These are force-multiplier phases that improve all subsequent work.
    """
    all_streams = parse_roadmap(roadmap_path)
    bootstrap = [ws for ws in all_streams if ws.is_bootstrap and ws.is_claimable]
    return sorted(bootstrap, key=lambda ws: (ws.batch, ws.id))


def get_prioritized_work_streams(roadmap_path: Path | None = None) -> list[WorkStream]:
    """
    Get available work streams sorted by priority.

    Bootstrap phases come first, then normal phases.
    Within each priority level, sorted by batch then phase ID.

    Returns:
        List of claimable work streams, bootstrap phases first
    """
    all_streams = parse_roadmap(roadmap_path)
    claimable = [ws for ws in all_streams if ws.is_claimable]

    # Sort: bootstrap first (0), then normal (1), then by batch and ID
    return sorted(
        claimable,
        key=lambda ws: (0 if ws.is_bootstrap else 1, ws.batch, ws.id)
    )

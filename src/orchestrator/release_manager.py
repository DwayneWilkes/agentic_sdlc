"""
Release Manager Agent (Phase 6.4).

Coordinates merges, prevents conflicts, tracks rollback info,
aggregates release notes, and manages staged deployments.

Implementation follows TDD approach with 36 tests written first.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

# ============================================================================
# Enums
# ============================================================================


class MergeReadinessStatus(str, Enum):
    """Status of merge readiness assessment."""
    READY = "ready"
    NOT_READY = "not_ready"
    WARNING = "warning"


class ConflictType(str, Enum):
    """Types of conflicts that can be detected."""
    FILE = "file"  # Git merge conflict
    SEMANTIC = "semantic"  # Same function/area modified in parallel


class ChangeCategory(str, Enum):
    """Categories for release notes."""
    FEATURE = "feature"
    FIX = "fix"
    BREAKING = "breaking"
    REFACTOR = "refactor"
    DOCS = "docs"
    TESTS = "tests"
    CHORE = "chore"


class DeploymentStage(str, Enum):
    """Deployment stages for progressive rollout."""
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class PRInfo:
    """Information about a pull request."""
    number: int
    title: str
    branch: str
    author: str
    tests_passing: bool
    coverage: float
    review_count: int
    has_conflicts: bool
    files_changed: list[str]
    additions: int
    deletions: int
    depends_on: list[int] = field(default_factory=list)
    conflicting_files: list[str] = field(default_factory=list)


@dataclass
class MergeReadiness:
    """Assessment of whether a PR is ready to merge."""
    pr_number: int
    status: MergeReadinessStatus
    tests_passing: bool
    coverage_met: bool
    reviews_met: bool
    no_conflicts: bool
    blocking_issues: list[str] = field(default_factory=list)


@dataclass
class Conflict:
    """Represents a merge conflict."""
    conflict_type: ConflictType
    file_path: str
    pr_numbers: list[int]
    description: str


@dataclass
class RollbackPlan:
    """Information needed to rollback a release."""
    commit_hash: str
    pr_number: int | None
    affected_files: list[str]
    revert_command: str
    commits: list[str] = field(default_factory=list)
    dependent_prs: list[int] = field(default_factory=list)


@dataclass
class ReleaseNotes:
    """Aggregated release notes from multiple PRs."""
    version: str
    features: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)
    breaking_changes: list[str] = field(default_factory=list)
    refactors: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    chores: list[str] = field(default_factory=list)

    def format_markdown(self) -> str:
        """Format release notes as Markdown."""
        sections = []

        if self.breaking_changes:
            sections.append("## ⚠️ Breaking Changes\n")
            sections.extend(f"- {change}" for change in self.breaking_changes)
            sections.append("")

        if self.features:
            sections.append("## ✨ Features\n")
            sections.extend(f"- {feat}" for feat in self.features)
            sections.append("")

        if self.fixes:
            sections.append("## 🐛 Bug Fixes\n")
            sections.extend(f"- {fix}" for fix in self.fixes)
            sections.append("")

        if self.refactors:
            sections.append("## ♻️ Refactoring\n")
            sections.extend(f"- {ref}" for ref in self.refactors)
            sections.append("")

        if self.docs:
            sections.append("## 📝 Documentation\n")
            sections.extend(f"- {doc}" for doc in self.docs)
            sections.append("")

        if self.tests:
            sections.append("## ✅ Tests\n")
            sections.extend(f"- {test}" for test in self.tests)
            sections.append("")

        if self.chores:
            sections.append("## 🔧 Chores\n")
            sections.extend(f"- {chore}" for chore in self.chores)
            sections.append("")

        return "\n".join(sections)


@dataclass
class GateStatus:
    """Status of a deployment gate."""
    stage: DeploymentStage
    passed: bool
    requires_approval: bool = False
    reason: str = ""
    checks: dict[str, bool] = field(default_factory=dict)


@dataclass
class PRDependency:
    """Represents a dependency between PRs."""
    pr_number: int
    depends_on: list[int]


# ============================================================================
# Release Manager
# ============================================================================


class ReleaseManager:
    """
    Release Manager Agent that coordinates merges and deployments.

    Responsibilities:
    1. Assess merge readiness (tests, coverage, reviews, conflicts)
    2. Detect conflicts (file and semantic)
    3. Order merges intelligently (dependencies, risk)
    4. Track rollback information
    5. Aggregate release notes
    6. Manage staged deployments (dev → staging → prod)
    """

    def __init__(
        self,
        coverage_threshold: float = 80.0,
        require_reviews: bool = True,
        min_reviews: int = 1,
        production_requires_approval: bool = False,
    ):
        """
        Initialize the Release Manager.

        Args:
            coverage_threshold: Minimum test coverage % required
            require_reviews: Whether to require code reviews
            min_reviews: Minimum number of reviews required
            production_requires_approval: Whether prod deployments need manual approval
        """
        self.coverage_threshold = coverage_threshold
        self.require_reviews = require_reviews
        self.min_reviews = min_reviews
        self.production_requires_approval = production_requires_approval

        # Track deployments by stage and commit
        self._deployments: dict[str, dict[str, bool]] = {
            stage.value: {} for stage in DeploymentStage
        }

        # Track production approvals
        self._production_approvals: dict[str, str] = {}  # commit -> approver

        # Track committed PRs for rollback planning
        self._committed_prs: dict[str, PRInfo] = {}  # commit_hash -> PRInfo

    # ========================================================================
    # Merge Readiness Assessment
    # ========================================================================

    def assess_merge_readiness(self, pr: PRInfo) -> MergeReadiness:
        """
        Assess whether a PR is ready to merge.

        Checks:
        - Tests passing
        - Coverage meets threshold
        - Sufficient reviews
        - No merge conflicts

        Args:
            pr: Pull request information

        Returns:
            MergeReadiness with status and blocking issues
        """
        blocking_issues = []

        # Check tests
        tests_passing = pr.tests_passing
        if not tests_passing:
            blocking_issues.append("Tests are failing")

        # Check coverage
        coverage_met = pr.coverage >= self.coverage_threshold
        if not coverage_met:
            blocking_issues.append(
                f"Coverage {pr.coverage:.1f}% is below threshold "
                f"{self.coverage_threshold:.1f}%"
            )

        # Check reviews
        reviews_met = (
            not self.require_reviews or
            pr.review_count >= self.min_reviews
        )
        if not reviews_met:
            blocking_issues.append(
                f"Insufficient reviews: {pr.review_count}/{self.min_reviews}"
            )

        # Check conflicts
        no_conflicts = not pr.has_conflicts
        if not no_conflicts:
            files_list = ", ".join(pr.conflicting_files or ["unknown"])
            blocking_issues.append(
                f"Has merge conflicts in: {files_list}"
            )

        # Determine overall status
        if blocking_issues:
            status = MergeReadinessStatus.NOT_READY
        else:
            status = MergeReadinessStatus.READY

        return MergeReadiness(
            pr_number=pr.number,
            status=status,
            tests_passing=tests_passing,
            coverage_met=coverage_met,
            reviews_met=reviews_met,
            no_conflicts=no_conflicts,
            blocking_issues=blocking_issues,
        )

    # ========================================================================
    # Conflict Detection
    # ========================================================================

    def detect_conflicts(self, pr: PRInfo) -> list[Conflict]:
        """
        Detect file-level conflicts in a PR.

        Args:
            pr: Pull request to check

        Returns:
            List of detected conflicts
        """
        conflicts = []

        if pr.has_conflicts:
            for file_path in pr.conflicting_files:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.FILE,
                    file_path=file_path,
                    pr_numbers=[pr.number],
                    description=f"Git merge conflict in {file_path}",
                ))

        return conflicts

    def detect_semantic_conflicts(self, prs: list[PRInfo]) -> list[Conflict]:
        """
        Detect semantic conflicts across multiple PRs.

        Semantic conflicts occur when multiple PRs modify the same files,
        even if there's no Git conflict. This can indicate areas of
        parallel work that may need coordination.

        Args:
            prs: List of PRs to check for semantic conflicts

        Returns:
            List of potential semantic conflicts
        """
        conflicts = []

        # Group PRs by files they modify
        file_to_prs: dict[str, list[int]] = defaultdict(list)
        for pr in prs:
            for file_path in pr.files_changed:
                file_to_prs[file_path].append(pr.number)

        # Find files modified by multiple PRs
        for file_path, pr_numbers in file_to_prs.items():
            if len(pr_numbers) > 1:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.SEMANTIC,
                    file_path=file_path,
                    pr_numbers=pr_numbers,
                    description=(
                        f"Multiple PRs ({', '.join(f'#{n}' for n in pr_numbers)}) "
                        f"modify {file_path}"
                    ),
                ))

        return conflicts

    # ========================================================================
    # Merge Ordering
    # ========================================================================

    def order_merges(self, prs: list[PRInfo]) -> list[PRInfo]:
        """
        Order PRs for merging based on dependencies and risk.

        Algorithm:
        1. Build dependency graph
        2. Topological sort to respect dependencies
        3. Within each level, order by risk (smaller changes first)

        Args:
            prs: List of PRs to order

        Returns:
            Ordered list of PRs

        Raises:
            ValueError: If circular dependencies detected
        """
        if not prs:
            return []

        # Build dependency graph
        pr_map = {pr.number: pr for pr in prs}

        # Check for circular dependencies
        self._check_circular_dependencies(prs)

        # Topological sort with risk-based tie-breaking
        ordered: list[PRInfo] = []
        remaining = set(pr.number for pr in prs)

        while remaining:
            # Find PRs with no unmet dependencies
            ready = []
            for pr_num in remaining:
                pr = pr_map[pr_num]
                deps_met = all(
                    dep not in remaining or dep in [p.number for p in ordered]
                    for dep in pr.depends_on
                )
                if deps_met:
                    ready.append(pr)

            if not ready:
                # Shouldn't happen if cycle check passed
                raise ValueError("Unable to order PRs - possible dependency issue")

            # Sort ready PRs by risk (additions + deletions)
            ready.sort(key=lambda pr: pr.additions + pr.deletions)

            # Add to ordered list and remove from remaining
            for pr in ready:
                ordered.append(pr)
                remaining.discard(pr.number)

        return ordered

    def _check_circular_dependencies(self, prs: list[PRInfo]) -> None:
        """
        Check for circular dependencies in PRs.

        Args:
            prs: List of PRs to check

        Raises:
            ValueError: If circular dependency detected
        """
        pr_map = {pr.number: pr for pr in prs}

        def has_cycle(pr_num: int, visited: set[int], rec_stack: set[int]) -> bool:
            """DFS to detect cycle."""
            visited.add(pr_num)
            rec_stack.add(pr_num)

            if pr_num in pr_map:
                for dep in pr_map[pr_num].depends_on:
                    if dep not in visited:
                        if has_cycle(dep, visited, rec_stack):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(pr_num)
            return False

        visited: set[int] = set()
        for pr in prs:
            if pr.number not in visited:
                if has_cycle(pr.number, visited, set()):
                    raise ValueError(
                        f"Circular dependency detected involving PR #{pr.number}"
                    )

    # ========================================================================
    # Rollback Planning
    # ========================================================================

    def track_rollback_info(
        self,
        commit_hash: str,
        pr_info: PRInfo | None = None,
        merged_prs: list[PRInfo] | None = None,
    ) -> RollbackPlan:
        """
        Track rollback information for a commit.

        Args:
            commit_hash: Git commit hash
            pr_info: PR that was merged (if single PR)
            merged_prs: List of all merged PRs (for dependency analysis)

        Returns:
            RollbackPlan with revert information

        Raises:
            ValueError: If commit is unknown and no PR info provided
        """
        if pr_info is None and commit_hash not in self._committed_prs:
            raise ValueError(f"Unknown commit: {commit_hash}")

        if pr_info:
            self._committed_prs[commit_hash] = pr_info
        else:
            pr_info = self._committed_prs[commit_hash]

        # Find dependent PRs
        dependent_prs = []
        if merged_prs:
            for other_pr in merged_prs:
                if pr_info.number in other_pr.depends_on:
                    dependent_prs.append(other_pr.number)

        return RollbackPlan(
            commit_hash=commit_hash,
            pr_number=pr_info.number,
            affected_files=pr_info.files_changed,
            revert_command=f"git revert {commit_hash}",
            commits=[commit_hash],
            dependent_prs=dependent_prs,
        )

    def track_rollback_info_batch(
        self,
        commit_hashes: list[str],
        pr_numbers: list[int],
    ) -> RollbackPlan:
        """
        Track rollback information for multiple commits.

        Args:
            commit_hashes: List of commit hashes in order
            pr_numbers: Corresponding PR numbers

        Returns:
            RollbackPlan for reverting all commits
        """
        # Revert in reverse order (newest first)
        reversed_commits = list(reversed(commit_hashes))
        revert_cmd = f"git revert {' '.join(reversed_commits)}"

        # Collect all affected files
        affected_files = []
        for commit_hash in commit_hashes:
            if commit_hash in self._committed_prs:
                pr = self._committed_prs[commit_hash]
                affected_files.extend(pr.files_changed)

        return RollbackPlan(
            commit_hash=commit_hashes[0],  # First commit
            pr_number=None,  # Multiple PRs
            affected_files=list(set(affected_files)),  # Deduplicate
            revert_command=revert_cmd,
            commits=commit_hashes,
            dependent_prs=[],
        )

    # ========================================================================
    # Release Notes
    # ========================================================================

    def aggregate_release_notes(self, prs: list[PRInfo]) -> ReleaseNotes:
        """
        Aggregate release notes from multiple PRs.

        Categorizes changes based on PR title prefixes:
        - "feat:" → Features
        - "fix:" → Bug Fixes
        - "BREAKING:" → Breaking Changes
        - "refactor:" → Refactoring
        - "docs:" → Documentation
        - "test:" → Tests
        - "chore:" → Chores

        Args:
            prs: List of PRs to include in release

        Returns:
            Categorized release notes
        """
        notes = ReleaseNotes(version="v0.0.0")

        # Deduplicate PRs by number
        seen = set()
        unique_prs = []
        for pr in prs:
            if pr.number not in seen:
                seen.add(pr.number)
                unique_prs.append(pr)

        for pr in unique_prs:
            title = pr.title
            entry = f"{title} (#{pr.number})"

            # Categorize based on title prefix
            if "BREAKING" in title.upper():
                notes.breaking_changes.append(entry)
            elif title.lower().startswith("feat:"):
                notes.features.append(entry)
            elif title.lower().startswith("fix:"):
                notes.fixes.append(entry)
            elif title.lower().startswith("refactor:"):
                notes.refactors.append(entry)
            elif title.lower().startswith("docs:"):
                notes.docs.append(entry)
            elif title.lower().startswith("test:"):
                notes.tests.append(entry)
            elif title.lower().startswith("chore:"):
                notes.chores.append(entry)
            else:
                # Default to features if no prefix
                notes.features.append(entry)

        return notes

    # ========================================================================
    # Staged Deployment
    # ========================================================================

    def check_deployment_gate(
        self,
        stage: DeploymentStage,
        commit_hash: str,
    ) -> GateStatus:
        """
        Check if deployment can proceed to a given stage.

        Gate requirements:
        - DEV: Always passes (no prerequisites)
        - STAGING: Requires successful DEV deployment
        - PRODUCTION: Requires successful STAGING deployment
                      (+ manual approval if configured)

        Args:
            stage: Deployment stage to check
            commit_hash: Commit to deploy

        Returns:
            GateStatus indicating if gate passed
        """
        checks = {}
        requires_approval = False
        reason = ""

        if stage == DeploymentStage.DEV:
            # Dev always passes
            passed = True

        elif stage == DeploymentStage.STAGING:
            # Requires successful dev deployment
            dev_success = self._deployments[DeploymentStage.DEV.value].get(
                commit_hash, False
            )
            checks["dev_deployed"] = dev_success
            passed = dev_success
            if not passed:
                reason = "Dev deployment required before staging"

        elif stage == DeploymentStage.PRODUCTION:
            # Requires successful staging deployment
            staging_success = self._deployments[DeploymentStage.STAGING.value].get(
                commit_hash, False
            )
            checks["staging_deployed"] = staging_success

            # Check if approval required
            if self.production_requires_approval:
                approved = commit_hash in self._production_approvals
                checks["approved"] = approved
                requires_approval = True
                passed = staging_success and approved
                if not passed:
                    if not staging_success:
                        reason = "Staging deployment required before production"
                    else:
                        reason = "Manual approval required for production"
            else:
                passed = staging_success
                if not passed:
                    reason = "Staging deployment required before production"

        else:
            passed = False
            reason = f"Unknown stage: {stage}"

        return GateStatus(
            stage=stage,
            passed=passed,
            requires_approval=requires_approval,
            reason=reason,
            checks=checks,
        )

    def record_deployment(
        self,
        stage: DeploymentStage,
        commit_hash: str,
        success: bool,
    ) -> None:
        """
        Record a deployment attempt.

        Args:
            stage: Deployment stage
            commit_hash: Commit that was deployed
            success: Whether deployment succeeded
        """
        self._deployments[stage.value][commit_hash] = success

    def approve_production_deployment(
        self,
        commit_hash: str,
        approver: str,
    ) -> None:
        """
        Approve a commit for production deployment.

        Args:
            commit_hash: Commit to approve
            approver: Person/agent approving
        """
        self._production_approvals[commit_hash] = approver

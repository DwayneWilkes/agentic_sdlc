"""
Tests for Release Manager Agent (Phase 6.4).

Following TDD: These tests are written FIRST, before implementation.
"""


import pytest

from src.orchestrator.release_manager import (
    ConflictType,
    DeploymentStage,
    MergeReadinessStatus,
    PRInfo,
    ReleaseManager,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def release_manager():
    """Create a ReleaseManager instance for testing."""
    return ReleaseManager(
        coverage_threshold=80.0,
        require_reviews=True,
        min_reviews=1,
    )


@pytest.fixture
def passing_pr():
    """Create a PR that passes all checks."""
    return PRInfo(
        number=1,
        title="Add user authentication",
        branch="feature/auth",
        author="alice",
        tests_passing=True,
        coverage=85.0,
        review_count=2,
        has_conflicts=False,
        files_changed=["src/auth.py", "tests/test_auth.py"],
        additions=150,
        deletions=10,
    )


@pytest.fixture
def failing_tests_pr():
    """Create a PR with failing tests."""
    return PRInfo(
        number=2,
        title="Add payment processing",
        branch="feature/payments",
        author="bob",
        tests_passing=False,
        coverage=75.0,
        review_count=1,
        has_conflicts=False,
        files_changed=["src/payments.py"],
        additions=200,
        deletions=5,
    )


@pytest.fixture
def low_coverage_pr():
    """Create a PR with insufficient coverage."""
    return PRInfo(
        number=3,
        title="Add notification system",
        branch="feature/notifications",
        author="carol",
        tests_passing=True,
        coverage=65.0,
        review_count=2,
        has_conflicts=False,
        files_changed=["src/notifications.py"],
        additions=100,
        deletions=0,
    )


@pytest.fixture
def conflicting_pr():
    """Create a PR with merge conflicts."""
    return PRInfo(
        number=4,
        title="Refactor auth module",
        branch="refactor/auth",
        author="dave",
        tests_passing=True,
        coverage=90.0,
        review_count=1,
        has_conflicts=True,
        conflicting_files=["src/auth.py"],
        files_changed=["src/auth.py"],
        additions=50,
        deletions=30,
    )


# ============================================================================
# Test: Merge Readiness Assessment
# ============================================================================


def test_assess_merge_readiness_all_passing(release_manager, passing_pr):
    """Test merge readiness assessment for a PR that passes all checks."""
    readiness = release_manager.assess_merge_readiness(passing_pr)

    assert readiness.status == MergeReadinessStatus.READY
    assert readiness.tests_passing is True
    assert readiness.coverage_met is True
    assert readiness.reviews_met is True
    assert readiness.no_conflicts is True
    assert len(readiness.blocking_issues) == 0


def test_assess_merge_readiness_failing_tests(release_manager, failing_tests_pr):
    """Test merge readiness when tests are failing."""
    readiness = release_manager.assess_merge_readiness(failing_tests_pr)

    assert readiness.status == MergeReadinessStatus.NOT_READY
    assert readiness.tests_passing is False
    assert "Tests are failing" in readiness.blocking_issues


def test_assess_merge_readiness_low_coverage(release_manager, low_coverage_pr):
    """Test merge readiness when coverage is below threshold."""
    readiness = release_manager.assess_merge_readiness(low_coverage_pr)

    assert readiness.status == MergeReadinessStatus.NOT_READY
    assert readiness.coverage_met is False
    assert any("coverage" in issue.lower() for issue in readiness.blocking_issues)


def test_assess_merge_readiness_insufficient_reviews(release_manager, passing_pr):
    """Test merge readiness when reviews are insufficient."""
    pr_no_reviews = PRInfo(
        number=5,
        title="Quick fix",
        branch="fix/typo",
        author="eve",
        tests_passing=True,
        coverage=90.0,
        review_count=0,
        has_conflicts=False,
        files_changed=["README.md"],
        additions=1,
        deletions=1,
    )

    readiness = release_manager.assess_merge_readiness(pr_no_reviews)

    assert readiness.status == MergeReadinessStatus.NOT_READY
    assert readiness.reviews_met is False


def test_assess_merge_readiness_has_conflicts(release_manager, conflicting_pr):
    """Test merge readiness when PR has conflicts."""
    readiness = release_manager.assess_merge_readiness(conflicting_pr)

    assert readiness.status == MergeReadinessStatus.NOT_READY
    assert readiness.no_conflicts is False
    assert any("conflict" in issue.lower() for issue in readiness.blocking_issues)


def test_assess_merge_readiness_multiple_issues(release_manager):
    """Test merge readiness with multiple blocking issues."""
    pr_multiple_issues = PRInfo(
        number=6,
        title="Major refactor",
        branch="refactor/all",
        author="frank",
        tests_passing=False,
        coverage=50.0,
        review_count=0,
        has_conflicts=True,
        conflicting_files=["src/core.py"],
        files_changed=["src/core.py"],
        additions=500,
        deletions=300,
    )

    readiness = release_manager.assess_merge_readiness(pr_multiple_issues)

    assert readiness.status == MergeReadinessStatus.NOT_READY
    assert len(readiness.blocking_issues) >= 3  # tests, coverage, reviews, conflicts


# ============================================================================
# Test: Conflict Detection
# ============================================================================


def test_detect_conflicts_none(release_manager, passing_pr):
    """Test conflict detection when there are no conflicts."""
    conflicts = release_manager.detect_conflicts(passing_pr)

    assert len(conflicts) == 0


def test_detect_conflicts_file_conflict(release_manager, conflicting_pr):
    """Test detection of file-level conflicts."""
    conflicts = release_manager.detect_conflicts(conflicting_pr)

    assert len(conflicts) > 0
    assert any(c.conflict_type == ConflictType.FILE for c in conflicts)
    assert any(c.file_path == "src/auth.py" for c in conflicts)


def test_detect_conflicts_semantic_conflict(release_manager):
    """Test detection of semantic conflicts (same function modified in parallel)."""
    pr1 = PRInfo(
        number=10,
        title="Update parse_task signature",
        branch="update/parser",
        author="alice",
        tests_passing=True,
        coverage=85.0,
        review_count=1,
        has_conflicts=False,
        files_changed=["src/parser.py"],
        additions=5,
        deletions=2,
    )

    pr2 = PRInfo(
        number=11,
        title="Add parse_task validation",
        branch="enhance/parser",
        author="bob",
        tests_passing=True,
        coverage=85.0,
        review_count=1,
        has_conflicts=False,
        files_changed=["src/parser.py"],
        additions=10,
        deletions=0,
    )

    # Simulate semantic conflict detection
    conflicts = release_manager.detect_semantic_conflicts([pr1, pr2])

    # Should detect potential conflict in parser.py
    assert any(c.conflict_type == ConflictType.SEMANTIC for c in conflicts)


# ============================================================================
# Test: Merge Ordering
# ============================================================================


def test_order_merges_simple_linear(release_manager):
    """Test merge ordering for PRs with no dependencies."""
    pr1 = PRInfo(number=1, title="A", branch="a", author="alice",
                 tests_passing=True, coverage=85.0, review_count=1,
                 has_conflicts=False, files_changed=["a.py"],
                 additions=10, deletions=0)
    pr2 = PRInfo(number=2, title="B", branch="b", author="bob",
                 tests_passing=True, coverage=85.0, review_count=1,
                 has_conflicts=False, files_changed=["b.py"],
                 additions=20, deletions=0)
    pr3 = PRInfo(number=3, title="C", branch="c", author="carol",
                 tests_passing=True, coverage=85.0, review_count=1,
                 has_conflicts=False, files_changed=["c.py"],
                 additions=5, deletions=0)

    ordered = release_manager.order_merges([pr3, pr1, pr2])

    # Should order by risk (smaller changes first)
    assert ordered[0].number == 3  # smallest (5 additions)
    assert ordered[1].number == 1  # medium (10 additions)
    assert ordered[2].number == 2  # largest (20 additions)


def test_order_merges_with_dependencies(release_manager):
    """Test merge ordering when PRs have dependencies."""
    pr_base = PRInfo(number=1, title="Base feature", branch="base",
                     author="alice", tests_passing=True, coverage=85.0,
                     review_count=1, has_conflicts=False,
                     files_changed=["base.py"], additions=100, deletions=0)

    pr_dependent = PRInfo(number=2, title="Extends base", branch="extend",
                          author="bob", tests_passing=True, coverage=85.0,
                          review_count=1, has_conflicts=False,
                          files_changed=["extend.py"], additions=50, deletions=0,
                          depends_on=[1])

    ordered = release_manager.order_merges([pr_dependent, pr_base])

    # Base must come before dependent
    assert ordered[0].number == 1
    assert ordered[1].number == 2


def test_order_merges_complex_dag(release_manager):
    """Test merge ordering with complex dependency graph."""
    pr1 = PRInfo(number=1, title="A", branch="a", author="alice",
                 tests_passing=True, coverage=85.0, review_count=1,
                 has_conflicts=False, files_changed=["a.py"],
                 additions=10, deletions=0)

    pr2 = PRInfo(number=2, title="B (depends on A)", branch="b",
                 author="bob", tests_passing=True, coverage=85.0,
                 review_count=1, has_conflicts=False,
                 files_changed=["b.py"], additions=10, deletions=0,
                 depends_on=[1])

    pr3 = PRInfo(number=3, title="C (depends on A)", branch="c",
                 author="carol", tests_passing=True, coverage=85.0,
                 review_count=1, has_conflicts=False,
                 files_changed=["c.py"], additions=10, deletions=0,
                 depends_on=[1])

    pr4 = PRInfo(number=4, title="D (depends on B,C)", branch="d",
                 author="dave", tests_passing=True, coverage=85.0,
                 review_count=1, has_conflicts=False,
                 files_changed=["d.py"], additions=10, deletions=0,
                 depends_on=[2, 3])

    ordered = release_manager.order_merges([pr4, pr3, pr2, pr1])

    # A must be first, B and C after A, D last
    assert ordered[0].number == 1
    assert ordered[-1].number == 4
    assert ordered[1].number in [2, 3]
    assert ordered[2].number in [2, 3]


def test_order_merges_detects_cycle(release_manager):
    """Test that circular dependencies are detected."""
    pr1 = PRInfo(number=1, title="A", branch="a", author="alice",
                 tests_passing=True, coverage=85.0, review_count=1,
                 has_conflicts=False, files_changed=["a.py"],
                 additions=10, deletions=0, depends_on=[2])

    pr2 = PRInfo(number=2, title="B", branch="b", author="bob",
                 tests_passing=True, coverage=85.0, review_count=1,
                 has_conflicts=False, files_changed=["b.py"],
                 additions=10, deletions=0, depends_on=[1])

    with pytest.raises(ValueError, match="[Cc]ircular.*dependenc"):
        release_manager.order_merges([pr1, pr2])


# ============================================================================
# Test: Rollback Planning
# ============================================================================


def test_track_rollback_single_commit(release_manager, passing_pr):
    """Test rollback tracking for a single commit."""
    commit_hash = "abc123def456"

    rollback = release_manager.track_rollback_info(
        commit_hash=commit_hash,
        pr_info=passing_pr,
    )

    assert rollback.commit_hash == commit_hash
    assert rollback.pr_number == passing_pr.number
    assert len(rollback.affected_files) > 0
    assert "src/auth.py" in rollback.affected_files
    assert rollback.revert_command == f"git revert {commit_hash}"


def test_track_rollback_multi_commit_release(release_manager):
    """Test rollback tracking for a release with multiple commits."""
    commits = ["abc123", "def456", "ghi789"]
    pr_numbers = [1, 2, 3]

    rollback = release_manager.track_rollback_info_batch(
        commit_hashes=commits,
        pr_numbers=pr_numbers,
    )

    assert len(rollback.commits) == 3
    assert rollback.revert_command.startswith("git revert")
    assert all(c in rollback.revert_command for c in commits)


def test_rollback_plan_includes_dependencies(release_manager):
    """Test that rollback plan considers dependencies."""
    # If PR 2 depends on PR 1, reverting PR 1 should warn about PR 2
    pr1 = PRInfo(number=1, title="Base", branch="base", author="alice",
                 tests_passing=True, coverage=85.0, review_count=1,
                 has_conflicts=False, files_changed=["base.py"],
                 additions=100, deletions=0)

    pr2 = PRInfo(number=2, title="Dependent", branch="dep", author="bob",
                 tests_passing=True, coverage=85.0, review_count=1,
                 has_conflicts=False, files_changed=["dep.py"],
                 additions=50, deletions=0, depends_on=[1])

    rollback = release_manager.track_rollback_info(
        commit_hash="abc123",
        pr_info=pr1,
        merged_prs=[pr1, pr2],
    )

    assert len(rollback.dependent_prs) > 0
    assert 2 in rollback.dependent_prs


# ============================================================================
# Test: Release Notes Aggregation
# ============================================================================


def test_aggregate_release_notes_empty(release_manager):
    """Test release notes with no PRs."""
    notes = release_manager.aggregate_release_notes([])

    assert notes.version is not None
    assert len(notes.features) == 0
    assert len(notes.fixes) == 0
    assert len(notes.breaking_changes) == 0


def test_aggregate_release_notes_categorization(release_manager):
    """Test that changes are correctly categorized."""
    pr_feature = PRInfo(number=1, title="feat: Add user auth",
                        branch="feat/auth", author="alice",
                        tests_passing=True, coverage=85.0, review_count=1,
                        has_conflicts=False, files_changed=["auth.py"],
                        additions=100, deletions=0)

    pr_fix = PRInfo(number=2, title="fix: Resolve login bug",
                    branch="fix/login", author="bob",
                    tests_passing=True, coverage=85.0, review_count=1,
                    has_conflicts=False, files_changed=["login.py"],
                    additions=5, deletions=3)

    pr_breaking = PRInfo(number=3, title="BREAKING: Remove old API",
                         branch="breaking/api", author="carol",
                         tests_passing=True, coverage=85.0, review_count=1,
                         has_conflicts=False, files_changed=["api.py"],
                         additions=200, deletions=500)

    notes = release_manager.aggregate_release_notes(
        [pr_feature, pr_fix, pr_breaking]
    )

    assert len(notes.features) == 1
    assert len(notes.fixes) == 1
    assert len(notes.breaking_changes) == 1
    assert "auth" in notes.features[0].lower()
    assert "login" in notes.fixes[0].lower()
    assert "api" in notes.breaking_changes[0].lower()


def test_aggregate_release_notes_format(release_manager):
    """Test that release notes are properly formatted."""
    pr = PRInfo(number=1, title="Add cool feature", branch="feat/cool",
                author="alice", tests_passing=True, coverage=85.0,
                review_count=1, has_conflicts=False,
                files_changed=["cool.py"], additions=50, deletions=0)

    notes = release_manager.aggregate_release_notes([pr])
    formatted = notes.format_markdown()

    # Check for Features section (may have emoji)
    assert "Features" in formatted or "Changes" in formatted
    assert "cool feature" in formatted.lower()
    assert "#1" in formatted  # PR number reference


# ============================================================================
# Test: Staged Deployment Gates
# ============================================================================


def test_check_deployment_gate_dev(release_manager):
    """Test deployment gate for dev stage (should always pass)."""
    gate_status = release_manager.check_deployment_gate(
        stage=DeploymentStage.DEV,
        commit_hash="abc123",
    )

    assert gate_status.stage == DeploymentStage.DEV
    assert gate_status.passed is True


def test_check_deployment_gate_staging(release_manager):
    """Test deployment gate for staging (requires dev success)."""
    # First deploy to dev
    release_manager.record_deployment(
        stage=DeploymentStage.DEV,
        commit_hash="abc123",
        success=True,
    )

    # Then check staging gate
    gate_status = release_manager.check_deployment_gate(
        stage=DeploymentStage.STAGING,
        commit_hash="abc123",
    )

    assert gate_status.stage == DeploymentStage.STAGING
    assert gate_status.passed is True


def test_check_deployment_gate_staging_without_dev(release_manager):
    """Test staging gate fails without successful dev deployment."""
    gate_status = release_manager.check_deployment_gate(
        stage=DeploymentStage.STAGING,
        commit_hash="abc123",
    )

    assert gate_status.passed is False
    assert "dev" in gate_status.reason.lower()


def test_check_deployment_gate_production(release_manager):
    """Test production gate requires staging success."""
    commit = "abc123"

    # Deploy to dev and staging
    release_manager.record_deployment(DeploymentStage.DEV, commit, True)
    release_manager.record_deployment(DeploymentStage.STAGING, commit, True)

    # Check production gate
    gate_status = release_manager.check_deployment_gate(
        stage=DeploymentStage.PRODUCTION,
        commit_hash=commit,
    )

    assert gate_status.stage == DeploymentStage.PRODUCTION
    assert gate_status.passed is True


def test_check_deployment_gate_production_requires_approval(release_manager):
    """Test production gate can require manual approval."""
    rm = ReleaseManager(
        coverage_threshold=80.0,
        require_reviews=True,
        min_reviews=1,
        production_requires_approval=True,
    )

    commit = "abc123"
    rm.record_deployment(DeploymentStage.DEV, commit, True)
    rm.record_deployment(DeploymentStage.STAGING, commit, True)

    # Without approval
    gate_status = rm.check_deployment_gate(
        stage=DeploymentStage.PRODUCTION,
        commit_hash=commit,
    )
    assert gate_status.passed is False
    assert gate_status.requires_approval is True

    # With approval
    rm.approve_production_deployment(commit, approver="tech-lead")
    gate_status = rm.check_deployment_gate(
        stage=DeploymentStage.PRODUCTION,
        commit_hash=commit,
    )
    assert gate_status.passed is True


# ============================================================================
# Test: Edge Cases
# ============================================================================


def test_order_merges_empty_list(release_manager):
    """Test merge ordering with empty list."""
    ordered = release_manager.order_merges([])
    assert len(ordered) == 0


def test_aggregate_release_notes_duplicate_prs(release_manager):
    """Test release notes handles duplicate PR references gracefully."""
    pr = PRInfo(number=1, title="feat: Add auth", branch="feat/auth",
                author="alice", tests_passing=True, coverage=85.0,
                review_count=1, has_conflicts=False,
                files_changed=["auth.py"], additions=100, deletions=0)

    # Pass same PR twice
    notes = release_manager.aggregate_release_notes([pr, pr])

    # Should deduplicate
    assert len(notes.features) == 1


def test_rollback_unknown_commit(release_manager):
    """Test rollback tracking for unknown commit."""
    with pytest.raises(ValueError, match="Unknown commit"):
        release_manager.track_rollback_info(
            commit_hash="unknown123",
            pr_info=None,
        )


def test_detect_conflicts_concurrent_prs(release_manager):
    """Test conflict detection across multiple concurrent PRs."""
    # Three PRs all modifying same file
    pr1 = PRInfo(number=1, title="A", branch="a", author="alice",
                 tests_passing=True, coverage=85.0, review_count=1,
                 has_conflicts=False, files_changed=["shared.py"],
                 additions=10, deletions=5)
    pr2 = PRInfo(number=2, title="B", branch="b", author="bob",
                 tests_passing=True, coverage=85.0, review_count=1,
                 has_conflicts=False, files_changed=["shared.py"],
                 additions=15, deletions=2)
    pr3 = PRInfo(number=3, title="C", branch="c", author="carol",
                 tests_passing=True, coverage=85.0, review_count=1,
                 has_conflicts=False, files_changed=["shared.py"],
                 additions=8, deletions=10)

    conflicts = release_manager.detect_semantic_conflicts([pr1, pr2, pr3])

    # Should detect potential conflicts from concurrent edits
    assert len(conflicts) > 0

"""Tests for self-modification safety framework."""

import asyncio
import subprocess
from datetime import datetime

import pytest

from src.self_improvement.self_modification import (
    IsolatedTestEnvironment,
    ModificationStatus,
    RecursionLimiter,
    RecursionLimitExceededError,
    SelfModificationApprovalGate,
    SelfModificationProposal,
    UnsafeBranchError,
    VersionControl,
)


def test_modification_status_enum():
    """Test that ModificationStatus enum has expected values."""
    assert ModificationStatus.PROPOSED.value == "proposed"
    assert ModificationStatus.TESTING.value == "testing"
    assert ModificationStatus.APPROVED.value == "approved"
    assert ModificationStatus.REJECTED.value == "rejected"
    assert ModificationStatus.ROLLED_BACK.value == "rolled_back"


def test_self_modification_proposal_creation():
    """Test SelfModificationProposal dataclass creation."""
    proposal = SelfModificationProposal(
        proposal_id="test-proposal-1",
        description="Optimize task parser performance",
        target_files=["src/core/task_parser.py"],
        test_branch_name="self-improve/optimize-task-parser",
        recursion_depth=0,
        proposed_by="agent-optimizer",
    )

    assert proposal.proposal_id == "test-proposal-1"
    assert proposal.description == "Optimize task parser performance"
    assert proposal.target_files == ["src/core/task_parser.py"]
    assert proposal.test_branch_name == "self-improve/optimize-task-parser"
    assert proposal.recursion_depth == 0
    assert proposal.proposed_by == "agent-optimizer"
    assert proposal.status == ModificationStatus.PROPOSED
    assert isinstance(proposal.proposed_at, datetime)


def test_recursion_limiter_initialization():
    """Test RecursionLimiter initialization."""
    limiter = RecursionLimiter(max_depth=3)
    assert limiter.max_depth == 3
    assert limiter.current_depth == 0
    assert len(limiter.depth_history) == 0


def test_recursion_limiter_track_depth():
    """Test tracking modification depth."""
    limiter = RecursionLimiter(max_depth=3)

    limiter.track_depth("proposal-1")
    assert limiter.current_depth == 1
    assert limiter.depth_history == ["proposal-1"]

    limiter.track_depth("proposal-2")
    assert limiter.current_depth == 2
    assert limiter.depth_history == ["proposal-1", "proposal-2"]


def test_recursion_limiter_exceeds_limit():
    """Test that recursion limit is enforced."""
    limiter = RecursionLimiter(max_depth=2)

    limiter.track_depth("proposal-1")
    limiter.track_depth("proposal-2")

    with pytest.raises(RecursionLimitExceededError) as exc_info:
        limiter.track_depth("proposal-3")

    assert "Maximum recursion depth 2 exceeded" in str(exc_info.value)


def test_recursion_limiter_check_limit():
    """Test check_limit method."""
    limiter = RecursionLimiter(max_depth=2)

    assert limiter.check_limit() is True

    limiter.track_depth("proposal-1")
    assert limiter.check_limit() is True

    limiter.track_depth("proposal-2")
    assert limiter.check_limit() is False


def test_recursion_limiter_reset():
    """Test resetting recursion limiter."""
    limiter = RecursionLimiter(max_depth=3)
    limiter.track_depth("proposal-1")
    limiter.track_depth("proposal-2")

    limiter.reset()

    assert limiter.current_depth == 0
    assert len(limiter.depth_history) == 0


def test_version_control_initialization(tmp_path):
    """Test VersionControl initialization."""
    vc = VersionControl(repo_path=str(tmp_path))
    assert vc.repo_path == str(tmp_path)


def test_version_control_validate_not_on_main(tmp_path):
    """Test that validation prevents operations on main branch."""
    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    vc = VersionControl(repo_path=str(tmp_path))

    # Should raise error when on main
    with pytest.raises(UnsafeBranchError) as exc_info:
        vc.validate_not_on_main()

    assert "Cannot perform self-modification on main branch" in str(exc_info.value)


def test_version_control_get_current_branch(tmp_path):
    """Test getting current branch name."""
    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    vc = VersionControl(repo_path=str(tmp_path))

    current = vc.get_current_branch()
    assert current in ["main", "master"]


def test_version_control_create_feature_branch(tmp_path):
    """Test creating a feature branch for self-modification."""
    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    vc = VersionControl(repo_path=str(tmp_path))

    branch_name = vc.create_feature_branch("optimize-parser")

    assert branch_name.startswith("self-improve/")
    assert "optimize-parser" in branch_name
    assert vc.get_current_branch() == branch_name


def test_version_control_rollback(tmp_path):
    """Test rolling back to previous state."""
    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    test_file = tmp_path / "test.txt"
    test_file.write_text("initial")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create feature branch and make a change
    vc = VersionControl(repo_path=str(tmp_path))
    branch_name = vc.create_feature_branch("test-rollback")

    test_file.write_text("modified")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Test change"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Rollback
    vc.rollback()

    # Should be back on main/master
    assert vc.get_current_branch() in ["main", "master"]
    # Branch should be deleted
    result = subprocess.run(
        ["git", "branch"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert branch_name not in result.stdout


def test_isolated_test_environment_initialization():
    """Test IsolatedTestEnvironment initialization."""
    env = IsolatedTestEnvironment(repo_path="/tmp/test")
    assert env.repo_path == "/tmp/test"
    assert env.version_control.repo_path == "/tmp/test"


def test_isolated_test_environment_create_test_branch(tmp_path):
    """Test creating an isolated test branch."""
    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    env = IsolatedTestEnvironment(repo_path=str(tmp_path))

    proposal = SelfModificationProposal(
        proposal_id="test-1",
        description="Test modification",
        target_files=["test.txt"],
        test_branch_name="self-improve/test",
        recursion_depth=0,
        proposed_by="test-agent",
    )

    branch_name = env.create_test_branch(proposal)

    assert branch_name == "self-improve/test"
    assert env.version_control.get_current_branch() == branch_name


def test_isolated_test_environment_cleanup(tmp_path):
    """Test cleaning up failed test branch."""
    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    env = IsolatedTestEnvironment(repo_path=str(tmp_path))

    proposal = SelfModificationProposal(
        proposal_id="test-cleanup",
        description="Test cleanup",
        target_files=["test.txt"],
        test_branch_name="self-improve/test-cleanup",
        recursion_depth=0,
        proposed_by="test-agent",
    )

    env.create_test_branch(proposal)

    # Cleanup should delete branch and return to main
    env.cleanup()

    assert env.version_control.get_current_branch() in ["main", "master"]


@pytest.mark.asyncio
async def test_self_modification_approval_gate_initialization():
    """Test SelfModificationApprovalGate initialization."""
    gate = SelfModificationApprovalGate(
        timeout_seconds=300,
        recursion_limiter=RecursionLimiter(max_depth=3),
    )

    assert gate.timeout_seconds == 300
    assert gate.recursion_limiter.max_depth == 3


@pytest.mark.asyncio
async def test_self_modification_approval_gate_validates_recursion():
    """Test that approval gate enforces recursion limits."""
    limiter = RecursionLimiter(max_depth=1)
    limiter.track_depth("proposal-1")  # At limit

    gate = SelfModificationApprovalGate(
        timeout_seconds=300,
        recursion_limiter=limiter,
    )

    proposal = SelfModificationProposal(
        proposal_id="proposal-2",
        description="Another modification",
        target_files=["test.py"],
        test_branch_name="self-improve/test-2",
        recursion_depth=1,
        proposed_by="test-agent",
    )

    with pytest.raises(RecursionLimitExceededError):
        await gate.submit_self_modification(proposal, "test-agent")


@pytest.mark.asyncio
async def test_self_modification_approval_gate_submit_and_approve():
    """Test submitting and approving a self-modification."""
    gate = SelfModificationApprovalGate(
        timeout_seconds=5,
        recursion_limiter=RecursionLimiter(max_depth=3),
    )

    proposal = SelfModificationProposal(
        proposal_id="proposal-1",
        description="Optimize parser",
        target_files=["parser.py"],
        test_branch_name="self-improve/optimize-parser",
        recursion_depth=0,
        proposed_by="optimizer-agent",
    )

    # Start approval in background
    async def approve_after_delay():
        await asyncio.sleep(0.1)
        gate.approve_request(request_id, "human-reviewer", "Safe to proceed")

    request_id = await gate.submit_self_modification(proposal, "optimizer-agent")
    task = asyncio.create_task(approve_after_delay())

    approved = await gate.wait_for_decision(request_id)
    await task

    assert approved is True


@pytest.mark.asyncio
async def test_self_modification_approval_gate_deny():
    """Test denying a self-modification."""
    gate = SelfModificationApprovalGate(
        timeout_seconds=5,
        recursion_limiter=RecursionLimiter(max_depth=3),
    )

    proposal = SelfModificationProposal(
        proposal_id="proposal-dangerous",
        description="Risky modification",
        target_files=["core.py"],
        test_branch_name="self-improve/risky",
        recursion_depth=0,
        proposed_by="test-agent",
    )

    # Deny immediately
    async def deny_after_delay():
        await asyncio.sleep(0.1)
        gate.deny_request(request_id, "human-reviewer", "Too risky")

    request_id = await gate.submit_self_modification(proposal, "test-agent")
    task = asyncio.create_task(deny_after_delay())

    approved = await gate.wait_for_decision(request_id)
    await task

    assert approved is False

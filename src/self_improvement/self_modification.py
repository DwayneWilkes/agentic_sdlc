"""Self-modification safety framework.

This module provides a safety framework for agent self-modification, ensuring:
1. All modifications are tested in isolated feature branches
2. Version control and rollback mechanisms
3. Recursive improvement depth limits
4. Human approval gates for merging to main
"""

import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.security.approval_gate import ApprovalGate


class ModificationStatus(Enum):
    """Status of a self-modification proposal."""

    PROPOSED = "proposed"
    TESTING = "testing"
    APPROVED = "approved"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class UnsafeBranchError(Exception):
    """Exception raised when attempting unsafe operations on main branch."""

    pass


class RecursionLimitExceededError(Exception):
    """Exception raised when recursion depth limit is exceeded."""

    pass


@dataclass
class SelfModificationProposal:
    """Proposal for a self-modification.

    Represents a proposed change to the agent's own code, including
    what files will be modified, the rationale, and tracking information.
    """

    proposal_id: str
    """Unique identifier for this proposal."""

    description: str
    """Human-readable description of the modification."""

    target_files: list[str]
    """List of files that will be modified."""

    test_branch_name: str
    """Name of the feature branch for testing."""

    recursion_depth: int
    """Depth in the self-modification chain (0 = first modification)."""

    proposed_by: str
    """Agent or system that proposed this modification."""

    proposed_at: datetime = field(default_factory=datetime.now)
    """Timestamp when proposal was created."""

    status: ModificationStatus = ModificationStatus.PROPOSED
    """Current status of the proposal."""

    test_results: str | None = None
    """Results from isolated testing."""

    approval_request_id: str | None = None
    """ID of the approval request if submitted."""


class RecursionLimiter:
    """Limits recursive self-modification depth.

    Prevents runaway self-improvement by enforcing a maximum depth
    for chained modifications (modification → modification → ...).
    """

    def __init__(self, max_depth: int = 3) -> None:
        """Initialize recursion limiter.

        Args:
            max_depth: Maximum allowed recursion depth
        """
        self.max_depth = max_depth
        self.current_depth = 0
        self.depth_history: list[str] = []

    def track_depth(self, proposal_id: str) -> None:
        """Track a new modification in the chain.

        Args:
            proposal_id: ID of the proposal being tracked

        Raises:
            RecursionLimitExceeded: If max_depth would be exceeded
        """
        if self.current_depth >= self.max_depth:
            raise RecursionLimitExceededError(
                f"Maximum recursion depth {self.max_depth} exceeded. "
                f"Current chain: {' → '.join(self.depth_history)}"
            )

        self.current_depth += 1
        self.depth_history.append(proposal_id)

    def check_limit(self) -> bool:
        """Check if another modification is allowed.

        Returns:
            True if below limit, False if at limit
        """
        return self.current_depth < self.max_depth

    def get_depth_history(self) -> list[str]:
        """Get the modification chain history.

        Returns:
            List of proposal IDs in modification order
        """
        return self.depth_history.copy()

    def reset(self) -> None:
        """Reset the recursion limiter to initial state."""
        self.current_depth = 0
        self.depth_history = []


class VersionControl:
    """Version control operations for self-modification.

    Manages git operations including branch creation, commits,
    and rollback for safe self-modification.
    """

    def __init__(self, repo_path: str = ".") -> None:
        """Initialize version control.

        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = repo_path

    def get_current_branch(self) -> str:
        """Get the current git branch name.

        Returns:
            Name of the current branch
        """
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def validate_not_on_main(self) -> None:
        """Validate that we're not on the main branch.

        Raises:
            UnsafeBranchError: If currently on main or master branch
        """
        current_branch = self.get_current_branch()
        if current_branch in ["main", "master"]:
            raise UnsafeBranchError(
                f"Cannot perform self-modification on main branch. "
                f"Current branch: {current_branch}. "
                f"Create a feature branch first."
            )

    def create_feature_branch(self, description: str) -> str:
        """Create a feature branch for self-modification.

        Args:
            description: Short description for branch name

        Returns:
            Name of the created branch
        """
        # Sanitize description for branch name
        safe_description = description.lower().replace(" ", "-")
        safe_description = "".join(c for c in safe_description if c.isalnum() or c == "-")

        branch_name = f"self-improve/{safe_description}-{uuid.uuid4().hex[:8]}"

        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=self.repo_path,
            capture_output=True,
            check=True,
        )

        return branch_name

    def commit_changes(
        self,
        message: str,
        files: list[str] | None = None,
    ) -> str:
        """Commit changes with self-modification marker.

        Args:
            message: Commit message
            files: Specific files to commit (None = all changes)

        Returns:
            Commit hash
        """
        # Add files
        if files:
            for file in files:
                subprocess.run(
                    ["git", "add", file],
                    cwd=self.repo_path,
                    capture_output=True,
                    check=True,
                )
        else:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )

        # Commit with self-modification marker
        full_message = f"{message}\n\n[SELF-MODIFICATION]"

        subprocess.run(
            ["git", "commit", "-m", full_message],
            cwd=self.repo_path,
            capture_output=True,
            check=True,
        )

        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout.strip()

    def rollback(self) -> None:
        """Rollback to main branch and delete current feature branch.

        This is used when a self-modification fails testing.
        """
        current_branch = self.get_current_branch()

        # Switch to main/master
        try:
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            # Try master if main doesn't exist
            subprocess.run(
                ["git", "checkout", "master"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )

        # Delete the feature branch
        if current_branch not in ["main", "master"]:
            subprocess.run(
                ["git", "branch", "-D", current_branch],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )


class IsolatedTestEnvironment:
    """Isolated testing environment for self-modifications.

    Creates a safe environment for testing self-modifications before
    they are approved and merged to main.
    """

    def __init__(self, repo_path: str = ".") -> None:
        """Initialize isolated test environment.

        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = repo_path
        self.version_control = VersionControl(repo_path=repo_path)

    def create_test_branch(self, proposal: SelfModificationProposal) -> str:
        """Create an isolated test branch for a proposal.

        Args:
            proposal: The self-modification proposal

        Returns:
            Name of the created branch
        """
        # Create the feature branch
        subprocess.run(
            ["git", "checkout", "-b", proposal.test_branch_name],
            cwd=self.repo_path,
            capture_output=True,
            check=True,
        )

        return proposal.test_branch_name

    def run_tests_in_isolation(self) -> tuple[bool, str]:
        """Run full test suite in isolation.

        Returns:
            Tuple of (success: bool, output: str)
        """
        try:
            result = subprocess.run(
                ["pytest", "tests/", "-v"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            success = result.returncode == 0
            output = result.stdout + "\n" + result.stderr

            return success, output

        except subprocess.TimeoutExpired:
            return False, "Test execution timeout after 10 minutes"

        except Exception as e:
            return False, f"Test execution failed: {str(e)}"

    def cleanup(self) -> None:
        """Cleanup the test environment.

        Returns to main branch and deletes the test branch.
        """
        self.version_control.rollback()

    def prepare_for_merge(self) -> bool:
        """Validate that the branch is ready for merge.

        Returns:
            True if ready for merge, False otherwise
        """
        # Run tests
        tests_pass, _ = self.run_tests_in_isolation()
        if not tests_pass:
            return False

        # Could add more checks here:
        # - Code coverage requirements
        # - Linting checks
        # - Type checking
        # etc.

        return True


class SelfModificationApprovalGate(ApprovalGate):
    """Approval gate specifically for self-modifications.

    Extends the base ApprovalGate with self-modification-specific
    validation including recursion limit checks.
    """

    def __init__(
        self,
        timeout_seconds: float = 300.0,
        auto_deny_on_timeout: bool = True,
        recursion_limiter: RecursionLimiter | None = None,
    ) -> None:
        """Initialize self-modification approval gate.

        Args:
            timeout_seconds: How long to wait for approval
            auto_deny_on_timeout: Whether to auto-deny on timeout
            recursion_limiter: Recursion limiter instance
        """
        super().__init__(
            timeout_seconds=timeout_seconds,
            auto_deny_on_timeout=auto_deny_on_timeout,
        )
        self.recursion_limiter = recursion_limiter or RecursionLimiter()

    async def submit_self_modification(
        self,
        proposal: SelfModificationProposal,
        agent_id: str,
    ) -> str:
        """Submit a self-modification for approval.

        Args:
            proposal: The self-modification proposal
            agent_id: Agent submitting the proposal

        Returns:
            Request ID for tracking

        Raises:
            RecursionLimitExceeded: If recursion depth limit exceeded
        """
        # Check recursion limit
        if not self.recursion_limiter.check_limit():
            raise RecursionLimitExceededError(
                f"Maximum recursion depth {self.recursion_limiter.max_depth} "
                f"already reached. Cannot submit more modifications."
            )

        # Track this modification
        self.recursion_limiter.track_depth(proposal.proposal_id)

        # Create action for approval
        from src.security.access_control import Action, ActionType, Resource, ResourceType

        action = Action(
            action_type=ActionType.MODIFY,
            resource=Resource(
                ResourceType.FILE,
                f"self-modification:{proposal.proposal_id}",
            ),
            agent_id=agent_id,
        )

        # Submit for approval
        request_id = self.submit_request(
            action=action,
            requested_by=agent_id,
            reason=f"Self-modification: {proposal.description}\n"
            f"Target files: {', '.join(proposal.target_files)}\n"
            f"Recursion depth: {proposal.recursion_depth}",
        )

        proposal.approval_request_id = request_id
        proposal.status = ModificationStatus.TESTING

        return request_id

    async def wait_for_decision(self, request_id: str) -> bool:
        """Wait for approval decision.

        Args:
            request_id: ID of the approval request

        Returns:
            True if approved, False if denied
        """
        try:
            decision = await super().wait_for_approval(request_id)
            return decision.approved

        except Exception:
            return False

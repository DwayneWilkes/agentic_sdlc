"""Task Assignment Optimizer with Priority Queue."""

from dataclasses import dataclass

from src.models.agent import Agent
from src.models.priority import WorkQueueTask
from src.models.task import Subtask


@dataclass
class WorkloadInfo:
    """
    Tracks agent workload for load balancing.

    Counts both the number of assigned tasks and estimated token usage
    to enable fair distribution of work across agents.
    """

    agent_id: str
    assigned_tasks: int = 0
    estimated_tokens: int = 0


class TaskAssigner:
    """
    Assigns tasks to agents based on capabilities, priority, and workload balancing.

    Features:
    - Capability-based matching (assign tasks to agents with required skills)
    - Priority queue system (CRITICAL > HIGH > MEDIUM > LOW)
    - Workload balancing (distribute work evenly across capable agents)
    - Claim/release mechanism (prevent duplicate work)
    """

    def __init__(self, agents: list[Agent]):
        """
        Initialize the task assigner.

        Args:
            agents: List of available agents
        """
        self.agents = agents
        self.work_queue: list[WorkQueueTask] = []

    def add_tasks(self, subtasks: list[Subtask]) -> None:
        """
        Add subtasks to the work queue.

        Args:
            subtasks: List of subtasks to add to queue
        """
        for subtask in subtasks:
            wqt = WorkQueueTask.from_subtask(subtask)
            self.work_queue.append(wqt)

        # Sort by priority (highest first)
        self.work_queue.sort(key=lambda t: t.priority.priority_order, reverse=True)

    def _get_capability_match_score(self, agent: Agent, task: WorkQueueTask) -> int:
        """
        Calculate how well an agent's capabilities match a task's requirements.

        Args:
            agent: Agent to evaluate
            task: Task with capability requirements

        Returns:
            Score (number of matching capabilities)
        """
        required_capabilities = task.requirements.get("capabilities", [])
        if not required_capabilities:
            # No specific requirements, any agent can do it
            return 1

        # Count how many required capabilities the agent has
        agent_capability_names = [cap.name for cap in agent.capabilities]
        matches = sum(
            1 for req_cap in required_capabilities if req_cap in agent_capability_names
        )

        return matches

    def _get_agent_workload(self, agent_id: str) -> WorkloadInfo:
        """
        Get current workload for an agent.

        Args:
            agent_id: ID of agent to check

        Returns:
            WorkloadInfo with task count and token estimate
        """
        # Find the agent
        agent = next((a for a in self.agents if a.id == agent_id), None)
        if not agent:
            return WorkloadInfo(agent_id=agent_id)

        # Count claimed tasks and estimate tokens
        claimed_tasks = [t for t in self.work_queue if t.assigned_agent == agent_id]
        task_count = len(claimed_tasks)
        token_estimate = sum(t.estimated_tokens or 0 for t in claimed_tasks)

        return WorkloadInfo(
            agent_id=agent_id,
            assigned_tasks=task_count,
            estimated_tokens=token_estimate,
        )

    def assign_tasks(self) -> dict[str, str | None]:
        """
        Assign all tasks in the queue to capable agents with load balancing.

        Returns:
            Dictionary mapping task_id to assigned agent_id (or None if unassignable)
        """
        assignments: dict[str, str | None] = {}

        # Process tasks in priority order
        for task in self.work_queue:
            if task.assigned_agent:
                # Already assigned
                assignments[task.id] = task.assigned_agent
                continue

            # Find capable agents
            capable_agents = []
            for agent in self.agents:
                score = self._get_capability_match_score(agent, task)
                if score > 0:
                    capable_agents.append((agent, score))

            if not capable_agents:
                # No agent can do this task
                assignments[task.id] = None
                continue

            # Sort by capability match (higher better) then by workload (lower better)
            capable_agents.sort(
                key=lambda x: (
                    -x[1],  # Higher capability score first
                    self._get_agent_workload(x[0].id).assigned_tasks,  # Lower workload first
                    self._get_agent_workload(x[0].id).estimated_tokens,  # Lower tokens first
                )
            )

            # Assign to best agent
            best_agent = capable_agents[0][0]
            task.claim(best_agent.id)
            assignments[task.id] = best_agent.id

            # Update agent's assigned tasks list
            if task.id not in best_agent.assigned_tasks:
                best_agent.assigned_tasks.append(task.id)

        return assignments

    def claim_task(self, task_id: str, agent_id: str) -> bool:
        """
        Claim a specific task for an agent.

        Args:
            task_id: ID of task to claim
            agent_id: ID of agent claiming the task

        Returns:
            True if claim succeeded

        Raises:
            ValueError: If task is already claimed
        """
        task = next((t for t in self.work_queue if t.id == task_id), None)
        if not task:
            return False

        task.claim(agent_id)

        # Update agent's assigned tasks
        agent = next((a for a in self.agents if a.id == agent_id), None)
        if agent and task_id not in agent.assigned_tasks:
            agent.assigned_tasks.append(task_id)

        return True

    def release_task(self, task_id: str) -> bool:
        """
        Release a claimed task (make it available again).

        Args:
            task_id: ID of task to release

        Returns:
            True if release succeeded
        """
        task = next((t for t in self.work_queue if t.id == task_id), None)
        if not task or not task.assigned_agent:
            return False

        # Remove from agent's assigned tasks
        agent_id = task.assigned_agent
        agent = next((a for a in self.agents if a.id == agent_id), None)
        if agent and task_id in agent.assigned_tasks:
            agent.assigned_tasks.remove(task_id)

        task.release()
        return True

    def get_next_task(self, agent_id: str) -> WorkQueueTask | None:
        """
        Get the next highest-priority unassigned task that this agent can do.

        Args:
            agent_id: ID of agent requesting work

        Returns:
            Next task or None if no suitable tasks available
        """
        agent = next((a for a in self.agents if a.id == agent_id), None)
        if not agent:
            return None

        # Find highest priority unassigned task that agent can do
        for task in self.work_queue:
            if task.assigned_agent:
                continue

            score = self._get_capability_match_score(agent, task)
            if score > 0:
                return task

        return None

    def get_queue_status(self) -> dict[str, int]:
        """
        Get summary of queue status.

        Returns:
            Dictionary with counts by status
        """
        status_counts: dict[str, int] = {
            "total_tasks": len(self.work_queue),
            "pending": 0,
            "claimed": 0,
            "completed": 0,
            "failed": 0,
        }

        for task in self.work_queue:
            if task.status in status_counts:
                status_counts[task.status] += 1

        return status_counts

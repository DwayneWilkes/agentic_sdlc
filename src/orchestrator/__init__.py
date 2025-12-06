"""
Orchestrator - Coordinates autonomous agent teams.

The orchestrator:
- Reads the roadmap to identify available work streams
- Spawns autonomous agents for unblocked tasks
- Monitors agent progress via NATS
- Verifies work completion (tests, quality gates)
- Coordinates parallel execution
"""

from src.orchestrator.agent_runner import AgentProcess, AgentRunner, AgentState
from src.orchestrator.goal_interpreter import InterpretedGoal, interpret_goal
from src.orchestrator.orchestrator import Orchestrator, OrchestratorConfig, OrchestratorMode
from src.orchestrator.work_stream import (
    WorkStream,
    WorkStreamStatus,
    get_bootstrap_phases,
    get_prioritized_work_streams,
    parse_roadmap,
)

__all__ = [
    "Orchestrator",
    "OrchestratorConfig",
    "OrchestratorMode",
    "WorkStream",
    "WorkStreamStatus",
    "parse_roadmap",
    "get_bootstrap_phases",
    "get_prioritized_work_streams",
    "AgentRunner",
    "AgentProcess",
    "AgentState",
    "interpret_goal",
    "InterpretedGoal",
]

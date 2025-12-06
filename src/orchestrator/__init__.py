"""
Orchestrator - Coordinates autonomous agent teams.

The orchestrator:
- Reads the roadmap to identify available work streams
- Spawns autonomous agents for unblocked tasks
- Monitors agent progress via NATS
- Verifies work completion (tests, quality gates)
- Coordinates parallel execution
"""

from src.orchestrator.orchestrator import Orchestrator, OrchestratorConfig, OrchestratorMode
from src.orchestrator.work_stream import WorkStream, WorkStreamStatus, parse_roadmap
from src.orchestrator.agent_runner import AgentRunner, AgentProcess, AgentState
from src.orchestrator.goal_interpreter import interpret_goal, InterpretedGoal

__all__ = [
    "Orchestrator",
    "OrchestratorConfig",
    "OrchestratorMode",
    "WorkStream",
    "WorkStreamStatus",
    "parse_roadmap",
    "AgentRunner",
    "AgentProcess",
    "AgentState",
    "interpret_goal",
    "InterpretedGoal",
]

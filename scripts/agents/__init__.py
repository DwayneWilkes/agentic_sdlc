"""Python agent launchers for the orchestrator system.

This package contains Python implementations of agent launchers that replace
the bash scripts for better maintainability, testability, and prompt handling.

Usage:
    python -m scripts.agents.coder
    python -m scripts.agents.tech_lead
    python -m scripts.agents.pm
"""

from scripts.agents.base import AgentLauncher, AgentConfig

__all__ = ["AgentLauncher", "AgentConfig"]

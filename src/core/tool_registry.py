"""
Tool Registry - Tracks agent tool contributions and usage.

This module implements the tool creation incentive system:
- Tracks who creates tools and when
- Records tool usage by other agents
- Identifies "tool developer" experts for future assignments
- Counts tool creations as contributions in agent work history

Tools are identified by their MCP tool name and stored in config/tool_registry.json.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ToolRegistry:
    """Registry for tracking tool contributions and usage."""

    def __init__(self, config_path: Path | None = None, project_id: str | None = None):
        """
        Initialize tool registry.

        Args:
            config_path: Path to tool_registry.json. Defaults to config/tool_registry.json.
            project_id: Current project identifier.
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "tool_registry.json"

        self.config_path = config_path
        self.project_id = project_id or config_path.parent.parent.name
        self.data = self._load_data()

    def _load_data(self) -> dict:
        """Load registry from JSON file."""
        if not self.config_path.exists():
            return {
                "tools": {},
                "agent_contributions": {},
                "last_updated": None,
            }

        with open(self.config_path) as f:
            return json.load(f)

    def _save_data(self) -> None:
        """Save registry to JSON file."""
        self.data["last_updated"] = datetime.now().isoformat()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.data, f, indent=2)
            f.write("\n")

    def register_tool(
        self,
        tool_name: str,
        creator_name: str,
        description: str,
        tool_type: str = "mcp",
        file_path: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """
        Register a new tool creation by an agent.

        Args:
            tool_name: Unique tool identifier (e.g., "analyze_task")
            creator_name: Agent's personal name who created it
            description: What the tool does
            tool_type: Type of tool (mcp, python_function, script)
            file_path: Path to the tool's source file
            project_id: Project where tool was created

        Returns:
            Tool registration record
        """
        project = project_id or self.project_id

        # Create tool entry
        tool_record = {
            "name": tool_name,
            "creator": creator_name,
            "description": description,
            "type": tool_type,
            "file_path": file_path,
            "project": project,
            "created_at": datetime.now().isoformat(),
            "usage_count": 0,
            "users": [],  # Agents who have used this tool
        }

        # Store by tool name
        self.data["tools"][tool_name] = tool_record

        # Update agent contributions
        if creator_name not in self.data["agent_contributions"]:
            self.data["agent_contributions"][creator_name] = {
                "tools_created": [],
                "tools_used": [],
                "tool_developer_score": 0,
            }

        agent = self.data["agent_contributions"][creator_name]
        if tool_name not in agent["tools_created"]:
            agent["tools_created"].append(tool_name)
            agent["tool_developer_score"] += 10  # Base score for creation

        self._save_data()
        return tool_record

    def record_tool_usage(
        self,
        tool_name: str,
        user_name: str,
        context: str | None = None,
    ) -> bool:
        """
        Record that an agent used a tool created by another agent.

        This rewards the tool creator with additional score.

        Args:
            tool_name: Name of the tool used
            user_name: Agent who used the tool
            context: Optional context about the usage

        Returns:
            True if recorded successfully
        """
        if tool_name not in self.data["tools"]:
            return False

        tool = self.data["tools"][tool_name]
        tool["usage_count"] += 1

        # Track unique users
        if user_name not in tool["users"]:
            tool["users"].append(user_name)

            # Award bonus to creator when their tool is adopted by a new agent
            creator = tool["creator"]
            if creator in self.data["agent_contributions"]:
                # +5 for each unique adopter
                self.data["agent_contributions"][creator]["tool_developer_score"] += 5

        # Track what tools this agent has used
        if user_name not in self.data["agent_contributions"]:
            self.data["agent_contributions"][user_name] = {
                "tools_created": [],
                "tools_used": [],
                "tool_developer_score": 0,
            }

        if tool_name not in self.data["agent_contributions"][user_name]["tools_used"]:
            self.data["agent_contributions"][user_name]["tools_used"].append(tool_name)

        self._save_data()
        return True

    def get_tool(self, tool_name: str) -> dict | None:
        """Get a tool's registration record."""
        return self.data["tools"].get(tool_name)

    def get_tools_by_creator(self, creator_name: str) -> list[dict]:
        """Get all tools created by an agent."""
        return [
            tool for tool in self.data["tools"].values()
            if tool["creator"] == creator_name
        ]

    def get_top_tool_developers(self, limit: int = 5) -> list[tuple[str, int]]:
        """
        Get agents ranked by tool development contribution.

        Returns:
            List of (agent_name, score) tuples, highest first
        """
        contributions = self.data["agent_contributions"]
        ranked = sorted(
            [(name, data["tool_developer_score"]) for name, data in contributions.items()],
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:limit]

    def get_most_used_tools(self, limit: int = 10) -> list[dict]:
        """Get tools ranked by usage count."""
        tools = sorted(
            self.data["tools"].values(),
            key=lambda x: x["usage_count"],
            reverse=True,
        )
        return tools[:limit]

    def get_agent_contribution_summary(self, agent_name: str) -> dict[str, Any]:
        """
        Get summary of an agent's tool contributions.

        Returns:
            Dict with tools_created, tools_used, score, and ranking
        """
        if agent_name not in self.data["agent_contributions"]:
            return {
                "tools_created": [],
                "tools_used": [],
                "tool_developer_score": 0,
                "rank": None,
            }

        contribution = self.data["agent_contributions"][agent_name]

        # Calculate rank
        rankings = self.get_top_tool_developers(limit=100)
        rank = next(
            (i + 1 for i, (name, _) in enumerate(rankings) if name == agent_name),
            None
        )

        return {
            "tools_created": contribution["tools_created"],
            "tools_used": contribution["tools_used"],
            "tool_developer_score": contribution["tool_developer_score"],
            "rank": rank,
        }

    def suggest_tool_developer_for_task(self, task_type: str) -> str | None:
        """
        Suggest the best agent for tool development tasks.

        This implements the "reuse excellent tool developers" pattern.

        Args:
            task_type: Type of task needing a tool

        Returns:
            Name of recommended agent, or None if no data
        """
        rankings = self.get_top_tool_developers(limit=1)
        if rankings:
            return rankings[0][0]
        return None

    def list_available_tools(self, tool_type: str | None = None) -> list[dict]:
        """
        List all available tools for agents to use.

        Args:
            tool_type: Filter by type (mcp, python_function, script)

        Returns:
            List of tool records
        """
        tools = list(self.data["tools"].values())
        if tool_type:
            tools = [t for t in tools if t["type"] == tool_type]
        return tools


# Singleton instance
_registry_instance: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance


def register_tool_contribution(
    tool_name: str,
    creator_name: str,
    description: str,
    tool_type: str = "mcp",
    file_path: str | None = None,
) -> dict:
    """
    Convenience function to register a tool contribution.

    Args:
        tool_name: Unique tool identifier
        creator_name: Agent who created it
        description: What the tool does
        tool_type: Type of tool
        file_path: Source file path

    Returns:
        Tool registration record
    """
    registry = get_tool_registry()
    return registry.register_tool(
        tool_name, creator_name, description, tool_type, file_path
    )


def record_tool_use(tool_name: str, user_name: str) -> bool:
    """
    Convenience function to record tool usage.

    Args:
        tool_name: Tool being used
        user_name: Agent using it

    Returns:
        True if recorded
    """
    registry = get_tool_registry()
    return registry.record_tool_usage(tool_name, user_name)

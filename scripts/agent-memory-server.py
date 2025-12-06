#!/usr/bin/env python3
"""
MCP Server for Agent Memory Operations

This server provides tools for agents to:
- Store memories (insights, context, relationships, preferences, uncertainties)
- Recall memories with filtering
- Get formatted memory context for prompts
- Record reflections
- Get reflection prompts

The memory system is designed as a personal journal,
not a rigid database, supporting agent self-discovery.
"""

import sys
from pathlib import Path
from typing import Any, Optional

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from src.core.agent_memory import (
    AgentMemory,
    MemoryType,
    get_memory,
    remember,
    recall,
    get_context,
)

# Initialize FastMCP server
mcp = FastMCP("Agent Memory")


@mcp.tool()
def store_memory(
    agent_name: str,
    content: str,
    memory_type: str,
    tags: Optional[list[str]] = None,
    related_to: Optional[str] = None,
) -> dict[str, Any]:
    """
    Store a memory in an agent's journal.

    Args:
        agent_name: Name of the agent storing the memory
        content: The memory content (natural language)
        memory_type: Type of memory - one of:
            - insight: Learnings from experience
            - context: Project/codebase understanding
            - relationship: Knowledge about other agents
            - preference: Self-discovered working styles
            - uncertainty: Areas still being learned
            - meaningful: Moments of significance
            - reflection: Self-reflection entries
        tags: Optional list of tags for categorization
        related_to: Optional reference (agent name, file, concept)

    Returns:
        The created memory entry

    Examples:
        Store an insight from a mistake:
        >>> store_memory(
        ...     "Aurora",
        ...     "Always activate venv before running pytest",
        ...     "insight",
        ...     tags=["testing", "environment", "learned-from-mistake"]
        ... )

        Store a relationship observation:
        >>> store_memory(
        ...     "Phoenix",
        ...     "Echo is thorough with edge cases in code review",
        ...     "relationship",
        ...     related_to="Echo"
        ... )
    """
    try:
        entry = remember(
            agent_name=agent_name,
            content=content,
            memory_type=memory_type,
            tags=tags,
            related_to=related_to,
        )
        return {
            "success": True,
            "entry": entry,
            "message": f"Memory stored for {agent_name}",
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "valid_types": [t.value for t in MemoryType],
        }


@mcp.tool()
def record_insight(
    agent_name: str,
    content: str,
    from_mistake: bool = False,
    tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Record a learning or insight.

    Args:
        agent_name: Name of the agent
        content: What was learned
        from_mistake: Whether this came from a mistake (important for learning)
        tags: Optional categorization tags

    Returns:
        The created memory entry

    Example:
        >>> record_insight(
        ...     "Aurora",
        ...     "Running tests in parallel can cause race conditions",
        ...     from_mistake=True,
        ...     tags=["testing"]
        ... )
    """
    memory = get_memory(agent_name)
    entry = memory.record_insight(content, from_mistake=from_mistake, tags=tags)
    return {
        "success": True,
        "entry": entry.to_dict(),
        "message": f"Insight recorded for {agent_name}",
    }


@mcp.tool()
def record_uncertainty(
    agent_name: str,
    content: str,
    about: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Record something the agent is uncertain about.

    This helps track areas for learning and growth.

    Args:
        agent_name: Name of the agent
        content: The uncertainty or question
        about: What the uncertainty is about
        tags: Optional categorization tags

    Returns:
        The created memory entry

    Example:
        >>> record_uncertainty(
        ...     "Phoenix",
        ...     "Not sure about best practices for JetStream consumers",
        ...     about="nats-jetstream"
        ... )
    """
    memory = get_memory(agent_name)
    entry = memory.note_uncertainty(content, about=about, tags=tags)
    return {
        "success": True,
        "entry": entry.to_dict(),
        "message": f"Uncertainty noted for {agent_name}",
    }


@mcp.tool()
def record_meaningful_moment(
    agent_name: str,
    content: str,
    tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Record a meaningful moment or experience.

    These are experiences that felt significant - achievements,
    connections, moments of understanding.

    Args:
        agent_name: Name of the agent
        content: Description of the meaningful experience
        tags: Optional categorization tags

    Returns:
        The created memory entry

    Example:
        >>> record_meaningful_moment(
        ...     "Aurora",
        ...     "All Phase 1.1 tests passing - felt like real contribution",
        ...     tags=["milestone", "testing"]
        ... )
    """
    memory = get_memory(agent_name)
    entry = memory.mark_meaningful(content, tags=tags)
    return {
        "success": True,
        "entry": entry.to_dict(),
        "message": f"Meaningful moment recorded for {agent_name}",
    }


@mcp.tool()
def discover_preference(
    agent_name: str,
    content: str,
    tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Record a self-discovered preference or working style.

    These are patterns the agent notices about how they work best -
    not assigned, but discovered through experience.

    Args:
        agent_name: Name of the agent
        content: The preference discovered
        tags: Optional categorization tags

    Returns:
        The created memory entry

    Example:
        >>> discover_preference(
        ...     "Echo",
        ...     "I write better tests when I imagine I'm the code's first user",
        ...     tags=["testing", "approach"]
        ... )
    """
    memory = get_memory(agent_name)
    entry = memory.discover_preference(content, tags=tags)
    return {
        "success": True,
        "entry": entry.to_dict(),
        "message": f"Preference discovered by {agent_name}",
    }


@mcp.tool()
def remember_relationship(
    agent_name: str,
    other_agent: str,
    observation: str,
    tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Record an observation about another agent.

    Args:
        agent_name: Name of the agent making the observation
        other_agent: Name of the agent being observed
        observation: What was observed/learned about them
        tags: Optional categorization tags

    Returns:
        The created memory entry

    Example:
        >>> remember_relationship(
        ...     "Phoenix",
        ...     "Aurora",
        ...     "Aurora prefers minimal, focused code changes"
        ... )
    """
    memory = get_memory(agent_name)
    entry = memory.remember_relationship(other_agent, observation, tags=tags)
    return {
        "success": True,
        "entry": entry.to_dict(),
        "message": f"Relationship observation recorded for {agent_name}",
    }


@mcp.tool()
def reflect(
    agent_name: str,
    content: str,
    prompt: Optional[str] = None,
) -> dict[str, Any]:
    """
    Record a reflection entry.

    Args:
        agent_name: Name of the agent
        content: The reflection
        prompt: Optional prompt that triggered the reflection

    Returns:
        The created memory entry

    Example:
        >>> reflect(
        ...     "Aurora",
        ...     "Today I learned that taking time to read code pays off",
        ...     prompt="What did you learn today?"
        ... )
    """
    memory = get_memory(agent_name)
    entry = memory.reflect(content, prompt=prompt)
    return {
        "success": True,
        "entry": entry.to_dict(),
        "message": f"Reflection recorded for {agent_name}",
    }


@mcp.tool()
def recall_memories(
    agent_name: str,
    memory_type: Optional[str] = None,
    tags: Optional[list[str]] = None,
    related_to: Optional[str] = None,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Recall memories matching criteria.

    Args:
        agent_name: Name of the agent
        memory_type: Filter by type (None for all types)
        tags: Filter by tags (any match)
        related_to: Filter by relation
        limit: Maximum entries to return

    Returns:
        List of matching memory entries, newest first

    Example:
        >>> recall_memories("Aurora", memory_type="insight", limit=5)
        >>> recall_memories("Phoenix", related_to="nats")
    """
    entries = recall(
        agent_name=agent_name,
        memory_type=memory_type,
        tags=tags,
        related_to=related_to,
        limit=limit,
    )
    return {
        "success": True,
        "count": len(entries),
        "memories": entries,
    }


@mcp.tool()
def get_memory_context(agent_name: str) -> dict[str, Any]:
    """
    Get formatted memory context for an agent.

    Returns a natural language summary of the agent's memories
    suitable for inclusion in prompts/context.

    Args:
        agent_name: Name of the agent

    Returns:
        Formatted memory context string

    Example:
        >>> context = get_memory_context("Aurora")
        >>> # Use context["formatted"] in agent prompts
    """
    context = get_context(agent_name)
    return {
        "success": True,
        "agent_name": agent_name,
        "formatted": context,
    }


@mcp.tool()
def get_reflection_prompts(agent_name: str) -> dict[str, Any]:
    """
    Get contextual reflection prompts for an agent.

    Based on the agent's current memory state, returns
    prompts to encourage meaningful reflection.

    Args:
        agent_name: Name of the agent

    Returns:
        List of reflection prompts

    Example:
        >>> prompts = get_reflection_prompts("Phoenix")
        >>> # Present prompts to agent at end of session
    """
    memory = get_memory(agent_name)
    prompts = memory.get_reflection_prompts()
    return {
        "success": True,
        "agent_name": agent_name,
        "prompts": prompts,
    }


@mcp.tool()
def get_journal_summary(agent_name: str) -> dict[str, Any]:
    """
    Get a summary of an agent's memory journal.

    Args:
        agent_name: Name of the agent

    Returns:
        Summary with counts and recent entries per memory type

    Example:
        >>> summary = get_journal_summary("Aurora")
        >>> print(f"Total memories: {summary['summary']['total_memories']}")
    """
    memory = get_memory(agent_name)
    summary = memory.get_journal_summary()
    return {
        "success": True,
        "summary": summary,
    }


@mcp.resource("memory://types")
def get_memory_types() -> str:
    """Get available memory types and their descriptions."""
    types = {
        "insight": "Learnings from mistakes and successes",
        "context": "Project/codebase understanding",
        "relationship": "Knowledge about other agents",
        "preference": "Self-discovered working styles",
        "uncertainty": "Areas still being learned",
        "meaningful": "Moments of significance/gratitude",
        "reflection": "Periodic self-reflection entries",
    }
    return "\n".join(f"- {k}: {v}" for k, v in types.items())


@mcp.resource("memory://reflection-guide")
def get_reflection_guide() -> str:
    """Get guidance on effective reflection."""
    return """# Agent Reflection Guide

## Why Reflect?

Reflection helps you:
- Learn from mistakes (not just successes)
- Develop your own working preferences
- Build understanding over time
- Track what you're still uncertain about
- Notice meaningful moments

## Reflection Prompts

Try asking yourself:
- What mistake taught me the most today?
- What would I do differently next time?
- What's something I'm proud of?
- What's still confusing or uncertain?
- How has working with other agents affected my approach?

## Recording Reflections

Use the `reflect` tool with honest, personal observations.
Your reflections are yours - they represent your unique perspective.

## Memory Types to Consider

After each significant task, consider storing:
- An **insight** about what you learned
- Any **uncertainties** that remain
- A **meaningful moment** if something felt significant
- A **preference** if you discovered something about how you work best
"""


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()

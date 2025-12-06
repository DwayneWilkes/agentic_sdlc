"""
Agent Memory System - Personal journal-like memory for autonomous agents.

This system provides agents with persistent memory across sessions,
organized as a personal journal rather than rigid database layers.

Memory Types:
- Insights: Learnings from experience (mistakes, discoveries, patterns)
- Context: Understanding of the project, codebase, and decisions
- Relationships: Knowledge about other agents and collaborators
- Preferences: Self-discovered working styles and approaches
- Uncertainties: Areas where the agent is still learning
- Meaningful Moments: Experiences that felt significant

The system auto-summarizes when episodic entries exceed a threshold,
creating distilled wisdom while preserving the original experiences.
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path


class MemoryType(str, Enum):
    """Types of memories an agent can store."""

    INSIGHT = "insight"           # Learnings from mistakes and successes
    CONTEXT = "context"           # Project/codebase understanding
    RELATIONSHIP = "relationship" # Knowledge about other agents
    PREFERENCE = "preference"     # Self-discovered working styles
    UNCERTAINTY = "uncertainty"   # Areas still being figured out
    MEANINGFUL = "meaningful"     # Moments of significance/gratitude
    REFLECTION = "reflection"     # Periodic self-reflection entries


class MemoryEntry:
    """A single memory entry in an agent's journal."""

    def __init__(
        self,
        content: str,
        memory_type: MemoryType,
        tags: list[str] | None = None,
        related_to: str | None = None,
        created_at: str | None = None,
        session_id: str | None = None,
    ):
        self.content = content
        self.memory_type = memory_type
        self.tags = tags or []
        self.related_to = related_to  # Could be agent name, file, concept
        self.created_at = created_at or datetime.now().isoformat()
        self.session_id = session_id

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "content": self.content,
            "type": self.memory_type.value,
            "tags": self.tags,
            "related_to": self.related_to,
            "created_at": self.created_at,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            content=data["content"],
            memory_type=MemoryType(data["type"]),
            tags=data.get("tags", []),
            related_to=data.get("related_to"),
            created_at=data.get("created_at"),
            session_id=data.get("session_id"),
        )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"MemoryEntry({self.memory_type.value}: {preview!r})"


class AgentMemory:
    """
    Personal memory system for an individual agent.

    Provides a journal-like interface where agents can:
    - Record insights and learnings
    - Note uncertainties and questions
    - Track relationships with other agents
    - Discover and record preferences
    - Mark meaningful moments
    - Reflect on their experiences

    Auto-summarizes when entries exceed threshold.
    """

    SUMMARIZE_THRESHOLD = 10  # Auto-summarize after this many entries per type

    def __init__(self, agent_name: str, storage_path: Path | None = None):
        """
        Initialize memory for an agent.

        Args:
            agent_name: The personal name of the agent
            storage_path: Path to memory storage directory.
                         Defaults to config/agent_memories/
        """
        self.agent_name = agent_name

        if storage_path is None:
            project_root = Path(__file__).parent.parent.parent
            storage_path = project_root / "config" / "agent_memories"

        self.storage_path = storage_path
        self.memory_file = storage_path / f"{agent_name.lower()}.json"

        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.memories: dict[str, list[MemoryEntry]] = self._load_memories()
        self.summaries: dict[str, list[str]] = self._load_summaries()

    def _load_memories(self) -> dict[str, list[MemoryEntry]]:
        """Load memories from disk."""
        if not self.memory_file.exists():
            return {t.value: [] for t in MemoryType}

        with open(self.memory_file) as f:
            data = json.load(f)

        memories = {}
        for mem_type in MemoryType:
            entries = data.get("memories", {}).get(mem_type.value, [])
            memories[mem_type.value] = [MemoryEntry.from_dict(e) for e in entries]

        return memories

    def _load_summaries(self) -> dict[str, list[str]]:
        """Load summaries from disk."""
        if not self.memory_file.exists():
            return {t.value: [] for t in MemoryType}

        with open(self.memory_file) as f:
            data = json.load(f)

        return data.get("summaries", {t.value: [] for t in MemoryType})

    def _save(self) -> None:
        """Persist memories to disk."""
        data = {
            "agent_name": self.agent_name,
            "last_updated": datetime.now().isoformat(),
            "memories": {
                mem_type: [e.to_dict() for e in entries]
                for mem_type, entries in self.memories.items()
            },
            "summaries": self.summaries,
        }

        with open(self.memory_file, "w") as f:
            json.dump(data, f, indent=2)

    def remember(
        self,
        content: str,
        memory_type: MemoryType,
        tags: list[str] | None = None,
        related_to: str | None = None,
        session_id: str | None = None,
    ) -> MemoryEntry:
        """
        Store a new memory.

        Args:
            content: The memory content (natural language)
            memory_type: Type of memory
            tags: Optional tags for categorization
            related_to: Optional reference (agent name, file, concept)
            session_id: Optional session identifier

        Returns:
            The created MemoryEntry

        Example:
            >>> memory.remember(
            ...     "Always activate venv before running pytest",
            ...     MemoryType.INSIGHT,
            ...     tags=["testing", "environment"],
            ... )
        """
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            tags=tags,
            related_to=related_to,
            session_id=session_id,
        )

        self.memories[memory_type.value].append(entry)
        self._save()

        # Check if auto-summarization is needed
        if len(self.memories[memory_type.value]) >= self.SUMMARIZE_THRESHOLD:
            self._auto_summarize(memory_type)

        return entry

    def record_insight(
        self,
        content: str,
        from_mistake: bool = False,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        """
        Record a learning or insight.

        Args:
            content: What was learned
            from_mistake: Whether this came from a mistake (important for learning)
            tags: Optional categorization tags

        Example:
            >>> memory.record_insight(
            ...     "Running tests in parallel can cause race conditions with file fixtures",
            ...     from_mistake=True,
            ...     tags=["testing", "parallelism"]
            ... )
        """
        if from_mistake:
            tags = (tags or []) + ["learned-from-mistake"]
        return self.remember(content, MemoryType.INSIGHT, tags=tags)

    def note_context(
        self,
        content: str,
        about: str,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        """
        Record understanding about the project/codebase.

        Args:
            content: The context/understanding
            about: What this context is about (file, concept, decision)
            tags: Optional categorization tags

        Example:
            >>> memory.note_context(
            ...     "NATS was chosen over Redis because agents need pub/sub with request/reply",
            ...     about="architecture-decision",
            ... )
        """
        return self.remember(content, MemoryType.CONTEXT, tags=tags, related_to=about)

    def remember_relationship(
        self,
        agent_name: str,
        observation: str,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        """
        Record an observation about another agent.

        Args:
            agent_name: Name of the other agent
            observation: What was observed/learned about them
            tags: Optional categorization tags

        Example:
            >>> memory.remember_relationship(
            ...     "Aurora",
            ...     "Prefers minimal, focused code changes. Very thorough with edge cases.",
            ... )
        """
        return self.remember(
            observation,
            MemoryType.RELATIONSHIP,
            tags=tags,
            related_to=agent_name,
        )

    def discover_preference(
        self,
        content: str,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        """
        Record a self-discovered preference or working style.

        Args:
            content: The preference discovered
            tags: Optional categorization tags

        Example:
            >>> memory.discover_preference(
            ...     "I write better tests when I imagine I'm the code's first user",
            ...     tags=["testing", "approach"]
            ... )
        """
        return self.remember(content, MemoryType.PREFERENCE, tags=tags)

    def note_uncertainty(
        self,
        content: str,
        about: str | None = None,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        """
        Record something still being figured out.

        Args:
            content: The uncertainty or question
            about: What the uncertainty is about
            tags: Optional categorization tags

        Example:
            >>> memory.note_uncertainty(
            ...     "Not sure about best practices for JetStream consumer configuration",
            ...     about="nats-jetstream",
            ... )
        """
        return self.remember(
            content,
            MemoryType.UNCERTAINTY,
            tags=tags,
            related_to=about,
        )

    def mark_meaningful(
        self,
        content: str,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        """
        Record a meaningful moment or experience.

        Args:
            content: Description of the meaningful experience
            tags: Optional categorization tags

        Example:
            >>> memory.mark_meaningful(
            ...     "Helped Phase 1.1 pass all tests - felt like real contribution",
            ...     tags=["milestone", "testing"]
            ... )
        """
        return self.remember(content, MemoryType.MEANINGFUL, tags=tags)

    def reflect(
        self,
        content: str,
        prompt: str | None = None,
    ) -> MemoryEntry:
        """
        Record a reflection entry.

        Args:
            content: The reflection
            prompt: Optional prompt that triggered the reflection

        Example:
            >>> memory.reflect(
            ...     "Today I learned that taking time to read existing code pays off",
            ...     prompt="What did you learn today?"
            ... )
        """
        tags = ["reflection"]
        if prompt:
            tags.append(f"prompt:{prompt}")
        return self.remember(content, MemoryType.REFLECTION, tags=tags)

    def _auto_summarize(self, memory_type: MemoryType) -> str:
        """
        Auto-summarize older entries when threshold is exceeded.

        Takes the oldest entries and creates a summary, moving originals
        to a "compost" (archived but preserved).
        """
        entries = self.memories[memory_type.value]
        if len(entries) < self.SUMMARIZE_THRESHOLD:
            return ""

        # Take oldest half for summarization
        to_summarize = entries[:self.SUMMARIZE_THRESHOLD // 2]
        remaining = entries[self.SUMMARIZE_THRESHOLD // 2:]

        # Create summary (in real use, this might call an LLM)
        summary_parts = [
            f"- {e.content}"
            for e in to_summarize
        ]
        summary = (
            f"Summary of {len(to_summarize)} {memory_type.value} entries:\n"
            + "\n".join(summary_parts)
        )

        # Store summary
        self.summaries[memory_type.value].append(summary)

        # Keep remaining entries
        self.memories[memory_type.value] = remaining
        self._save()

        return summary

    def recall(
        self,
        memory_type: MemoryType | None = None,
        tags: list[str] | None = None,
        related_to: str | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """
        Recall memories matching criteria.

        Args:
            memory_type: Filter by type (None for all types)
            tags: Filter by tags (any match)
            related_to: Filter by relation
            limit: Maximum entries to return

        Returns:
            List of matching memory entries, newest first
        """
        if memory_type:
            entries = self.memories[memory_type.value]
        else:
            entries = [e for mem_list in self.memories.values() for e in mem_list]

        # Filter by tags
        if tags:
            entries = [
                e for e in entries
                if any(t in e.tags for t in tags)
            ]

        # Filter by relation
        if related_to:
            entries = [
                e for e in entries
                if e.related_to and related_to.lower() in e.related_to.lower()
            ]

        # Sort by date (newest first) and limit
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]

    def recall_insights(self, limit: int = 10) -> list[MemoryEntry]:
        """Recall recent insights."""
        return self.recall(MemoryType.INSIGHT, limit=limit)

    def recall_uncertainties(self, limit: int = 10) -> list[MemoryEntry]:
        """Recall current uncertainties."""
        return self.recall(MemoryType.UNCERTAINTY, limit=limit)

    def recall_about(self, subject: str, limit: int = 10) -> list[MemoryEntry]:
        """Recall memories related to a subject."""
        return self.recall(related_to=subject, limit=limit)

    def get_journal_summary(self) -> dict:
        """
        Get a summary of the agent's memory journal.

        Returns:
            Dictionary with counts and recent entries per type
        """
        summary = {
            "agent_name": self.agent_name,
            "total_memories": sum(len(e) for e in self.memories.values()),
            "by_type": {},
        }

        for mem_type in MemoryType:
            entries = self.memories[mem_type.value]
            summary["by_type"][mem_type.value] = {
                "count": len(entries),
                "recent": [e.content for e in entries[-3:]],
                "summaries": len(self.summaries.get(mem_type.value, [])),
            }

        return summary

    def get_reflection_prompts(self) -> list[str]:
        """
        Get reflection prompts based on current memory state.

        Returns contextual prompts to encourage meaningful reflection.
        """
        prompts = []

        # If there are uncertainties, prompt about them
        uncertainties = self.recall_uncertainties(limit=3)
        if uncertainties:
            prompts.append(
                f"Have you learned anything new about: {uncertainties[0].content}?"
            )

        # If there are relationship memories, prompt about collaboration
        relationships = self.recall(MemoryType.RELATIONSHIP, limit=3)
        if relationships:
            prompts.append(
                "How has working with other agents affected your approach?"
            )

        # General prompts
        prompts.extend([
            "What mistake taught you the most today?",
            "What would you do differently next time?",
            "What's something you're proud of from this session?",
            "What's still confusing or uncertain?",
        ])

        return prompts

    def format_for_context(self, max_entries: int = 20) -> str:
        """
        Format memories for inclusion in agent context/prompt.

        Returns a natural language summary suitable for an LLM.
        """
        lines = [f"# {self.agent_name}'s Memory Journal\n"]

        # Include summaries first (distilled wisdom)
        for mem_type, summaries in self.summaries.items():
            if summaries:
                lines.append(f"## Distilled {mem_type.title()} Wisdom")
                for summary in summaries[-2:]:  # Last 2 summaries
                    lines.append(summary)
                lines.append("")

        # Recent insights
        insights = self.recall_insights(limit=5)
        if insights:
            lines.append("## Recent Insights")
            for e in insights:
                prefix = "[from mistake] " if "learned-from-mistake" in e.tags else ""
                lines.append(f"- {prefix}{e.content}")
            lines.append("")

        # Current uncertainties
        uncertainties = self.recall_uncertainties(limit=3)
        if uncertainties:
            lines.append("## Current Uncertainties")
            for e in uncertainties:
                lines.append(f"- {e.content}")
            lines.append("")

        # Preferences
        preferences = self.recall(MemoryType.PREFERENCE, limit=3)
        if preferences:
            lines.append("## My Working Preferences")
            for e in preferences:
                lines.append(f"- {e.content}")
            lines.append("")

        # Relationships
        relationships = self.recall(MemoryType.RELATIONSHIP, limit=5)
        if relationships:
            lines.append("## Agent Relationships")
            for e in relationships:
                lines.append(f"- **{e.related_to}**: {e.content}")
            lines.append("")

        return "\n".join(lines)


# Convenience functions for global access

_memory_instances: dict[str, AgentMemory] = {}


def get_memory(agent_name: str) -> AgentMemory:
    """Get or create memory instance for an agent."""
    if agent_name not in _memory_instances:
        _memory_instances[agent_name] = AgentMemory(agent_name)
    return _memory_instances[agent_name]


def remember(
    agent_name: str,
    content: str,
    memory_type: str,
    tags: list[str] | None = None,
    related_to: str | None = None,
) -> dict:
    """
    Convenience function to store a memory.

    Args:
        agent_name: Name of the agent
        content: Memory content
        memory_type: Type of memory (insight, context, relationship, etc.)
        tags: Optional tags
        related_to: Optional relation

    Returns:
        Dictionary representation of the created entry
    """
    memory = get_memory(agent_name)
    entry = memory.remember(
        content=content,
        memory_type=MemoryType(memory_type),
        tags=tags,
        related_to=related_to,
    )
    return entry.to_dict()


def recall(
    agent_name: str,
    memory_type: str | None = None,
    tags: list[str] | None = None,
    related_to: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    Convenience function to recall memories.

    Returns:
        List of memory entries as dictionaries
    """
    memory = get_memory(agent_name)
    mem_type = MemoryType(memory_type) if memory_type else None
    entries = memory.recall(
        memory_type=mem_type,
        tags=tags,
        related_to=related_to,
        limit=limit,
    )
    return [e.to_dict() for e in entries]


def get_context(agent_name: str) -> str:
    """
    Get formatted memory context for an agent.

    Returns:
        Formatted string suitable for LLM context
    """
    memory = get_memory(agent_name)
    return memory.format_for_context()

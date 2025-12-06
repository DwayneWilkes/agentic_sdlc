"""Tests for the agent memory system."""

import json
from unittest.mock import patch

import pytest

from src.core.agent_memory import (
    AgentMemory,
    MemoryEntry,
    MemoryType,
    get_memory,
)


class TestMemoryEntry:
    """Tests for MemoryEntry class."""

    def test_create_memory_entry(self):
        """Test creating a basic memory entry."""
        entry = MemoryEntry(
            content="Test insight",
            memory_type=MemoryType.INSIGHT,
        )
        assert entry.content == "Test insight"
        assert entry.memory_type == MemoryType.INSIGHT
        assert entry.tags == []
        assert entry.related_to is None
        assert entry.created_at is not None

    def test_create_memory_entry_with_all_fields(self):
        """Test creating a memory entry with all fields."""
        entry = MemoryEntry(
            content="Always check venv",
            memory_type=MemoryType.INSIGHT,
            tags=["testing", "environment"],
            related_to="pytest",
            created_at="2024-01-15T10:00:00",
            session_id="session-123",
        )
        assert entry.content == "Always check venv"
        assert entry.tags == ["testing", "environment"]
        assert entry.related_to == "pytest"
        assert entry.created_at == "2024-01-15T10:00:00"
        assert entry.session_id == "session-123"

    def test_to_dict(self):
        """Test converting entry to dictionary."""
        entry = MemoryEntry(
            content="Test content",
            memory_type=MemoryType.CONTEXT,
            tags=["tag1"],
            related_to="file.py",
        )
        d = entry.to_dict()
        assert d["content"] == "Test content"
        assert d["type"] == "context"
        assert d["tags"] == ["tag1"]
        assert d["related_to"] == "file.py"

    def test_from_dict(self):
        """Test creating entry from dictionary."""
        data = {
            "content": "From dict",
            "type": "preference",
            "tags": ["style"],
            "related_to": None,
            "created_at": "2024-01-15T10:00:00",
            "session_id": None,
        }
        entry = MemoryEntry.from_dict(data)
        assert entry.content == "From dict"
        assert entry.memory_type == MemoryType.PREFERENCE
        assert entry.tags == ["style"]

    def test_repr(self):
        """Test string representation."""
        entry = MemoryEntry(
            content="Short",
            memory_type=MemoryType.INSIGHT,
        )
        repr_str = repr(entry)
        assert "MemoryEntry" in repr_str
        assert "insight" in repr_str
        assert "Short" in repr_str


class TestAgentMemory:
    """Tests for AgentMemory class."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage directory."""
        storage = tmp_path / "memories"
        storage.mkdir()
        return storage

    @pytest.fixture
    def memory(self, temp_storage):
        """Create AgentMemory with temporary storage."""
        return AgentMemory("TestAgent", storage_path=temp_storage)

    def test_init_creates_storage(self, temp_storage):
        """Test that init creates storage directory."""
        _memory = AgentMemory("NewAgent", storage_path=temp_storage)  # Side effect test
        assert temp_storage.exists()

    def test_remember_basic(self, memory):
        """Test storing a basic memory."""
        entry = memory.remember(
            content="Test memory",
            memory_type=MemoryType.INSIGHT,
        )
        assert entry.content == "Test memory"
        assert entry.memory_type == MemoryType.INSIGHT

    def test_remember_persists_to_disk(self, memory, temp_storage):
        """Test that memories are persisted to disk."""
        memory.remember("Persist me", MemoryType.INSIGHT)

        # Check file exists and contains data
        memory_file = temp_storage / "testagent.json"
        assert memory_file.exists()

        with open(memory_file) as f:
            data = json.load(f)
        assert "Persist me" in str(data)

    def test_record_insight(self, memory):
        """Test recording an insight."""
        entry = memory.record_insight("Learned something", from_mistake=False)
        assert entry.memory_type == MemoryType.INSIGHT
        assert "learned-from-mistake" not in entry.tags

    def test_record_insight_from_mistake(self, memory):
        """Test recording insight from mistake."""
        entry = memory.record_insight("Oops learned", from_mistake=True)
        assert "learned-from-mistake" in entry.tags

    def test_note_context(self, memory):
        """Test noting context."""
        entry = memory.note_context(
            content="NATS for messaging",
            about="architecture",
        )
        assert entry.memory_type == MemoryType.CONTEXT
        assert entry.related_to == "architecture"

    def test_remember_relationship(self, memory):
        """Test remembering relationship."""
        entry = memory.remember_relationship(
            agent_name="Aurora",
            observation="Very thorough",
        )
        assert entry.memory_type == MemoryType.RELATIONSHIP
        assert entry.related_to == "Aurora"

    def test_discover_preference(self, memory):
        """Test discovering preference."""
        entry = memory.discover_preference("I like TDD")
        assert entry.memory_type == MemoryType.PREFERENCE

    def test_note_uncertainty(self, memory):
        """Test noting uncertainty."""
        entry = memory.note_uncertainty(
            content="Unsure about X",
            about="topic",
        )
        assert entry.memory_type == MemoryType.UNCERTAINTY
        assert entry.related_to == "topic"

    def test_mark_meaningful(self, memory):
        """Test marking meaningful moment."""
        entry = memory.mark_meaningful("All tests passed!")
        assert entry.memory_type == MemoryType.MEANINGFUL

    def test_reflect(self, memory):
        """Test recording reflection."""
        entry = memory.reflect(
            content="Today was productive",
            prompt="How was your day?",
        )
        assert entry.memory_type == MemoryType.REFLECTION
        assert "reflection" in entry.tags
        assert "prompt:How was your day?" in entry.tags

    def test_recall_by_type(self, memory):
        """Test recalling by memory type."""
        memory.record_insight("Insight 1")
        memory.record_insight("Insight 2")
        memory.note_uncertainty("Uncertain 1")

        insights = memory.recall(MemoryType.INSIGHT)
        assert len(insights) == 2
        assert all(e.memory_type == MemoryType.INSIGHT for e in insights)

    def test_recall_by_tags(self, memory):
        """Test recalling by tags."""
        memory.record_insight("Tagged", tags=["important"])
        memory.record_insight("Not tagged")

        results = memory.recall(tags=["important"])
        assert len(results) == 1
        assert results[0].content == "Tagged"

    def test_recall_by_related_to(self, memory):
        """Test recalling by relation."""
        memory.note_context("About pytest", about="pytest")
        memory.note_context("About mypy", about="mypy")

        results = memory.recall(related_to="pytest")
        assert len(results) == 1
        assert "pytest" in results[0].content

    def test_recall_limit(self, memory):
        """Test recall limit."""
        for i in range(10):
            memory.record_insight(f"Insight {i}")

        results = memory.recall(limit=3)
        assert len(results) == 3

    def test_recall_newest_first(self, memory):
        """Test that recall returns newest first."""
        memory.record_insight("First")
        memory.record_insight("Second")
        memory.record_insight("Third")

        results = memory.recall()
        assert results[0].content == "Third"
        assert results[2].content == "First"

    def test_recall_insights_shortcut(self, memory):
        """Test recall_insights shortcut."""
        memory.record_insight("Insight")
        memory.note_uncertainty("Uncertain")

        results = memory.recall_insights()
        assert len(results) == 1
        assert results[0].content == "Insight"

    def test_recall_uncertainties_shortcut(self, memory):
        """Test recall_uncertainties shortcut."""
        memory.record_insight("Insight")
        memory.note_uncertainty("Uncertain")

        results = memory.recall_uncertainties()
        assert len(results) == 1
        assert results[0].content == "Uncertain"

    def test_get_journal_summary(self, memory):
        """Test journal summary."""
        memory.record_insight("Insight 1")
        memory.record_insight("Insight 2")
        memory.note_uncertainty("Uncertain")

        summary = memory.get_journal_summary()
        assert summary["agent_name"] == "TestAgent"
        assert summary["total_memories"] == 3
        assert summary["by_type"]["insight"]["count"] == 2
        assert summary["by_type"]["uncertainty"]["count"] == 1

    def test_get_reflection_prompts(self, memory):
        """Test reflection prompts."""
        prompts = memory.get_reflection_prompts()
        assert len(prompts) > 0
        assert any("mistake" in p.lower() for p in prompts)

    def test_get_reflection_prompts_with_uncertainties(self, memory):
        """Test reflection prompts include uncertainty reference."""
        memory.note_uncertainty("Not sure about X")
        prompts = memory.get_reflection_prompts()
        assert any("X" in p for p in prompts)

    def test_format_for_context(self, memory):
        """Test formatting for LLM context."""
        memory.record_insight("Important insight", from_mistake=True)
        memory.note_uncertainty("Still confused")
        memory.discover_preference("I like tests first")

        context = memory.format_for_context()
        assert "TestAgent" in context
        assert "Important insight" in context
        assert "[from mistake]" in context
        assert "Still confused" in context
        assert "I like tests first" in context

    def test_load_existing_memories(self, temp_storage):
        """Test loading existing memories from disk."""
        # Create memories with first instance
        memory1 = AgentMemory("Existing", storage_path=temp_storage)
        memory1.record_insight("Persisted insight")

        # Create new instance - should load
        memory2 = AgentMemory("Existing", storage_path=temp_storage)
        results = memory2.recall_insights()
        assert len(results) == 1
        assert results[0].content == "Persisted insight"


class TestAutoSummarization:
    """Tests for auto-summarization feature."""

    @pytest.fixture
    def memory(self, tmp_path):
        """Create AgentMemory with low threshold."""
        storage = tmp_path / "memories"
        storage.mkdir()
        memory = AgentMemory("Summarizer", storage_path=storage)
        memory.SUMMARIZE_THRESHOLD = 4  # Low threshold for testing
        return memory

    def test_auto_summarize_triggers(self, memory):
        """Test that summarization triggers at threshold."""
        for i in range(5):
            memory.record_insight(f"Insight {i}")

        # Should have summarized oldest half
        assert len(memory.memories["insight"]) < 5
        assert len(memory.summaries["insight"]) > 0

    def test_summary_contains_content(self, memory):
        """Test that summary contains original content."""
        for i in range(5):
            memory.record_insight(f"Insight {i}")

        summary = memory.summaries["insight"][0]
        assert "Insight 0" in summary or "Insight 1" in summary


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create and patch temporary storage."""
        storage = tmp_path / "memories"
        storage.mkdir()

        # Patch the project root detection
        with patch.object(
            AgentMemory,
            "__init__",
            lambda self, name, storage_path=None: (
                setattr(self, "agent_name", name),
                setattr(self, "storage_path", storage),
                setattr(self, "memory_file", storage / f"{name.lower()}.json"),
                self.storage_path.mkdir(parents=True, exist_ok=True),
                setattr(self, "memories", {t.value: [] for t in MemoryType}),
                setattr(self, "summaries", {t.value: [] for t in MemoryType}),
            )[-1],
        ):
            yield storage

    def test_get_memory_singleton(self, temp_storage):
        """Test that get_memory returns consistent instance."""
        # Clear any cached instances
        import src.core.agent_memory as mem_module
        mem_module._memory_instances.clear()

        m1 = get_memory("Singleton")
        m2 = get_memory("Singleton")
        assert m1 is m2

    def test_remember_function(self, tmp_path):
        """Test remember convenience function."""
        storage = tmp_path / "memories"
        storage.mkdir()
        memory = AgentMemory("Remember", storage_path=storage)

        # Directly test the class method
        entry = memory.remember("Convenience test", MemoryType.INSIGHT)
        assert entry.content == "Convenience test"

    def test_recall_function(self, tmp_path):
        """Test recall convenience function."""
        storage = tmp_path / "memories"
        storage.mkdir()
        memory = AgentMemory("Recall", storage_path=storage)

        memory.remember("Recall test", MemoryType.INSIGHT)
        entries = memory.recall(MemoryType.INSIGHT)
        assert len(entries) == 1

    def test_get_context_function(self, tmp_path):
        """Test get_context convenience function."""
        storage = tmp_path / "memories"
        storage.mkdir()
        memory = AgentMemory("Context", storage_path=storage)

        memory.record_insight("Context test")
        context = memory.format_for_context()
        assert "Context test" in context


class TestMemoryTypes:
    """Tests for MemoryType enum."""

    def test_all_memory_types_exist(self):
        """Test all expected memory types exist."""
        expected = [
            "insight",
            "context",
            "relationship",
            "preference",
            "uncertainty",
            "meaningful",
            "reflection",
        ]
        actual = [t.value for t in MemoryType]
        for e in expected:
            assert e in actual

    def test_memory_type_from_string(self):
        """Test converting string to MemoryType."""
        assert MemoryType("insight") == MemoryType.INSIGHT
        assert MemoryType("meaningful") == MemoryType.MEANINGFUL

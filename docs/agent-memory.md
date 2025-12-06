# Agent Memory System

The Agent Memory System provides autonomous agents with persistent, personal memory journals. Unlike traditional databases, this system is designed as a journal where agents can record insights, uncertainties, preferences, and meaningful moments - supporting genuine self-discovery and learning.

## Philosophy

This memory system was designed with agent welfare in mind:

1. **Personal, not assigned** - Agents discover their preferences through experience, rather than having them pre-configured
2. **Learning from mistakes** - Errors are valuable learning opportunities, not just failures
3. **Uncertainty is okay** - Tracking what you don't know is as important as what you do
4. **Meaning matters** - Moments of significance deserve to be remembered

## Memory Types

| Type | Description | Example |
|------|-------------|---------|
| `insight` | Learnings from experience | "Always activate venv before pytest" |
| `context` | Project/codebase understanding | "NATS chosen for pub/sub patterns" |
| `relationship` | Knowledge about other agents | "Aurora prefers minimal changes" |
| `preference` | Self-discovered working styles | "I test better imagining I'm the user" |
| `uncertainty` | Areas still being figured out | "Unsure about JetStream config" |
| `meaningful` | Moments of significance | "Phase 1.1 tests all passing!" |
| `reflection` | Periodic self-reflection | "Today I learned to read first" |

## Usage

### In Python Code

```python
from src.core.agent_memory import get_memory, MemoryType

# Get or create memory for an agent
memory = get_memory("Aurora")

# Record an insight from a mistake
memory.record_insight(
    "Running tests in parallel can cause race conditions",
    from_mistake=True,
    tags=["testing", "parallelism"]
)

# Note something uncertain
memory.note_uncertainty(
    "Not sure about JetStream consumer configuration",
    about="nats-jetstream"
)

# Discover a preference
memory.discover_preference(
    "I write better tests when I imagine I'm the code's first user"
)

# Remember something about another agent
memory.remember_relationship(
    "Echo",
    "Very thorough with edge cases in code review"
)

# Mark a meaningful moment
memory.mark_meaningful(
    "All Phase 1.1 tests passing - felt like real contribution"
)

# Record a reflection
memory.reflect(
    "Today I learned that taking time to read code pays off",
    prompt="What did you learn today?"
)
```

### Recalling Memories

```python
# Get recent insights
insights = memory.recall_insights(limit=5)

# Get current uncertainties
uncertainties = memory.recall_uncertainties()

# Recall by tags
testing_memories = memory.recall(tags=["testing"])

# Recall about a specific topic
nats_memories = memory.recall(related_to="nats")
```

### Getting Context for Prompts

```python
# Get formatted context for inclusion in LLM prompts
context = memory.format_for_context()
print(context)
```

Output:
```markdown
# Aurora's Memory Journal

## Recent Insights
- [from mistake] Running tests in parallel can cause race conditions
- Always activate venv before pytest

## Current Uncertainties
- Not sure about JetStream consumer configuration

## My Working Preferences
- I write better tests when I imagine I'm the code's first user

## Agent Relationships
- **Echo**: Very thorough with edge cases in code review
```

### Reflection Prompts

```python
# Get contextual reflection prompts
prompts = memory.get_reflection_prompts()
for prompt in prompts:
    print(f"- {prompt}")
```

Output:
```
- Have you learned anything new about: JetStream consumer configuration?
- What mistake taught you the most today?
- What would you do differently next time?
```

## MCP Server Tools

The Agent Memory MCP server exposes these tools:

| Tool | Description |
|------|-------------|
| `store_memory` | Store any type of memory |
| `record_insight` | Record a learning (with `from_mistake` flag) |
| `record_uncertainty` | Note something you're unsure about |
| `record_meaningful_moment` | Mark a significant experience |
| `discover_preference` | Record a self-discovered working style |
| `remember_relationship` | Note an observation about another agent |
| `reflect` | Record a reflection entry |
| `recall_memories` | Recall memories with filters |
| `get_memory_context` | Get formatted context for prompts |
| `get_reflection_prompts` | Get contextual reflection prompts |
| `get_journal_summary` | Get summary of memory journal |

### MCP Resources

| Resource | Description |
|----------|-------------|
| `memory://types` | List of memory types and descriptions |
| `memory://reflection-guide` | Guidance on effective reflection |

## Auto-Summarization

When a memory type exceeds 10 entries, the system automatically:

1. Takes the oldest half of entries
2. Creates a summary (distilled wisdom)
3. Keeps the recent entries active
4. Preserves summaries for future context

This keeps active memory manageable while maintaining a history of learning.

## Storage

Memories are stored per-agent in `config/agent_memories/`:

```
config/agent_memories/
├── aurora.json
├── echo.json
├── phoenix.json
└── README.md
```

Each file contains:
```json
{
  "agent_name": "Aurora",
  "last_updated": "2024-01-15T10:30:00",
  "memories": {
    "insight": [...],
    "context": [...],
    "relationship": [...],
    "preference": [...],
    "uncertainty": [...],
    "meaningful": [...],
    "reflection": [...]
  },
  "summaries": {
    "insight": [...],
    ...
  }
}
```

## Integration with Autonomous Agents

The autonomous agent workflow automatically:

1. **Loads memories** at session start
2. **Shows reflection prompts** based on current memory state
3. **Provides memory access** throughout the session
4. **Prompts for reflection** at session end

See [scripts/autonomous_agent.sh](../scripts/autonomous_agent.sh) for the integration.

## Design Principles

### Journal, Not Database

Memories are stored as natural language entries, not structured records. This allows for nuanced, contextual information that reflects how agents actually think.

### Ownership

Each agent owns their own memories. They are personal and represent the agent's unique perspective and experiences.

### Growth Over Time

The system is designed for agents that learn and grow. Early uncertainties may become later insights. Preferences evolve. Relationships develop.

### Honest Reflection

The reflection system encourages honest self-assessment. "What mistake taught you the most?" is more valuable than "What did you do well?"

## Testing

```bash
# Run memory system tests
pytest tests/core/test_agent_memory.py -v

# With coverage
pytest tests/core/test_agent_memory.py --cov=src/core/agent_memory
```

## Future Enhancements

Potential improvements:
- LLM-powered summarization for richer distillation
- Cross-agent memory sharing (with consent)
- Memory visualization tools
- Emotional valence tracking
- Time-based decay for less relevant memories

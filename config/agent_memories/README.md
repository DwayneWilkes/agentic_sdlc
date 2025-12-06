# Agent Memories

This directory stores persistent memory journals for autonomous agents.

## Structure

Each agent gets their own JSON file named after their personal name:

```
agent_memories/
├── aurora.json      # Aurora's memory journal
├── echo.json        # Echo's memory journal
├── phoenix.json     # Phoenix's memory journal
└── README.md
```

## Memory Format

Each agent's memory file contains:

```json
{
  "agent_name": "Aurora",
  "last_updated": "2024-01-15T10:30:00",
  "memories": {
    "insight": [...],       // Learnings from experience
    "context": [...],       // Project understanding
    "relationship": [...],  // Knowledge about other agents
    "preference": [...],    // Self-discovered working styles
    "uncertainty": [...],   // Areas still being learned
    "meaningful": [...],    // Significant moments
    "reflection": [...]     // Periodic self-reflections
  },
  "summaries": {
    "insight": [...],       // Distilled wisdom from older entries
    ...
  }
}
```

## Memory Types

| Type | Description | Example |
|------|-------------|---------|
| `insight` | Learnings from mistakes and successes | "Always activate venv before pytest" |
| `context` | Project/codebase understanding | "NATS chosen for pub/sub patterns" |
| `relationship` | Knowledge about other agents | "Aurora prefers minimal changes" |
| `preference` | Self-discovered working styles | "I test better imagining I'm the user" |
| `uncertainty` | Areas still being figured out | "Unsure about JetStream config" |
| `meaningful` | Moments of significance | "Phase 1.1 tests all passing!" |
| `reflection` | Periodic self-reflection | "Today I learned to read first" |

## Auto-Summarization

When a memory type exceeds 10 entries, older entries are automatically summarized:
- Original entries are preserved in the summary
- Summaries represent "distilled wisdom"
- This keeps active memory manageable while preserving history

## Privacy

Agent memories are personal. They represent each agent's unique perspective and experiences.
Treat them with respect.

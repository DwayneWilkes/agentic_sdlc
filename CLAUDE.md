# Agentic SDLC - Orchestrator Agent

This project implements an autonomous orchestrator agent system that decomposes complex tasks, designs teams of specialized subagents, coordinates parallel execution, and recursively self-improves.

## Project Overview

The Orchestrator Agent is a meta-agent system designed for general problem-solving. It:

- Takes a task/goal as input
- Analyzes and decomposes the task into manageable subtasks
- Designs an appropriate team of specialized subagents (e.g., SWE teams for software tasks, research teams for analysis)
- Assigns tasks and coordinates parallel execution
- Integrates outputs into a coherent final result
- Learns from performance and recursively improves its own code and strategies

## Architecture

### Core Components

1. **Task Analysis & Decomposition Engine** - Parses goals, extracts constraints, creates dependency graphs
2. **Team Design & Agent Selection** - Identifies required roles, composes balanced teams
3. **Task Assignment & Parallelization** - Optimizes workload distribution, maximizes concurrency
4. **Coordination & Communication** - Manages inter-agent communication, resolves conflicts
5. **Monitoring & Progress Tracking** - Tracks agent status, validates outputs
6. **Error Handling & Resilience** - Detects failures, implements recovery strategies
7. **Integration & Synthesis** - Combines agent outputs into final deliverable
8. **Self-Improvement & Meta-Learning** - Analyzes performance, optimizes strategies, modifies own code

### Current Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Task Analysis & Decomposition | ✅ Implemented | TaskParser + TaskDecomposer with DAG (1.1-1.4) |
| Team Design & Agent Selection | ✅ Implemented | TeamComposer + AgentFactory + AgentSelector (2.1, 2.2) |
| Task Assignment | ✅ Implemented | TaskAssigner with priority queue (4.1) |
| Coordination (NATS) | ✅ Implemented | Message bus, handoffs, conflict resolution (5.1, 5.3-5.5) |
| Monitoring | 🟡 Partial | ExecutionCycles, no progress tracking yet |
| Error Handling | ✅ Implemented | ErrorDetection + RecoveryStrategy (2.3, 2.4) |
| Parallel Execution | 🔵 Ready | Phase 4.2 unblocked, ready to implement |
| Integration & Synthesis | 🔴 Blocked | Waiting on Phase 6.3 dependencies |
| Self-Improvement | ✅ Implemented | Safety framework + coffee breaks (9.1, 9.4) |
| Security | ✅ Implemented | Sandboxing, kill switches, approval gates (3.1-3.3) |
| Agent Memory & Naming | ✅ Implemented | Persistent memory, names, work history |
| Roadmap Gardening | ✅ Implemented | Auto-unblock phases when dependencies met |
| Goal Arbitration | 🔵 Ready | Phase 10.6 unblocked, ready to implement |

**Batch 1 (Foundation):** 5/5 phases complete (100%)
**Batch 2 (Foundation):** 9/9 phases complete (100%)
**Batch 3 (Security):** 3/3 phases complete (100%)
**Batch 4 (Performance):** 1/3 phases complete (33%)
**Batch 5 (Coordination):** 5/5 phases complete (100%)
**BOOTSTRAP phases:** 6/6 complete (100%)
**Overall Progress:** 32/56 phases complete (57%)

## Project Structure

```text
agentic_sdlc/
├── src/                    # Source code
│   ├── models/            # Data models (Task, Agent, Team)
│   ├── core/              # Core orchestration logic
│   ├── agents/            # Agent implementations
│   ├── coordination/      # Communication & coordination
│   └── self_improvement/  # Meta-learning & self-modification
├── tests/                 # Test suite
├── plans/                 # Planning documents
│   ├── requirements.md    # Orchestrator rubric
│   ├── priorities.md      # Feature prioritization analysis
│   └── roadmap.md         # Implementation roadmap
├── personas/              # Agent persona definitions
├── config/                # Configuration files
└── docs/                  # Documentation

```

## Requirements

See [plans/requirements.md](plans/requirements.md) for the complete orchestrator design and evaluation rubric.

## Development Roadmap

The project follows a phased implementation approach:

- **Phase 1: Foundation** - Core data models, task decomposition, team design, error handling, security
- **Phase 2: Performance** - Parallelization, coordination, monitoring, integration
- **Phase 3: User Experience** - User interaction, transparency, resource management, metrics
- **Phase 4: Advanced Intelligence** - Self-improvement, meta-reasoning, domain adaptability

See [plans/roadmap.md](plans/roadmap.md) for detailed implementation phases.

## Design Principles

1. **Modularity** - Each component is independently testable and replaceable
2. **Safety First** - Sandboxing, validation, and kill switches built in from the start
3. **Efficiency** - Maximize parallelism, minimize resource waste
4. **Transparency** - All decisions are explainable and traceable
5. **Resilience** - Graceful degradation when components fail
6. **Self-Improvement** - System learns and evolves over time
7. **Isolation for Dangerous Changes** - Use feature branches for self-improvement, refactoring, or any changes that could break the current implementation

## Safety Guidelines for Self-Modification

When agents perform self-improvement or other potentially dangerous modifications:

1. **Always use feature branches** - Never modify `main` directly for experimental changes
2. **Test in isolation** - Run full test suite on the branch before merging
3. **Require human approval** - Self-modifications should not auto-merge to main
4. **Maintain rollback capability** - Keep the previous working state accessible
5. **Document the change rationale** - Explain why the self-improvement was proposed

```bash
# Example workflow for self-improvement
git checkout -b self-improve/optimize-task-parser
# ... make changes ...
pytest tests/  # Must pass
git commit -m "Self-improvement: Optimize task parser performance"
# Human reviews and merges (or rejects)
```

## MCP Integration

This project includes Model Context Protocol (MCP) servers for orchestrator operations.

### Available MCP Servers

#### Orchestrator MCP Server

**Location**: `scripts/orchestrator-mcp-server.py`

**Tools**:

- `analyze_task(task_description)` - Extract goal, constraints, context, and task type
- `decompose_task(task_description, max_depth)` - Break down tasks into subtasks with dependency graph
- `design_team(task_type, subtasks, constraints)` - Design optimal agent teams
- `assign_tasks(agents, subtasks, dependencies)` - Assign tasks to agents optimally
- `track_progress(execution_id)` - Monitor ongoing execution
- `analyze_performance(execution_id)` - Post-execution performance analysis
- `propose_self_improvement(performance_data)` - Generate self-improvement proposals

**Resources**:

- `orchestrator://roadmap` - Implementation roadmap
- `orchestrator://requirements` - Requirements rubric
- `orchestrator://priorities` - Feature prioritization
- `orchestrator://project-status` - Current project status

### MCP Configuration

The MCP server is configured in `.claude/mcp-config.json` and auto-starts with Claude Code.

## Subagent Development Approach

This project uses a **meta-strategy**: building the orchestrator using subagents.

See [plans/subagent-development-strategy.md](plans/subagent-development-strategy.md) for:

- **Development team structure** - Specialized agent roles (Architect, Parser Developer, etc.)
- **Parallel execution streams** - Concurrent development workflows
- **Communication protocols** - How agents coordinate
- **Integration points** - Dependency management and handoffs
- **LLM-optimized agent prompts** - Ready-to-use instructions for each agent

This validates the orchestrator design while building it - a practical proof-of-concept.

## Inter-Agent Communication (NATS)

The orchestrator uses **NATS** for all inter-agent communication, providing:

- **High performance** - Sub-millisecond latency, millions of messages/second
- **Simplicity** - Clean pub/sub and request/reply patterns
- **Scalability** - Horizontal scaling with clustering
- **Reliability** - JetStream for persistence

### NATS Architecture

**Subject Hierarchy**:

```text
orchestrator.
├── broadcast.{message_type}          # Broadcast to all agents
├── agent.{agent_id}.{message_type}   # Direct agent messages
├── team.{team_id}.{message_type}     # Team channels
└── queue.{queue_name}                # Work queues
```

**Communication Patterns**:

1. **Broadcast** - Status updates, announcements
2. **Direct Messaging** - Agent-to-agent communication
3. **Request/Reply** - Synchronous queries with timeout
4. **Work Queues** - Load-balanced parallel execution

See [docs/nats-architecture.md](docs/nats-architecture.md) for complete architecture details.

### Quick Start with NATS

```bash
# Start NATS server
docker-compose up -d nats

# Run example communication patterns
python examples/nats_example.py

# Monitor NATS
open http://localhost:8222
```

## Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose (for NATS)
- Virtual environment (included in `.venv/`)
- fastmcp, mcp, and nats-py packages (already installed)

### Installation

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start NATS server
docker-compose up -d nats

# Verify MCP server works
python scripts/orchestrator-mcp-server.py --help

# Test NATS communication
python examples/nats_example.py
```

### Running Tests

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Using MCP Tools (from Claude Code or MCP client)

```python
# Example: Analyze a task
result = mcp.call_tool("analyze_task", {
    "task_description": "Build a REST API for user authentication"
})

# Example: Access roadmap
roadmap = mcp.get_resource("orchestrator://roadmap")
```

## Contributing

This project follows the orchestrator rubric defined in [plans/requirements.md](plans/requirements.md). When contributing:

1. Ensure changes align with the current phase in [plans/roadmap.md](plans/roadmap.md)
2. Add tests for new functionality
3. Update documentation
4. Follow the safety constraints defined in the requirements

## License

TBD

## Related Documents

- [Requirements Rubric](plans/requirements.md) - Complete orchestrator design criteria
- [Prioritization Analysis](plans/priorities.md) - Strategic feature prioritization
- [Implementation Roadmap](plans/roadmap.md) - Phased development plan

# Orchestrator

The Orchestrator coordinates autonomous agent teams to accomplish goals. It reads the roadmap, interprets user goals, spawns agents, monitors progress, and verifies completion.

## Quick Start

```bash
# Check what work is available
python scripts/orchestrator.py status

# Run next available work stream
python scripts/orchestrator.py run

# Run with a natural language goal
python scripts/orchestrator.py goal "Build the task parser"

# Interactive mode - talk to the orchestrator
python scripts/orchestrator.py interactive
```

## Commands

### `status` - Show Roadmap Status

```bash
python scripts/orchestrator.py status
```

Shows:

- Summary of work streams by status
- Available work streams that can be claimed
- In-progress work streams

### `run` - Run Single Work Stream

```bash
# Run next available work stream
python scripts/orchestrator.py run

# Run specific work stream
python scripts/orchestrator.py run 1.2

# Dry run (show what would happen)
python scripts/orchestrator.py run --dry-run

# Skip verification after completion
python scripts/orchestrator.py run --no-verify
```

### `parallel` - Run Multiple Work Streams

```bash
# Run up to 3 work streams in parallel (default)
python scripts/orchestrator.py parallel

# Run up to 5 work streams
python scripts/orchestrator.py parallel -n 5
```

### `batch` - Complete All Available Work

```bash
# Run all available work streams
python scripts/orchestrator.py batch

# With custom concurrency
python scripts/orchestrator.py batch -n 3
```

### `goal` - Natural Language Goals

```bash
# Express your goal in natural language
python scripts/orchestrator.py goal "I want to build the task parser"

# Auto-confirm without prompting
python scripts/orchestrator.py goal "Run everything" --auto

# Dry run to see what would be matched
python scripts/orchestrator.py goal "Start decomposition" --dry-run
```

The goal interpreter understands:

- Work stream names ("task parser", "decomposition engine")
- Keywords ("parser", "decompose", "registry")
- Meta-goals ("next", "all", "everything", "foundation")

### `interactive` - Interactive Mode

```bash
python scripts/orchestrator.py interactive
```

In interactive mode you can:

- Express goals in natural language
- Check status with `status`
- See running agents with `running`
- Stop agents with `stop` or `stop <agent_id>`
- Get detailed report with `report`
- Exit with `quit`

Example session:

```text
You: Start working on the task parser

Orchestrator:
  Matched goal to Phase 1.2: Task Parser and Goal Extraction

  Would you like me to start working on this? [y/N] y

  Spawning agent for Phase 1.2...
  Agent coder-1.2-1234567890 is now working.

You: running

Running agents:
  • coder-1.2-1234567890 → Phase 1.2
      Running for 45s

You: stop

Stopped 1 agent(s)
```

### `stop` - Stop All Agents

```bash
python scripts/orchestrator.py stop
```

### `report` - Detailed Report

```bash
# Human-readable report
python scripts/orchestrator.py report

# JSON output
python scripts/orchestrator.py report --json
```

## Architecture

### Components

```text
src/orchestrator/
├── __init__.py           # Module exports
├── orchestrator.py       # Main Orchestrator class
├── work_stream.py        # Roadmap parsing
├── agent_runner.py       # Agent spawning and monitoring
├── goal_interpreter.py   # Natural language goal interpretation
└── nats_coordinator.py   # NATS-based agent communication
```

### Orchestrator Class

```python
from src.orchestrator import Orchestrator, OrchestratorConfig

# Create orchestrator
config = OrchestratorConfig(
    max_concurrent_agents=3,
    agent_timeout_seconds=1800,  # 30 minutes
)
orchestrator = Orchestrator(config=config)

# Get roadmap status
status = orchestrator.get_roadmap_status()

# Run work stream
agent = orchestrator.run(work_stream_id="1.2")

# Run multiple in parallel
agents = orchestrator.run_parallel(max_agents=3)

# Wait for completion
orchestrator.runner.wait_for_all()

# Verify work
results = orchestrator.verify_completion(agent)

# Stop all agents
orchestrator.stop()
```

### Goal Interpreter

```python
from src.orchestrator import interpret_goal

result = interpret_goal("Build the task parser")
print(f"Matched: {[ws.id for ws in result.matched_work_streams]}")
print(f"Confidence: {result.confidence:.0%}")
print(f"Action: {result.suggested_action}")
```

### Agent Runner

```python
from src.orchestrator import AgentRunner

runner = AgentRunner(max_concurrent=3)

# Spawn agent
agent = runner.spawn_agent(
    work_stream_id="1.2",
    on_output=lambda line: print(line),
)

# Monitor
while agent.is_running:
    print(f"Duration: {agent.duration_seconds}s")
    time.sleep(5)

# Check result
if agent.state.value == "completed":
    print("Success!")
```

### Work Stream Parser

```python
from src.orchestrator import parse_roadmap, get_available_work_streams

# Parse entire roadmap
all_streams = parse_roadmap()

# Get only available work
available = get_available_work_streams()

for ws in available:
    print(f"Phase {ws.id}: {ws.name} [{ws.effort}]")
```

## NATS Integration

The orchestrator can communicate with agents via NATS for real-time control:

```python
from src.orchestrator.nats_coordinator import NATSCoordinator

coordinator = NATSCoordinator()
await coordinator.connect()

# Stop all agents
await coordinator.stop_all_agents()

# Send feedback to specific agent
await coordinator.send_feedback(
    agent_id="coder-1.2-123",
    feedback="Focus on edge cases",
    action="continue",
)

# Redirect agent to different work
await coordinator.redirect_agent(
    agent_id="coder-1.2-123",
    new_work_stream="1.3",
    reason="1.2 is blocked by dependency",
)
```

NATS subjects:

- `orchestrator.broadcast.*` - Commands to all agents
- `orchestrator.agent.{id}.*` - Commands to specific agent
- `orchestrator.status.{id}` - Status updates from agents

## Verification

After an agent completes, the orchestrator can verify:

```python
results = orchestrator.verify_completion(agent)

# Checks performed:
# - exit_code: Agent exited with code 0
# - tests: pytest tests/ passes
# - roadmap: Work stream status updated
# - git_clean: No uncommitted changes
```

## Event Callbacks

Monitor orchestrator activity:

```python
def on_event(event):
    print(f"[{event.timestamp}] {event.event_type}: {event.message}")

orchestrator.add_event_callback(on_event)
```

Event types:

- `spawning_agent` - About to spawn an agent
- `agent_running` - Agent started running
- `agent_completed` - Agent finished successfully
- `agent_failed` - Agent failed
- `verification_complete` - Verification finished

## Configuration

```python
OrchestratorConfig(
    mode=OrchestratorMode.PARALLEL,  # SINGLE, PARALLEL, or BATCH
    max_concurrent_agents=3,          # Max agents at once
    agent_timeout_seconds=1800,       # 30 minute timeout
    verify_after_completion=True,     # Run verification
    auto_commit=True,                 # Allow agents to commit
    dry_run=False,                    # Just show, don't execute
)
```

## Orchestrator Agent Persona

For Claude Code users, there's an orchestrator agent persona at `.claude/agents/orchestrator_agent.md` that provides guidance on how to act as an orchestrator coordinator.

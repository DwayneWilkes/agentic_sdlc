# Agent Naming System

Autonomous agents choose their own personal names to make logs, communication, and debugging more human-friendly.

## Overview

Instead of technical IDs like `coder-autonomous-1733409000`, agents choose their own meaningful names. The system ensures uniqueness and persists the mapping.

## Benefits

- **Agent autonomy** - Agents choose names meaningful to them
- **Readable logs** - "Aurora completed task" vs "coder-autonomous-1733409000 completed task"
- **Natural communication** - "Echo asked Nova for help" vs agent ID chains
- **Easier debugging** - Track specific agents across sessions
- **Identity** - Agents develop their own sense of identity
- **Persistence** - Names persist across sessions (if using same agent_id)

## How It Works

### 1. Agent Chooses and Claims a Name

```python
from src.core.agent_naming import claim_agent_name, get_taken_names

# First check what names are already taken
taken = get_taken_names()
print(f"Names already taken: {taken}")

# Choose any name that feels meaningful
my_name = "Aurora"  # Your choice!

# Claim it
success, result = claim_agent_name(
    agent_id="coder-autonomous-123",
    chosen_name=my_name,
    role="coder"
)

if success:
    print(f"Hello! I am {result}")  # "Hello! I am Aurora"
else:
    print(result)  # "Name 'Aurora' is already taken..."
    # Choose a different name and try again
```

### 2. Name Persists

```python
# Later, same agent_id gets same name automatically
success, name = claim_agent_name(
    agent_id="coder-autonomous-123",
    chosen_name="anything",  # Ignored - already have a name
    role="coder"
)

print(name)  # Still "Aurora"
```

### 3. Check Availability

```python
from src.core.agent_naming import is_name_available

if is_name_available("Nova"):
    print("Nova is available!")
else:
    print("Nova is already taken")
```

### 4. Use in Communication

```python
await bus.broadcast(
    from_agent=name,  # "Aurora"
    message_type=MessageType.STATUS_UPDATE,
    content={"status": "started", "work_stream": "Phase 1.1"}
)
```

## Suggested Name Pools (Optional Inspiration)

Agents may draw inspiration from these pools, but can choose any name:

### Coder Pool (Computer Science Pioneers)

Ada, Alan, Grace, Dennis, Linus, Ken, Brian, Donald, Bjarne, Guido, James, Brendan, Anders, Rob, Yukihiro, Larry, Rasmus, John, Margaret, Jean, Kathleen, Frances, Betty, Ruth, Evelyn, Hedy, Sophie, Mary, Dorothy

### Architect Pool (Builders & Mathematicians)

Apollo, Athena, Minerva, Vitruvius, Imhotep, Fibonacci, Euclid, Archimedes, Pythagoras, Hypatia, Eratosthenes

### Parser Pool (Language & Syntax)

Syntax, Lexer, Token, AST, Chomsky, Backus, Naur

### Decomposer Pool (Divide & Conquer)

Divide, Conquer, Fragment, Partition, Split, Factor

### Tester Pool (Verification)

Verify, Assert, Prove, Check, Validate, Inspect

### Reviewer Pool (Analysis)

Critique, Audit, Scrutiny, Examine, Assess, Evaluate

### Orchestrator Pool (Coordination)

Conductor, Maestro, Director, Coordinator, Synergy

### Default Pool (Greek Letters)

Alpha, Beta, Gamma, Delta, Epsilon, Zeta, Eta, Theta, Iota, Kappa, Lambda, Mu, Nu, Xi, Omicron, Pi, Rho, Sigma, Tau, Upsilon, Phi, Chi, Psi, Omega

## API Reference

### `claim_agent_name(agent_id, role, preferred_name)`

Claim a personal name for an agent.

**Parameters:**

- `agent_id` (str) - Unique technical ID (e.g., "coder-autonomous-123")
- `role` (str) - Agent role type ("coder", "architect", "tester", etc.)
- `preferred_name` (str | None) - Optional preferred name

**Returns:**

- `str` - Personal name (e.g., "Ada")

**Example:**

```python
# Random name from coder pool
name = claim_agent_name("coder-001", "coder")

# Prefer specific name (if available)
name = claim_agent_name("coder-002", "coder", preferred_name="Grace")

# Different role
name = claim_agent_name("arch-001", "architect")  # Gets architect name
```

### `get_naming()`

Get the global naming instance.

**Returns:**

- `AgentNaming` - Naming system instance

**Example:**

```python
from src.core.agent_naming import get_naming

naming = get_naming()

# Get agent's name
name = naming.get_name("coder-001")  # "Ada"

# Reverse lookup
agent_id = naming.get_agent_id("Ada")  # "coder-001"

# List all assigned names
assigned = naming.list_assigned_names()
# {
#   "coder-001": {"name": "Ada", "role": "coder", "claimed_at": "2025-12-05T14:30:00"},
#   "arch-001": {"name": "Apollo", "role": "architect", "claimed_at": "2025-12-05T14:31:00"}
# }

# Get available names for a role
available = naming.get_available_names("coder")
# ["Alan", "Grace", "Dennis", ...]  (Ada is taken)

# Release a name
naming.release_name("coder-001")  # Ada is now available again
```

## Configuration

Configuration is stored in `config/agent_names.json`:

```json
{
  "name_pools": {
    "coder": ["Ada", "Alan", "Grace", ...],
    "architect": ["Apollo", "Athena", ...],
    ...
  },
  "assigned_names": {
    "coder-001": {
      "name": "Ada",
      "role": "coder",
      "claimed_at": "2025-12-05T14:30:00.000Z"
    }
  },
  "naming_config": {
    "format": "{name}-{role_suffix}",
    "allow_duplicates": false,
    "add_numeric_suffix_on_conflict": true,
    "persistent": true
  }
}
```

### Configuration Options

- **`allow_duplicates`** - Allow same name for multiple agents (default: false)
- **`add_numeric_suffix_on_conflict`** - If preferred name is taken, add number (e.g., "Ada-2")
- **`persistent`** - Save assignments to disk (default: true)

## Name Conflicts

If all names in a pool are taken, numeric suffixes are added:

```python
# First agent gets "Ada"
name1 = claim_agent_name("coder-001", "coder", preferred_name="Ada")  # "Ada"

# Second agent requesting Ada gets "Ada-2"
name2 = claim_agent_name("coder-002", "coder", preferred_name="Ada")  # "Ada-2"
```

## Usage in Coder Agent

Coder agents should claim a name at the start of their session:

```python
import time
from src.core.agent_naming import claim_agent_name

# Generate unique agent ID with timestamp
agent_id = f"coder-autonomous-{int(time.time())}"

# Claim personal name
personal_name = claim_agent_name(agent_id, "coder")

print(f"🤖 Hello! I'm {personal_name}, your autonomous coder.")
print(f"   Agent ID: {agent_id}")

# Use personal name in all communications
# - Dev log entries
# - NATS broadcasts
# - Commit messages
# - Roadmap updates
```

## Usage in Dev Logs

Include personal name in dev log entries:

```markdown
## 2025-12-05 - Core Data Models Implementation

**Agent**: Ada (coder-autonomous-1733409000)
**Work Stream**: Phase 1.1 - Core Data Models
**Status**: Complete

### What Was Implemented

- Task, Subtask, Agent, Team models with full type hints
- Comprehensive test coverage (95%)

### Notes

- Ada chose Pydantic for data validation
- All tests passing
```

## Usage in NATS Communication

Use personal names in broadcast messages:

```python
await bus.broadcast(
    from_agent=f"{personal_name}-coder",  # "Ada-coder"
    message_type=MessageType.STATUS_UPDATE,
    content={
        "status": "completed",
        "work_stream": "Phase 1.1",
        "agent_name": personal_name  # Include in content too
    }
)
```

## Adding New Names

To add names to a pool:

1. Edit `config/agent_names.json`
2. Add names to the appropriate pool array
3. Save the file

```json
{
  "name_pools": {
    "coder": [
      "Ada",
      "NewName1",  // Add here
      "NewName2"   // Add here
    ]
  }
}
```

## Adding New Roles

To add a new role pool:

```json
{
  "name_pools": {
    "coder": [...],
    "my_new_role": [  // New pool
      "Name1",
      "Name2",
      "Name3"
    ]
  }
}
```

Then use it:

```python
name = claim_agent_name("agent-001", "my_new_role")
```

## Best Practices

1. **Claim early** - Claim name at start of agent session
2. **Use consistently** - Use same name throughout session
3. **Include in logs** - Always mention personal name in dev logs
4. **Broadcast updates** - Include name in NATS messages
5. **Release on exit** - Release name when agent terminates (optional)

## Examples

### Example 1: Coder Agent Session

```python
from src.core.agent_naming import claim_agent_name, get_naming
import time

# Start session
agent_id = f"coder-autonomous-{int(time.time())}"
name = claim_agent_name(agent_id, "coder")

print(f"🤖 {name} starting work on Phase 1.1")

# ... do work ...

# Check what other agents are active
naming = get_naming()
all_agents = naming.list_assigned_names()
print(f"Active agents: {[entry['name'] for entry in all_agents.values()]}")

# End session (optional)
naming.release_name(agent_id)
print(f"👋 {name} signing off")
```

### Example 2: Team Coordination

```python
# Architect agent
arch_id = "architect-001"
arch_name = claim_agent_name(arch_id, "architect")  # "Apollo"

# Coder agents
coder1_name = claim_agent_name("coder-001", "coder")  # "Ada"
coder2_name = claim_agent_name("coder-002", "coder")  # "Grace"

# Communication
print(f"{arch_name}: Task model is ready!")
print(f"{coder1_name}: Thanks {arch_name}, starting on TaskParser")
print(f"{coder2_name}: I'll handle the Decomposer")
```

### Example 3: Debugging

```python
# Find which agent is "Ada"
naming = get_naming()
agent_id = naming.get_agent_id("Ada")
print(f"Ada's agent ID: {agent_id}")

# List all coders
all_agents = naming.list_assigned_names()
coders = {
    name: entry
    for name, entry in all_agents.items()
    if entry["role"] == "coder"
}
print(f"Coder agents: {[entry['name'] for entry in coders.values()]}")
```

## See Also

- [Coder Agent Workflow](../.claude/agents/coder_agent.md)
- [NATS Communication](./nats-architecture.md)
- [Development Log](./devlog.md)
- [Agent Naming Implementation](../src/core/agent_naming.py)

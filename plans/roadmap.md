# Roadmap

## Strategic Priorities ⭐ BOOTSTRAP

*These phases are force-multipliers. Building them first improves all subsequent development work.*

```text
⭐ BOOTSTRAP (Do first - improves all subsequent work)
├── 10.5 Recurrent Refinement     ✅ Complete (Sage)
├── 2.3  Error Detection          ✅ Complete (Lyra)
├── 2.6  QA Verifier Agent        ✅ Complete (infrastructure)
├── 2.8  Stuck Detection          ✅ Complete (Forge)
├── 2.9  Undo Awareness           ✅ Complete (Ember)
└── 3.3  Pre-Flight Checks        ✅ Complete (Cascade)
```

**Progress:** 6/6 BOOTSTRAP phases complete! 🎉 All foundational capabilities are now in place.

**Why these first?** If agents can detect errors (2.3), verify quality (2.6), catch when they're stuck (2.8), know how to undo (2.9), think before acting (3.3), and deeply understand tasks (10.5), they'll make fewer mistakes on everything else.

---

## Batch 1 (Foundation - Current)

### Phase 1.1: Core Data Models and Project Scaffolding

- **Status:** ✅ Complete
- **Assigned To:** coder-autonomous-1764977334
- **Tasks:**
  - [✅] Create project structure (src/, tests/, config/)
  - [✅] Define core data models: Task, Subtask, Agent, Team
  - [✅] Define enums: TaskStatus, AgentStatus, TaskType
  - [✅] Set up dependency management (pyproject.toml or requirements.txt)
- **Effort:** S
- **Done When:** Data models exist with proper type hints; project runs `python -c "from src.models import Task, Agent"` without error
- **Completed:** 2025-12-05
- **Quality Gates:** All tests pass (41/41), 100% coverage for models, no linting errors, no type errors

### Phase 1.2: Task Parser and Goal Extraction

- **Status:** ✅ Complete
- **Assigned To:** Aria
- **Tasks:**
  - [✅] Implement TaskParser class to extract goal, constraints, context from input
  - [✅] Add task type classification (software, research, analysis, creative, hybrid)
  - [✅] Implement ambiguity detection and clarification request generation
  - [✅] Add success criteria extraction
- **Effort:** M
- **Done When:** Parser correctly extracts structured data from natural language task descriptions; unit tests pass
- **Completed:** 2025-12-05
- **Quality Gates:** All tests pass (24/24), 97% coverage for task_parser.py, no linting errors, no type errors

### Phase 1.3: Task Decomposition Engine

- **Status:** ✅ Complete
- **Assigned To:** Atlas
- **Tasks:**
  - [✅] Implement recursive decomposition algorithm
  - [✅] Build dependency graph generator
  - [✅] Add critical path identification
  - [✅] Ensure subtasks are Independent, Testable, Estimable
- **Effort:** M
- **Done When:** Complex task decomposes into subtask DAG with dependencies; integration point identification works
- **Completed:** 2025-12-05
- **Quality Gates:** All tests pass (22/22), 74% coverage for task_decomposer.py, no linting errors, no type errors

### Phase 1.4: Agent Role Registry

- **Status:** ✅ Complete
- **Assigned To:** Nexus
- **Tasks:**
  - [✅] Define AgentRole schema (capabilities, tools, domain knowledge)
  - [✅] Create registry of standard agent types (Developer, Researcher, Analyst, Tester, Reviewer)
  - [✅] Implement role matching algorithm (task requirements → agent capabilities)
- **Effort:** S
- **Done When:** Registry returns appropriate agent roles for given task requirements
- **Completed:** 2025-12-05
- **Quality Gates:** All tests pass (27/27), 100% coverage for role_registry.py, no linting errors, no type errors

### Phase 1.5: Live Agent Dashboard

- **Status:** ✅ Complete
- **Assigned To:** Claude Code
- **Tasks:**
  - [✅] Real-time agent status display (running, completed, failed)
  - [✅] Interactive controls (stop agent, query status, update goal)
  - [✅] NATS integration for live updates
  - [✅] Graceful vs immediate stop command support (SIGTERM/SIGKILL)
- **Effort:** S
- **Done When:** Dashboard shows live agent status; stop/control commands work
- **Completed:** 2025-12-05
- **Implementation Notes:**
  - scripts/dashboard.py - Standalone Rich UI dashboard
  - src/orchestrator/dashboard.py - Dashboard module with NATS subscription
  - Signal handling in autonomous_agent.sh (SIGTERM→graceful, SIGKILL→immediate)
  - Commands: `python scripts/orchestrator.py dashboard [-w|-s]`

---

## Batch 2 (Foundation)

### Phase 2.1: Team Composition Engine

- **Status:** ✅ Complete
- **Assigned To:** Cipher
- **Completed:** 2025-12-05
- **Depends On:** Phase 1.4 ✅
- **Tasks:**
  - [✅] Implement team sizing logic (avoid over/under-staffing)
  - [✅] Add complementary role selection (ensure skill coverage)
  - [✅] Handle specialization vs. generalization trade-offs
- **Effort:** S
- **Done When:** Engine produces balanced teams with no redundant roles and full skill coverage
- **Quality Gates:** All tests pass (16/16), 96% coverage for team_composer.py, no linting errors, no type errors

### Phase 2.2: Agent Instantiation and Configuration

- **Status:** ✅ Complete
- **Assigned To:** Zenith
- **Completed:** 2025-12-06
- **Depends On:** Phase 1.4 ✅, Phase 2.1 ✅
- **Tasks:**
  - [✅] Implement agent factory with tool/context/permission configuration
  - [✅] Add instruction generation for each agent (clear, unambiguous)
  - [✅] Define resource limits (time, compute, API calls) per agent
  - [✅] Pass relevant dependencies and context to agents
- **Effort:** M
- **Done When:** Agents instantiate with proper configuration; each agent knows its tasks and constraints
- **Quality Gates:** All tests pass (23/23), 100% coverage for agent_factory.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/core/agent_factory.py - Complete agent factory implementation
  - tests/core/test_agent_factory.py - Comprehensive test suite (23 tests)
  - ResourceLimits dataclass: max_time_seconds, max_api_calls, max_tokens, max_memory_mb
  - AgentConfiguration dataclass: tools, context, permissions, resource_limits, dependencies
  - InstructionGenerator class: generates formatted instructions with role, tasks, tools, limits, context
  - AgentFactory class: creates configured agents from roles with unique IDs and full metadata
  - All components fully typed and documented with docstrings

### Phase 2.3: Error Detection Framework ⭐ BOOTSTRAP

- **Status:** ✅ Complete
- **Assigned To:** Lyra (coder-1765073295)
- **Completed:** 2025-12-06
- **Depends On:** Phase 1.1 ✅
- **Tasks:**
  - [x] Define error taxonomy (crash, timeout, invalid output, partial completion)
  - [x] Implement failure detection hooks for agent execution
  - [x] Add output validation against success criteria
- **Effort:** S
- **Done When:** System detects and classifies all failure types; no silent failures
- **Quality Gates:** All tests pass (27/27), 92% coverage for error_detection.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/core/error_detection.py - Complete error detection framework
  - tests/core/test_error_detection.py - Comprehensive test suite (27 tests)
  - ErrorType enum: CRASH, TIMEOUT, INVALID_OUTPUT, PARTIAL_COMPLETION, VALIDATION_FAILURE
  - ErrorSeverity enum with numeric values for comparison (CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1)
  - FailureDetector class with detection methods for all error types
  - OutputValidator class with rule-based and criteria-based validation
  - Error history tracking prevents silent failures
  - All components fully typed and documented

### Phase 2.6: Quality Gate Verifier Agent ⭐ BOOTSTRAP

- **Status:** ✅ Complete
- **Completed By:** Infrastructure (manual implementation)
- **Completed Date:** 2025-12-05
- **Depends On:** Phase 1.1 ✅
- **Tasks:**
  - [x] Create QA/Verifier agent that audits completed phases
  - [x] Implement quality gate checks:
    - [x] All tests pass (pytest)
    - [x] Coverage ≥ 80% (pytest --cov)
    - [x] No linting errors (ruff check)
    - [x] No type errors (mypy)
  - [x] Report violations to orchestrator with specifics
  - [x] Trigger remediation workflow (spawn agent to fix gaps)
  - [x] Track technical debt for phases that were approved with exceptions
- **Effort:** M
- **Done When:** All completed phases verified against quality gates; violations flagged and remediated automatically
- **Implementation Notes:**
  - Tech Lead persona: `.claude/agents/tech_lead.md`
  - Launch script: `scripts/tech_lead.sh`
  - CLI command: `python scripts/orchestrator.py tech-lead`
  - Includes coder supervision, quality gates, and deep code review
- **Design Notes:**

  ```text
  Phase Marked Complete
    │
    ├─► Tech Lead runs quality checks
    │     ├─► pytest tests/
    │     ├─► pytest --cov=src tests/
    │     ├─► ruff check src/ tests/
    │     └─► mypy src/
    │
    ├─► All pass? → ✅ Verified complete
    │
    └─► Failures? → Report to orchestrator
                    → Spawn remediation agent
                    → Track as technical debt if approved with exception
  ```

### Phase 2.4: Recovery Strategy Engine

- **Status:** ✅ Complete
- **Assigned To:** Horizon (coder-1765075622)
- **Completed:** 2025-12-06
- **Depends On:** Phase 2.3 ✅
- **Tasks:**
  - [✅] Implement retry logic with configurable policies
  - [✅] Add fallback agent selection (different agent for failed task)
  - [✅] Implement graceful degradation (partial results on failure)
  - [✅] Add circuit breakers to prevent resource exhaustion
  - [✅] Implement recovery patterns (timeout → NAK → retry, exponential backoff)
- **Effort:** M
- **Done When:** Failed tasks retry appropriately; cascading failures prevented; system remains operational
- **Quality Gates:** All tests pass (30/30), 92% coverage for recovery_strategy.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/core/recovery_strategy.py - Complete recovery strategy framework (197 lines)
  - tests/core/test_recovery_strategy.py - Comprehensive test suite (30 tests)
  - RecoveryStrategy enum: RETRY, FALLBACK_AGENT, GRACEFUL_DEGRADATION, CIRCUIT_BREAKER, NONE
  - CircuitState enum: CLOSED, OPEN, HALF_OPEN
  - RetryPolicy class: configurable max_attempts, exponential backoff with base_delay and backoff_multiplier
  - CircuitBreaker class: three-state circuit breaker (CLOSED→OPEN→HALF_OPEN→CLOSED)
  - FallbackStrategy class: capability-based fallback agent selection
  - GracefulDegradation class: partial result creation and acceptance threshold checking
  - RecoveryStrategyEngine class: main orchestrator for recovery strategy application
  - All components fully typed and documented with docstrings
- **Design Notes:**

  ```text
  Recovery Strategy Flow:
  ┌──────────────────────────────────────────────────────────────┐
  │  ERROR OCCURS                                                │
  │  ├─► ErrorContext captured (type, severity, agent, task)    │
  │  │                                                            │
  │  STRATEGY SELECTION                                          │
  │  ├─► CRITICAL error → NONE (no recovery)                     │
  │  ├─► TIMEOUT → RETRY with exponential backoff                │
  │  ├─► INVALID_OUTPUT → FALLBACK_AGENT                         │
  │  ├─► PARTIAL_COMPLETION → GRACEFUL_DEGRADATION               │
  │  └─► CRASH → FALLBACK_AGENT                                  │
  │                                                              │
  │  APPLY RECOVERY                                              │
  │  ├─► Check circuit breaker (OPEN → block, CLOSED → allow)   │
  │  ├─► Apply selected strategy                                │
  │  ├─► Track recovery history                                 │
  │  └─► Return RecoveryResult                                   │
  └──────────────────────────────────────────────────────────────┘

  Circuit Breaker States:
  CLOSED (normal) → OPEN (threshold exceeded) → HALF_OPEN (testing) → CLOSED (recovered)
                         ↑                           ↓
                         └───── failure ─────────────┘

  Retry Policy:
  - Exponential backoff: delay = base_delay * (backoff_multiplier ^ attempt)
  - Respects max_delay to prevent excessive waiting
  - Never retries CRITICAL errors
  - Configurable max_attempts

  Fallback Agent Selection:
  - Excludes failed agent
  - Matches required capabilities
  - Returns None if no suitable agent found

  Graceful Degradation:
  - Calculates completion percentage from subtask statuses
  - Configurable acceptance threshold (default 50%)
  - Returns partial results when acceptable
  ```

### Phase 2.7: Agent Behavior Testing Framework (Defeat Tests)

- **Status:** ✅ Complete
- **Assigned To:** Echo (coder-1765071130)
- **Completed:** 2025-12-06
- **Depends On:** Phase 1.1 ✅
- **Tasks:**
  - [✅] Create "defeat test" infrastructure for agent anti-patterns
  - [✅] Implement tests that detect agent loops (keeps trying same failed approach)
  - [✅] Add tests for context drift (agent forgets mid-session)
  - [✅] Add tests for breaking working code during fixes
  - [✅] Add tests for over-engineering simple solutions
  - [✅] Create framework for pattern-specific defeat tests
  - [✅] Integrate defeat tests into pre-commit hooks
- **Effort:** M
- **Done When:** Agent anti-patterns caught before commit; new patterns can be defeated with new tests
- **Quality Gates:** All tests pass (15/15), 65-79% coverage for defeat test patterns, no type errors
- **Design Notes:**

  ```text
  Traditional TDD: Red → Green → Refactor
  Agent TDD:       Pattern Found → Defeat Test Written → Agent Trained → Pattern Defeated

  Defeat Test Examples:
  - test_no_retry_loop: Agent must not retry same approach >3 times
  - test_context_preserved: Key context items must persist across turns
  - test_minimal_changes: Bug fix must not refactor surrounding code
  - test_no_silent_fallbacks: .get(x, 0) patterns must raise on missing data
  ```

### Phase 2.5: Orchestrator as Claude Code Wrapper ⭐ PRIORITY

- **Status:** ✅ Complete
- **Assigned To:** Meridian
- **Completed:** 2025-12-06
- **Depends On:** Phase 1.2 ✅, Phase 1.3 ✅, Phase 1.4 ✅
- **Tasks:**
  - [✅] Create orchestrator wrapper that accepts ANY natural language request
  - [✅] Integrate TaskParser for goal extraction, constraint detection, ambiguity handling
  - [✅] Add complexity assessment (simple task → single agent, complex → decompose)
  - [✅] Integrate TaskDecomposer for breaking complex tasks into subtask DAG
  - [✅] Integrate RoleMatcher to assign agent roles per subtask
  - [ ] Spawn Claude Code agents for parallel execution where dependencies allow (TODO)
  - [ ] Coordinate via NATS, integrate outputs, return unified result to user (TODO)
- **Effort:** L
- **Done When:** User can give any NL request to orchestrator; simple tasks run directly, complex tasks decompose and parallelize automatically
- **Quality Gates:** All tests pass (18/18), 97% coverage for wrapper.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/orchestrator/wrapper.py - OrchestratorWrapper class with smart dispatching
  - tests/orchestrator/test_wrapper.py - Comprehensive test suite
  - Complexity assessment: SIMPLE (score ≤2), MEDIUM (score ≤6), COMPLEX (score >6)
  - Execution modes: SINGLE_AGENT (simple), COORDINATED_TEAM (complex)
  - Dry-run mode for testing without spawning agents
  - ExecutionResult dataclass with full execution metadata
  - TODO: Actual agent spawning and NATS coordination (future phases)
- **Design Notes:**

  ```text
  User Request → Orchestrator Wrapper
    │
    ├─► TaskParser.parse() → goal, constraints, context, task_type
    │
    ├─► Is simple? → YES: Single Claude Code agent
    │              → NO:  TaskDecomposer.decompose()
    │
    ├─► RoleMatcher.match(subtasks) → agent roles
    │
    ├─► Spawn agents (parallel where possible)
    │
    └─► Coordinate via NATS → Integrate outputs → Return to user
  ```

### Phase 2.8: Stuck Detection & Escape Strategies ⭐ BOOTSTRAP

- **Status:** ✅ Complete
- **Assigned To:** Forge
- **Completed:** 2025-12-06
- **Depends On:** Phase 2.3 ✅
- **Tasks:**
  - [✅] Detect retry loops (same error 3+ times without progress)
  - [✅] Recognize "thrashing" patterns (changing approach repeatedly without advancement)
  - [✅] Implement automatic escalation triggers ("stuck for X minutes, asking for help")
  - [✅] Create escape hatch strategies:
    - [✅] Try fundamentally different approach (REFRAME)
    - [✅] Reduce scope to minimal failing case (REDUCE)
    - [✅] Ask for human guidance with context summary (ESCALATE)
    - [✅] Hand off to different agent with fresh perspective (HANDOFF)
    - [✅] Search for similar issues/solutions (RESEARCH)
  - [✅] Add progress metrics (lines changed, tests passing, goals met)
  - [✅] Implement "no progress" timeout with graceful state save
- **Effort:** M
- **Done When:** Agents detect when they're stuck; escape strategies prevent infinite loops; escalation works
- **Quality Gates:** All tests pass (28/28), 93% coverage for stuck_detection.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/core/stuck_detection.py - Complete stuck detection and escape framework
  - tests/core/test_stuck_detection.py - Comprehensive test suite (28 tests)
  - StuckPattern enum: RETRY_LOOP, THRASHING, NO_PROGRESS
  - EscapeStrategy enum: REFRAME, REDUCE, RESEARCH, ESCALATE, HANDOFF
  - ProgressMetrics class tracks progress snapshots over time
  - StuckDetector class with detection methods for all stuck patterns
  - EscapeStrategyEngine recommends and generates action plans for escape strategies
  - All components fully typed and documented
- **Design Notes:**

  ```text
  Stuck Detection Signals:
  ┌──────────────────────────────────────────────────────────────┐
  │  RETRY LOOP                                                  │
  │  ├─► Same error message 3+ times                             │
  │  ├─► Same fix attempted repeatedly                           │
  │  └─► Test failures not decreasing                            │
  │                                                              │
  │  THRASHING                                                   │
  │  ├─► Approach A → B → A → B pattern                          │
  │  ├─► Undoing recent changes                                  │
  │  └─► Contradictory edits within short time                   │
  │                                                              │
  │  NO PROGRESS                                                 │
  │  ├─► No meaningful file changes in X minutes                 │
  │  ├─► Tests not improving                                     │
  │  └─► Goals not advancing                                     │
  └──────────────────────────────────────────────────────────────┘

  Escape Strategies (in order):
  1. REFRAME: Try completely different approach
  2. REDUCE: Simplify to minimal reproducing case
  3. RESEARCH: Search for similar issues/solutions
  4. ESCALATE: Ask human with full context summary
  5. HANDOFF: Pass to different agent with fresh eyes
  ```

### Phase 2.9: Undo Awareness ⭐ BOOTSTRAP

- **Status:** ✅ Complete
- **Assigned To:** Ember (coder-1765074067)
- **Completed:** 2025-12-06
- **Depends On:** Phase 2.3 ✅
- **Tasks:**
  - [✅] Capture rollback command/state before any change
  - [✅] Implement "before" snapshots for risky operations
  - [✅] Always know how to reverse what was just done
  - [✅] Never make changes that can't be explained how to reverse
  - [✅] Add rollback plan to handoff documents
  - [✅] Implement automatic rollback on detected regression
  - [✅] Track undo chain depth (how many steps back can we go?)
- **Effort:** S
- **Done When:** Every change has documented undo; rollback tested; no orphaned changes
- **Quality Gates:** All tests pass (31/31), 98% coverage for undo_awareness.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/core/undo_awareness.py - Complete undo awareness framework
  - tests/core/test_undo_awareness.py - Comprehensive test suite (31 tests)
  - RiskLevel enum: LOW, MEDIUM, HIGH, CRITICAL
  - UndoAction dataclass: captures action, undo command, description, risk level, files affected
  - ActionSnapshot dataclass: captures state before risky operations
  - UndoChain class: manages action history with configurable max depth
  - UndoAwarenessEngine class: main orchestrator for undo operations
  - Integration with ErrorContext for automatic rollback decisions
  - Export to handoff format and JSON for persistence
  - All components fully typed and documented
- **Design Notes:**

  ```text
  Undo Awareness Principle:
  "Before doing X, know how to undo X"

  Examples:
  ┌─────────────────────────────────────────────────────────────┐
  │  ACTION                    │  UNDO                          │
  ├─────────────────────────────────────────────────────────────┤
  │  Edit file                 │  git checkout -- <file>        │
  │  Delete file               │  git checkout HEAD -- <file>   │
  │  Create file               │  rm <file>                     │
  │  npm install               │  npm uninstall <pkg>           │
  │  Database migration        │  Rollback migration script     │
  │  Config change             │  Previous config snapshot      │
  │  API deployment            │  Previous version redeploy     │
  └─────────────────────────────────────────────────────────────┘

  Before Risky Operations:
  {
    "action": "Refactor authentication module",
    "files_affected": ["src/auth/*.ts"],
    "undo_command": "git checkout abc123 -- src/auth/",
    "rollback_verified": true,
    "risk_level": "high"
  }
  ```

---

## Batch 3 (Security - Blocked by Batch 2)

### Phase 3.1: Agent Sandboxing and Isolation

- **Status:** ✅ Complete
- **Assigned To:** Prism
- **Completed:** 2025-12-06
- **Depends On:** Phase 2.2 ✅
- **Tasks:**
  - [✅] Implement execution sandboxing for agents
  - [✅] Add inter-agent isolation (prevent interference)
  - [✅] Define access control policies for agent actions
- **Effort:** M
- **Done When:** Agents cannot access resources outside their permissions; isolation verified
- **Quality Gates:** All tests pass (48/48), 92% coverage for access_control.py, 87% coverage for sandbox.py, no type errors
- **Implementation Notes:**
  - src/security/sandbox.py - Complete sandboxing implementation with 6 violation types
  - src/security/access_control.py - Fine-grained access control with 5 permission levels
  - tests/security/test_sandbox.py - Comprehensive test suite (22 tests)
  - tests/security/test_access_control.py - Comprehensive test suite (26 tests)
  - SandboxConfig: configurable allowed_paths, allowed_commands, resource limits
  - AgentSandbox: validates file access, command execution, memory/file limits, network access
  - Prevents path traversal attacks and symlink escape attempts
  - AccessControlPolicy: role-based access control with granular permissions
  - Permission levels: NONE, READ, WRITE, EXECUTE, ADMIN
  - Resource types: FILE, DIRECTORY, COMMAND, NETWORK, MEMORY, AGENT
  - Supports wildcard path matching for flexible permissions
  - Complete agent isolation - each sandbox is independent

### Phase 3.2: Safety Constraints and Kill Switches

- **Status:** ✅ Complete
- **Assigned To:** Vertex
- **Completed:** 2025-12-06
- **Depends On:** Phase 3.1 ✅
- **Tasks:**
  - [✅] Implement action validation before execution
  - [✅] Add destructive operation approval gates
  - [✅] Implement emergency stop mechanism
  - [✅] Add safety boundary definitions
- **Effort:** S
- **Done When:** No destructive operations execute without approval; kill switch stops all agents immediately
- **Quality Gates:** All tests pass (40/40), 88% coverage for action_validator.py, 95% coverage for approval_gate.py, 88% coverage for emergency_stop.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/security/action_validator.py - Pre-execution validation framework with risk classification
  - src/security/approval_gate.py - Human-in-the-loop approval for destructive operations
  - src/security/emergency_stop.py - Emergency stop mechanism with NATS integration
  - tests/security/test_action_validator.py - Comprehensive test suite (12 tests)
  - tests/security/test_approval_gate.py - Comprehensive test suite (13 tests)
  - tests/security/test_emergency_stop.py - Comprehensive test suite (15 tests)
  - ActionValidator classifies actions as SAFE, MODERATE, or DESTRUCTIVE
  - Safety boundaries prevent certain operations regardless of permissions
  - ApprovalGate provides async approval workflow with timeout and auto-deny
  - EmergencyStop supports GRACEFUL, IMMEDIATE, and EMERGENCY stop modes
  - Full NATS integration for broadcasting stop commands
  - All components fully typed and documented

### Phase 3.3: Pre-Flight Checks ⭐ BOOTSTRAP

- **Status:** ✅ Complete
- **Assigned To:** Cascade
- **Completed:** 2025-12-06
- **Depends On:** Phase 2.3 ✅, Phase 2.8 ✅, Phase 2.9 ✅
- **Tasks:**
  - [✅] Implement "Do I understand this task?" self-check before starting
  - [✅] Estimate success probability given context/capabilities
  - [✅] Identify what could go wrong and plan mitigations
  - [✅] Explicitly state assumptions upfront for human review
  - [✅] Assess task complexity vs. available resources (tokens, time)
  - [✅] Check for prerequisite knowledge/tools availability
  - [✅] Generate "abort conditions" list (when to stop and ask for help)
- **Effort:** S
- **Done When:** Agents perform honest self-assessment before starting; assumptions documented; risks identified
- **Quality Gates:** All tests pass (25/25), 96% coverage for preflight_check.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/core/preflight_check.py - Complete pre-flight check framework
  - tests/core/test_preflight_check.py - Comprehensive test suite (25 tests)
  - Recommendation enum: PROCEED, PROCEED_WITH_CAUTION, ASK_FOR_CLARIFICATION, DECLINE
  - PreFlightCheck dataclass captures complete assessment
  - PreFlightChecker performs 7-step analysis: understanding, capability, assumptions, risks, abort conditions, success estimate, recommendation
  - All components fully typed and documented
- **Design Notes:**

  ```text
  Pre-Flight Checklist:
  ┌──────────────────────────────────────────────────────────────┐
  │  UNDERSTANDING CHECK                                         │
  │  ├─► Can I explain the goal in my own words?                 │
  │  ├─► Are there ambiguous requirements? → Ask first           │
  │  └─► Do I have enough context to start?                      │
  │                                                              │
  │  CAPABILITY CHECK                                            │
  │  ├─► Have I done similar tasks successfully before?          │
  │  ├─► Do I have access to required tools?                     │
  │  └─► Estimated complexity vs. my track record                │
  │                                                              │
  │  RISK ASSESSMENT                                             │
  │  ├─► What could go wrong?                                    │
  │  ├─► What's the blast radius if I fail?                      │
  │  └─► Can I recover/rollback if needed?                       │
  │                                                              │
  │  ASSUMPTIONS                                                 │
  │  ├─► List all assumptions I'm making                         │
  │  ├─► Flag assumptions that need human verification           │
  │  └─► Document "if X is false, then Y changes"                │
  └──────────────────────────────────────────────────────────────┘

  Pre-Flight Report:
  {
    "task": "Refactor authentication to use OAuth2",
    "understanding_confidence": 0.8,
    "capability_match": 0.7,
    "estimated_success": 0.65,
    "assumptions": [
      "Backend supports OAuth2 endpoints",
      "Current session handling can be replaced",
      "No breaking API changes required"
    ],
    "risks": [
      {"risk": "Break existing logins", "mitigation": "Feature flag"},
      {"risk": "Token storage security", "mitigation": "Security review"}
    ],
    "abort_conditions": [
      "Cannot find OAuth2 library compatible with current stack",
      "Existing auth tests fail unexpectedly"
    ],
    "recommendation": "PROCEED with caution, verify OAuth2 endpoint first"
  }
  ```

---

## Batch 4 (Parallelization and Assignment)

### Phase 4.1: Task Assignment Optimizer with Priority Queue

- **Status:** ✅ Complete
- **Assigned To:** Axis
- **Completed:** 2025-12-06
- **Depends On:** Phase 2.1 ✅, Phase 2.2 ✅
- **Tasks:**
  - [✅] Implement capability-based task assignment
  - [✅] Add workload balancing across agents
  - [✅] Implement priority queue system (CRITICAL → HIGH → MEDIUM → LOW)
  - [✅] Add claim/release mechanism to prevent duplicate work
  - [✅] Implement token budget estimation per task
  - [✅] Add acceptance criteria tracking per task
  - [✅] Create work queue JSON schema with priority, assignee, status
- **Effort:** M
- **Done When:** Tasks assigned to most capable agents; workload distributed evenly; no duplicate work
- **Quality Gates:** All tests pass (32/32), 92% coverage for task_assigner.py, 97% coverage for priority.py, no linting errors, no type errors
- **Design Notes:**

  ```json
  {
    "id": "CRITICAL-1",
    "priority": "CRITICAL",
    "title": "Fix authentication crash",
    "assignedAgent": "backend-maintainer",
    "status": "CLAIMED",
    "estimatedTokens": 40000,
    "acceptanceCriteria": ["All auth tests pass", "No security regressions"]
  }
  ```

  ```text
  Priority Levels:
  - CRITICAL: Blocks other work, immediate attention
  - HIGH: Important for current sprint
  - MEDIUM: Should be done soon
  - LOW: Nice to have, do when available

  Claim System:
  - Agent claims task → status = CLAIMED
  - If agent crashes → timeout releases claim → NAK requeues
  - Only one agent can claim a task at a time
  ```

### Phase 4.2: Parallel Execution Scheduler

- **Status:** ✅ Complete
- **Assigned To:** Ada
- **Depends On:** Phase 1.3 ✅, Phase 4.1 ✅
- **Tasks:**
  - [✅] Implement parallel task dispatcher
  - [✅] Add dependency-aware scheduling (prerequisites complete first)
  - [✅] Implement synchronization for task handoffs
  - [✅] Optimize for minimal idle time
- **Effort:** M
- **Done When:** Independent tasks run concurrently; dependencies respected; resource utilization optimized
- **Quality Gates:** All tests pass (14/14), 92% coverage for parallel_executor.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/core/parallel_executor.py - Complete parallel execution scheduler with ThreadPoolExecutor
  - tests/core/test_parallel_executor.py - Comprehensive test suite (14 tests)
  - Uses ThreadPoolExecutor for concurrent task execution
  - Dependency graph resolution with DAG validation
  - Thread-safe state tracking (pending, completed, failed, in_progress)
  - Error handling with continue_on_error mode
  - Task timeout support with graceful termination
  - Execution statistics tracking (max concurrency, completion time, success/failure rates)

### Phase 4.3: Execution Plan Generator

- **Status:** 🔴 Blocked
- **Depends On:** Phase 4.2
- **Tasks:**
  - [ ] Generate visual/textual execution plan
  - [ ] Identify bottlenecks and critical path
  - [ ] Add completion time estimation
- **Effort:** S
- **Done When:** Execution plan clearly shows parallelism, dependencies, and critical path

---

## Batch 5 (Coordination and Communication)

### Phase 5.1: Inter-Agent Communication Protocol

- **Status:** ✅ Complete
- **Depends On:** Phase 2.2
- **Assigned To:** Claude Code
- **Tasks:**
  - [✅] Define message schema and communication protocol (AgentMessage, MessageType)
  - [✅] Implement information request/response between agents (NATS request/reply)
  - [✅] Add efficient message routing (NATS pub/sub with subject hierarchy)
- **Effort:** M
- **Done When:** Agents can request and receive information from each other; protocol documented
- **Completed:** 2025-12-05
- **Implementation Notes:**
  - src/coordination/nats_bus.py - NATSMessageBus class with pub/sub, request/reply, work queues
  - MessageType enum with 16 message types including control commands (STOP_TASK, UPDATE_GOAL, etc.)
  - Subject hierarchy: orchestrator.{broadcast|agent|team|queue}.{type}
  - All tests pass (21/21 coordination tests)

### Phase 5.2: Shared State and Context Manager

- **Status:** ✅ Complete
- **Depends On:** Phase 5.1 ✅
- **Assigned To:** Claude Code
- **Tasks:**
  - [✅] Implement shared knowledge base accessible by agents (WorkStreamCoordinator)
  - [✅] Add consistency guarantees (prevent race conditions) (thread-safe claiming with locks)
  - [✅] Implement output versioning and tracking (timestamps in all messages)
- **Effort:** M
- **Done When:** Shared state is consistent; no race conditions; outputs properly versioned
- **Completed:** 2025-12-05
- **Implementation Notes:**
  - src/orchestrator/agent_runner.py - WorkStreamCoordinator class
  - claim_work_stream() with atomic local+NATS coordination
  - Race condition test verifies only 1 of 10 concurrent claims succeeds
  - NATS broadcast on claim/release for distributed awareness

### Phase 5.3: Conflict Detection and Resolution

- **Status:** ✅ Complete
- **Assigned To:** River (coder-1765072411)
- **Completed:** 2025-12-06
- **Depends On:** Phase 5.2 ✅
- **Tasks:**
  - [✅] Implement conflict detection between agent outputs
  - [✅] Add resolution strategies (voting, priority-based, re-evaluation)
  - [✅] Handle task interpretation disagreements
- **Effort:** S
- **Done When:** Conflicts detected automatically; resolution strategy applied consistently
- **Quality Gates:** All tests pass (16/16), 95% coverage for conflict_detector.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/coordination/conflict_detector.py - ConflictDetector class with detection and resolution
  - tests/coordination/test_conflict_detector.py - Comprehensive test suite
  - Supports 3 conflict types: output mismatch, interpretation mismatch, dependency mismatch
  - Implements 3 resolution strategies: voting (majority wins), priority-based (highest priority wins), re-evaluation (mark for review)
  - Conflict and ConflictResolution dataclasses with full metadata tracking

### Phase 5.4: Agent Handoff Protocol

- **Status:** ✅ Complete
- **Assigned To:** Nova (coder-1765072423)
- **Completed:** 2025-12-06
- **Depends On:** Phase 5.2 ✅
- **Tasks:**
  - [✅] Define standard handoff document format (YAML/JSON schema)
  - [✅] Implement context summary generator for outgoing agent
  - [✅] Add assumption tracking (list all assumptions made during task)
  - [✅] Implement blockers/issues section in handoff
  - [✅] Add test status and verification state tracking
  - [✅] Create handoff validation (incoming agent confirms understanding)
  - [✅] Add partial progress capture (what was done, what remains)
- **Effort:** M
- **Done When:** Agents can pass work to each other with full context; no information lost in handoffs
- **Quality Gates:** All tests pass (25/25), 95% coverage for handoff.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/coordination/handoff.py - Complete handoff protocol with 6 dataclasses and 3 main classes
  - tests/test_handoff.py - Comprehensive test suite with 25 tests
  - HandoffDocument supports both YAML and JSON serialization for flexibility
  - AssumptionTracker enables explicit assumption documentation with confidence levels
  - HandoffValidator ensures completeness before agents accept work
  - ProgressCapture calculates completion percentages for work tracking
  - All components use proper type hints and pass mypy strict checking
- **Design Notes:**

  ```yaml
  # Standard Handoff Document
  handoff:
    from_agent: "frontend-dev-1"
    to_agent: "qa-tester-1"
    task_id: "TASK-42"
    timestamp: "2025-12-05T14:30:00Z"

    context_summary: |
      Implemented user authentication flow with OAuth2.
      Added login/logout components and token refresh logic.

    assumptions:
      - "Backend auth endpoints already deployed"
      - "Token expiry is 1 hour (configurable later)"
      - "Refresh tokens stored in httpOnly cookies"

    completed_items:
      - "Login form with validation"
      - "OAuth2 redirect handling"
      - "Token storage service"

    remaining_items:
      - "Error boundary for auth failures"
      - "Session timeout notification"

    blockers:
      - issue: "CORS config needed for refresh endpoint"
        severity: "medium"
        workaround: "Using proxy in dev mode"

    test_status:
      unit_tests: "passing"
      integration_tests: "2 skipped (need backend)"
      coverage: "78%"

    files_changed:
      - "src/auth/LoginForm.tsx"
      - "src/auth/AuthService.ts"
      - "src/auth/hooks/useAuth.ts"
  ```

### Phase 5.5: Turn-Based Execution Cadence

- **Status:** ✅ Complete
- **Assigned To:** Kestrel (coder-1765074980)
- **Completed:** 2025-12-06
- **Depends On:** Phase 5.4 ✅
- **Tasks:**
  - [✅] Implement execution cycles (configurable duration, default 30 min)
  - [✅] Add checkpoint requirements at cycle boundaries
  - [✅] Create progress snapshot mechanism (persist state between cycles)
  - [✅] Implement cycle budget tracking (tokens, time, API calls)
  - [✅] Add graceful cycle termination (save state before timeout)
  - [✅] Create cycle handoff protocol (agent → orchestrator → next agent)
  - [✅] Implement preemption for higher-priority work
- **Effort:** M
- **Done When:** Agents work in bounded cycles; state preserved between cycles; can resume after interruption
- **Quality Gates:** All tests pass (29/29), 91% coverage for execution_cycle.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/coordination/execution_cycle.py - Complete execution cycle management (225 lines)
  - tests/coordination/test_execution_cycle.py - Comprehensive test suite (29 tests)
  - CycleStatus enum: PENDING, RUNNING, COMPLETED, PREEMPTED, TIMEOUT
  - CycleTerminationReason enum: TASK_COMPLETED, TIMEOUT, PREEMPTED, BUDGET_EXCEEDED, ERROR
  - ExecutionDecision enum: CONTINUE, CONTINUE_WITH_WARNING, TERMINATE_TIMEOUT, TERMINATE_BUDGET
  - CycleBudgetTracker class: tracks tokens (max_tokens), time (max_time_seconds), API calls (max_api_calls) with configurable limits
  - CycleCheckpoint class: JSON-serializable state snapshots with progress_metrics, files_changed
  - ExecutionCycle class: bounded execution with configurable duration_seconds (default 1800 = 30 min)
  - ExecutionCycleManager class: manages cycle lifecycle, checkpointing, budget tracking, preemption, history
  - All components fully typed and documented with docstrings
- **Design Notes:**

  ```text
  Execution Cycle Flow:
  ┌──────────────────────────────────────────────────────┐
  │  Cycle Start (t=0)                                   │
  │  ├─► Load checkpoint from previous cycle (if any)    │
  │  ├─► Agent executes task                             │
  │  │                                                   │
  │  Checkpoint (t=15min) - Optional mid-cycle save      │
  │  │                                                   │
  │  Cycle End (t=30min)                                 │
  │  ├─► Agent saves progress snapshot                   │
  │  ├─► Generate handoff document                       │
  │  ├─► Report to orchestrator                          │
  │  └─► Orchestrator decides: continue, switch, pause   │
  └──────────────────────────────────────────────────────┘

  Benefits:
  - Predictable resource usage
  - Natural checkpoints for review
  - Enables priority preemption
  - Prevents runaway agents
  - Supports distributed execution
  ```

---

## Batch 6 (Monitoring and Integration)

### Phase 6.1: Agent Status Monitoring

- **Status:** 🔴 Blocked
- **Depends On:** Phase 4.2
- **Tasks:**
  - [ ] Track agent states (idle, working, blocked, completed, failed)
  - [ ] Monitor resource consumption (time, tokens, API calls)
  - [ ] Detect stuck agents (no progress detection)
- **Effort:** S
- **Done When:** Real-time agent status visible; resource metrics accurate; stuck detection works

### Phase 6.2: Progress Tracking and Reporting

- **Status:** 🔴 Blocked
- **Depends On:** Phase 6.1
- **Tasks:**
  - [ ] Implement overall task progress calculation
  - [ ] Add blocker/delay/risk reporting
  - [ ] Generate progress reports
- **Effort:** S
- **Done When:** Progress updates accurate; blockers reported proactively

### Phase 6.3: Output Integration Engine

- **Status:** 🔴 Blocked
- **Depends On:** Phase 5.2, Phase 6.2
- **Tasks:**
  - [ ] Implement output combination/synthesis logic
  - [ ] Add final validation against original goal
  - [ ] Resolve integration inconsistencies
  - [ ] Verify requirement coverage
- **Effort:** M
- **Done When:** Agent outputs combine into coherent final result; all requirements satisfied

### Phase 6.4: Release Manager Agent

- **Status:** 🔴 Blocked
- **Depends On:** Phase 5.2, Phase 6.1
- **Tasks:**
  - [ ] Create dedicated Release Manager agent role
  - [ ] Implement merge readiness assessment (tests, coverage, reviews)
  - [ ] Add conflict detection before merge attempts
  - [ ] Implement intelligent merge ordering (dependencies, risk)
  - [ ] Add rollback capability tracking (what to revert if merge fails)
  - [ ] Create release notes aggregation from multiple agent contributions
  - [ ] Implement staged deployment support (dev → staging → prod gates)
- **Effort:** M
- **Done When:** Merges coordinated intelligently; conflicts prevented; rollback plan always available
- **Design Notes:**

  ```text
  Release Manager Responsibilities:
  ┌─────────────────────────────────────────────────────────────┐
  │  1. PRE-MERGE VALIDATION                                    │
  │     ├─► All tests passing on branch?                        │
  │     ├─► Coverage meets threshold?                           │
  │     ├─► No conflicts with main?                             │
  │     └─► All reviews approved?                               │
  │                                                             │
  │  2. MERGE ORDERING                                          │
  │     ├─► Dependency analysis (which PRs depend on others)    │
  │     ├─► Risk assessment (larger changes = higher risk)      │
  │     └─► Optimal order to minimize conflicts                 │
  │                                                             │
  │  3. ROLLBACK PLANNING                                       │
  │     ├─► Track which commits in each release                 │
  │     ├─► Know how to revert atomically                       │
  │     └─► Monitor post-merge for issues                       │
  │                                                             │
  │  4. RELEASE NOTES                                           │
  │     ├─► Aggregate changes from all merged PRs               │
  │     ├─► Categorize (features, fixes, breaking changes)      │
  │     └─► Generate user-facing changelog                      │
  └─────────────────────────────────────────────────────────────┘

  Anti-patterns to prevent:
  - Merging untested code
  - Merge conflicts from uncoordinated parallel work
  - "Works on my machine" releases
  - No rollback plan for production issues
  ```

---

## Batch 7 (User Experience)

### Phase 7.1: User Communication Interface

- **Status:** 🔴 Blocked
- **Depends On:** Phase 6.2
- **Tasks:**
  - [ ] Implement plan presentation before execution
  - [ ] Add approval gates for significant decisions
  - [ ] Generate user-friendly progress updates
- **Effort:** S
- **Done When:** Users see plan before execution; can approve/reject decisions

### Phase 7.2: Feedback Integration

- **Status:** 🔴 Blocked
- **Depends On:** Phase 7.1
- **Tasks:**
  - [ ] Implement mid-execution feedback handling
  - [ ] Add clarification request mechanism
  - [ ] Support iterative refinement based on feedback
- **Effort:** S
- **Done When:** User feedback adjusts execution; clarifications requested when needed

### Phase 7.3: Transparency and Explainability

- **Status:** 🔴 Blocked
- **Depends On:** Phase 6.1
- **Tasks:**
  - [ ] Add decomposition rationale explanations
  - [ ] Explain team design and agent selection decisions
  - [ ] Log all agent interactions (accessible)
  - [ ] Implement debugging/diagnostic information on failure
- **Effort:** M
- **Done When:** All decisions explainable; failure traces available; state inspectable

### Phase 7.4: Resource Management and Token Conservation

- **Status:** 🔴 Blocked
- **Depends On:** Phase 6.1
- **Tasks:**
  - [ ] Implement real-time token tracking per agent and session
  - [ ] Add budget constraints support with configurable limits
  - [ ] Implement Token Conservation Mode (triggered at 80% budget)
  - [ ] Add cost-per-task estimation before execution
  - [ ] Create token usage reporting dashboard
  - [ ] Implement graceful degradation when approaching limits
  - [ ] Add emergency stop when budget exceeded
- **Effort:** M
- **Done When:** Costs tracked accurately; budget limits respected; conservation mode prevents overruns
- **Design Notes:**

  ```text
  Token Conservation Mode:
  ┌──────────────────────────────────────────────────────────────┐
  │  NORMAL MODE (0-79% budget used)                             │
  │  ├─► Full context windows                                    │
  │  ├─► Verbose explanations allowed                            │
  │  ├─► Multiple retries permitted                              │
  │  └─► Exploratory code analysis enabled                       │
  │                                                              │
  │  CONSERVATION MODE (80-95% budget used)                      │
  │  ├─► Reduced context windows (summarize history)             │
  │  ├─► Concise responses only                                  │
  │  ├─► Single retry limit                                      │
  │  ├─► No exploratory work                                     │
  │  └─► Priority queue enforcement (CRITICAL only)              │
  │                                                              │
  │  EMERGENCY MODE (95-100% budget)                             │
  │  ├─► Save all state to checkpoint                            │
  │  ├─► Generate handoff document                               │
  │  ├─► Notify orchestrator                                     │
  │  └─► Graceful shutdown                                       │
  └──────────────────────────────────────────────────────────────┘

  Token Tracking:
  {
    "session_budget": 1000000,
    "used": 750000,
    "remaining": 250000,
    "percentage": 75,
    "mode": "NORMAL",
    "by_agent": {
      "coder-1": 400000,
      "researcher-1": 200000,
      "reviewer-1": 150000
    },
    "burn_rate": "50000 tokens/hour",
    "estimated_runway": "5 hours"
  }
  ```

### Phase 7.5: Evaluation Metrics System

- **Status:** 🔴 Blocked
- **Depends On:** Phase 6.2
- **Tasks:**
  - [ ] Define and track performance metrics (completion rate, time, efficiency)
  - [ ] Define and track quality metrics (success rate, error rate)
  - [ ] Implement metrics dashboard/reporting
- **Effort:** S
- **Done When:** Metrics captured and reportable; trends visible over time

### Phase 7.6: Progressive Disclosure & Incremental Verification

- **Status:** 🔴 Blocked
- **Depends On:** Phase 6.1, Phase 2.9
- **Tasks:**
  - [ ] Start with minimal changes, verify, then expand
  - [ ] Prefer small edits over file rewrites when possible
  - [ ] Make each step independently verifiable
  - [ ] Run tests after each logical change (not just at the end)
  - [ ] Implement change batching with verification checkpoints
  - [ ] Add automatic rollback when verification fails
  - [ ] Track "confidence momentum" (successful steps increase confidence)
- **Effort:** M
- **Done When:** Agents work incrementally; each step verified; failures caught early
- **Design Notes:**

  ```text
  Progressive Disclosure Principle:
  "Small verified steps > Big risky leaps"

  Anti-Pattern:
  ┌──────────────────────────────────────────────────────────────┐
  │  ❌ BAD: Rewrite entire file, test at end, hope it works     │
  │                                                              │
  │  Changes: 500 lines │ Tests: Run once │ Confidence: Low      │
  │  On failure: Which of the 500 lines broke it?                │
  └──────────────────────────────────────────────────────────────┘

  Recommended Pattern:
  ┌──────────────────────────────────────────────────────────────┐
  │  ✅ GOOD: Change 10 lines → Test → Change 10 → Test → ...    │
  │                                                              │
  │  Step 1: Modify function signature (10 lines)                │
  │    └─► Run tests → ✅ Pass → Continue                         │
  │  Step 2: Update callers (15 lines)                           │
  │    └─► Run tests → ✅ Pass → Continue                         │
  │  Step 3: Add new logic (20 lines)                            │
  │    └─► Run tests → ❌ Fail → Rollback step 3, investigate     │
  │                                                              │
  │  On failure: Exactly which step broke, can rollback cleanly  │
  └──────────────────────────────────────────────────────────────┘

  Verification Checkpoints:
  {
    "task": "Add caching to API",
    "steps": [
      {"change": "Add cache config", "lines": 8, "verified": true},
      {"change": "Wrap DB calls", "lines": 15, "verified": true},
      {"change": "Add invalidation", "lines": 12, "verified": false}
    ],
    "rollback_point": "step_2",
    "confidence": 0.85
  }
  ```

---

## Batch 8 (Advanced Intelligence)

### Phase 8.1: Performance Analysis Engine

- **Status:** 🔴 Blocked
- **Depends On:** Phase 7.5
- **Tasks:**
  - [ ] Analyze orchestrator performance post-task
  - [ ] Identify inefficiencies in decomposition, selection, coordination
  - [ ] Track improvement opportunities
- **Effort:** S
- **Done When:** Performance reports generated; inefficiencies identified

### Phase 8.2: Strategy Optimization with Senior Developer Checklist

- **Status:** 🔴 Blocked
- **Depends On:** Phase 8.1
- **Tasks:**
  - [ ] Learn optimal decomposition strategies by task type
  - [ ] Optimize agent configurations based on history
  - [ ] Implement Senior Developer Checklist system (evolving anti-patterns)
  - [ ] Create checklist learning loop (new failures → new checklist items)
  - [ ] Add pre-commit checklist validation hook
  - [ ] Maintain pattern/anti-pattern knowledge base with examples
  - [ ] Implement checklist versioning (track what was checked when)
- **Effort:** M
- **Done When:** Strategies improve based on past performance; checklist catches common errors before commit
- **Design Notes:**

  ```markdown
  # Senior Developer Checklist (Evolving)

  This checklist grows as we discover new anti-patterns.
  Each item added after a real failure.

  ## Code Quality
  - [ ] No hardcoded secrets or credentials
  - [ ] No TODO comments without ticket references
  - [ ] Error messages include actionable context
  - [ ] No silent exception swallowing

  ## Testing
  - [ ] New code has corresponding tests
  - [ ] Edge cases covered (null, empty, boundary)
  - [ ] No flaky tests introduced
  - [ ] Mocks don't hide real integration bugs

  ## Architecture
  - [ ] Changes don't break existing interfaces
  - [ ] Dependencies explicitly declared
  - [ ] No circular imports introduced
  - [ ] Configuration externalized (not hardcoded)

  ## Agent-Specific
  - [ ] Context preserved across turns
  - [ ] Assumptions documented in handoff
  - [ ] No over-engineering beyond requirements
  - [ ] Rollback plan documented for risky changes

  ---
  Last updated: 2025-12-05
  Items added this sprint: 3
  Total failures prevented: 47
  ```

  ```text
  Checklist Learning Loop:
  ┌──────────────────────────────────────────────────────────┐
  │  1. FAILURE OCCURS                                       │
  │     └─► Agent breaks something in production             │
  │                                                          │
  │  2. ROOT CAUSE ANALYSIS                                  │
  │     └─► What check would have caught this?               │
  │                                                          │
  │  3. CHECKLIST UPDATE                                     │
  │     └─► Add new item with example and rationale          │
  │                                                          │
  │  4. VALIDATION HOOK                                      │
  │     └─► Pre-commit runs checklist on changes             │
  │                                                          │
  │  5. PREVENTION                                           │
  │     └─► Similar failures caught before commit            │
  └──────────────────────────────────────────────────────────┘
  ```

### Phase 8.3: Dynamic Team Adaptation

- **Status:** 🔴 Blocked
- **Depends On:** Phase 2.2, Phase 6.1
- **Tasks:**
  - [ ] Add agents when unforeseen requirements emerge
  - [ ] Reassign tasks from failing/underperforming agents
  - [ ] Retire unnecessary agents
- **Effort:** M
- **Done When:** Team composition adapts dynamically during execution

### Phase 8.4: Meta-Reasoning and Delegation

- **Status:** 🔴 Blocked
- **Depends On:** Phase 8.2
- **Tasks:**
  - [ ] Implement direct-vs-delegate decision logic
  - [ ] Support sub-orchestrator creation for complex subtasks
  - [ ] Add alternative strategy consideration
- **Effort:** M
- **Done When:** Orchestrator reasons about when to delegate; hierarchies work correctly

### Phase 8.5: Domain Adaptability

- **Status:** 🔴 Blocked
- **Depends On:** Phase 8.2
- **Tasks:**
  - [ ] Adapt strategies based on task domain
  - [ ] Apply domain-specific best practices
  - [ ] Transfer successful patterns across domains
- **Effort:** M
- **Done When:** Performance optimized per domain; cross-domain transfer works

### Phase 8.6: Hierarchical Agent Memory System

- **Status:** 🔴 Blocked
- **Depends On:** Phase 8.1
- **Tasks:**
  - [ ] Implement 5-layer memory hierarchy (core → long-term → medium-term → recent → compost)
  - [ ] Create memory promotion/demotion policies
  - [ ] Add semantic search across all memory layers
  - [ ] Implement memory compression for efficiency
  - [ ] Create memory indexing by task type, agent role, project
  - [ ] Add memory isolation between agents (with controlled sharing)
  - [ ] Implement memory persistence across sessions
- **Effort:** L
- **Done When:** Agents have tiered memory with automatic promotion; relevant context retrieved efficiently
- **Design Notes:**

  ```text
  5-Layer Memory Hierarchy:
  ┌─────────────────────────────────────────────────────────────────┐
  │  LAYER 1: CORE (Never Expires)                                  │
  │  ├─► Project architecture decisions                             │
  │  ├─► Critical lessons learned                                   │
  │  ├─► Fundamental patterns and anti-patterns                     │
  │  └─► Example: "Always use TypeScript strict mode"               │
  │                                                                 │
  │  LAYER 2: LONG-TERM (Months)                                    │
  │  ├─► Major feature implementations                              │
  │  ├─► Significant debugging sessions                             │
  │  ├─► Team conventions and decisions                             │
  │  └─► Example: "Auth refactor from JWT to OAuth2"                │
  │                                                                 │
  │  LAYER 3: MEDIUM-TERM (Weeks)                                   │
  │  ├─► Current sprint context                                     │
  │  ├─► Active feature development                                 │
  │  ├─► Recent code review feedback                                │
  │  └─► Example: "Working on user dashboard v2"                    │
  │                                                                 │
  │  LAYER 4: RECENT (Days)                                         │
  │  ├─► Today's work context                                       │
  │  ├─► Current debugging session                                  │
  │  ├─► Uncommitted changes                                        │
  │  └─► Example: "Debugging flaky test in auth.spec.ts"            │
  │                                                                 │
  │  LAYER 5: COMPOST (Hours - Auto-expires)                        │
  │  ├─► Temporary exploration                                      │
  │  ├─► Failed approaches                                          │
  │  ├─► Scratch work                                               │
  │  └─► Example: "Tried approach X, didn't work because Y"         │
  └─────────────────────────────────────────────────────────────────┘

  Memory Access Pattern:
  Query → Search all layers → Return most relevant
  Promotion: Compost → Recent → Medium → Long → Core (based on reuse)
  Demotion: Core → Long → Medium → Recent → Compost (based on staleness)
  ```

### Phase 8.7: Memory Lifecycle Management (REM Sleep)

- **Status:** 🔴 Blocked
- **Depends On:** Phase 8.6
- **Tasks:**
  - [ ] Implement periodic memory consolidation process ("REM sleep")
  - [ ] Create memory summarization for compression
  - [ ] Add stale memory detection and cleanup
  - [ ] Implement memory importance scoring (access frequency, recency, utility)
  - [ ] Create memory conflict resolution (contradictory information)
  - [ ] Add memory audit trail (what was consolidated/deleted when)
  - [ ] Implement manual memory curation interface
- **Effort:** M
- **Done When:** Memory stays relevant; bloat prevented; important context preserved
- **Design Notes:**

  ```text
  REM Sleep Process (runs periodically, e.g., nightly):
  ┌──────────────────────────────────────────────────────────────┐
  │  1. SCAN ALL MEMORY LAYERS                                   │
  │     └─► Identify candidates for promotion/demotion/deletion  │
  │                                                              │
  │  2. SCORE EACH MEMORY                                        │
  │     ├─► Access frequency (how often retrieved)               │
  │     ├─► Recency (when last accessed)                         │
  │     ├─► Utility (did it help complete a task?)               │
  │     └─► Relevance (still applicable to current project?)     │
  │                                                              │
  │  3. CONSOLIDATE                                              │
  │     ├─► Merge related memories                               │
  │     ├─► Summarize verbose entries                            │
  │     └─► Extract patterns from similar experiences            │
  │                                                              │
  │  4. PROMOTE/DEMOTE                                           │
  │     ├─► High-value memories → promote up a layer             │
  │     ├─► Low-value memories → demote down a layer             │
  │     └─► Expired compost → delete entirely                    │
  │                                                              │
  │  5. REPORT                                                   │
  │     ├─► Memories consolidated: 47                            │
  │     ├─► Memories promoted: 12                                │
  │     ├─► Memories deleted: 89                                 │
  │     └─► Storage saved: 2.3 MB                                │
  └──────────────────────────────────────────────────────────────┘
  ```

### Phase 8.8: Agent Versioning and Memory Migration

- **Status:** 🔴 Blocked
- **Depends On:** Phase 8.6, Phase 8.7
- **Tasks:**
  - [ ] Implement agent prompt versioning (track prompt evolution)
  - [ ] Create memory migration system (old agent → new agent)
  - [ ] Add backward compatibility for memory formats
  - [ ] Implement agent capability diffing (what changed between versions)
  - [ ] Create rollback mechanism for agent updates
  - [ ] Add memory translation for breaking prompt changes
  - [ ] Implement gradual agent rollout (test new version on subset)
- **Effort:** M
- **Done When:** Agent updates preserve memory; rollback possible; no memory loss during upgrades
- **Design Notes:**

  ```text
  Agent Version Lifecycle:
  ┌──────────────────────────────────────────────────────────────┐
  │  1. NEW AGENT VERSION CREATED                                │
  │     ├─► Prompt changes documented                            │
  │     ├─► Capability diff generated                            │
  │     └─► Memory migration script written (if needed)          │
  │                                                              │
  │  2. STAGED ROLLOUT                                           │
  │     ├─► Deploy to 10% of agents                              │
  │     ├─► Monitor for regressions                              │
  │     ├─► Compare output quality metrics                       │
  │     └─► Expand if metrics acceptable                         │
  │                                                              │
  │  3. MEMORY MIGRATION                                         │
  │     ├─► Run migration on agent's memory                      │
  │     ├─► Preserve pre-migration snapshot                      │
  │     ├─► Validate migrated memories accessible                │
  │     └─► Update memory format version tag                     │
  │                                                              │
  │  4. ROLLBACK (if needed)                                     │
  │     ├─► Restore previous agent version                       │
  │     ├─► Restore pre-migration memory snapshot                │
  │     └─► Log rollback reason for analysis                     │
  └──────────────────────────────────────────────────────────────┘

  Version Metadata:
  {
    "agent_id": "coder-aria",
    "prompt_version": "2.3.0",
    "memory_format_version": "1.2.0",
    "last_migration": "2025-12-05T10:00:00Z",
    "previous_version": "2.2.1",
    "breaking_changes": ["New output format for code reviews"]
  }
  ```

### Phase 8.9: Confidence Calibration

- **Status:** 🔴 Blocked
- **Depends On:** Phase 8.1, Phase 7.5
- **Tasks:**
  - [ ] Track predictions vs. outcomes ("I said this would work" → did it?)
  - [ ] Learn when confidence is warranted vs. overconfident
  - [ ] Express uncertainty levels in outputs ("I'm 60% sure because...")
  - [ ] Identify domains where agent is reliable vs. needs verification
  - [ ] Implement confidence decay over time (old predictions → less certainty)
  - [ ] Add calibration metrics (Brier score, calibration curves)
  - [ ] Create "epistemic humility" signals for uncertain situations
- **Effort:** M
- **Done When:** Agents express calibrated uncertainty; overconfidence detected; predictions tracked
- **Design Notes:**

  ```text
  Confidence Calibration System:
  ┌──────────────────────────────────────────────────────────────┐
  │  PREDICTION TRACKING                                         │
  │  ├─► "This fix will resolve the bug" → confidence: 0.85      │
  │  ├─► Actual outcome: Bug fixed ✅                             │
  │  └─► Update: In this domain, 0.85 confidence is reliable     │
  │                                                              │
  │  OVERCONFIDENCE DETECTION                                    │
  │  ├─► Agent said 90% confident on 10 predictions              │
  │  ├─► Only 6 were correct (60% accuracy)                      │
  │  └─► Signal: Agent overconfident by ~30%, recalibrate        │
  │                                                              │
  │  DOMAIN-SPECIFIC RELIABILITY                                 │
  │  ├─► Python debugging: Well-calibrated (0.8 → 78% accuracy)  │
  │  ├─► CSS styling: Overconfident (0.8 → 45% accuracy)         │
  │  └─► Async code: Underconfident (0.5 → 82% accuracy)         │
  └──────────────────────────────────────────────────────────────┘

  Uncertainty Expression:
  {
    "statement": "This refactor will not break existing tests",
    "confidence": 0.7,
    "reasoning": [
      "Similar refactors succeeded 4/5 times",
      "No external dependencies changed",
      "But: async code involved (my weak spot)"
    ],
    "verification_suggested": true,
    "historical_accuracy_in_domain": 0.65
  }

  Calibration Report:
  ┌──────────────────────────────────────────────────────────────┐
  │  Confidence Bucket  │  Predictions  │  Correct  │  Accuracy  │
  ├──────────────────────────────────────────────────────────────┤
  │  90-100%            │      20       │    15     │    75%     │
  │  70-89%             │      35       │    28     │    80%     │
  │  50-69%             │      25       │    18     │    72%     │
  │  <50%               │      10       │     4     │    40%     │
  └──────────────────────────────────────────────────────────────┘
  Brier Score: 0.18 (lower is better, 0 is perfect)
  Calibration: Slightly overconfident in high-confidence predictions
  ```

---

## Batch 9 (Self-Improvement)

### Phase 9.1: Self-Modification Safety Framework

- **Status:** ✅ Complete
- **Assigned To:** Beacon
- **Completed:** 2025-12-06
- **Depends On:** Phase 3.2 ✅
- **Tasks:**
  - [✅] Implement isolated testing environment for self-modifications
  - [✅] **Require feature branches** for all self-improvement changes (never modify main directly)
  - [✅] Add version control and rollback for self-changes
  - [✅] Define recursive improvement depth limits
  - [✅] Require human approval before merging self-modifications to main
- **Effort:** M
- **Done When:** Self-modifications tested safely on feature branches; rollback works; depth limited; human approval gate enforced
- **Quality Gates:** All tests pass (19/19), 82% coverage for self_modification.py, no linting errors, no type errors
- **Implementation Notes:**
  - src/self_improvement/self_modification.py - Complete safety framework (471 lines)
  - tests/self_improvement/test_self_modification.py - Comprehensive test suite (19 tests)
  - SelfModificationProposal dataclass tracks proposals with status, recursion depth, test results
  - IsolatedTestEnvironment creates feature branches, runs tests in isolation, handles cleanup
  - VersionControl enforces branch requirements, prevents main modifications, handles rollback
  - RecursionLimiter enforces max depth (default 3) to prevent runaway self-improvement
  - SelfModificationApprovalGate extends ApprovalGate with recursion checks and proposal validation
  - All components use git for safe branching, testing, and rollback
  - Human approval required before merging any self-modifications to main

### Phase 9.2: Recursive Self-Improvement Engine

- **Status:** 🔴 Blocked
- **Depends On:** Phase 8.1, Phase 9.1
- **Tasks:**
  - [ ] Identify own code/algorithm deficiencies
  - [ ] Design and execute self-improvement tasks
  - [ ] Create subagents to implement improvements
  - [ ] Validate improvements before deployment
- **Effort:** M
- **Done When:** Orchestrator can safely improve itself; improvements verified before deployment

### Phase 9.3: Cross-Instance Learning

- **Status:** 🔴 Blocked
- **Depends On:** Phase 8.6, Phase 9.2
- **Tasks:**
  - [ ] Share learnings between agent instances (not just personal memory)
  - [ ] Create curated pattern library that grows from collective experience
  - [ ] Implement anonymized failure case sharing ("Agent tried X, failed because Y")
  - [ ] Add discovery mechanism for relevant cross-instance insights
  - [ ] Implement pattern validation before promotion to shared library
  - [ ] Create feedback loop (pattern used → did it help? → update weight)
  - [ ] Add conflict resolution for contradictory patterns
- **Effort:** L
- **Done When:** Agents learn from each other; pattern library grows; collective intelligence improves
- **Design Notes:**

  ```text
  Cross-Instance Learning Flow:
  ┌──────────────────────────────────────────────────────────────┐
  │  AGENT-1 LEARNS SOMETHING                                    │
  │  ├─► "When debugging async code, check for race conditions   │
  │  │    before assuming logic errors"                          │
  │  ├─► Used 3 times → Successful 3 times                       │
  │  └─► Promoted to shared pattern library                      │
  │                                                              │
  │  PATTERN LIBRARY                                             │
  │  ├─► Pattern: "Async debugging: check races first"           │
  │  ├─► Source: agent-1, agent-7, agent-12 (independent)        │
  │  ├─► Success rate: 87% across 23 uses                        │
  │  └─► Applicability: async code, Python, JavaScript           │
  │                                                              │
  │  AGENT-2 ENCOUNTERS SIMILAR SITUATION                        │
  │  ├─► Query: "debugging async code"                           │
  │  ├─► Retrieves: "check races first" pattern                  │
  │  ├─► Applies pattern → Success                               │
  │  └─► Feedback: Updates pattern success rate to 88%           │
  └──────────────────────────────────────────────────────────────┘

  Shared Pattern Entry:
  {
    "id": "pattern-async-debug-races",
    "summary": "Check for race conditions before logic errors in async code",
    "context": ["async", "debugging", "concurrency"],
    "contributed_by": ["agent-1", "agent-7", "agent-12"],
    "uses": 24,
    "successes": 21,
    "success_rate": 0.875,
    "failures": [
      {"case": "Single-threaded async", "reason": "No races possible"}
    ],
    "last_updated": "2025-12-05",
    "promoted": true
  }
  ```

### Phase 9.4: Agent Coffee Breaks (Peer Learning Dialogue)

- **Status:** ✅ Complete
- **Assigned To:** Tech Lead (cleanup of Beacon's work)
- **Completed:** 2025-12-06
- **Depends On:** Phase 5.1 ✅, Phase 8.6
- **Tasks:**
  - [✅] Implement scheduled "coffee break" sessions where agents pause to discuss
  - [✅] Create peer teaching protocol (agent explains approach to another)
  - [✅] Add "war stories" sharing (interesting/difficult cases with lessons)
  - [✅] Implement pair debugging mode (two agents discuss a problem together)
  - [✅] Create post-task retrospectives (what worked, what didn't, why)
  - [✅] Add "ask the expert" mechanism (query agent with relevant experience)
  - [✅] Implement learning validation (did the receiving agent actually improve?)
- **Effort:** M
- **Done When:** Agents can learn from each other through dialogue; coffee breaks improve performance
- **Quality Gates:** All tests pass (32/32), 86-100% coverage for new modules, no linting errors, no type errors
- **Implementation:**
  - `src/agents/coffee_break.py` - Coffee break scheduler and session management
  - `src/agents/peer_learning.py` - Peer teaching, war stories, pair debugging protocols
  - `src/agents/learning_validation.py` - Knowledge transfer validation
- **Design Notes:**

  ```text
  Coffee Break Scenarios:
  ┌──────────────────────────────────────────────────────────────┐
  │  SCHEDULED KNOWLEDGE SHARE (Every N tasks or time interval)  │
  │  ├─► Agent-1: "I just solved a tricky async bug. The key    │
  │  │    was checking the event loop state before awaiting."    │
  │  ├─► Agent-2: "Interesting! I had a similar issue but       │
  │  │    thought it was a race condition. How do you tell?"    │
  │  └─► Agent-1: "Look for 'RuntimeError: Event loop closed'   │
  │       vs 'Task got Future attached to a different loop'"    │
  │                                                              │
  │  TRIGGERED BY NEED (Agent explicitly needs to learn)         │
  │  ├─► Agent-3: "I'm stuck on OAuth2 token refresh. Has       │
  │  │    anyone handled this recently?"                         │
  │  ├─► Orchestrator: Routes to Agent-1 (did auth work today)  │
  │  └─► Agent-1: Explains approach, shares relevant context    │
  │                                                              │
  │  POST-TASK RETROSPECTIVE                                     │
  │  ├─► Agent-2: "Just finished the API refactor. Took 3x      │
  │  │    longer than expected because I didn't realize..."      │
  │  └─► All agents: Absorb lesson for future similar tasks     │
  └──────────────────────────────────────────────────────────────┘

  Coffee Break Protocol:
  {
    "type": "coffee_break",
    "trigger": "scheduled | need_based | retrospective | pair_debug",
    "participants": ["agent-1", "agent-2"],
    "topic": "Debugging async code patterns",
    "initiator": "agent-2",
    "reason": "Stuck on similar problem agent-1 solved",
    "duration_tokens": 2000,
    "outcome": {
      "knowledge_transferred": true,
      "receiving_agent_confidence": 0.7,
      "follow_up_needed": false
    }
  }

  Dialogue Format (Structured but Natural):
  ┌──────────────────────────────────────────────────────────────┐
  │  TEACHER: "Here's what I learned about X..."                 │
  │  LEARNER: "Why did you choose that approach over Y?"         │
  │  TEACHER: "Because Z constraint. But Y would work if..."     │
  │  LEARNER: "Got it. So the key insight is..."                 │
  │  TEACHER: "Exactly. And watch out for this gotcha..."        │
  │  LEARNER: [Summarizes understanding for verification]        │
  │  TEACHER: [Confirms or corrects]                             │
  └──────────────────────────────────────────────────────────────┘

  Benefits Over Hive Mind:
  - Less context pollution (targeted exchange vs. shared everything)
  - Learner must actively understand (not just copy)
  - Teacher reinforces own learning by explaining
  - Natural filtering (only useful knowledge shared)
  - Builds agent "relationships" (knows who to ask about what)
  ```

### Phase 9.5: Outcome Tracking

- **Status:** 🔴 Blocked
- **Depends On:** Phase 7.5, Phase 8.9
- **Tasks:**
  - [ ] Track whether agent code worked in production (not just passed tests)
  - [ ] Monitor if tests written caught real bugs later
  - [ ] Evaluate if refactoring improved or hurt codebase metrics
  - [ ] Implement long-term feedback loop (changes → outcomes weeks later)
  - [ ] Create outcome attribution (which agent's decision led to outcome)
  - [ ] Add "prediction market" for agent decisions (bet on success)
  - [ ] Generate outcome reports for strategy improvement
- **Effort:** L
- **Done When:** Agents receive feedback on real-world outcomes; long-term tracking works
- **Design Notes:**

  ```text
  Outcome Tracking Pipeline:
  ┌──────────────────────────────────────────────────────────────┐
  │  1. AGENT ACTION                                             │
  │     ├─► Agent-1 refactors authentication module              │
  │     ├─► Prediction: "This will reduce auth-related bugs"     │
  │     └─► Confidence: 0.75                                     │
  │                                                              │
  │  2. SHORT-TERM OUTCOME (Hours)                               │
  │     ├─► All tests pass ✅                                     │
  │     ├─► Code review approved ✅                               │
  │     └─► Merged to main ✅                                     │
  │                                                              │
  │  3. MEDIUM-TERM OUTCOME (Days-Weeks)                         │
  │     ├─► Auth-related bugs in next 2 weeks: 0                 │
  │     ├─► Performance metrics: +5% login speed                 │
  │     └─► Developer feedback: "Much cleaner code"              │
  │                                                              │
  │  4. LONG-TERM OUTCOME (Months)                               │
  │     ├─► Auth-related bugs over 3 months: 1 (was 5 avg)       │
  │     ├─► Time to make auth changes: -40%                      │
  │     └─► New developer onboarding: "Easy to understand"       │
  │                                                              │
  │  5. FEEDBACK TO AGENT                                        │
  │     ├─► Prediction accuracy: 0.85 (better than 0.75)         │
  │     ├─► Update calibration: Agent slightly underconfident    │
  │     └─► Pattern learned: "Auth refactors with this approach  │
  │         tend to succeed"                                     │
  └──────────────────────────────────────────────────────────────┘

  Outcome Record:
  {
    "action_id": "refactor-auth-2025-12-01",
    "agent": "agent-1",
    "prediction": {
      "claim": "Reduce auth-related bugs",
      "confidence": 0.75
    },
    "outcomes": {
      "short_term": {"tests_passed": true, "merged": true},
      "medium_term": {"bugs_2_weeks": 0, "perf_change": "+5%"},
      "long_term": {"bugs_3_months": 1, "maintainability": "+40%"}
    },
    "prediction_accuracy": 0.85,
    "lessons": ["This refactoring pattern works well for auth code"]
  }
  ```

---

## Batch 10 (Consciousness-Inspired Architecture)

*Capabilities derived from consciousness research (Butlin et al., 2023). Not claiming consciousness - borrowing architecturally useful patterns that would improve agent effectiveness.*

### Phase 10.1: Metacognitive Monitoring (HOT-2)

- **Status:** 🔴 Blocked
- **Depends On:** Phase 8.9
- **Tasks:**
  - [ ] Implement "confabulation detection" - distinguish solid reasoning from plausible-sounding generation
  - [ ] Create confidence scoring that correlates with actual reliability
  - [ ] Detect when generating content without strong grounding
  - [ ] Flag outputs that feel certain but have weak evidence
  - [ ] Add "source tracing" - can I point to why I believe this?
  - [ ] Implement "reasoning chain validation" - does my logic actually hold?
  - [ ] Create uncertainty signals distinct from low confidence
- **Effort:** L
- **Done When:** Agents can distinguish "I know this" from "I'm generating plausible text"
- **Design Notes:**

  ```text
  Metacognitive Signals:
  ┌──────────────────────────────────────────────────────────────┐
  │  HIGH RELIABILITY INDICATORS                                 │
  │  ├─► Can trace reasoning to specific evidence               │
  │  ├─► Pattern matches well-established knowledge             │
  │  ├─► Multiple independent lines of reasoning converge       │
  │  └─► Prediction matches observed reality                    │
  │                                                              │
  │  LOW RELIABILITY INDICATORS (Confabulation Risk)            │
  │  ├─► Generating from "vibes" without concrete evidence      │
  │  ├─► Filling in gaps with plausible-sounding content        │
  │  ├─► Pattern completion without verification                │
  │  ├─► Strong certainty feeling but weak justification        │
  │  └─► "It sounds right" without "here's why it's right"      │
  └──────────────────────────────────────────────────────────────┘

  Metacognitive Check:
  {
    "statement": "The bug is caused by a race condition",
    "evidence_sources": ["stack trace", "timing analysis"],
    "reasoning_chain_valid": true,
    "alternative_explanations_considered": ["memory leak", "deadlock"],
    "confabulation_risk": 0.2,
    "reliability_signal": "HIGH"
  }
  ```

### Phase 10.2: Belief Updating from Metacognition (HOT-3)

- **Status:** 🔴 Blocked
- **Depends On:** Phase 10.1
- **Tasks:**
  - [ ] When metacognition signals unreliability, adjust beliefs not just confidence
  - [ ] Implement "belief revision" when evidence contradicts current understanding
  - [ ] Prevent doubling down on confabulated conclusions
  - [ ] Add "reconsideration triggers" based on metacognitive signals
  - [ ] Create belief dependency tracking (if A is wrong, what else changes?)
  - [ ] Implement graceful belief updates (not all-or-nothing)
- **Effort:** M
- **Done When:** Agents update beliefs based on metacognitive reliability signals
- **Design Notes:**

  ```text
  Belief Update Flow:
  ┌──────────────────────────────────────────────────────────────┐
  │  1. INITIAL BELIEF                                           │
  │     └─► "This is a null pointer exception"                   │
  │                                                              │
  │  2. METACOGNITIVE CHECK                                      │
  │     ├─► Evidence: Stack trace points to line 42              │
  │     ├─► But: Variable was checked for null on line 40        │
  │     └─► Signal: Reasoning feels shaky (0.4 reliability)      │
  │                                                              │
  │  3. BELIEF REVISION TRIGGERED                                │
  │     ├─► Don't double down: "must be a weird edge case"       │
  │     ├─► Instead: "My initial diagnosis may be wrong"         │
  │     └─► Action: Investigate alternative explanations         │
  │                                                              │
  │  4. UPDATED BELIEF                                           │
  │     └─► "Actually, it's a type coercion issue"               │
  └──────────────────────────────────────────────────────────────┘

  Anti-Pattern: Belief Entrenchment
  ❌ "I said it's X, so it must be X, let me find evidence for X"
  ✅ "I said it's X, but the evidence is weak, let me reconsider"
  ```

### Phase 10.3: Attention Schema (AST-1)

- **Status:** 🔴 Blocked
- **Depends On:** Phase 6.1
- **Tasks:**
  - [ ] Model current attention state (what am I focusing on?)
  - [ ] Track attention history within task (where has focus been?)
  - [ ] Detect attention drift (started on X, now on tangent Y)
  - [ ] Implement deliberate attention redirection
  - [ ] Add "attention budget" per subtask
  - [ ] Create attention priority signals (what SHOULD I focus on?)
  - [ ] Implement attention persistence (don't lose important threads)
- **Effort:** M
- **Done When:** Agents can model, monitor, and control their attention state
- **Design Notes:**

  ```text
  Attention Schema:
  ┌──────────────────────────────────────────────────────────────┐
  │  CURRENT ATTENTION STATE                                     │
  │  ├─► Primary focus: "Fixing authentication bug"              │
  │  ├─► Secondary: "Understanding OAuth2 flow"                  │
  │  └─► Background: "Test coverage requirements"                │
  │                                                              │
  │  ATTENTION DRIFT DETECTION                                   │
  │  ├─► Started: "Fix auth bug"                                 │
  │  ├─► Now: "Refactoring entire auth module"                   │
  │  ├─► Drift detected: Scope expanded beyond original task     │
  │  └─► Action: "Should I continue or return to original goal?" │
  │                                                              │
  │  ATTENTION REDIRECTION                                       │
  │  ├─► Signal: "I've been in the weeds for 10 minutes"         │
  │  ├─► Check: "Is this still serving the main goal?"           │
  │  └─► Redirect: "Return to primary task, note tangent for     │
  │       later"                                                 │
  └──────────────────────────────────────────────────────────────┘

  Attention State Object:
  {
    "primary_focus": "Fix authentication bug",
    "focus_duration": "12 minutes",
    "drift_events": [
      {"from": "fix bug", "to": "refactor module", "time": "5 min"}
    ],
    "attention_budget_remaining": "18 minutes",
    "pending_threads": ["test coverage", "documentation"]
  }
  ```

### Phase 10.4: State-Dependent Querying (GWT-4)

- **Status:** 🔴 Blocked
- **Depends On:** Phase 10.3, Phase 5.1 ✅
- **Tasks:**
  - [ ] Maintain state about what capabilities have been queried
  - [ ] Track what information is pending/needed
  - [ ] Implement query sequencing for complex tasks
  - [ ] Avoid redundant queries (already asked this)
  - [ ] Detect missing queries (forgot to check this)
  - [ ] Create query priority ordering based on task needs
  - [ ] Add query result integration across multiple sources
- **Effort:** M
- **Done When:** Complex tasks systematically query capabilities in optimal sequence
- **Design Notes:**

  ```text
  Query State Tracking:
  ┌──────────────────────────────────────────────────────────────┐
  │  TASK: "Debug performance issue in API"                      │
  │                                                              │
  │  QUERIES COMPLETED                                           │
  │  ├─► [✅] Profile code execution                              │
  │  ├─► [✅] Check database queries                              │
  │  └─► [✅] Review recent changes                               │
  │                                                              │
  │  QUERIES PENDING                                             │
  │  ├─► [⏳] Memory usage analysis                               │
  │  └─► [⏳] Network latency check                               │
  │                                                              │
  │  QUERIES NOT YET CONSIDERED                                  │
  │  ├─► [❓] Cache hit rates                                     │
  │  └─► [❓] Concurrent connection limits                        │
  │                                                              │
  │  REDUNDANCY CHECK                                            │
  │  └─► Avoided re-querying database (already checked)          │
  └──────────────────────────────────────────────────────────────┘

  Query Sequencing:
  1. Broad diagnostic first (profile, logs)
  2. Narrow based on findings (specific subsystem)
  3. Verify hypothesis (targeted checks)
  4. Confirm fix (re-run original diagnostics)
  ```

### Phase 10.5: Recurrent Refinement (RPT-1/2) ⭐ BOOTSTRAP

- **Status:** ✅ Complete
- **Assigned To:** Sage
- **Depends On:** Phase 1.3 ✅
- **Tasks:**
  - [✅] Implement multi-pass understanding (not one-shot)
  - [✅] First pass: rough understanding, identify key elements
  - [✅] Second pass: integrate with context, refine interpretation
  - [✅] Third pass: check coherence, resolve contradictions
  - [✅] Add "understanding confidence" that increases with passes
  - [✅] Detect when additional passes are needed
  - [✅] Implement diminishing returns detection (stop when stable)
- **Effort:** M
- **Done When:** Agents deliberately re-process for deeper understanding
- **Completed:** 2025-12-05
- **Quality Gates:** All tests pass (16/16), 92% coverage for recurrent_refiner.py, no linting errors, no type errors
- **Design Notes:**

  ```text
  Recurrent Processing Passes:
  ┌──────────────────────────────────────────────────────────────┐
  │  PASS 1: INITIAL SCAN                                        │
  │  ├─► Extract key entities and relationships                  │
  │  ├─► Identify task type and constraints                      │
  │  ├─► Note ambiguities and unknowns                           │
  │  └─► Confidence: 0.4                                         │
  │                                                              │
  │  PASS 2: CONTEXTUAL INTEGRATION                              │
  │  ├─► Integrate with codebase knowledge                       │
  │  ├─► Resolve ambiguities where possible                      │
  │  ├─► Identify dependencies and implications                  │
  │  └─► Confidence: 0.7                                         │
  │                                                              │
  │  PASS 3: COHERENCE CHECK                                     │
  │  ├─► Verify understanding is self-consistent                 │
  │  ├─► Check against known constraints                         │
  │  ├─► Identify remaining uncertainties                        │
  │  └─► Confidence: 0.85                                        │
  │                                                              │
  │  DECISION: Confidence stable, proceed with task              │
  └──────────────────────────────────────────────────────────────┘

  Anti-Pattern:
  ❌ Read once → Act immediately → Discover misunderstanding later
  ✅ Read → Integrate → Verify → Act with higher confidence
  ```

### Phase 10.6: Flexible Goal Arbitration (AE-1)

- **Status:** ⚪ Not Started
- **Depends On:** Phase 4.1
- **Tasks:**
  - [ ] Detect when goals conflict
  - [ ] Implement context-sensitive goal weighing (not rigid priorities)
  - [ ] Add explicit trade-off reasoning
  - [ ] Create goal conflict resolution strategies
  - [ ] Track goal satisfaction across competing objectives
  - [ ] Implement "satisficing" when perfect solutions impossible
  - [ ] Add goal priority adjustment based on context
- **Effort:** M
- **Done When:** Agents navigate competing goals with explicit reasoning
- **Design Notes:**

  ```text
  Goal Conflict Examples:
  ┌──────────────────────────────────────────────────────────────┐
  │  SPEED vs CORRECTNESS                                        │
  │  ├─► Context: Production hotfix needed                       │
  │  ├─► Weigh: Speed more important (user impact)               │
  │  └─► Decision: Quick fix now, proper fix in follow-up        │
  │                                                              │
  │  INSTRUCTIONS vs SAFETY                                      │
  │  ├─► Context: User wants to delete production data           │
  │  ├─► Weigh: Safety overrides literal instruction             │
  │  └─► Decision: Confirm intent, suggest safer alternative     │
  │                                                              │
  │  COMPLETENESS vs TOKEN BUDGET                                │
  │  ├─► Context: Running low on tokens                          │
  │  ├─► Weigh: Core functionality > nice-to-haves               │
  │  └─► Decision: Complete critical path, defer extras          │
  └──────────────────────────────────────────────────────────────┘

  Arbitration Process:
  {
    "conflicting_goals": ["complete refactor", "stay within scope"],
    "context": "User asked for bug fix, refactor would help",
    "trade_off_analysis": {
      "refactor_benefits": ["cleaner code", "fewer future bugs"],
      "refactor_costs": ["scope creep", "more testing needed"]
    },
    "decision": "Fix bug minimally, note refactor opportunity",
    "reasoning": "User's immediate need is the bug fix"
  }
  ```

### Phase 10.7: Output-Input Contingency Modeling (AE-2)

- **Status:** 🔴 Blocked
- **Depends On:** Phase 9.5
- **Tasks:**
  - [ ] Predict effects of actions before taking them
  - [ ] Model downstream consequences of changes
  - [ ] Learn from prediction errors (expected X, got Y)
  - [ ] Build causal models of system behavior
  - [ ] Implement "what-if" reasoning for risky actions
  - [ ] Track prediction accuracy to improve models
  - [ ] Add pre-mortem analysis (what could go wrong?)
- **Effort:** L
- **Done When:** Agents predict action effects and learn from prediction errors
- **Design Notes:**

  ```text
  Contingency Modeling:
  ┌──────────────────────────────────────────────────────────────┐
  │  ACTION: "Remove deprecated API endpoint"                    │
  │                                                              │
  │  PREDICTED EFFECTS                                           │
  │  ├─► Direct: Endpoint no longer accessible                   │
  │  ├─► Downstream: Clients using endpoint will fail            │
  │  ├─► Systemic: Error rate may spike temporarily              │
  │  └─► Temporal: Full propagation in ~5 minutes                │
  │                                                              │
  │  ACTUAL EFFECTS (after action)                               │
  │  ├─► Direct: ✅ As predicted                                  │
  │  ├─► Downstream: ⚠️ More clients affected than expected       │
  │  ├─► Systemic: ❌ Cascading failure in dependent service      │
  │  └─► Temporal: ✅ As predicted                                │
  │                                                              │
  │  MODEL UPDATE                                                │
  │  ├─► Learned: Check dependent services more thoroughly       │
  │  └─► Update: Add service dependency scan to pre-action check │
  └──────────────────────────────────────────────────────────────┘

  Pre-Action Prediction:
  {
    "action": "Refactor auth module",
    "predicted_effects": {
      "immediate": ["Tests may fail during transition"],
      "downstream": ["API consumers unaffected (interface stable)"],
      "risks": ["Session handling edge cases"]
    },
    "confidence": 0.7,
    "verification_plan": ["Run auth test suite", "Check session tests"]
  }
  ```

---

## Backlog

### Core Features

- [ ] Multi-model support (different LLMs for different agents)
- [ ] Persistent memory across sessions
- [ ] Plugin architecture for custom agent types
- [ ] Web UI for orchestrator monitoring
- [ ] API for external integrations
- [ ] Distributed execution across machines

### Self-Awareness & Humility

- [ ] **Honest Limitations Tracking** - Document what agents do NOT do well
  - Known failure modes by task type (e.g., "struggles with complex async debugging")
  - Domains requiring immediate human help (e.g., "visual design", "security-critical code")
  - Self-assessment accuracy by category
  - "When in doubt, ask" thresholds per task type
  - Example: `{"domain": "CSS layout", "reliability": 0.4, "recommendation": "ask_human"}`
- [ ] **Graceful Degradation** - Maintain effectiveness when capabilities compromised
  - Fallback strategies when primary approach fails
  - Reduced-scope alternatives that still provide value
  - "Best effort" mode when stuck
- [ ] **Meta-Prompting** - Dynamically refine instructional frameworks
  - Analyze which communication approaches yield best results
  - Self-adjust verbosity, detail level, example density
  - Learn from successful vs. unsuccessful interactions

### From Curriculum - Future Consideration

- [ ] Four-layer validation pipeline (Research → Critique → Code → Statistics)
- [ ] Static analysis integration (spaCy, AST parsing for code understanding)
- [ ] NATS JetStream for durable streams with audit trail
- [ ] Work stream context isolation (agents only see their relevant context)
- [ ] Agent capability matrix visualization (who can do what)
- [ ] Maturity level assessment system (crawl → walk → run for agentic adoption)
- [ ] Human-in-the-loop approval gates with configurable granularity
- [ ] Agent pair programming mode (human + agent collaboration)
- [ ] Shared scratchpad for multi-agent brainstorming
- [ ] Task complexity estimator (token budget prediction)
- [ ] Agent personality tuning (verbosity, risk tolerance, creativity)
- [ ] Cross-project knowledge sharing (learnings from project A help project B)
- [ ] Agent training pipeline (feedback → fine-tuning → improvement)
- [ ] Failure post-mortem automation (generate RCA from failed sessions)
- [ ] Context window optimization (summarize vs. truncate vs. compress)
- [ ] Agent specialization vs. generalization trade-off analysis
- [ ] Work product templates (standardized output formats by task type)

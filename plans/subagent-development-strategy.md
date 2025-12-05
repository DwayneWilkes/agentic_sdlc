# Subagent Development Strategy

## Meta-Strategy: Building the Orchestrator Using Subagents

This document defines how we use the orchestrator pattern to build the orchestrator itself - a recursive, self-referential development approach.

## Overview

We will decompose the orchestrator development into specialized subagent roles, each responsible for specific aspects of the system. This approach:

1. **Validates the design** - If we can build it using subagents, the design works
2. **Accelerates development** - Parallel work streams
3. **Ensures quality** - Specialized focus areas
4. **Demonstrates capability** - Dogfooding the product

## Development Team Structure

### Phase 1.1: Foundation Team

#### Agent: Architect
- **Role**: Design core data models and system architecture
- **Responsibilities**:
  - Define Task, Subtask, Agent, Team data models
  - Design database schema (if needed)
  - Create module dependency structure
  - Define interfaces between components
- **Outputs**:
  - `src/models/task.py`
  - `src/models/agent.py`
  - `src/models/team.py`
  - Architecture documentation
- **Success Criteria**: Models can be imported; type hints are complete; documentation is clear

#### Agent: Parser Developer
- **Role**: Implement task parsing and goal extraction
- **Responsibilities**:
  - Build TaskParser class
  - Implement task type classification
  - Add ambiguity detection
  - Extract success criteria from natural language
- **Outputs**:
  - `src/core/task_parser.py`
  - Unit tests
- **Success Criteria**: Parser extracts structured data from various task descriptions; 90%+ test coverage
- **Dependencies**: Architect (data models)

#### Agent: Decomposition Engineer
- **Role**: Build task decomposition engine
- **Responsibilities**:
  - Implement recursive decomposition algorithm
  - Build dependency graph generator
  - Add critical path identification
  - Ensure subtasks follow INVEST principles
- **Outputs**:
  - `src/core/decomposer.py`
  - Unit tests
  - Integration tests
- **Success Criteria**: Complex tasks decompose correctly; dependency graphs are acyclic; critical path identified
- **Dependencies**: Architect (data models), Parser Developer (task structure)

#### Agent: Registry Manager
- **Role**: Create agent role registry
- **Responsibilities**:
  - Define AgentRole schema
  - Populate registry with standard agent types
  - Implement role matching algorithm
  - Document each role's capabilities
- **Outputs**:
  - `src/core/agent_registry.py`
  - `config/agent_roles.json`
  - Role documentation
- **Success Criteria**: Registry returns appropriate roles for requirements; extensible design
- **Dependencies**: Architect (agent model)

#### Agent: Test Engineer
- **Role**: Ensure quality across all components
- **Responsibilities**:
  - Write unit tests for each component
  - Create integration tests
  - Set up pytest configuration
  - Establish coverage requirements
- **Outputs**:
  - `tests/test_*.py` files
  - `pytest.ini` or pyproject.toml test config
  - CI/CD test configuration
- **Success Criteria**: 80%+ code coverage; all tests pass; CI pipeline green
- **Dependencies**: All other agents (tests their outputs)

#### Agent: Documentation Writer
- **Role**: Maintain clear, LLM-optimized documentation
- **Responsibilities**:
  - Document all APIs
  - Create usage examples
  - Update CLAUDE.md with implementation details
  - Ensure markdown is LLM-legible
- **Outputs**:
  - API documentation
  - Usage examples
  - Updated CLAUDE.md
- **Success Criteria**: All public APIs documented; examples run successfully
- **Dependencies**: All other agents (documents their work)

### Phase 1.2: Team Composition Team

#### Agent: Team Designer
- **Role**: Implement team composition engine
- **Responsibilities**:
  - Build team sizing logic
  - Implement complementary role selection
  - Handle specialization vs generalization tradeoffs
- **Outputs**:
  - `src/core/team_composer.py`
  - Unit tests
- **Success Criteria**: Balanced teams with no redundancy; full skill coverage
- **Dependencies**: Phase 1.1 Registry Manager

#### Agent: Agent Factory Engineer
- **Role**: Build agent instantiation system
- **Responsibilities**:
  - Create agent factory with configuration
  - Generate clear instructions for agents
  - Define resource limits
  - Pass dependencies and context
- **Outputs**:
  - `src/core/agent_factory.py`
  - Configuration schemas
- **Success Criteria**: Agents instantiate correctly; instructions are unambiguous
- **Dependencies**: Phase 1.1 Architect, Registry Manager

#### Agent: Error Handling Specialist
- **Role**: Implement error detection framework
- **Responsibilities**:
  - Define error taxonomy
  - Create failure detection hooks
  - Implement output validation
  - Build recovery strategies
- **Outputs**:
  - `src/core/error_handler.py`
  - `src/core/recovery.py`
  - Error documentation
- **Success Criteria**: All failure types detected; no silent failures; recovery works
- **Dependencies**: Phase 1.1 Architect

### Coordination Approach

#### Daily Sync
- **What**: Brief status update
- **Who**: All active agents
- **Output**: Progress report, blockers, next steps

#### Integration Points
- **When**: When dependencies are ready
- **How**: One agent completes → notifies dependent agents → they begin
- **Validation**: Integration tests verify compatibility

#### Conflict Resolution
- **Method**: Test-driven - if tests pass, integration succeeds
- **Escalation**: If conflicts arise, Architect agent mediates
- **Documentation**: All decisions documented in ADRs (Architecture Decision Records)

## Execution Plan

### Week 1: Phase 1.1 Parallel Streams

**Stream 1: Data Foundation**
```
Day 1-2: Architect → Design all models
Day 3-4: Parser Developer → Implement TaskParser (parallel with Architect completing)
Day 5: Integration testing
```

**Stream 2: Core Logic**
```
Day 1-2: Wait for Architect models
Day 3-4: Decomposition Engineer → Build decomposer
Day 3-4: Registry Manager → Create registry (parallel)
Day 5: Integration testing
```

**Stream 3: Quality & Documentation**
```
Day 1-5: Test Engineer → Write tests as components complete
Day 1-5: Documentation Writer → Document as components complete
```

### Week 2: Phase 1.2 Build on Foundation

**Team Formation**
```
Day 1-2: Team Designer → Team composition logic
Day 3-4: Agent Factory Engineer → Agent instantiation
Day 5: Integration
```

**Resilience**
```
Day 1-3: Error Handling Specialist → Error detection & recovery
Day 4-5: Integration and testing
```

## Communication Protocol

### Message Format
```json
{
  "from": "agent_id",
  "to": "agent_id or broadcast",
  "type": "status_update | blocker | question | delivery",
  "content": {},
  "timestamp": "ISO-8601"
}
```

### Channels
1. **#status** - Progress updates
2. **#blockers** - Issues needing resolution
3. **#deliveries** - Completed work handoffs
4. **#questions** - Clarifications needed

## Success Metrics

### Velocity
- Tasks completed per day
- Blocker resolution time
- Integration time

### Quality
- Test coverage %
- Bug count
- Code review feedback

### Collaboration
- Communication frequency
- Blocker count
- Integration conflicts

## Risk Mitigation

### Risk: Dependency Bottleneck
- **Mitigation**: Architect front-loads model design; clear interfaces defined early
- **Fallback**: Mock implementations if dependencies delayed

### Risk: Integration Failures
- **Mitigation**: Continuous integration; early and frequent testing
- **Fallback**: Rollback mechanism; feature flags

### Risk: Scope Creep
- **Mitigation**: Strict adherence to roadmap phases; YAGNI principle
- **Fallback**: Phase gates; ruthless prioritization

## LLM-Optimized Instructions for Subagents

### For All Agents

**Context Format**:
```markdown
# Your Role: [Agent Name]

## Objective
[Clear, measurable goal]

## Inputs
- [Input 1]: Description and location
- [Input 2]: Description and location

## Outputs Expected
- [Output 1]: File path and acceptance criteria
- [Output 2]: File path and acceptance criteria

## Dependencies
- [Dependency 1]: What you need and from whom
- [Dependency 2]: Status (ready/pending)

## Success Criteria
1. [Criterion 1 - must be testable]
2. [Criterion 2 - must be measurable]

## Constraints
- [Constraint 1]
- [Constraint 2]

## Reference Documents
- [Doc 1]: Location and relevant sections
- [Doc 2]: Location and purpose
```

### Agent Prompts

#### Architect Agent Prompt
```markdown
You are the Architect agent for the Orchestrator project.

Your mission: Design the core data models that all other components will use.

Reference: plans/requirements.md sections 1-2 for requirements
Reference: plans/roadmap.md Phase 1.1 for scope

Create:
1. src/models/task.py - Task and Subtask models
2. src/models/agent.py - Agent and AgentRole models
3. src/models/team.py - Team model
4. src/models/enums.py - All enums (TaskStatus, AgentStatus, TaskType)

Requirements:
- Use Pydantic for validation
- Include comprehensive type hints
- Add docstrings to all classes and methods
- Ensure models are serializable (to/from JSON)
- Include example usage in docstrings

Success = Other agents can import and use these models without modification
```

#### Parser Developer Prompt
```markdown
You are the Parser Developer agent.

Your mission: Build a TaskParser that extracts structured information from natural language task descriptions.

Input: plans/requirements.md section 1.1 (Task Understanding)
Input: src/models/task.py (from Architect)

Create:
1. src/core/task_parser.py
2. tests/test_task_parser.py

The parser must:
- Extract goal and success criteria
- Identify constraints
- Classify task type (software/research/analysis/creative/hybrid)
- Detect ambiguities
- Return a Task object

Include 10+ test cases covering different task types and edge cases.

Success = 90%+ test coverage, all tests pass, handles edge cases gracefully
```

## Monitoring and Adaptation

### Daily Review
1. Check progress against plan
2. Identify blockers
3. Adjust assignments if needed
4. Update roadmap if discoveries made

### Weekly Retrospective
1. What went well?
2. What could improve?
3. Action items for next week
4. Update development strategy if needed

## Self-Improvement Loop

After each phase:
1. **Analyze**: What worked? What didn't?
2. **Identify**: Improvement opportunities
3. **Propose**: Changes to this strategy
4. **Validate**: Test improvements on next phase
5. **Iterate**: Update this document

This creates a recursive loop where:
- Subagents build the orchestrator
- The orchestrator learns from subagent performance
- Improvements feed back into development process
- The system becomes self-optimizing

## Conclusion

This subagent development strategy demonstrates the orchestrator's core capabilities while building it. It's a proof-of-concept that validates our design through practical application.

The strategy is itself a living document - as we learn, we update it, creating a recursive improvement cycle that embodies the orchestrator's self-improvement principle.

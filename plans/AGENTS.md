# plans/ - Planning Documents

Strategic planning, requirements, and roadmap for the orchestrator.

## Key Documents

| File                              | Purpose                  | Read For       |
| --------------------------------- | ------------------------ | -------------- |
| `requirements.md`                 | Orchestrator rubric      | What to build  |
| `roadmap.md`                      | Phases with status       | What's next    |
| `priorities.md`                   | Feature ordering         | Strategy       |
| `subagent-development-strategy.md`| Building with agents     | Meta-approach  |

## requirements.md

Defines what a good orchestrator must do across 15 areas:

1. Task Analysis & Decomposition
2. Agent Design & Selection
3. Task Assignment
4. Communication & Coordination
5. ...and more

Each area has criteria for Basic, Good, and Excellent implementations.

## roadmap.md

Phased implementation plan:

- **Phase 1.x** - Foundation (models, parsing)
- **Phase 2.x** - Core logic (decomposition, teams)
- **Phase 3.x** - Execution (running agents)
- ...through Phase 9 (self-improvement)

Status markers:

- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Complete
- `[BLOCKED: reason]` - Waiting on dependency

## completed/

Archive of completed planning documents and phase reviews.

## Working With Plans

When implementing features:

1. Check `roadmap.md` for current phase
2. Reference `requirements.md` for acceptance criteria
3. Update status when complete
4. The `RoadmapGardener` auto-unblocks dependent phases

## Related

- Implementation: [src/](../src/AGENTS.md)
- Project overview: [AGENTS.md](../AGENTS.md)

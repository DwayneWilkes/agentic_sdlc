# src/self_improvement/ - Meta-Learning & Self-Modification

Autonomous improvement of the orchestrator itself.

## Current State

**Not started** - This is Phase 9 in the roadmap.

## Planned Capabilities

### Performance Analysis

- Track execution metrics
- Identify bottlenecks
- Measure success rates

### Strategy Optimization

- Learn from successful patterns
- Adjust team compositions
- Refine decomposition strategies

### Code Self-Modification

- Propose improvements to orchestrator code
- Generate and test patches
- Safe rollback mechanisms

## Safety Constraints

From CLAUDE.md, self-modification must:

1. **Use feature branches** - Never modify main directly
2. **Test in isolation** - Full test suite must pass
3. **Require human approval** - No auto-merge
4. **Maintain rollback** - Previous state accessible
5. **Document rationale** - Explain why changes help

## Example Workflow

```bash
# Self-improvement proposes a change
git checkout -b self-improve/optimize-task-parser

# Make changes, run tests
pytest tests/

# Commit with explanation
git commit -m "Self-improvement: Optimize task parser

Analysis showed 40% of time spent in regex matching.
Replaced with compiled patterns, 3x speedup measured."

# Human reviews and decides
```

## Related

- Roadmap Phase 9: [plans/roadmap.md](../../plans/roadmap.md)
- Safety guidelines: [CLAUDE.md](../../CLAUDE.md)

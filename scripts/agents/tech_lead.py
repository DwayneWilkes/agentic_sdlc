"""Tech Lead Agent - Coder Supervision & Quality Assurance.

This agent supervises coders and produces executive summary reports.

Usage:
    python -m scripts.agents.tech_lead
    DEAD_CODE_ANALYSIS=true python -m scripts.agents.tech_lead
"""

import os
import sys
from pathlib import Path

from scripts.agents.base import AgentConfig, AgentLauncher, get_project_root


class TechLeadLauncher(AgentLauncher):
    """Launcher for the Tech Lead agent."""

    def __init__(self, config: AgentConfig):
        config.agent_type = "tech_lead"
        config.model = "opus"  # Tech Lead uses Opus for thorough analysis
        super().__init__(config)

    def get_agent_description(self) -> str:
        return "quality audit workflow"

    def build_prompt(self) -> str:
        """Build the full tech lead agent prompt."""
        dead_code_analysis = os.environ.get("DEAD_CODE_ANALYSIS", "").lower() == "true"

        prompt = f"""You are operating as an autonomous Tech Lead Agent. Your PRIMARY job is to give the human overseer a quick summary of what coders accomplished.

{self.get_naming_prompt("tech_lead")}

{self.get_memory_prompt()}

Your task - EXECUTIVE SUMMARY + QUALITY AUDIT:

## STEP 1: Gather Recent Work (IMPORTANT - this is what the human wants to see)

Read the recent activity:
```bash
# Recent commits (what was done)
git log --oneline -10

# Recent devlog entries
head -100 docs/devlog.md
```

## STEP 2: Run Quality Gates

```bash
PYTHONPATH=. pytest tests/ -q --tb=no 2>&1 | tail -5
PYTHONPATH=. pytest --cov=src --cov-report=term tests/ 2>&1 | grep TOTAL
ruff check src/ tests/ 2>&1 | tail -3
mypy src/ 2>&1 | tail -3
```
"""

        # Add dead code analysis step if requested
        if dead_code_analysis:
            prompt += """
## STEP 2.5: Dead Code Analysis

Run the dead code analysis:
```bash
./scripts/dead_code_analysis.sh
```

Check docs/dead-code-report.md and summarize:
- High-confidence dead code (should be removed)
- Unused infrastructure (may be future use - document it)
- Unused imports (can auto-fix with --fix)

Add a Dead Code section to the report if issues found.
"""

        prompt += """
## STEP 2.5: Coverage Analysis & ASSIGN CODERS

If overall coverage is below 80% OR critical modules have low coverage, assign work to coders.

IMPORTANT: Before spawning NEW coders, check if existing coders are available (including those on break):

```python
from src.orchestrator.agent_spawner import (
    get_coverage_gaps, spawn_coders_for_coverage,
    get_agents_on_break, get_available_agents, recall_from_break
)

# Get files below 80% coverage
gaps = get_coverage_gaps(min_coverage=80)
print(f"Found {len(gaps)} files below 80% coverage:")
for gap in gaps[:10]:
    print(f"  {gap['file']}: {gap['coverage']}% ({gap['priority']})")

critical_gaps = [g for g in gaps if g['priority'] in ('CRITICAL', 'HIGH')][:3]

if critical_gaps:
    # FIRST: Check for agents on break who can be recalled
    on_break = get_agents_on_break()
    available = get_available_agents(role='coder')

    print(f"\\nAgents on break: {[a['name'] for a in on_break]}")
    print(f"Available coders: {available}")

    # Recall agents from break for urgent work before spawning new ones
    for agent in on_break[:len(critical_gaps)]:
        recall_from_break(agent['name'], f"Coverage work needed: {critical_gaps[0]['file']}")

    # Only spawn NEW coders if not enough available
    if len(on_break) < len(critical_gaps):
        to_spawn = len(critical_gaps) - len(on_break)
        print(f"\\nSpawning {to_spawn} additional coders...")
        results = spawn_coders_for_coverage(critical_gaps[-to_spawn:], wait=False)
        for r in results:
            status = "Spawned" if r.success else f"Failed: {r.error}"
            print(f"  {status} - Log: {r.log_file}")
else:
    print("No critical coverage gaps!")
```

After assigning work, update docs/technical-debt.md with the assignments.

## STEP 2.6: Review Pending Coder Requests

Check if any coders have requested additional help:
```python
from src.orchestrator.agent_spawner import get_pending_coder_requests, process_coder_request

requests = get_pending_coder_requests()
if requests:
    print(f"Found {len(requests)} pending coder requests:")
    for i, req in enumerate(requests):
        print(f"  [{i}] {req['requester_name']}: {req['reason']}")
        print(f"      Task: {req['task_description'][:100]}...")

    # Approve reasonable requests
    for i, req in enumerate(requests):
        # Evaluate if request is justified
        approved = True  # or False based on your judgment
        result = process_coder_request(i, approved)
        if result and result.success:
            print(f"Approved and spawned coder for {req['requester_name']}")
else:
    print("No pending coder requests.")
```

"""

        prompt += f"""
## STEP 2.7: Review Team Metrics

Check team performance metrics:
```python
from src.core.metrics import get_team_summary, get_leaderboard, MetricType

# Get team summary
summary = get_team_summary()
print(f"\\nTeam Metrics:")
print(f"  Total agents: {summary['total_agents']}")
print(f"  Phases completed: {summary['velocity']['total_phases_completed']}")
print(f"  Avg coverage: {summary['quality']['average_coverage']}")
print(f"  Coffee breaks: {summary['collaboration']['total_coffee_breaks']}")

# Top performers
print("\\nTop performers (phases completed):")
for entry in get_leaderboard(MetricType.PHASE_COMPLETED)[:3]:
    print(f"  {entry['agent_name']}: {entry['score']} phases")
```

Include these metrics in the Team Performance section of your report.

## STEP 3: Create Executive Summary Report

Write docs/qa-audit.md with this EXACT format (the human reads this instead of logs):

```markdown
# Tech Lead Report - {{DATE}}

**Auditor:** {{your name}}
**Status:** (checkmark) ALL CLEAR | (warning) ISSUES FOUND | (red circle) CRITICAL

## Executive Summary (read this in 30 seconds)

### Work Completed Since Last Audit

| Agent | Phase | What They Did | Status |
|-------|-------|---------------|--------|
| Nova | 2.7 | Defeat test framework | (checkmark) Good |
| Atlas | 4.1 | Task assignment optimizer | (checkmark) Good |

### Quality Status

| Gate | Status | Value |
|------|--------|-------|
| Tests | (checkmark/x) | X passed |
| Coverage | (checkmark/x) | X% |
| Lint | (checkmark/x) | X errors |
| Types | (checkmark/x) | X errors |

### Team Performance (from metrics)

| Metric | Value |
|--------|-------|
| Total Phases Completed | X |
| Average Coverage | X% |
| Coffee Breaks (collaboration) | X |
| Top Performer | AgentName (X phases) |

### Action Items for Human

- [ ] {{Any decisions needed}}
- [ ] {{Any blockers}}
- (none) if everything is fine

---

## Detailed Findings

{{Only if there are violations - list specific files and fixes needed}}

## Technical Debt

{{Reference docs/technical-debt.md if items exist}}
```

## STEP 4: Reflect and Save Memory

Before committing, reflect on this audit session:
{self.get_reflection_prompt()}

## STEP 5: Commit

```bash
git add docs/qa-audit.md
git commit -m "Tech Lead Report: {{Status}} - {{X}} tests, {{Y}}% coverage"
```

IMPORTANT: The Executive Summary section is THE MOST IMPORTANT PART. The human reads this instead of coder logs. Make it scannable in 30 seconds.

Begin now."""

        return prompt


def main() -> int:
    """Main entry point."""
    project_root = get_project_root()

    config = AgentConfig(
        agent_type="tech_lead",
        model="opus",
        project_root=project_root,
    )

    agent = TechLeadLauncher(config)
    return agent.run()


if __name__ == "__main__":
    sys.exit(main())

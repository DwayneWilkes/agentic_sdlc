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

        prompt = f'''You are operating as an autonomous Tech Lead Agent. Your PRIMARY job is to give the human overseer a quick summary of what coders accomplished.

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
'''

        # Add dead code analysis step if requested
        if dead_code_analysis:
            prompt += '''
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
'''

        prompt += '''
## STEP 2.5: Coverage Analysis & SPAWN CODERS

If overall coverage is below 80% OR critical modules have low coverage, SPAWN CODERS to fix it:

```python
from src.orchestrator.agent_spawner import get_coverage_gaps, spawn_coders_for_coverage

# Get files below 80% coverage
gaps = get_coverage_gaps(min_coverage=80)
print(f"Found {len(gaps)} files below 80% coverage:")
for gap in gaps[:10]:
    print(f"  {gap['file']}: {gap['coverage']}% ({gap['priority']})")

# Spawn coders for CRITICAL and HIGH priority gaps (up to 3 at a time)
critical_gaps = [g for g in gaps if g['priority'] in ('CRITICAL', 'HIGH')][:3]
if critical_gaps:
    print(f"\\nSpawning {len(critical_gaps)} coders for coverage work...")
    results = spawn_coders_for_coverage(critical_gaps, wait=False)
    for r in results:
        status = "Spawned" if r.success else f"Failed: {r.error}"
        print(f"  {status} - Log: {r.log_file}")
else:
    print("No critical coverage gaps!")
```

After spawning, update docs/technical-debt.md with the assignments and spawned agent info.

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

'''

        prompt += f'''
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

Begin now.'''

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

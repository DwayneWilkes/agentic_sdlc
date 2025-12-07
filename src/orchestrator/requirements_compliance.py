"""Requirements compliance checker for the orchestrator.

This module evaluates the current implementation against the requirements
defined in plans/requirements.md and generates compliance reports.

The orchestrator is responsible for requirements governance - ensuring the
implementation meets the design criteria in the 15 capability areas.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ComplianceStatus(Enum):
    """Status of requirement compliance."""

    YES = "yes"
    NO = "no"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass
class Requirement:
    """A single requirement from the rubric."""

    id: str  # e.g., "1.1.1"
    section: str  # e.g., "Task Analysis and Decomposition"
    subsection: str  # e.g., "Task Understanding"
    question: str
    status: ComplianceStatus = ComplianceStatus.UNKNOWN
    evidence: str = ""
    notes: str = ""


@dataclass
class ComplianceReport:
    """Full compliance report across all requirements."""

    requirements: list[Requirement] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def calculate_summary(self) -> None:
        """Calculate compliance summary statistics."""
        total = len(self.requirements)
        yes_count = sum(1 for r in self.requirements if r.status == ComplianceStatus.YES)
        partial_count = sum(1 for r in self.requirements if r.status == ComplianceStatus.PARTIAL)
        no_count = sum(1 for r in self.requirements if r.status == ComplianceStatus.NO)
        unknown_count = sum(1 for r in self.requirements if r.status == ComplianceStatus.UNKNOWN)

        self.summary = {
            "total": total,
            "yes": yes_count,
            "partial": partial_count,
            "no": no_count,
            "unknown": unknown_count,
            "compliance_rate": (yes_count + partial_count * 0.5) / total if total > 0 else 0,
            "fully_compliant": yes_count == total,
        }

    def get_gaps(self) -> list[Requirement]:
        """Get requirements that are not fully met."""
        return [
            r
            for r in self.requirements
            if r.status in (ComplianceStatus.NO, ComplianceStatus.PARTIAL)
        ]

    def get_by_section(self, section: str) -> list[Requirement]:
        """Get requirements for a specific section."""
        return [r for r in self.requirements if r.section == section]


def parse_requirements(requirements_path: Path | None = None) -> list[Requirement]:
    """Parse requirements.md and extract all requirements.

    Args:
        requirements_path: Path to requirements.md file

    Returns:
        List of Requirement objects
    """
    if requirements_path is None:
        requirements_path = Path(__file__).parent.parent.parent / "plans" / "requirements.md"

    if not requirements_path.exists():
        return []

    content = requirements_path.read_text()
    requirements = []

    current_section = ""
    current_subsection = ""
    section_num = 0
    subsection_num = 0
    req_num = 0

    lines = content.split("\n")
    for line in lines:
        # Match section headers like "## 1. Task Analysis and Decomposition"
        section_match = re.match(r"^## (\d+)\. (.+)$", line)
        if section_match:
            section_num = int(section_match.group(1))
            current_section = section_match.group(2).strip()
            subsection_num = 0
            req_num = 0
            continue

        # Match subsection headers like "1.1 Task Understanding:"
        subsection_match = re.match(r"^(\d+)\.(\d+) (.+):$", line)
        if subsection_match:
            subsection_num = int(subsection_match.group(2))
            current_subsection = subsection_match.group(3).strip()
            req_num = 0
            continue

        # Match requirement questions like "- Does the orchestrator correctly identify..."
        req_match = re.match(r"^- (.+\?)\s*\(Yes/No/Partially\)$", line)
        if req_match and current_section and current_subsection:
            req_num += 1
            req_id = f"{section_num}.{subsection_num}.{req_num}"
            question = req_match.group(1).strip()

            requirements.append(
                Requirement(
                    id=req_id,
                    section=current_section,
                    subsection=current_subsection,
                    question=question,
                )
            )

    return requirements


# Evidence checkers - maps requirement patterns to code locations/tests
EVIDENCE_CHECKERS: dict[str, dict[str, Any]] = {
    # Section 1: Task Analysis and Decomposition
    "1.1.1": {
        "files": ["src/core/task_parser.py", "src/core/task_decomposer.py"],
        "tests": ["tests/core/test_task_parser.py"],
        "keywords": ["extract_goal", "success_criteria"],
    },
    "1.1.2": {
        "files": ["src/core/task_parser.py"],
        "tests": ["tests/core/test_task_parser.py"],
        "keywords": ["constraints", "requirements", "context"],
    },
    "1.1.3": {
        "files": ["src/core/task_parser.py"],
        "keywords": ["ambiguity", "clarification"],
    },
    "1.1.4": {
        "files": ["src/core/task_parser.py"],
        "tests": ["tests/core/test_task_parser.py"],
        "keywords": ["task_type", "classify"],
    },
    "1.2.1": {
        "files": ["src/core/task_decomposer.py"],
        "tests": ["tests/core/test_task_decomposer.py"],
        "keywords": ["decompose", "subtasks"],
    },
    "1.2.2": {
        "files": ["src/core/task_decomposer.py"],
        "keywords": ["independent", "testable", "estimable"],
    },
    "1.2.3": {
        "files": ["src/core/task_decomposer.py"],
        "tests": ["tests/core/test_task_decomposer.py"],
        "keywords": ["dependency", "dependencies", "graph"],
    },
    # Section 2: Team Design
    "2.1.1": {
        "files": ["src/agents/role_registry.py", "src/orchestrator/team_composition.py"],
        "keywords": ["role", "specialized"],
    },
    "2.2.1": {
        "files": ["src/orchestrator/team_composition.py"],
        "tests": ["tests/orchestrator/test_team_composition.py"],
        "keywords": ["team", "composition", "compose_team"],
    },
    # Section 4: Coordination
    "4.1.1": {
        "files": ["src/coordination/nats_bus.py", "src/coordination/message_types.py"],
        "tests": ["tests/coordination/test_nats_bus.py"],
        "keywords": ["message", "protocol", "publish", "subscribe"],
    },
    "4.2.1": {
        "files": ["src/coordination/conflict_resolution.py"],
        "tests": ["tests/coordination/test_conflict_resolution.py"],
        "keywords": ["conflict", "detect"],
    },
    # Section 5: Monitoring
    "5.1.1": {
        "files": ["src/orchestrator/agent_runner.py"],
        "keywords": ["status", "idle", "working", "blocked"],
    },
    # Section 6: Error Handling
    "6.1.1": {
        "files": ["src/core/safety_framework.py"],
        "tests": ["tests/core/test_safety_framework.py"],
        "keywords": ["failure", "detect", "error"],
    },
    "6.2.1": {
        "files": ["src/core/safety_framework.py"],
        "keywords": ["recovery", "retry", "fallback"],
    },
    # Section 8: Self-Improvement
    "8.1.1": {
        "files": ["src/self_improvement/"],
        "keywords": ["performance", "analyze"],
    },
    "8.5.1": {
        "files": ["src/core/agent_memory.py", "config/agent_memories/"],
        "tests": ["tests/core/test_agent_memory.py"],
        "keywords": ["memory", "remember", "past"],
    },
    # Section 15: Security
    "15.1.1": {
        "files": ["src/core/safety_framework.py"],
        "keywords": ["sandbox", "isolate"],
    },
    "15.2.1": {
        "files": ["src/core/safety_framework.py", "CLAUDE.md"],
        "keywords": ["safety", "boundary", "destructive"],
    },
    "15.3.1": {
        "files": ["CLAUDE.md"],
        "keywords": ["self-modification", "safeguard", "feature branch"],
    },
}


def check_file_exists(path: str, project_root: Path) -> bool:
    """Check if a file or directory exists."""
    full_path = project_root / path
    return full_path.exists()


def check_keyword_in_file(filepath: Path, keywords: list[str]) -> list[str]:
    """Check if keywords exist in a file."""
    if not filepath.exists():
        return []

    found = []
    try:
        content = filepath.read_text().lower()
        for keyword in keywords:
            if keyword.lower() in content:
                found.append(keyword)
    except Exception:
        pass

    return found


def evaluate_requirement(
    requirement: Requirement, project_root: Path | None = None
) -> Requirement:
    """Evaluate a single requirement against the codebase.

    Args:
        requirement: The requirement to evaluate
        project_root: Root of the project to check

    Returns:
        Updated requirement with status and evidence
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    checker = EVIDENCE_CHECKERS.get(requirement.id)
    if not checker:
        requirement.status = ComplianceStatus.UNKNOWN
        requirement.notes = "No automated check defined"
        return requirement

    evidence_parts = []
    score = 0
    max_score = 0

    # Check for required files
    files = checker.get("files", [])
    if files:
        max_score += 2
        existing_files = [f for f in files if check_file_exists(f, project_root)]
        if existing_files:
            score += 1 if len(existing_files) < len(files) else 2
            evidence_parts.append(f"Files found: {', '.join(existing_files)}")

    # Check for tests
    tests = checker.get("tests", [])
    if tests:
        max_score += 2
        existing_tests = [t for t in tests if check_file_exists(t, project_root)]
        if existing_tests:
            score += 2
            evidence_parts.append(f"Tests found: {', '.join(existing_tests)}")

    # Check for keywords in files
    keywords = checker.get("keywords", [])
    if keywords and files:
        max_score += 1
        all_found_keywords = set()
        for f in files:
            filepath = project_root / f
            if filepath.is_file():
                found = check_keyword_in_file(filepath, keywords)
                all_found_keywords.update(found)
            elif filepath.is_dir():
                for child in filepath.rglob("*.py"):
                    found = check_keyword_in_file(child, keywords)
                    all_found_keywords.update(found)

        if all_found_keywords:
            score += 0.5 if len(all_found_keywords) < len(keywords) else 1
            evidence_parts.append(f"Keywords found: {', '.join(all_found_keywords)}")

    # Determine status based on score
    if max_score > 0:
        ratio = score / max_score
        if ratio >= 0.8:
            requirement.status = ComplianceStatus.YES
        elif ratio >= 0.4:
            requirement.status = ComplianceStatus.PARTIAL
        else:
            requirement.status = ComplianceStatus.NO
    else:
        requirement.status = ComplianceStatus.UNKNOWN

    requirement.evidence = "; ".join(evidence_parts) if evidence_parts else "No evidence found"
    return requirement


def generate_compliance_report(project_root: Path | None = None) -> ComplianceReport:
    """Generate a full compliance report.

    Args:
        project_root: Root of the project to check

    Returns:
        ComplianceReport with all requirements evaluated
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    requirements = parse_requirements()
    evaluated = [evaluate_requirement(req, project_root) for req in requirements]

    report = ComplianceReport(requirements=evaluated)
    report.calculate_summary()

    return report


def format_report_markdown(report: ComplianceReport) -> str:
    """Format the compliance report as markdown.

    Args:
        report: The compliance report to format

    Returns:
        Markdown formatted string
    """
    lines = [
        "# Requirements Compliance Report",
        "",
        "## Summary",
        "",
        f"- **Total Requirements:** {report.summary['total']}",
        f"- **Fully Compliant (Yes):** {report.summary['yes']}",
        f"- **Partially Compliant:** {report.summary['partial']}",
        f"- **Not Compliant (No):** {report.summary['no']}",
        f"- **Unknown/Not Checked:** {report.summary['unknown']}",
        f"- **Compliance Rate:** {report.summary['compliance_rate']:.1%}",
        "",
    ]

    # Group by section
    sections: dict[str, list[Requirement]] = {}
    for req in report.requirements:
        if req.section not in sections:
            sections[req.section] = []
        sections[req.section].append(req)

    for section, reqs in sections.items():
        lines.append(f"## {section}")
        lines.append("")

        status_emoji = {"yes": "✅", "partial": "🟡", "no": "❌", "unknown": "❓"}

        for req in reqs:
            emoji = status_emoji.get(req.status.value, "❓")
            lines.append(f"### {req.id} {req.subsection}")
            lines.append("")
            lines.append(f"**Question:** {req.question}")
            lines.append("")
            lines.append(f"**Status:** {emoji} {req.status.value.upper()}")
            lines.append("")
            if req.evidence:
                lines.append(f"**Evidence:** {req.evidence}")
                lines.append("")
            if req.notes:
                lines.append(f"**Notes:** {req.notes}")
                lines.append("")

    # Gaps section
    gaps = report.get_gaps()
    if gaps:
        lines.append("## Action Items (Gaps to Address)")
        lines.append("")
        for gap in gaps:
            priority = "HIGH" if gap.status == ComplianceStatus.NO else "MEDIUM"
            lines.append(f"- [{priority}] {gap.id}: {gap.question[:80]}...")
        lines.append("")

    return "\n".join(lines)


def save_compliance_report(report: ComplianceReport, output_path: Path | None = None) -> Path:
    """Save the compliance report to a file.

    Args:
        report: The compliance report to save
        output_path: Where to save (defaults to docs/requirements-compliance.md)

    Returns:
        Path to the saved report
    """
    if output_path is None:
        output_path = Path(__file__).parent.parent.parent / "docs" / "requirements-compliance.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = format_report_markdown(report)
    output_path.write_text(markdown)

    return output_path


if __name__ == "__main__":
    # Generate and save compliance report
    report = generate_compliance_report()
    output = save_compliance_report(report)
    print(f"Compliance report saved to: {output}")
    print("\nSummary:")
    print(f"  Total: {report.summary['total']}")
    print(f"  Compliant: {report.summary['yes']}")
    print(f"  Partial: {report.summary['partial']}")
    print(f"  Gaps: {report.summary['no']}")
    print(f"  Rate: {report.summary['compliance_rate']:.1%}")

"""
Task Parser for extracting structured information from natural language.

This module provides the TaskParser class for parsing natural language
task descriptions into structured data models.
"""

import re
from dataclasses import dataclass, field

from src.models.enums import TaskType


@dataclass
class ParsedTask:
    """
    Result of parsing a task description.

    Contains structured information extracted from natural language input.
    """

    goal: str
    task_type: TaskType
    constraints: dict[str, list[str]] = field(default_factory=dict)
    context: dict[str, list[str]] = field(default_factory=dict)
    success_criteria: list[str] = field(default_factory=list)
    ambiguities: list[str] = field(default_factory=list)
    raw_description: str = ""

    def generate_clarification_requests(self) -> list[str]:
        """
        Generate clarification questions for detected ambiguities.

        Returns:
            List of clarification questions to ask the user
        """
        if not self.ambiguities:
            return []

        clarifications = []
        for ambiguity in self.ambiguities:
            if "vague" in ambiguity.lower():
                # Extract the vague term
                match = re.search(r"'([^']+)'", ambiguity)
                if match:
                    term = match.group(1)
                    clarifications.append(
                        f"What specifically do you mean by '{term}'? "
                        f"Can you provide measurable criteria?"
                    )
            elif "missing" in ambiguity.lower() or "unclear" in ambiguity.lower():
                clarifications.append(f"Can you clarify: {ambiguity}?")
            else:
                clarifications.append(f"Please clarify: {ambiguity}")

        return clarifications


class TaskParser:
    """
    Parses natural language task descriptions into structured data.

    Extracts:
    - Primary goal
    - Task type classification
    - Constraints (time, technology, quality, etc.)
    - Context (background, stakeholders, etc.)
    - Success criteria
    - Ambiguities (unclear or missing requirements)
    """

    # Keywords for task type classification
    SOFTWARE_KEYWORDS = {
        "implement",
        "build",
        "code",
        "develop",
        "api",
        "function",
        "class",
        "module",
        "endpoint",
        "deploy",
        "test",
        "fix",
        "debug",
        "refactor",
        "integrate",
        "application",
        "software",
        "program",
        "script",
        "service",
        "component",
        "feature",
        "bug",
    }

    RESEARCH_KEYWORDS = {
        "research",
        "investigate",
        "explore",
        "study",
        "survey",
        "review",
        "examine",
        "literature",
        "trends",
        "state-of-the-art",
        "latest",
        "papers",
        "findings",
        "discover",
        "learn about",
    }

    ANALYSIS_KEYWORDS = {
        "analyze",
        "evaluate",
        "assess",
        "compare",
        "benchmark",
        "measure",
        "identify",
        "determine",
        "calculate",
        "estimate",
        "profile",
        "audit",
        "inspect",
        "review",
        "examine",
        "check",
        "verify",
    }

    CREATIVE_KEYWORDS = {
        "design",
        "compose",
        "draft",
        "sketch",
        "mockup",
        "wireframe",
        "logo",
        "ui",
        "ux",
        "interface",
        "visual",
        "artwork",
        "campaign",
        "content",
        "story",
        "narrative",
        "documentation",
        "engaging",
        "marketing",
    }

    # Vague terms that indicate ambiguity
    VAGUE_TERMS = {
        "better",
        "faster",
        "improve",
        "enhance",
        "optimize",
        "good",
        "nice",
        "user-friendly",
        "intuitive",
        "modern",
        "efficient",
        "scalable",
        "robust",
        "reliable",
        "performant",
    }

    def parse(self, task_description: str) -> ParsedTask:
        """
        Parse a natural language task description into structured data.

        Args:
            task_description: The task description to parse

        Returns:
            ParsedTask containing extracted information
        """
        task_description = task_description.strip() if task_description else ""

        # Handle empty descriptions
        if not task_description:
            return ParsedTask(
                goal="",
                task_type=TaskType.SOFTWARE,
                ambiguities=["Task description is empty - no goal specified"],
                raw_description="",
            )

        return ParsedTask(
            goal=self._extract_goal(task_description),
            task_type=self._classify_task_type(task_description),
            constraints=self._extract_constraints(task_description),
            context=self._extract_context(task_description),
            success_criteria=self._extract_success_criteria(task_description),
            ambiguities=self._detect_ambiguities(task_description),
            raw_description=task_description,
        )

    def _extract_goal(self, text: str) -> str:
        """
        Extract the primary goal from the task description.

        For now, uses the first sentence as the primary goal.
        Future: Could use more sophisticated NLP.

        Args:
            text: Task description

        Returns:
            The primary goal statement
        """
        # Split into sentences
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return text

        # First sentence is usually the main goal
        return sentences[0]

    def _classify_task_type(self, text: str) -> TaskType:
        """
        Classify the task type based on keywords.

        Args:
            text: Task description

        Returns:
            TaskType classification
        """
        text_lower = text.lower()
        words = set(re.findall(r"\b\w+\b", text_lower))

        # Count matches for each type
        software_score = len(words & self.SOFTWARE_KEYWORDS)
        research_score = len(words & self.RESEARCH_KEYWORDS)
        analysis_score = len(words & self.ANALYSIS_KEYWORDS)
        creative_score = len(words & self.CREATIVE_KEYWORDS)

        scores = [
            (software_score, TaskType.SOFTWARE),
            (research_score, TaskType.RESEARCH),
            (analysis_score, TaskType.ANALYSIS),
            (creative_score, TaskType.CREATIVE),
        ]

        # Sort by score
        scores.sort(reverse=True, key=lambda x: x[0])

        # If multiple types are present, it's hybrid
        types_present = sum(1 for score, _ in scores if score >= 1)

        if types_present >= 3:
            # 3 or more types present = definitely hybrid
            return TaskType.HYBRID
        elif types_present >= 2 and scores[0][0] >= 1 and scores[1][0] >= 1:
            # 2 types present and second is close to first = hybrid
            if scores[1][0] >= scores[0][0] * 0.4:
                return TaskType.HYBRID

        # Return the highest scoring type, or SOFTWARE as default
        if scores[0][0] > 0:
            return scores[0][1]

        return TaskType.SOFTWARE  # Default

    def _extract_constraints(self, text: str) -> dict[str, list[str]]:
        """
        Extract constraints from the task description.

        Args:
            text: Task description

        Returns:
            Dictionary of constraint types to constraint values
        """
        constraints: dict[str, list[str]] = {
            "time": [],
            "technology": [],
            "quality": [],
            "other": [],
        }

        # Time constraints
        time_patterns = [
            r"\b(?:within|in|by)\s+(\d+\s+(?:day|week|month|hour)s?)\b",
            r"\b(?:by|before)\s+(monday|tuesday|wednesday|thursday|friday"
            r"|saturday|sunday)\b",
            r"\b(?:deadline|due date):\s*([^.!?]+)",
        ]
        for pattern in time_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                constraints["time"].append(match.group(1))

        # Technology constraints
        tech_patterns = [
            r"\b(?:using|with|in)\s+(react|vue|angular|python|java|typescript"
            r"|javascript|postgresql|mysql|mongodb|redis)\b",
            r"\b(?:must use|should use|require)\s+"
            r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b",
        ]
        for pattern in tech_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                constraints["technology"].append(match.group(1))

        # Quality constraints
        quality_patterns = [
            r"(\d+%)\s+(?:test\s+)?coverage",
            r"(?:must|should)\s+pass\s+([^.!?]+(?:lint|test|check))",
            r"\b(no\s+(?:errors|warnings|bugs))\b",
        ]
        for pattern in quality_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                constraints["quality"].append(match.group(1))

        # Must/should statements
        must_should = re.finditer(
            r"\b(?:must|should|need to|required to)\s+([^.!?]+)",
            text,
            re.IGNORECASE,
        )
        for match in must_should:
            constraint = match.group(1).strip()
            # Categorize or add to 'other'
            if not any(constraint in v for v in constraints.values()):
                constraints["other"].append(constraint)

        # Remove empty categories
        return {k: v for k, v in constraints.items() if v}

    def _extract_context(self, text: str) -> dict[str, list[str]]:
        """
        Extract context information from the task description.

        Args:
            text: Task description

        Returns:
            Dictionary of context types to context values
        """
        context: dict[str, list[str]] = {
            "background": [],
            "stakeholder": [],
            "other": [],
        }

        # Background context (current state, problems)
        background_patterns = [
            r"\b(?:current|currently|existing|old|outdated|legacy)\s+([^.!?]+)",
            r"\b(?:problem|issue|challenge):\s*([^.!?]+)",
            r"\bhas\s+(\d+[,\d]*\s+(?:users|customers|records|entries))",
        ]
        for pattern in background_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                context["background"].append(match.group(1).strip())

        # Stakeholder context
        stakeholder_patterns = [
            r"\b((?:marketing|sales|engineering|product|customer|user)s?"
            r"\s+team)\b",
            r"\b(?:for|to)\s+((?:users|customers|clients|stakeholders))\b",
        ]
        for pattern in stakeholder_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                context["stakeholder"].append(match.group(1).strip())

        # Remove empty categories
        return {k: v for k, v in context.items() if v}

    def _extract_success_criteria(self, text: str) -> list[str]:
        """
        Extract success criteria from the task description.

        Args:
            text: Task description

        Returns:
            List of success criteria
        """
        criteria = []

        # Explicit success criteria
        explicit_patterns = [
            r"(?:success criteria|done when|acceptance criteria):\s*"
            r"([^.!?]+(?:[.!?][^.!?]+)*)",
            r"\b(?:returns?|responds?)\s+(\d+\s+status)",
            r"\b(?:must|should)\s+(handle\s+\d+[^.!?]+)",
            r"\b(?:within|under|less than)\s+(\d+\s*(?:ms|seconds?"
            r"|milliseconds?))",
            r"\b(?:must|should)\s+support\s+([^.!?]+)",
        ]

        for pattern in explicit_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                criterion = match.group(1).strip()
                # Split on numbered lists
                sub_criteria = re.split(r"\d+\)", criterion)
                criteria.extend([c.strip() for c in sub_criteria if c.strip()])

        # Performance criteria
        perf_patterns = [
            r"(\d+[,\d]*\s+(?:requests?|queries)\s+per\s+(?:second|minute))",
            r"(?:respond|response time)(?:\s+(?:within|under))?\s+"
            r"(\d+\s*(?:ms|milliseconds?|seconds?))",
        ]
        for pattern in perf_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                criteria.append(match.group(1).strip())

        return list(set(criteria))  # Remove duplicates

    def _detect_ambiguities(self, text: str) -> list[str]:
        """
        Detect ambiguities and unclear requirements in the task description.

        Args:
            text: Task description

        Returns:
            List of detected ambiguities
        """
        ambiguities = []
        text_lower = text.lower()
        words = set(re.findall(r"\b\w+\b", text_lower))

        # Check for vague terms
        vague_found = words & self.VAGUE_TERMS
        for term in vague_found:
            ambiguities.append(
                f"Vague requirement: '{term}' needs specific "
                f"measurable criteria"
            )

        # Check for very short descriptions
        if len(text.split()) < 5:
            ambiguities.append(
                "Task description is very short and may be missing "
                "critical details"
            )

        # Check for missing details in certain contexts
        if any(word in text_lower for word in ["database", "store", "save"]):
            db_tech = ["postgresql", "mysql", "mongodb", "redis", "sqlite"]
            if not any(word in text_lower for word in db_tech):
                ambiguities.append(
                    "Missing detail: What database technology should be used?"
                )

        if any(word in text_lower for word in ["api", "endpoint"]):
            methods = ["get", "post", "put", "delete", "patch"]
            if not any(word in text_lower for word in methods):
                ambiguities.append(
                    "Missing detail: What HTTP method(s) should the "
                    "endpoint support?"
                )

        # Check for unclear scope
        if "feature" in text_lower or "system" in text_lower:
            if len(text.split()) < 20:
                ambiguities.append(
                    "Unclear scope: The feature/system description may "
                    "need more detail"
                )

        return ambiguities

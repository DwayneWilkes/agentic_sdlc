"""
Goal Interpreter - Translates user goals into work stream assignments.

Analyzes natural language goals and matches them to available work streams
in the roadmap.

Optimizations:
- Fuzzy matching for typos using difflib.SequenceMatcher
- Word tokenization with caching
"""

from difflib import SequenceMatcher
from functools import lru_cache
from typing import Optional
from dataclasses import dataclass

from src.orchestrator.work_stream import (
    WorkStream,
    parse_roadmap,
    get_available_work_streams,
)

# Minimum similarity ratio for fuzzy matching
FUZZY_THRESHOLD = 0.7


@lru_cache(maxsize=256)
def _tokenize(text: str) -> tuple[str, ...]:
    """Tokenize and cache text for repeated matching."""
    return tuple(text.lower().split())


def _fuzzy_match(text: str, keyword: str, threshold: float = FUZZY_THRESHOLD) -> bool:
    """Check if keyword fuzzy-matches anywhere in text."""
    text_lower = text.lower()

    # Exact match first (fast path)
    if keyword in text_lower:
        return True

    # Fuzzy match each word
    for word in text_lower.split():
        ratio = SequenceMatcher(None, word, keyword).ratio()
        if ratio >= threshold:
            return True

    return False


def _similarity_score(goal: str, work_stream_name: str) -> float:
    """Calculate similarity between goal and work stream name."""
    goal_words = set(_tokenize(goal))
    name_words = set(_tokenize(work_stream_name))

    # Calculate word overlap
    if not name_words:
        return 0.0

    # Check both exact and fuzzy matches
    matches = 0
    for name_word in name_words:
        if len(name_word) <= 3:  # Skip short words
            continue
        for goal_word in goal_words:
            if goal_word == name_word:
                matches += 1
                break
            elif SequenceMatcher(None, goal_word, name_word).ratio() >= FUZZY_THRESHOLD:
                matches += 0.7  # Partial credit for fuzzy match
                break

    return matches / len([w for w in name_words if len(w) > 3]) if name_words else 0.0


@dataclass
class InterpretedGoal:
    """Result of interpreting a user goal."""

    original_goal: str
    matched_work_streams: list[WorkStream]
    confidence: float  # 0.0 to 1.0
    explanation: str
    suggested_action: str


# Keywords mapped to work stream phases
KEYWORD_MAPPINGS = {
    # Phase 1.2 - Task Parser
    "parser": ["1.2"],
    "parse": ["1.2"],
    "goal extraction": ["1.2"],
    "task type": ["1.2"],
    "classify": ["1.2"],
    "ambiguity": ["1.2"],

    # Phase 1.3 - Decomposition
    "decompose": ["1.3"],
    "decomposition": ["1.3"],
    "breakdown": ["1.3"],
    "break down": ["1.3"],
    "subtask": ["1.3"],
    "dependency": ["1.3"],
    "critical path": ["1.3"],

    # Phase 1.4 - Agent Registry
    "registry": ["1.4"],
    "agent role": ["1.4"],
    "capabilities": ["1.4"],
    "role matching": ["1.4"],

    # Phase 2.x - Team and Error Handling
    "team": ["2.1"],
    "composition": ["2.1"],
    "instantiation": ["2.2"],
    "error": ["2.3", "2.4"],
    "recovery": ["2.4"],
    "retry": ["2.4"],

    # Phase 3.x - Security
    "sandbox": ["3.1"],
    "security": ["3.1", "3.2"],
    "isolation": ["3.1"],
    "safety": ["3.2"],
    "kill switch": ["3.2"],

    # Phase 4.x - Parallelization
    "assignment": ["4.1"],
    "parallel": ["4.2"],
    "scheduler": ["4.2"],
    "execution plan": ["4.3"],

    # Phase 5.x - Communication
    "communication": ["5.1"],
    "protocol": ["5.1"],
    "shared state": ["5.2"],
    "conflict": ["5.3"],

    # Phase 6.x - Monitoring
    "monitor": ["6.1"],
    "status": ["6.1"],
    "progress": ["6.2"],
    "integration": ["6.3"],

    # Phase 7.x - UX
    "user interface": ["7.1"],
    "feedback": ["7.2"],
    "transparency": ["7.3"],
    "cost": ["7.4"],
    "metrics": ["7.5"],

    # Phase 8.x - Advanced
    "performance": ["8.1"],
    "optimization": ["8.2"],
    "adaptation": ["8.3"],
    "meta": ["8.4"],
    "domain": ["8.5"],

    # Phase 9.x - Self-improvement
    "self-improvement": ["9.1", "9.2"],
    "recursive": ["9.2"],

    # General keywords
    "foundation": ["1.2", "1.3", "1.4"],
    "start": ["1.2"],
    "begin": ["1.2"],
    "next": [],  # Will use first available
    "all": [],  # Will use all available
    "everything": [],  # Will use all available
}


def interpret_goal(goal: str, roadmap_path=None) -> InterpretedGoal:
    """
    Interpret a user's goal and match it to work streams.

    Args:
        goal: Natural language goal from the user
        roadmap_path: Optional path to roadmap

    Returns:
        InterpretedGoal with matched work streams and explanation
    """
    goal_lower = goal.lower()
    all_streams = parse_roadmap(roadmap_path)
    available = get_available_work_streams(roadmap_path)

    # Check for "all" or "everything"
    if any(word in goal_lower for word in ["all", "everything", "batch"]):
        return InterpretedGoal(
            original_goal=goal,
            matched_work_streams=available,
            confidence=0.9,
            explanation=f"Running all {len(available)} available work streams",
            suggested_action="run_batch",
        )

    # Check for "next" or just starting
    if any(word in goal_lower for word in ["next", "start", "begin", "first"]):
        if available:
            return InterpretedGoal(
                original_goal=goal,
                matched_work_streams=[available[0]],
                confidence=0.9,
                explanation=f"Running next available work stream: Phase {available[0].id}",
                suggested_action="run_single",
            )

    # Match keywords to phases (with fuzzy matching)
    matched_phases = set()
    for keyword, phases in KEYWORD_MAPPINGS.items():
        if _fuzzy_match(goal_lower, keyword):
            matched_phases.update(phases)

    # Also search work stream names with similarity scoring
    similarity_scores: dict[str, float] = {}
    for ws in all_streams:
        score = _similarity_score(goal, ws.name)
        if score > 0.3:  # Minimum threshold for name matching
            similarity_scores[ws.id] = score
            matched_phases.add(ws.id)

        # Check if phase number is mentioned
        if ws.id in goal:
            matched_phases.add(ws.id)
            similarity_scores[ws.id] = 1.0  # Exact phase match

    # Filter to available work streams, sorted by similarity score
    matched_streams = [
        ws for ws in available
        if ws.id in matched_phases
    ]
    # Sort by similarity score (highest first)
    matched_streams.sort(
        key=lambda ws: similarity_scores.get(ws.id, 0),
        reverse=True
    )

    # Build explanation with confidence based on match quality
    if matched_streams:
        # Higher confidence for better similarity matches
        avg_score = sum(similarity_scores.get(ws.id, 0.5) for ws in matched_streams) / len(matched_streams)
        confidence = min(0.95, 0.4 + 0.3 * avg_score + 0.1 * min(len(matched_streams), 3))

        if len(matched_streams) == 1:
            explanation = f"Matched goal to Phase {matched_streams[0].id}: {matched_streams[0].name}"
            action = "run_single"
        else:
            explanation = f"Matched goal to {len(matched_streams)} work streams"
            action = "run_parallel"
    else:
        # No specific match - offer available work
        confidence = 0.3
        explanation = "Couldn't match specific work streams. Showing available work."
        matched_streams = available[:3]  # Suggest top 3
        action = "suggest"

    return InterpretedGoal(
        original_goal=goal,
        matched_work_streams=matched_streams,
        confidence=confidence,
        explanation=explanation,
        suggested_action=action,
    )


def format_interpretation(result: InterpretedGoal) -> str:
    """Format an interpreted goal for display."""
    lines = [f"Goal: {result.original_goal}"]
    lines.append(f"Interpretation: {result.explanation}")
    lines.append(f"Confidence: {result.confidence:.0%}")
    lines.append("")

    if result.matched_work_streams:
        lines.append("Matched work streams:")
        for ws in result.matched_work_streams:
            lines.append(f"  • Phase {ws.id}: {ws.name} [{ws.effort}]")
    else:
        lines.append("No matching work streams available.")

    lines.append("")
    lines.append(f"Suggested action: {result.suggested_action}")

    return "\n".join(lines)

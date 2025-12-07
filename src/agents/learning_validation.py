"""
Learning Validation - Measure knowledge transfer effectiveness.

Validates whether agents actually learned from peer learning sessions
by testing their knowledge before and after.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ValidationTest:
    """
    A test to validate learning.

    Attributes:
        test_id: Unique test identifier
        topic: Topic being tested
        questions: List of questions
        difficulty: Test difficulty (beginner, intermediate, advanced)
        created_at: When test was created
    """

    test_id: str
    topic: str
    questions: list[str]
    difficulty: str = "intermediate"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ValidationResult:
    """
    Result of a learning validation test.

    Attributes:
        agent_id: Agent who took the test
        test_id: Test identifier
        topic: Topic tested
        passed: Whether agent passed
        knowledge_before: Knowledge level before learning (0-1)
        knowledge_after: Knowledge level after learning (0-1)
        improvement: Improvement amount (knowledge_after - knowledge_before)
        answers: Agent's answers to questions
        timestamp: When test was taken
    """

    agent_id: str
    test_id: str
    topic: str
    passed: bool
    knowledge_before: float
    knowledge_after: float
    improvement: float
    answers: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "test_id": self.test_id,
            "topic": self.topic,
            "passed": self.passed,
            "knowledge_before": self.knowledge_before,
            "knowledge_after": self.knowledge_after,
            "improvement": self.improvement,
            "answers": self.answers,
            "timestamp": self.timestamp,
        }


class LearningValidator:
    """
    Validates learning effectiveness.

    Measures whether knowledge transfer was successful by:
    - Creating validation tests
    - Evaluating answers
    - Calculating improvement
    - Recommending follow-up learning if needed
    """

    PASS_THRESHOLD = 0.6  # 60% knowledge level to pass
    FOLLOW_UP_THRESHOLD = 0.4  # Recommend follow-up if improvement < 40%

    def __init__(self) -> None:
        """Initialize learning validator."""
        self.validation_history: list[ValidationResult] = []

    def create_test(
        self,
        topic: str,
        questions: list[str],
        difficulty: str = "intermediate",
    ) -> ValidationTest:
        """
        Create a validation test.

        Args:
            topic: Topic to test
            questions: List of questions
            difficulty: Test difficulty

        Returns:
            ValidationTest instance
        """
        test_id = f"test-{uuid.uuid4().hex[:8]}"

        return ValidationTest(
            test_id=test_id,
            topic=topic,
            questions=questions,
            difficulty=difficulty,
        )

    def validate(
        self,
        agent_id: str,
        test: ValidationTest,
        answers: dict[str, str],
        knowledge_before: float,
    ) -> ValidationResult:
        """
        Validate learning by evaluating test answers.

        Args:
            agent_id: Agent being validated
            test: Validation test
            answers: Agent's answers
            knowledge_before: Knowledge level before learning

        Returns:
            ValidationResult with pass/fail and improvement metrics
        """
        # Simplified scoring: count non-empty, substantive answers
        # In a real system, this would use LLM evaluation or semantic similarity
        total_questions = len(test.questions)

        # Keywords that indicate weak/uncertain answers
        weak_indicators = ["don't know", "maybe", "not sure", "i think", "possibly", "perhaps"]

        substantive_answers = sum(
            1 for answer in answers.values()
            if answer
            and len(answer) > 10
            and not any(indicator in answer.lower() for indicator in weak_indicators)
        )

        # Calculate knowledge after as percentage of good answers
        knowledge_after = substantive_answers / total_questions

        # Adjust based on difficulty
        if test.difficulty == "beginner":
            knowledge_after *= 1.1  # Easier, boost score
        elif test.difficulty == "advanced":
            knowledge_after *= 0.9  # Harder, reduce score

        # Ensure in valid range
        knowledge_after = min(1.0, max(0.0, knowledge_after))

        # Calculate improvement
        improvement = knowledge_after - knowledge_before

        # Determine pass/fail
        passed = knowledge_after >= self.PASS_THRESHOLD

        result = ValidationResult(
            agent_id=agent_id,
            test_id=test.test_id,
            topic=test.topic,
            passed=passed,
            knowledge_before=knowledge_before,
            knowledge_after=knowledge_after,
            improvement=improvement,
            answers=answers,
        )

        self.validation_history.append(result)
        return result

    def calculate_improvement(
        self,
        knowledge_before: float,
        knowledge_after: float,
    ) -> float:
        """
        Calculate knowledge improvement.

        Args:
            knowledge_before: Knowledge before learning
            knowledge_after: Knowledge after learning

        Returns:
            Improvement amount
        """
        return knowledge_after - knowledge_before

    def needs_follow_up(self, result: ValidationResult) -> bool:
        """
        Determine if follow-up learning is needed.

        Args:
            result: Validation result

        Returns:
            True if follow-up recommended, False otherwise
        """
        # Recommend follow-up if:
        # 1. Didn't pass
        # 2. Improvement was minimal
        # 3. Knowledge level still low
        return (
            not result.passed
            or result.improvement < self.FOLLOW_UP_THRESHOLD
            or result.knowledge_after < self.PASS_THRESHOLD
        )

    def recommend_follow_up(self, result: ValidationResult) -> dict[str, Any]:
        """
        Recommend follow-up learning.

        Args:
            result: Validation result

        Returns:
            Dictionary with follow-up recommendations
        """
        return {
            "topics": [result.topic],
            "reason": f"Knowledge level ({result.knowledge_after:.1%}) needs improvement",
            "suggested_difficulty": "beginner" if result.knowledge_after < 0.3 else "intermediate",
            "previous_improvement": result.improvement,
        }

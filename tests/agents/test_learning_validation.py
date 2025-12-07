"""
Tests for learning validation - measuring knowledge transfer effectiveness.
"""

from src.agents.learning_validation import (
    LearningValidator,
    ValidationResult,
    ValidationTest,
)


class TestLearningValidator:
    """Tests for learning validator."""

    def test_validator_creation(self):
        """Test creating a learning validator."""
        validator = LearningValidator()
        assert validator is not None

    def test_create_validation_test(self):
        """Test creating a validation test."""
        validator = LearningValidator()

        test = validator.create_test(
            topic="Test-Driven Development",
            questions=[
                "What is the TDD cycle?",
                "Why write tests first?",
                "What is pytest?",
            ],
            difficulty="beginner",
        )

        assert test.topic == "Test-Driven Development"
        assert len(test.questions) == 3
        assert test.difficulty == "beginner"

    def test_validate_learning_success(self):
        """Test validating successful learning."""
        validator = LearningValidator()

        # Create a test
        test = ValidationTest(
            test_id="test-123",
            topic="Docker basics",
            questions=[
                "What is a Docker image?",
                "What is a Docker container?",
            ],
            difficulty="beginner",
        )

        # Agent answers correctly
        answers = {
            "What is a Docker image?": "An immutable template for containers",
            "What is a Docker container?": "A running instance of an image",
        }

        result = validator.validate(
            agent_id="learner-agent",
            test=test,
            answers=answers,
            knowledge_before=0.3,
        )

        assert result.passed
        assert result.knowledge_after > result.knowledge_before
        assert result.improvement > 0

    def test_validate_learning_failure(self):
        """Test validating failed learning."""
        validator = LearningValidator()

        test = ValidationTest(
            test_id="test-123",
            topic="Advanced async patterns",
            questions=[
                "How do you handle backpressure?",
                "What is cooperative multitasking?",
            ],
            difficulty="advanced",
        )

        # Agent gives incorrect/incomplete answers
        answers = {
            "How do you handle backpressure?": "I don't know",
            "What is cooperative multitasking?": "Maybe something with tasks?",
        }

        result = validator.validate(
            agent_id="learner-agent",
            test=test,
            answers=answers,
            knowledge_before=0.2,
        )

        assert not result.passed
        assert result.knowledge_after <= result.knowledge_before + 0.1  # Minimal improvement

    def test_calculate_improvement(self):
        """Test calculating knowledge improvement."""
        validator = LearningValidator()

        improvement = validator.calculate_improvement(
            knowledge_before=0.3,
            knowledge_after=0.8,
        )

        assert improvement == 0.5

        # No improvement
        no_change = validator.calculate_improvement(
            knowledge_before=0.5,
            knowledge_after=0.5,
        )
        assert no_change == 0.0

    def test_recommend_follow_up(self):
        """Test recommending follow-up learning."""
        validator = LearningValidator()

        # Low improvement - needs follow-up
        result = ValidationResult(
            agent_id="learner",
            test_id="test-123",
            topic="Git workflows",
            passed=False,
            knowledge_before=0.2,
            knowledge_after=0.35,
            improvement=0.15,
        )

        assert validator.needs_follow_up(result)
        follow_up = validator.recommend_follow_up(result)
        assert "Git workflows" in follow_up["topics"]

        # High improvement - no follow-up needed
        result_good = ValidationResult(
            agent_id="learner",
            test_id="test-456",
            topic="pytest basics",
            passed=True,
            knowledge_before=0.3,
            knowledge_after=0.85,
            improvement=0.55,
        )

        assert not validator.needs_follow_up(result_good)


class TestValidationTest:
    """Tests for validation test."""

    def test_validation_test_creation(self):
        """Test creating a validation test."""
        test = ValidationTest(
            test_id="test-123",
            topic="Python decorators",
            questions=[
                "What is a decorator?",
                "How do you write a decorator?",
            ],
            difficulty="intermediate",
        )

        assert test.test_id == "test-123"
        assert test.topic == "Python decorators"
        assert len(test.questions) == 2
        assert test.difficulty == "intermediate"


class TestValidationResult:
    """Tests for validation result."""

    def test_validation_result_creation(self):
        """Test creating a validation result."""
        result = ValidationResult(
            agent_id="learner-agent",
            test_id="test-123",
            topic="Docker basics",
            passed=True,
            knowledge_before=0.2,
            knowledge_after=0.7,
            improvement=0.5,
            answers={
                "What is Docker?": "A containerization platform",
            },
        )

        assert result.agent_id == "learner-agent"
        assert result.test_id == "test-123"
        assert result.passed
        assert result.improvement == 0.5
        assert len(result.answers) == 1

    def test_result_serialization(self):
        """Test serializing validation result."""
        result = ValidationResult(
            agent_id="learner",
            test_id="test-123",
            topic="Testing",
            passed=True,
            knowledge_before=0.3,
            knowledge_after=0.8,
            improvement=0.5,
        )

        data = result.to_dict()
        assert data["agent_id"] == "learner"
        assert data["test_id"] == "test-123"
        assert data["passed"] is True
        assert data["improvement"] == 0.5


def test_integration_learning_cycle():
    """Test full learning and validation cycle."""
    validator = LearningValidator()

    # Step 1: Create a validation test
    test = validator.create_test(
        topic="Git rebase",
        questions=[
            "What is git rebase?",
            "When should you use rebase instead of merge?",
        ],
        difficulty="intermediate",
    )

    # Step 2: Agent takes test
    answers = {
        "What is git rebase?": "Reapplies commits on top of another base",
        "When should you use rebase instead of merge?": "For a linear history",
    }

    # Step 3: Validate learning
    result = validator.validate(
        agent_id="learner",
        test=test,
        answers=answers,
        knowledge_before=0.4,
    )

    # Step 4: Check if follow-up needed
    if validator.needs_follow_up(result):
        follow_up = validator.recommend_follow_up(result)
        assert "topics" in follow_up

    assert result.agent_id == "learner"
    assert result.topic == "Git rebase"

"""Tests for TaskParser - extracting goal, constraints, context from task descriptions."""


from src.core.task_parser import ParsedTask, TaskParser
from src.models.enums import TaskType


class TestTaskParserBasicParsing:
    """Test basic parsing functionality."""

    def test_parse_simple_software_task(self):
        """Test parsing a simple software development task."""
        parser = TaskParser()
        result = parser.parse(
            "Build a REST API for user authentication with JWT tokens. "
            "Must support login, logout, and token refresh endpoints."
        )

        assert isinstance(result, ParsedTask)
        assert "REST API" in result.goal
        assert "authentication" in result.goal.lower()
        assert result.task_type == TaskType.SOFTWARE
        assert len(result.success_criteria) > 0

    def test_parse_research_task(self):
        """Test parsing a research task."""
        parser = TaskParser()
        result = parser.parse(
            "Research the latest trends in transformer architectures for NLP. "
            "Focus on efficiency improvements and novel attention mechanisms. "
            "Summarize findings in a report."
        )

        assert result.task_type == TaskType.RESEARCH
        assert "transformer" in result.goal.lower() or "nlp" in result.goal.lower()

    def test_parse_analysis_task(self):
        """Test parsing an analysis task."""
        parser = TaskParser()
        result = parser.parse(
            "Analyze the performance bottlenecks in our database queries. "
            "Identify slow queries and propose optimization strategies."
        )

        assert result.task_type == TaskType.ANALYSIS
        assert "analyze" in result.goal.lower() or "performance" in result.goal.lower()

    def test_parse_creative_task(self):
        """Test parsing a creative task."""
        parser = TaskParser()
        result = parser.parse(
            "Design a logo for our new product that conveys innovation and trust. "
            "Should work well in both color and monochrome."
        )

        assert result.task_type == TaskType.CREATIVE
        assert "design" in result.goal.lower() or "logo" in result.goal.lower()


class TestConstraintExtraction:
    """Test extraction of constraints from task descriptions."""

    def test_extract_time_constraints(self):
        """Test extraction of time-based constraints."""
        parser = TaskParser()
        result = parser.parse(
            "Build a dashboard within 2 weeks. Must be completed by Friday."
        )

        assert "constraints" in result.__dict__ or len(result.constraints) > 0
        # Check if time constraints are captured
        constraint_str = str(result.constraints).lower()
        assert (
            "2 weeks" in constraint_str
            or "friday" in constraint_str
            or "time" in result.constraints
        )

    def test_extract_technology_constraints(self):
        """Test extraction of technology/tool constraints."""
        parser = TaskParser()
        result = parser.parse(
            "Build a web app using React and TypeScript. Must use PostgreSQL for the database."
        )

        constraint_str = str(result.constraints).lower()
        assert (
            "react" in constraint_str
            or "typescript" in constraint_str
            or "postgresql" in constraint_str
        )

    def test_extract_quality_constraints(self):
        """Test extraction of quality constraints."""
        parser = TaskParser()
        result = parser.parse(
            "Implement the feature with 90% test coverage. Code must pass all linting rules."
        )

        constraint_str = str(result.constraints).lower()
        assert (
            "coverage" in constraint_str
            or "test" in constraint_str
            or "quality" in result.constraints
        )


class TestContextExtraction:
    """Test extraction of context information."""

    def test_extract_background_context(self):
        """Test extraction of background/situational context."""
        parser = TaskParser()
        result = parser.parse(
            "Our current authentication system is insecure and outdated. "
            "We need to rebuild it using modern best practices. "
            "The system currently has 10,000 active users."
        )

        context_str = str(result.context).lower()
        assert len(result.context) > 0
        assert "insecure" in context_str or "outdated" in context_str or "users" in context_str

    def test_extract_stakeholder_context(self):
        """Test extraction of stakeholder information."""
        parser = TaskParser()
        result = parser.parse(
            "The marketing team needs this feature for the Q4 campaign. "
            "Build an email template system that they can use without developer help."
        )

        context_str = str(result.context).lower()
        assert "marketing" in context_str or "stakeholder" in result.context


class TestAmbiguityDetection:
    """Test detection of ambiguities and unclear requirements."""

    def test_detect_vague_requirements(self):
        """Test detection of vague/unclear requirements."""
        parser = TaskParser()
        result = parser.parse(
            "Make the system faster. Improve the user experience."
        )

        assert len(result.ambiguities) > 0
        # Should detect "faster" and "improve" as vague terms

    def test_detect_missing_details(self):
        """Test detection of missing critical details."""
        parser = TaskParser()
        result = parser.parse(
            "Build a database for storing customer data."
        )

        # Should detect missing: what kind of data? what scale? what access patterns?
        assert len(result.ambiguities) > 0

    def test_no_ambiguities_for_clear_task(self):
        """Test that clear, well-specified tasks have few/no ambiguities."""
        parser = TaskParser()
        result = parser.parse(
            "Implement a REST endpoint POST /api/users that accepts "
            "email and password fields, validates them, hashes the password with bcrypt, "
            "stores the user in PostgreSQL, and returns a 201 status with the user ID."
        )

        # A very specific task should have fewer ambiguities
        assert len(result.ambiguities) <= 2


class TestSuccessCriteriaExtraction:
    """Test extraction of success criteria."""

    def test_extract_explicit_criteria(self):
        """Test extraction of explicitly stated success criteria."""
        parser = TaskParser()
        result = parser.parse(
            "Build an API endpoint. Success criteria: "
            "1) Returns 200 status on success, "
            "2) Validates input properly, "
            "3) Has 100% test coverage."
        )

        assert len(result.success_criteria) >= 2
        criteria_str = " ".join(result.success_criteria).lower()
        assert "200" in criteria_str or "test coverage" in criteria_str

    def test_extract_implicit_criteria(self):
        """Test extraction of implied success criteria."""
        parser = TaskParser()
        result = parser.parse(
            "The endpoint must handle 1000 requests per second and respond within 100ms."
        )

        assert len(result.success_criteria) > 0
        criteria_str = " ".join(result.success_criteria).lower()
        assert "1000" in criteria_str or "100ms" in criteria_str or "performance" in criteria_str


class TestTaskTypeClassification:
    """Test task type classification logic."""

    def test_software_keywords(self):
        """Test classification based on software development keywords."""
        parser = TaskParser()

        software_tasks = [
            "Implement a function that calculates prime numbers",
            "Build a REST API",
            "Write unit tests for the authentication module",
            "Deploy the application to production",
        ]

        for task_desc in software_tasks:
            result = parser.parse(task_desc)
            assert result.task_type == TaskType.SOFTWARE, f"Failed for: {task_desc}"

    def test_research_keywords(self):
        """Test classification based on research keywords."""
        parser = TaskParser()

        research_tasks = [
            "Research the best practices for microservices",
            "Investigate performance optimization techniques",
            "Survey the literature on quantum computing",
        ]

        for task_desc in research_tasks:
            result = parser.parse(task_desc)
            assert result.task_type == TaskType.RESEARCH, f"Failed for: {task_desc}"

    def test_analysis_keywords(self):
        """Test classification based on analysis keywords."""
        parser = TaskParser()

        analysis_tasks = [
            "Analyze the security vulnerabilities in our codebase",
            "Evaluate different database solutions for our use case",
            "Compare the performance of various algorithms",
        ]

        for task_desc in analysis_tasks:
            result = parser.parse(task_desc)
            assert result.task_type == TaskType.ANALYSIS, f"Failed for: {task_desc}"

    def test_creative_keywords(self):
        """Test classification based on creative keywords."""
        parser = TaskParser()

        creative_tasks = [
            "Design a user interface for the dashboard",
            "Create a marketing campaign for the product launch",
            "Write documentation that is engaging and easy to follow",
        ]

        for task_desc in creative_tasks:
            result = parser.parse(task_desc)
            assert result.task_type == TaskType.CREATIVE, f"Failed for: {task_desc}"

    def test_hybrid_classification(self):
        """Test classification of hybrid tasks."""
        parser = TaskParser()

        result = parser.parse(
            "Research different UI frameworks, then design and implement "
            "a prototype dashboard using the best option."
        )

        # This task combines research, creative, and software - should be HYBRID
        assert result.task_type == TaskType.HYBRID


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_task_description(self):
        """Test handling of empty task description."""
        parser = TaskParser()

        result = parser.parse("")
        # Empty description should return a ParsedTask with ambiguities
        assert result.goal == ""
        assert len(result.ambiguities) > 0

    def test_very_short_task_description(self):
        """Test handling of very short task descriptions."""
        parser = TaskParser()

        result = parser.parse("Fix bug.")

        assert result.task_type is not None
        # Should flag as ambiguous
        assert len(result.ambiguities) > 0

    def test_very_long_task_description(self):
        """Test handling of very long task descriptions."""
        parser = TaskParser()

        long_desc = " ".join(["Build a feature."] * 100)
        result = parser.parse(long_desc)

        assert result is not None
        assert result.goal is not None


class TestClarificationRequests:
    """Test generation of clarification requests for ambiguous tasks."""

    def test_generate_clarifications_for_vague_task(self):
        """Test that clarification requests are generated for vague tasks."""
        parser = TaskParser()

        result = parser.parse("Make it better and faster.")

        assert len(result.ambiguities) > 0
        clarifications = result.generate_clarification_requests()
        assert len(clarifications) > 0
        assert any("what" in q.lower() or "how" in q.lower() for q in clarifications)

    def test_no_clarifications_for_clear_task(self):
        """Test that clear tasks generate few/no clarification requests."""
        parser = TaskParser()

        result = parser.parse(
            "Implement a Python function named 'is_prime' that takes an integer "
            "and returns True if it's prime, False otherwise. Include unit tests."
        )

        clarifications = result.generate_clarification_requests()
        assert len(clarifications) <= 1

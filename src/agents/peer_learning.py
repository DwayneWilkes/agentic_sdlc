"""
Peer Learning Protocol - Agent knowledge sharing and teaching.

Implements:
- Peer teaching sessions (expert to learner)
- War story sharing (narrative-based learning)
- Pair debugging (collaborative problem solving)
- Expertise tracking and expert discovery
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class KnowledgeTransferResult:
    """
    Result of a knowledge transfer session.

    Attributes:
        knowledge_transferred: Whether knowledge was successfully transferred
        new_knowledge_level: Learner's new knowledge level (0-1)
        key_learnings: List of key takeaways
        follow_up_needed: Whether follow-up session is needed
        follow_up_topics: Topics for follow-up (if needed)
    """

    knowledge_transferred: bool
    new_knowledge_level: float
    key_learnings: list[str] = field(default_factory=list)
    follow_up_needed: bool = False
    follow_up_topics: list[str] = field(default_factory=list)


@dataclass
class TeachingSession:
    """
    A peer teaching session where an expert teaches a learner.

    Attributes:
        session_id: Unique session identifier
        topic: Topic being taught
        learner: Agent ID of the learner
        teacher: Agent ID of the teacher (None if not assigned)
        current_knowledge: Learner's current knowledge level (0-1)
        desired_outcome: What the learner wants to achieve
        created_at: When session was created
        accepted_at: When teacher accepted the request
        completed_at: When session completed
        result: Knowledge transfer result
    """

    session_id: str
    topic: str
    learner: str
    teacher: str | None = None
    current_knowledge: float = 0.0
    desired_outcome: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    accepted_at: str | None = None
    completed_at: str | None = None
    result: KnowledgeTransferResult | None = None

    def complete(self, result: KnowledgeTransferResult) -> None:
        """
        Mark teaching session as complete.

        Args:
            result: The knowledge transfer result
        """
        self.result = result
        self.completed_at = datetime.now().isoformat()


@dataclass
class WarStory:
    """
    A war story - narrative-based learning from experience.

    Attributes:
        story_id: Unique story identifier
        teller: Agent who tells the story
        title: Story title
        context: Situation context
        what_happened: What actually happened
        lessons_learned: Key lessons from the experience
        tags: Topic tags
        listeners: Agents who heard this story
        created_at: When story was created
    """

    story_id: str
    teller: str
    title: str
    context: str
    what_happened: str
    lessons_learned: list[str]
    tags: list[str] = field(default_factory=list)
    listeners: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_listener(self, agent_id: str) -> None:
        """Add an agent who heard this story."""
        if agent_id not in self.listeners:
            self.listeners.append(agent_id)


@dataclass
class PairDebugSession:
    """
    A pair debugging session where two agents debug together.

    Attributes:
        session_id: Unique session identifier
        topic: What's being debugged
        pair_members: Agent IDs in the pair
        problem_description: Description of the problem
        initial_hypothesis: Initial guess at the problem
        solution: The solution (None if not solved)
        solved_by: Who found the solution
        how_solved: How they found it
        created_at: When session started
        solved_at: When problem was solved
    """

    session_id: str
    topic: str
    pair_members: list[str]
    problem_description: str
    initial_hypothesis: str | None = None
    solution: str | None = None
    solved_by: str | None = None
    how_solved: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    solved_at: str | None = None

    def solve(
        self,
        solution: str,
        who_found_it: str,
        how_they_found_it: str,
    ) -> None:
        """
        Record the solution to the problem.

        Args:
            solution: The solution
            who_found_it: Which agent found it
            how_they_found_it: How they discovered the solution
        """
        self.solution = solution
        self.solved_by = who_found_it
        self.how_solved = how_they_found_it
        self.solved_at = datetime.now().isoformat()


class PeerLearningProtocol:
    """
    Protocol for peer learning between agents.

    Manages:
    - Expertise tracking (who knows what)
    - Teaching session requests
    - War story sharing
    - Pair debugging coordination
    """

    def __init__(self, agent_id: str):
        """
        Initialize peer learning protocol.

        Args:
            agent_id: ID of the agent this protocol belongs to
        """
        self.agent_id = agent_id
        self.expertise_map: dict[str, dict[str, float]] = {}  # topic -> {agent: confidence}
        self.active_sessions: list[TeachingSession] = []
        self.war_stories: list[WarStory] = []

    def record_expertise(
        self,
        agent_id: str,
        topic: str,
        confidence: float,
    ) -> None:
        """
        Record an agent's expertise on a topic.

        Args:
            agent_id: Agent ID
            topic: Topic they're expert in
            confidence: Confidence level (0-1)
        """
        if topic not in self.expertise_map:
            self.expertise_map[topic] = {}
        self.expertise_map[topic][agent_id] = confidence

    def find_expert(self, topic: str) -> str | None:
        """
        Find the best expert on a topic.

        Args:
            topic: Topic to find expert for

        Returns:
            Agent ID of best expert, or None if no expert found
        """
        if topic not in self.expertise_map:
            return None

        experts = self.expertise_map[topic]
        if not experts:
            return None

        # Return agent with highest confidence
        return max(experts.items(), key=lambda x: x[1])[0]

    def request_teaching(
        self,
        topic: str,
        current_knowledge_level: float = 0.0,
        desired_outcome: str | None = None,
    ) -> TeachingSession:
        """
        Request a teaching session on a topic.

        Args:
            topic: Topic to learn
            current_knowledge_level: Current knowledge (0-1)
            desired_outcome: What learner wants to achieve

        Returns:
            TeachingSession (not yet accepted)
        """
        session_id = f"teach-{uuid.uuid4().hex[:8]}"

        session = TeachingSession(
            session_id=session_id,
            topic=topic,
            learner=self.agent_id,
            current_knowledge=current_knowledge_level,
            desired_outcome=desired_outcome,
        )

        self.active_sessions.append(session)
        return session

    def accept_teaching(self, session: TeachingSession) -> TeachingSession:
        """
        Accept a teaching request.

        Args:
            session: The teaching session to accept

        Returns:
            Updated session with teacher assigned
        """
        session.teacher = self.agent_id
        session.accepted_at = datetime.now().isoformat()
        return session

    def share_war_story(
        self,
        title: str,
        context: str,
        what_happened: str,
        lessons_learned: list[str],
        tags: list[str] | None = None,
    ) -> WarStory:
        """
        Share a war story.

        Args:
            title: Story title
            context: Situation context
            what_happened: What happened
            lessons_learned: Lessons from the experience
            tags: Topic tags

        Returns:
            WarStory instance
        """
        story_id = f"war-{uuid.uuid4().hex[:8]}"

        story = WarStory(
            story_id=story_id,
            teller=self.agent_id,
            title=title,
            context=context,
            what_happened=what_happened,
            lessons_learned=lessons_learned,
            tags=tags or [],
        )

        self.war_stories.append(story)
        return story

    def start_pair_debug(
        self,
        topic: str,
        partner_agent: str,
        problem_description: str,
        initial_hypothesis: str | None = None,
    ) -> PairDebugSession:
        """
        Start a pair debugging session.

        Args:
            topic: What's being debugged
            partner_agent: Agent ID of the partner
            problem_description: Description of the problem
            initial_hypothesis: Initial hypothesis

        Returns:
            PairDebugSession instance
        """
        session_id = f"debug-{uuid.uuid4().hex[:8]}"

        session = PairDebugSession(
            session_id=session_id,
            topic=topic,
            pair_members=[self.agent_id, partner_agent],
            problem_description=problem_description,
            initial_hypothesis=initial_hypothesis,
        )

        return session

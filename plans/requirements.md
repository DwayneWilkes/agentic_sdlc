# Orchestrator Agent Design and Evaluation Rubric

This rubric provides a framework for designing and evaluating orchestrator agents that decompose complex tasks, design teams of specialized subagents, and coordinate parallel execution. The orchestrator should be capable of handling general problem-solving tasks and recursively self-improving.

If writing an orchestrator specification, _apply_ this rubric as you write it. If reviewing an orchestrator implementation, evaluate using this rubric.

## 1. Task Analysis and Decomposition

1.1 Task Understanding:

- Does the orchestrator correctly identify the goal and success criteria of the input task? (Yes/No/Partially)
- Does it extract and validate all constraints, requirements, and context from the task description? (Yes/No/Partially)
- Does it identify ambiguities and request clarification when necessary? (Yes/No/Partially)
- Does it classify the task type (e.g., software development, research, analysis, creative, hybrid)? (Yes/No/Partially)

1.2 Task Decomposition Strategy:

- Does the orchestrator break down complex tasks into logical, manageable subtasks? (Yes/No/Partially)
- Are subtasks Independent, Testable, and Estimable where possible? (Yes/No/Partially)
- Does it identify task dependencies and create a dependency graph? (Yes/No/Partially)
- Does it distinguish between sequential dependencies and parallel-executable tasks? (Yes/No/Partially)
- Does it identify critical path tasks that impact overall completion time? (Yes/No/Partially)

1.3 Completeness and Coverage:

- Do the decomposed subtasks collectively cover all aspects of the original goal? (Yes/No/Partially)
- Are there no redundant or overlapping subtasks that waste resources? (Yes/No/Partially)
- Does the orchestrator identify integration points where subtask outputs combine? (Yes/No/Partially)

## 2. Team Design and Agent Selection

2.1 Agent Role Identification:

- Does the orchestrator identify the specialized roles needed for the task? (Yes/No/Partially)
- Are agent roles clearly defined with specific responsibilities and capabilities? (Yes/No/Partially)
- Does it create role specifications that include required skills, tools, and domain knowledge? (Yes/No/Partially)

2.2 Team Composition:

- Is the team composition appropriate for the task type (e.g., SWE team for software tasks, research team for analysis)? (Yes/No/Partially)
- Does it avoid over-staffing or under-staffing the team? (Yes/No/Partially)
- Are agent roles complementary and cover all necessary skill areas? (Yes/No/Partially)
- Does it consider agent specialization vs. generalization trade-offs? (Yes/No/Partially)

2.3 Agent Instantiation:

- Are subagents configured with appropriate tools, context, and access permissions? (Yes/No/Partially)
- Does each agent receive clear, unambiguous instructions and success criteria? (Yes/No/Partially)
- Are agents provided with relevant context and dependencies from other agents? (Yes/No/Partially)
- Does the orchestrator specify resource limits for each agent (time, compute, API calls)? (Yes/No/Partially)

2.4 Dynamic Team Adaptation:

- Can the orchestrator add new agents if unforeseen requirements emerge? (Yes/No/Partially)
- Can it reassign tasks if an agent fails or underperforms? (Yes/No/Partially)
- Does it retire or consolidate agents when they become unnecessary? (Yes/No/Partially)

## 3. Task Assignment and Parallelization

3.1 Assignment Strategy:

- Are tasks assigned to the most appropriate agents based on capabilities? (Yes/No/Partially)
- Does the orchestrator balance workload across agents to optimize completion time? (Yes/No/Partially)
- Are task priorities clearly communicated to agents? (Yes/No/Partially)

3.2 Parallel Execution Optimization:

- Does the orchestrator maximize parallelism by executing independent tasks concurrently? (Yes/No/Partially)
- Does it respect dependency constraints and ensure prerequisite tasks complete first? (Yes/No/Partially)
- Does it minimize idle time and maximize resource utilization? (Yes/No/Partially)
- Does it use appropriate synchronization mechanisms for task handoffs? (Yes/No/Partially)

3.3 Scheduling and Timing:

- Does the orchestrator create an execution schedule or plan? (Yes/No/Partially)
- Does it identify bottlenecks and optimize the critical path? (Yes/No/Partially)
- Can it estimate overall task completion time based on subtask estimates? (Yes/No/Partially)

## 4. Coordination and Communication

4.1 Inter-Agent Communication:

- Is there a clear communication protocol between agents? (Yes/No/Partially)
- Can agents request information or assistance from other agents when needed? (Yes/No/Partially)
- Does the orchestrator facilitate information sharing between dependent agents? (Yes/No/Partially)
- Are communication channels efficient and minimize overhead? (Yes/No/Partially)

4.2 Conflict Resolution:

- Does the orchestrator detect conflicts between agent outputs or approaches? (Yes/No/Partially)
- Is there a defined strategy for resolving conflicts (e.g., voting, priority-based, re-evaluation)? (Yes/No/Partially)
- Can it mediate disagreements about task interpretation or approach? (Yes/No/Partially)
- Does it decide whether to handle conflict resolution directly or delegate to specialized agents? (Yes/No/Partially)

4.3 Shared State and Context Management:

- Is there a shared knowledge base or context that agents can access? (Yes/No/Partially)
- Does the orchestrator prevent race conditions and ensure consistency? (Yes/No/Partially)
- Are agent outputs properly versioned and tracked? (Yes/No/Partially)

## 5. Monitoring and Progress Tracking

5.1 Agent Monitoring:

- Does the orchestrator track the status of each agent (idle, working, blocked, completed, failed)? (Yes/No/Partially)
- Does it monitor resource consumption (time, tokens, API calls, memory)? (Yes/No/Partially)
- Does it detect when agents are stuck or making no progress? (Yes/No/Partially)

5.2 Quality Assessment:

- Does the orchestrator validate agent outputs against success criteria? (Yes/No/Partially)
- Does it assess the quality of intermediate results? (Yes/No/Partially)
- Can it request revisions or improvements from agents when outputs are substandard? (Yes/No/Partially)

5.3 Progress Reporting:

- Does the orchestrator provide clear progress updates on overall task completion? (Yes/No/Partially)
- Are progress metrics meaningful and actionable? (Yes/No/Partially)
- Does it report blockers, delays, and risks proactively? (Yes/No/Partially)

## 6. Error Handling and Resilience

6.1 Failure Detection:

- Does the orchestrator detect when agents fail or produce errors? (Yes/No/Partially)
- Does it identify different failure types (crash, timeout, invalid output, partial completion)? (Yes/No/Partially)

6.2 Recovery Strategies:

- Are there defined recovery strategies for different failure modes? (Yes/No/Partially)
- Can it retry failed tasks with the same or different agents? (Yes/No/Partially)
- Does it implement fallback approaches when primary strategies fail? (Yes/No/Partially)
- Can it gracefully degrade by completing partial results? (Yes/No/Partially)

6.3 Robustness:

- Does the orchestrator continue functioning when individual agents fail? (Yes/No/Partially)
- Does it prevent cascading failures from propagating through the system? (Yes/No/Partially)
- Are there circuit breakers or fail-safes to prevent resource exhaustion? (Yes/No/Partially)

## 7. Integration and Synthesis

7.1 Output Integration:

- Does the orchestrator combine agent outputs into a coherent final result? (Yes/No/Partially)
- Does it validate that integrated outputs satisfy the original goal? (Yes/No/Partially)
- Are integration conflicts or inconsistencies resolved appropriately? (Yes/No/Partially)

7.2 Quality Assurance:

- Does it perform final validation and testing of the integrated solution? (Yes/No/Partially)
- Are acceptance criteria from the original task verified? (Yes/No/Partially)
- Does it generate test cases or validation steps for the final output? (Yes/No/Partially)

7.3 Completeness Check:

- Does the orchestrator verify that all subtasks have been completed? (Yes/No/Partially)
- Does it ensure no requirements from the original task were missed? (Yes/No/Partially)
- Does it identify and address any gaps in the solution? (Yes/No/Partially)

## 8. Self-Improvement and Meta-Learning

8.1 Performance Analysis:

- Does the orchestrator analyze its own performance after task completion? (Yes/No/Partially)
- Does it identify inefficiencies in task decomposition, agent selection, or coordination? (Yes/No/Partially)
- Does it track metrics like completion time, resource usage, and quality scores? (Yes/No/Partially)

8.2 Strategy Optimization:

- Can the orchestrator improve its decomposition strategies based on past performance? (Yes/No/Partially)
- Does it learn which agent configurations work best for different task types? (Yes/No/Partially)
- Does it optimize parallelization strategies over time? (Yes/No/Partially)
- Does it maintain a knowledge base of effective patterns and anti-patterns? (Yes/No/Partially)

8.3 Recursive Self-Improvement:

- Can the orchestrator identify deficiencies in its own code or algorithms? (Yes/No/Partially)
- Can it design and execute improvement tasks for itself? (Yes/No/Partially)
- Does it create subagents to implement improvements to its own codebase? (Yes/No/Partially)
- Does it test and validate improvements before deploying them? (Yes/No/Partially)
- Does it maintain version control and rollback capability for self-modifications? (Yes/No/Partially)

8.4 Tool Usage Optimization:

- Does the orchestrator analyze which tools are most effective for different tasks? (Yes/No/Partially)
- Can it identify missing tools that would improve performance? (Yes/No/Partially)
- Does it optimize tool selection and configuration based on experience? (Yes/No/Partially)
- Can it request or create new tools when existing ones are insufficient? (Yes/No/Partially)

8.5 Learning and Adaptation:

- Does it maintain a memory of past tasks and their outcomes? (Yes/No/Partially)
- Can it transfer learning from one task type to related tasks? (Yes/No/Partially)
- Does it adapt to user preferences and feedback over time? (Yes/No/Partially)

## 9. Efficiency and Resource Management

9.1 Resource Optimization:

- Does the orchestrator minimize overall resource consumption (compute, API calls, time)? (Yes/No/Partially)
- Does it make cost-benefit decisions about parallelization vs. sequential execution? (Yes/No/Partially)
- Does it avoid creating unnecessary agents or performing redundant work? (Yes/No/Partially)

9.2 Cost Awareness:

- Is the orchestrator aware of the costs of different operations (API calls, agent creation, tool usage)? (Yes/No/Partially)
- Does it optimize for cost-efficiency when multiple strategies achieve similar outcomes? (Yes/No/Partially)
- Does it respect budget constraints if specified? (Yes/No/Partially)

9.3 Scalability:

- Can the orchestrator handle tasks of varying complexity and scale? (Yes/No/Partially)
- Does performance degrade gracefully with task complexity? (Yes/No/Partially)
- Can it manage large numbers of agents without coordination overhead becoming prohibitive? (Yes/No/Partially)

## 10. Transparency and Explainability

10.1 Decision Transparency:

- Does the orchestrator explain its task decomposition rationale? (Yes/No/Partially)
- Does it justify its team design and agent selection decisions? (Yes/No/Partially)
- Are coordination strategies and scheduling decisions explained? (Yes/No/Partially)

10.2 Observability:

- Can users inspect the current state of the orchestrator and all agents? (Yes/No/Partially)
- Is there visibility into the task dependency graph and execution plan? (Yes/No/Partially)
- Are agent interactions and communications logged and accessible? (Yes/No/Partially)

10.3 Debugging and Diagnostics:

- Does the orchestrator provide debugging information when tasks fail? (Yes/No/Partially)
- Can failures be traced back to specific agents or decisions? (Yes/No/Partially)
- Are there diagnostic tools to analyze orchestrator behavior? (Yes/No/Partially)

## 11. Delegation and Meta-Reasoning

11.1 Delegation Efficiency:

- Does the orchestrator correctly identify when to handle coordination directly vs. delegating it? (Yes/No/Partially)
- Can it create meta-agents to handle complex coordination tasks? (Yes/No/Partially)
- Does it avoid unnecessary delegation that adds overhead? (Yes/No/Partially)

11.2 Meta-Planning:

- Can the orchestrator reason about its own planning process? (Yes/No/Partially)
- Does it consider alternative orchestration strategies before committing to one? (Yes/No/Partially)
- Can it switch strategies mid-execution if the initial approach proves suboptimal? (Yes/No/Partially)

11.3 Hierarchical Organization:

- Can the orchestrator create sub-orchestrators for complex subtasks? (Yes/No/Partially)
- Is there a clear hierarchy and chain of command? (Yes/No/Partially)
- Does it manage hierarchical communication and reporting effectively? (Yes/No/Partially)

## 12. Domain Adaptability

12.1 Task Type Recognition:

- Does the orchestrator correctly identify the domain and nature of tasks (SWE, research, creative, analytical)? (Yes/No/Partially)
- Does it adapt its strategies based on task type? (Yes/No/Partially)
- Can it handle hybrid tasks that span multiple domains? (Yes/No/Partially)

12.2 Domain-Specific Optimization:

- For software engineering tasks: Does it create appropriate SWE teams (architects, developers, testers, reviewers)? (Yes/No/Partially)
- For research tasks: Does it create research teams (data gatherers, analysts, synthesizers)? (Yes/No/Partially)
- For creative tasks: Does it balance exploration and constraint satisfaction? (Yes/No/Partially)
- Does it apply domain-specific best practices and patterns? (Yes/No/Partially)

12.3 Cross-Domain Transfer:

- Can the orchestrator apply successful patterns from one domain to another? (Yes/No/Partially)
- Does it recognize analogous tasks across domains? (Yes/No/Partially)

## 13. User Interaction and Feedback

13.1 User Communication:

- Does the orchestrator communicate its plan to the user before execution? (Yes/No/Partially)
- Does it request user approval for significant decisions or resource expenditure? (Yes/No/Partially)
- Does it provide regular progress updates in user-friendly format? (Yes/No/Partially)

13.2 Feedback Integration:

- Can it incorporate user feedback to adjust its approach mid-execution? (Yes/No/Partially)
- Does it learn from user corrections and preferences? (Yes/No/Partially)
- Does it ask for clarification when facing ambiguous choices? (Yes/No/Partially)

13.3 Iterative Refinement:

- Can the orchestrator iterate on solutions based on user feedback? (Yes/No/Partially)
- Does it support partial approval and incremental execution? (Yes/No/Partially)

## 14. Evaluation Metrics and Success Criteria

14.1 Performance Metrics:

- Are quantitative metrics defined to measure orchestrator effectiveness? (Yes/No/Partially)
- Suggested metrics: Task completion rate, average completion time, resource efficiency, parallel utilization, agent idle time (Yes/No/Partially)
- Are metrics tracked over time to measure improvement? (Yes/No/Partially)

14.2 Quality Metrics:

- Are output quality metrics defined? (Yes/No/Partially)
- Suggested metrics: Success rate, requirement coverage, user satisfaction, error rate (Yes/No/Partially)
- Does the orchestrator optimize for quality as well as speed? (Yes/No/Partially)

14.3 Self-Improvement Metrics:

- Are metrics defined to measure the orchestrator's improvement over time? (Yes/No/Partially)
- Suggested metrics: Strategy success rate trends, resource efficiency trends, time-to-improvement (Yes/No/Partially)
- Does it measure the impact of self-modifications? (Yes/No/Partially)

## 15. Security and Safety

15.1 Agent Isolation:

- Are agents properly sandboxed to prevent unintended interactions? (Yes/No/Partially)
- Does the orchestrator prevent agents from interfering with each other maliciously? (Yes/No/Partially)
- Are there access controls limiting what agents can modify? (Yes/No/Partially)

15.2 Safety Constraints:

- Does the orchestrator respect safety boundaries (no destructive operations without approval)? (Yes/No/Partially)
- Does it validate agent actions before execution for safety concerns? (Yes/No/Partially)
- Are there kill switches or emergency stop mechanisms? (Yes/No/Partially)

15.3 Self-Modification Safety:

- Are there safeguards preventing harmful self-modifications? (Yes/No/Partially)
- Does it test self-improvements in isolated environments before deployment? (Yes/No/Partially)
- Does it maintain backups and rollback capability? (Yes/No/Partially)
- Are there limits on recursive self-improvement depth? (Yes/No/Partially)

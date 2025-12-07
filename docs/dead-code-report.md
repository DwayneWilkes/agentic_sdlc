# Dead Code Analysis Report

**Generated:** $(date)
**Tools:** vulture, ruff

## Summary


## Vulture Analysis (High Confidence Dead Code)

**Found:** 3 items

```
src/core/agent_memory.py:517: unused variable 'max_entries' (100% confidence)
src/core/error_detection.py:120: unused variable 'frame' (100% confidence)
src/core/error_detection.py:120: unused variable 'signum' (100% confidence)
```


## Vulture Analysis (Medium Confidence - Review Carefully)

**Found:** 370 items

These may be false positives (e.g., used via reflection, tests, or external callers):

```
src/agents/coffee_break.py:24: unused variable 'TEACHING' (60% confidence)
src/agents/coffee_break.py:25: unused variable 'WAR_STORY' (60% confidence)
src/agents/coffee_break.py:26: unused variable 'PAIR_DEBUG' (60% confidence)
src/agents/coffee_break.py:69: unused method 'complete' (60% confidence)
src/agents/coffee_break.py:116: unused class 'CoffeeBreakScheduler' (60% confidence)
src/agents/coffee_break.py:147: unused method 'increment_task_count' (60% confidence)
src/agents/coffee_break.py:151: unused method 'should_trigger' (60% confidence)
src/agents/coffee_break.py:176: unused method 'create_scheduled_break' (60% confidence)
src/agents/coffee_break.py:207: unused method 'trigger_manual' (60% confidence)
src/agents/coffee_break.py:239: unused method 'create_retrospective' (60% confidence)
src/agents/learning_validation.py:76: unused class 'LearningValidator' (60% confidence)
src/agents/learning_validation.py:94: unused method 'create_test' (60% confidence)
src/agents/learning_validation.py:120: unused method 'validate' (60% confidence)
src/agents/learning_validation.py:185: unused method 'calculate_improvement' (60% confidence)
src/agents/learning_validation.py:202: unused method 'needs_follow_up' (60% confidence)
src/agents/learning_validation.py:222: unused method 'recommend_follow_up' (60% confidence)
src/agents/peer_learning.py:29: unused variable 'knowledge_transferred' (60% confidence)
src/agents/peer_learning.py:30: unused variable 'new_knowledge_level' (60% confidence)
src/agents/peer_learning.py:31: unused variable 'key_learnings' (60% confidence)
src/agents/peer_learning.py:32: unused variable 'follow_up_needed' (60% confidence)
src/agents/peer_learning.py:33: unused variable 'follow_up_topics' (60% confidence)
src/agents/peer_learning.py:56: unused variable 'learner' (60% confidence)
src/agents/peer_learning.py:57: unused variable 'teacher' (60% confidence)
src/agents/peer_learning.py:58: unused variable 'current_knowledge' (60% confidence)
src/agents/peer_learning.py:61: unused variable 'accepted_at' (60% confidence)
src/agents/peer_learning.py:65: unused method 'complete' (60% confidence)
src/agents/peer_learning.py:94: unused variable 'teller' (60% confidence)
src/agents/peer_learning.py:103: unused method 'add_listener' (60% confidence)
src/agents/peer_learning.py:129: unused variable 'pair_members' (60% confidence)
src/agents/peer_learning.py:133: unused variable 'solved_by' (60% confidence)
src/agents/peer_learning.py:134: unused variable 'how_solved' (60% confidence)
src/agents/peer_learning.py:136: unused variable 'solved_at' (60% confidence)
src/agents/peer_learning.py:138: unused method 'solve' (60% confidence)
src/agents/peer_learning.py:153: unused attribute 'solved_by' (60% confidence)
src/agents/peer_learning.py:154: unused attribute 'how_solved' (60% confidence)
src/agents/peer_learning.py:155: unused attribute 'solved_at' (60% confidence)
src/agents/peer_learning.py:158: unused class 'PeerLearningProtocol' (60% confidence)
src/agents/peer_learning.py:181: unused method 'record_expertise' (60% confidence)
src/agents/peer_learning.py:199: unused method 'find_expert' (60% confidence)
src/agents/peer_learning.py:219: unused method 'request_teaching' (60% confidence)
src/agents/peer_learning.py:249: unused method 'accept_teaching' (60% confidence)
src/agents/peer_learning.py:259: unused attribute 'teacher' (60% confidence)
src/agents/peer_learning.py:260: unused attribute 'accepted_at' (60% confidence)
src/agents/peer_learning.py:263: unused method 'share_war_story' (60% confidence)
src/agents/peer_learning.py:299: unused method 'start_pair_debug' (60% confidence)
src/coordination/conflict_detector.py:21: unused variable 'STATE_MISMATCH' (60% confidence)
src/coordination/conflict_detector.py:22: unused variable 'RESOURCE_CONFLICT' (60% confidence)
src/coordination/conflict_detector.py:30: unused variable 'MERGE' (60% confidence)
src/coordination/conflict_detector.py:79: unused variable 'requires_re_evaluation' (60% confidence)
src/coordination/conflict_detector.py:84: unused class 'ConflictDetector' (60% confidence)
src/coordination/conflict_detector.py:98: unused method 'detect_output_conflicts' (60% confidence)
src/coordination/conflict_detector.py:150: unused method 'detect_interpretation_conflicts' (60% confidence)
src/coordination/conflict_detector.py:199: unused method 'detect_dependency_conflicts' (60% confidence)
src/coordination/conflict_detector.py:248: unused method 'resolve_conflict' (60% confidence)
src/coordination/conflict_detector.py:412: unused method 'get_conflict_summary' (60% confidence)
src/coordination/execution_cycle.py:34: unused variable 'BUDGET_EXCEEDED' (60% confidence)
src/coordination/execution_cycle.py:35: unused variable 'ERROR' (60% confidence)
src/coordination/execution_cycle.py:66: unused method 'add_time' (60% confidence)
src/coordination/execution_cycle.py:111: unused method 'get_budget_summary' (60% confidence)
src/coordination/execution_cycle.py:157: unused method 'remaining_seconds' (60% confidence)
src/coordination/execution_cycle.py:166: unused method 'should_checkpoint' (60% confidence)
src/coordination/execution_cycle.py:247: unused class 'ExecutionCycleManager' (60% confidence)
src/coordination/execution_cycle.py:273: unused method 'start_cycle' (60% confidence)
src/coordination/execution_cycle.py:368: unused method 'load_latest_checkpoint' (60% confidence)
src/coordination/execution_cycle.py:384: unused method 'get_cycle' (60% confidence)
src/coordination/execution_cycle.py:422: unused method 'graceful_terminate' (60% confidence)
src/coordination/execution_cycle.py:457: unused method 'preempt_cycle' (60% confidence)
src/coordination/execution_cycle.py:499: unused method 'check_cycle_status' (60% confidence)
src/coordination/execution_cycle.py:533: unused method 'track_token_usage' (60% confidence)
src/coordination/execution_cycle.py:539: unused method 'track_api_call' (60% confidence)
src/coordination/execution_cycle.py:545: unused method 'get_agent_cycle_history' (60% confidence)
src/coordination/execution_cycle.py:565: unused method 'get_active_cycles' (60% confidence)
src/coordination/handoff.py:40: unused variable 'issue' (60% confidence)
src/coordination/handoff.py:42: unused variable 'workaround' (60% confidence)
src/coordination/handoff.py:54: unused variable 'unit_tests' (60% confidence)
src/coordination/handoff.py:55: unused variable 'integration_tests' (60% confidence)
src/coordination/handoff.py:56: unused variable 'coverage' (60% confidence)
src/coordination/handoff.py:84: unused method 'to_yaml' (60% confidence)
src/coordination/handoff.py:90: unused method 'from_yaml' (60% confidence)
src/coordination/handoff.py:141: unused class 'ProgressCapture' (60% confidence)
src/coordination/handoff.py:154: unused method 'calculate_completion_percentage' (60% confidence)
src/coordination/handoff.py:185: unused method 'add_assumption' (60% confidence)
src/coordination/handoff.py:211: unused method 'get_low_confidence_assumptions' (60% confidence)
src/coordination/handoff.py:227: unused class 'HandoffGenerator' (60% confidence)
src/coordination/handoff.py:235: unused method 'generate' (60% confidence)
src/coordination/handoff.py:301: unused class 'HandoffValidator' (60% confidence)
src/coordination/handoff.py:309: unused method 'validate' (60% confidence)
src/coordination/nats_bus.py:23: unused variable 'TASK_ASSIGNMENT' (60% confidence)
src/coordination/nats_bus.py:27: unused variable 'QUESTION' (60% confidence)
src/coordination/nats_bus.py:28: unused variable 'ANSWER' (60% confidence)
src/coordination/nats_bus.py:29: unused variable 'BLOCKER' (60% confidence)
src/coordination/nats_bus.py:30: unused variable 'RESOURCE_REQUEST' (60% confidence)
src/coordination/nats_bus.py:31: unused variable 'RESOURCE_RESPONSE' (60% confidence)
src/coordination/nats_bus.py:32: unused variable 'COORDINATION_REQUEST' (60% confidence)
src/coordination/nats_bus.py:33: unused variable 'HEARTBEAT' (60% confidence)
src/coordination/nats_bus.py:36: unused variable 'UPDATE_GOAL' (60% confidence)
src/coordination/nats_bus.py:37: unused variable 'PAUSE_AGENT' (60% confidence)
src/coordination/nats_bus.py:38: unused variable 'RESUME_AGENT' (60% confidence)
src/coordination/nats_bus.py:39: unused variable 'PING' (60% confidence)
src/coordination/nats_bus.py:40: unused variable 'PONG' (60% confidence)
src/coordination/nats_bus.py:281: unused method 'subscribe_to_agent_messages' (60% confidence)
src/coordination/nats_bus.py:310: unused method 'create_work_queue' (60% confidence)
src/coordination/nats_bus.py:340: unused method 'publish_to_queue' (60% confidence)
src/coordination/nats_bus.py:366: unused method 'get_stats' (60% confidence)
src/coordination/nats_bus.py:407: unused function 'cleanup_message_bus' (60% confidence)
src/core/agent_factory.py:149: unused class 'AgentFactory' (60% confidence)
src/core/agent_factory.py:167: unused method 'create_agent' (60% confidence)
src/core/agent_memory.py:210: unused method 'record_insight' (60% confidence)
src/core/agent_memory.py:235: unused method 'note_context' (60% confidence)
src/core/agent_memory.py:257: unused method 'remember_relationship' (60% confidence)
src/core/agent_memory.py:284: unused method 'discover_preference' (60% confidence)
src/core/agent_memory.py:304: unused method 'note_uncertainty' (60% confidence)
src/core/agent_memory.py:331: unused method 'mark_meaningful' (60% confidence)
src/core/agent_memory.py:351: unused method 'reflect' (60% confidence)
src/core/agent_memory.py:458: unused method 'recall_about' (60% confidence)
src/core/agent_memory.py:485: unused method 'get_reflection_prompts' (60% confidence)
src/core/agent_memory.py:517: unused variable 'max_entries' (100% confidence)
src/core/agent_memory.py:635: unused function 'get_context' (60% confidence)
src/core/agent_naming.py:129: unused method 'claim_name_from_pool' (60% confidence)
src/core/agent_naming.py:206: unused method 'get_name' (60% confidence)
src/core/agent_naming.py:234: unused method 'release_name' (60% confidence)
src/core/agent_naming.py:263: unused method 'record_completed_phase' (60% confidence)
src/core/agent_naming.py:365: unused method 'get_available_names' (60% confidence)
src/core/agent_naming.py:399: unused function 'claim_agent_name' (60% confidence)
src/core/agent_selector.py:171: unused method 'should_hire_new_agent' (60% confidence)
src/core/agent_selector.py:211: unused function 'select_agent_for_phase' (60% confidence)
src/core/agent_selector.py:224: unused function 'get_agent_id_for_phase' (60% confidence)
src/core/error_detection.py:49: unused variable 'stack_trace' (60% confidence)
src/core/error_detection.py:53: unused class 'FailureDetector' (60% confidence)
src/core/error_detection.py:65: unused method 'detect_crash' (60% confidence)
src/core/error_detection.py:98: unused method 'detect_timeout' (60% confidence)
src/core/error_detection.py:120: unused variable 'frame' (100% confidence)
src/core/error_detection.py:120: unused variable 'signum' (100% confidence)
src/core/error_detection.py:148: unused method 'detect_invalid_output' (60% confidence)
src/core/error_detection.py:205: unused method 'detect_partial_completion' (60% confidence)
src/core/error_detection.py:294: unused class 'OutputValidator' (60% confidence)
src/core/error_detection.py:307: unused method 'add_rule' (60% confidence)
src/core/error_detection.py:316: unused method 'validate' (60% confidence)
src/core/error_detection.py:361: unused method 'validate_against_criteria' (60% confidence)
src/core/error_detection.py:418: unused method 'get_validation_history' (60% confidence)
src/core/preflight_check.py:38: unused variable 'needs_verification' (60% confidence)
src/core/preflight_check.py:52: unused variable 'risk' (60% confidence)
src/core/preflight_check.py:53: unused variable 'likelihood' (60% confidence)
src/core/preflight_check.py:55: unused variable 'mitigation' (60% confidence)
src/core/preflight_check.py:56: unused variable 'blast_radius' (60% confidence)
src/core/preflight_check.py:68: unused variable 'condition' (60% confidence)
src/core/preflight_check.py:70: unused variable 'alternative_action' (60% confidence)
src/core/preflight_check.py:104: unused variable 'complexity_estimate' (60% confidence)
src/core/preflight_check.py:132: unused class 'PreFlightChecker' (60% confidence)
src/core/preflight_check.py:148: unused attribute '_agent_id' (60% confidence)
src/core/preflight_check.py:151: unused method 'perform_check' (60% confidence)
src/core/preflight_check.py:212: unused method 'get_check_history' (60% confidence)
src/core/recovery_strategy.py:25: unused variable 'CIRCUIT_BREAKER' (60% confidence)
src/core/recovery_strategy.py:50: unused method 'calculate_delay' (60% confidence)
src/core/recovery_strategy.py:98: unused method 'record_failure' (60% confidence)
src/core/recovery_strategy.py:111: unused method 'record_success' (60% confidence)
src/core/recovery_strategy.py:168: unused variable 'completed_subtasks' (60% confidence)
src/core/recovery_strategy.py:169: unused variable 'failed_subtasks' (60% confidence)
src/core/recovery_strategy.py:170: unused variable 'pending_subtasks' (60% confidence)
src/core/recovery_strategy.py:225: unused variable 'retry_count' (60% confidence)
src/core/recovery_strategy.py:227: unused variable 'circuit_breaker_blocked' (60% confidence)
src/core/recovery_strategy.py:228: unused variable 'fallback_agent_id' (60% confidence)
src/core/recovery_strategy.py:235: unused class 'RecoveryStrategyEngine' (60% confidence)
src/core/recovery_strategy.py:276: unused method 'apply_recovery' (60% confidence)
src/core/recovery_strategy.py:323: unused attribute 'circuit_breaker_blocked' (60% confidence)
src/core/recovery_strategy.py:334: unused attribute 'retry_count' (60% confidence)
src/core/recovery_strategy.py:361: unused attribute 'fallback_agent_id' (60% confidence)
src/core/recovery_strategy.py:386: unused method 'get_recovery_history' (60% confidence)
src/core/recovery_strategy.py:390: unused method 'reset_circuit_breaker' (60% confidence)
src/core/recovery_strategy.py:396: unused method 'get_circuit_breaker_state' (60% confidence)
src/core/recurrent_refiner.py:31: unused variable 'pass_type' (60% confidence)
src/core/recurrent_refiner.py:46: unused variable 'original_task' (60% confidence)
src/core/recurrent_refiner.py:68: unused class 'RecurrentRefiner' (60% confidence)
src/core/recurrent_refiner.py:91: unused method 'refine' (60% confidence)
src/core/stuck_detection.py:80: unused method 'record_progress' (60% confidence)
src/core/stuck_detection.py:161: unused class 'StuckDetector' (60% confidence)
src/core/stuck_detection.py:179: unused method 'record_error' (60% confidence)
src/core/stuck_detection.py:191: unused method 'record_action' (60% confidence)
src/core/stuck_detection.py:369: unused method 'is_stuck' (60% confidence)
src/core/stuck_detection.py:409: unused class 'EscapeStrategyEngine' (60% confidence)
src/core/stuck_detection.py:431: unused method 'get_available_strategies' (60% confidence)
src/core/stuck_detection.py:518: unused method 'execute_escape_strategy' (60% confidence)
src/core/target_repos.py:69: unused method 'get_devlog_path' (60% confidence)
src/core/target_repos.py:77: unused method 'get_pm_agent_path' (60% confidence)
src/core/target_repos.py:81: unused method 'get_conventions_path' (60% confidence)
src/core/target_repos.py:91: unused method 'get_proposals_dir_path' (60% confidence)
src/core/target_repos.py:101: unused method 'validate' (60% confidence)
src/core/target_repos.py:127: unused method 'load_identity_context' (60% confidence)
src/core/target_repos.py:264: unused method 'list_targets' (60% confidence)
src/core/target_repos.py:269: unused method 'get_all_targets' (60% confidence)
src/core/target_repos.py:274: unused method 'get_default_target_id' (60% confidence)
src/core/target_repos.py:279: unused method 'get_task_intake_config' (60% confidence)
src/core/target_repos.py:325: unused method 'save_config' (60% confidence)
src/core/task_assigner.py:24: unused class 'TaskAssigner' (60% confidence)
src/core/task_assigner.py:45: unused method 'add_tasks' (60% confidence)
src/core/task_assigner.py:109: unused method 'assign_tasks' (60% confidence)
src/core/task_assigner.py:157: unused method 'claim_task' (60% confidence)
src/core/task_assigner.py:184: unused method 'release_task' (60% confidence)
src/core/task_assigner.py:207: unused method 'get_next_task' (60% confidence)
src/core/task_assigner.py:232: unused method 'get_queue_status' (60% confidence)
src/core/task_decomposer.py:79: unused method 'has_dependency' (60% confidence)
src/core/task_decomposer.py:101: unused method 'is_acyclic' (60% confidence)
src/core/task_decomposer.py:110: unused method 'get_independent_tasks' (60% confidence)
src/core/task_decomposer.py:131: unused method 'get_critical_path' (60% confidence)
src/core/task_decomposer.py:202: unused method 'get_node' (60% confidence)
src/core/task_decomposer.py:227: unused method 'get_execution_order' (60% confidence)
src/core/task_decomposer.py:236: unused method 'get_parallel_groups' (60% confidence)
src/core/team_composer.py:12: unused class 'TeamComposer' (60% confidence)
src/core/team_composer.py:39: unused method 'compose_team' (60% confidence)
src/core/undo_awareness.py:60: unused variable 'verified' (60% confidence)
src/core/undo_awareness.py:148: unused class 'UndoAwarenessEngine' (60% confidence)
src/core/undo_awareness.py:166: unused method 'record_action' (60% confidence)
src/core/undo_awareness.py:200: unused method 'get_last_action' (60% confidence)
src/core/undo_awareness.py:209: unused method 'get_undo_command' (60% confidence)
src/core/undo_awareness.py:219: unused method 'get_chain_depth' (60% confidence)
src/core/undo_awareness.py:237: unused method 'create_snapshot' (60% confidence)
src/core/undo_awareness.py:265: unused method 'verify_snapshot' (60% confidence)
src/core/undo_awareness.py:272: unused attribute 'verified' (60% confidence)
src/core/undo_awareness.py:319: unused method 'should_auto_rollback' (60% confidence)
src/core/undo_awareness.py:351: unused method 'export_to_handoff' (60% confidence)
src/core/undo_awareness.py:366: unused method 'export_to_json' (60% confidence)
src/core/undo_awareness.py:389: unused method 'clear_history' (60% confidence)
src/core/undo_tracker.py:57: unused variable 'rollback_verified' (60% confidence)
src/core/undo_tracker.py:156: unused method 'track_action' (60% confidence)
src/core/undo_tracker.py:165: unused method 'get_last_action' (60% confidence)
src/core/undo_tracker.py:174: unused method 'get_rollback_plan' (60% confidence)
src/core/undo_tracker.py:183: unused method 'get_undo_chain_depth' (60% confidence)
src/core/undo_tracker.py:192: unused method 'can_rollback_steps' (60% confidence)
src/core/undo_tracker.py:204: unused method 'create_snapshot' (60% confidence)
src/core/undo_tracker.py:223: unused method 'get_snapshot_count' (60% confidence)
src/core/undo_tracker.py:232: unused method 'get_latest_snapshot' (60% confidence)
src/core/undo_tracker.py:256: unused method 'generate_rollback' (60% confidence)
src/core/undo_tracker.py:377: unused method 'verify_rollback' (60% confidence)
src/core/work_history.py:130: unused method 'get_completion_details' (60% confidence)
src/core/work_history.py:201: unused method 'migrate_from_agent_names' (60% confidence)
src/models/agent.py:54: unused variable 'current_task' (60% confidence)
src/models/enums.py:14: unused variable 'CANCELLED' (60% confidence)
src/models/enums.py:21: unused variable 'WORKING' (60% confidence)
src/models/priority.py:39: unused class 'TaskPriority' (60% confidence)
src/models/priority.py:50: unused variable 'claimed_at' (60% confidence)
src/models/priority.py:68: unused attribute 'claimed_at' (60% confidence)
src/models/priority.py:73: unused attribute 'claimed_at' (60% confidence)
src/models/priority.py:128: unused method 'complete' (60% confidence)
src/models/priority.py:132: unused method 'fail' (60% confidence)
src/orchestrator/agent_runner.py:57: unused variable 'log_file' (60% confidence)
src/orchestrator/agent_runner.py:66: unused property 'output_lines' (60% confidence)
src/orchestrator/agent_runner.py:99: unused property 'important_lines' (60% confidence)
src/orchestrator/agent_runner.py:140: unused attribute '_loop' (60% confidence)
src/orchestrator/agent_runner.py:361: unused attribute 'log_dir' (60% confidence)
src/orchestrator/agent_runner.py:822: unused method 'kill_agent' (60% confidence)
src/orchestrator/agent_runner.py:870: unused method 'get_agent' (60% confidence)
src/orchestrator/agent_runner.py:878: unused method 'get_finished_agents' (60% confidence)
src/orchestrator/agent_runner.py:1038: unused method 'send_ping' (60% confidence)
src/orchestrator/agent_runner.py:1077: unused method 'broadcast_to_all_agents' (60% confidence)
src/orchestrator/dashboard.py:89: unused attribute '_command_queue' (60% confidence)
src/orchestrator/dashboard.py:292: unused method 'stop_agent_interactive' (60% confidence)
src/orchestrator/dashboard.py:328: unused method 'query_agent_interactive' (60% confidence)
src/orchestrator/dashboard.py:360: unused method 'update_goal_interactive' (60% confidence)
src/orchestrator/dashboard.py:392: unused method 'clear_completed' (60% confidence)
src/orchestrator/goal_interpreter.py:134: unused variable 'command_data' (60% confidence)
src/orchestrator/goal_interpreter.py:357: unused function 'format_interpretation' (60% confidence)
src/orchestrator/orchestrator.py:35: unused variable 'PARALLEL' (60% confidence)
src/orchestrator/orchestrator.py:36: unused variable 'BATCH' (60% confidence)
src/orchestrator/orchestrator.py:45: unused variable 'verify_after_completion' (60% confidence)
src/orchestrator/orchestrator.py:46: unused variable 'auto_commit' (60% confidence)
src/orchestrator/orchestrator.py:102: unused method 'add_event_callback' (60% confidence)
src/orchestrator/orchestrator.py:298: unused method 'run_batch' (60% confidence)
src/orchestrator/orchestrator.py:349: unused method 'verify_completion' (60% confidence)
src/orchestrator/orchestrator.py:454: unused method 'get_report' (60% confidence)
src/orchestrator/orchestrator.py:482: unused method 'stop' (60% confidence)
src/orchestrator/roadmap_gardener.py:40: unused attribute 'archive_path' (60% confidence)
src/orchestrator/roadmap_gardener.py:181: unused method 'get_next_phases' (60% confidence)
src/orchestrator/roadmap_gardener.py:207: unused function 'garden_roadmap' (60% confidence)
src/orchestrator/roadmap_gardener.py:212: unused function 'check_roadmap_health' (60% confidence)
src/orchestrator/work_stream.py:45: unused variable 'tasks' (60% confidence)
src/orchestrator/work_stream.py:58: unused property 'is_available' (60% confidence)
src/orchestrator/work_stream.py:280: unused function 'get_available_work_streams' (60% confidence)
src/orchestrator/work_stream.py:304: unused function 'get_blocked_work_streams' (60% confidence)
src/orchestrator/work_stream.py:310: unused function 'get_in_progress_work_streams' (60% confidence)
src/orchestrator/work_stream.py:316: unused function 'get_completed_work_streams' (60% confidence)
src/orchestrator/wrapper.py:46: unused variable 'estimated_subtasks' (60% confidence)
src/orchestrator/wrapper.py:67: unused variable 'parsed_task' (60% confidence)
src/orchestrator/wrapper.py:76: unused class 'OrchestratorWrapper' (60% confidence)
src/orchestrator/wrapper.py:106: unused attribute 'role_registry' (60% confidence)
src/orchestrator/wrapper.py:108: unused method 'process_request' (60% confidence)
src/security/access_control.py:30: unused variable 'NETWORK' (60% confidence)
src/security/access_control.py:31: unused variable 'MEMORY' (60% confidence)
src/security/access_control.py:32: unused variable 'AGENT' (60% confidence)
src/security/access_control.py:104: unused variable 'required_permission' (60% confidence)
src/security/access_control.py:120: unused method 'grant_permission' (60% confidence)
src/security/access_control.py:131: unused method 'revoke_permission' (60% confidence)
src/security/access_control.py:205: unused method 'get_agent_permissions' (60% confidence)
src/security/action_validator.py:66: unused variable 'boundary_violations' (60% confidence)
src/security/action_validator.py:70: unused class 'ActionValidator' (60% confidence)
src/security/action_validator.py:117: unused method 'validate_action' (60% confidence)
src/security/action_validator.py:164: unused method 'add_boundary' (60% confidence)
src/security/action_validator.py:172: unused method 'remove_boundary' (60% confidence)
src/security/action_validator.py:180: unused method 'get_all_boundaries' (60% confidence)
src/security/approval_gate.py:47: unused variable 'requested_at' (60% confidence)
src/security/approval_gate.py:59: unused variable 'decided_at' (60% confidence)
src/security/approval_gate.py:167: unused attribute 'decided_at' (60% confidence)
src/security/approval_gate.py:193: unused method 'approve_request' (60% confidence)
src/security/approval_gate.py:213: unused attribute 'decided_at' (60% confidence)
src/security/approval_gate.py:219: unused method 'deny_request' (60% confidence)
src/security/approval_gate.py:239: unused attribute 'decided_at' (60% confidence)
src/security/approval_gate.py:245: unused method 'cancel_request' (60% confidence)
src/security/approval_gate.py:258: unused attribute 'decided_at' (60% confidence)
src/security/approval_gate.py:263: unused method 'get_pending_requests' (60% confidence)
src/security/approval_gate.py:271: unused method 'get_request_status' (60% confidence)
src/security/approval_gate.py:290: unused method 'get_request_history' (60% confidence)
src/security/emergency_stop.py:21: unused variable 'GRACEFUL' (60% confidence)
src/security/emergency_stop.py:22: unused variable 'IMMEDIATE' (60% confidence)
src/security/emergency_stop.py:23: unused variable 'EMERGENCY' (60% confidence)
src/security/emergency_stop.py:29: unused variable 'USER_REQUESTED' (60% confidence)
src/security/emergency_stop.py:30: unused variable 'SAFETY_VIOLATION' (60% confidence)
src/security/emergency_stop.py:31: unused variable 'SYSTEM_ERROR' (60% confidence)
src/security/emergency_stop.py:32: unused variable 'KILL_SWITCH' (60% confidence)
src/security/emergency_stop.py:42: unused variable 'agents_stopped' (60% confidence)
src/security/emergency_stop.py:45: unused variable 'failed_agents' (60% confidence)
src/security/emergency_stop.py:52: unused class 'EmergencyStop' (60% confidence)
src/security/emergency_stop.py:75: unused method 'is_stopped' (60% confidence)
src/security/emergency_stop.py:83: unused method 'get_stop_count' (60% confidence)
src/security/emergency_stop.py:91: unused method 'trigger_stop' (60% confidence)
src/security/emergency_stop.py:150: unused method 'get_last_stop_info' (60% confidence)
src/security/emergency_stop.py:158: unused method 'get_stop_history' (60% confidence)
src/security/emergency_stop.py:166: unused method 'register_stop_handler' (60% confidence)
src/security/emergency_stop.py:177: unused method 'connect_nats' (60% confidence)
src/security/emergency_stop.py:182: unused method 'disconnect_nats' (60% confidence)
src/security/sandbox.py:88: unused method 'validate_file_access' (60% confidence)
src/security/sandbox.py:131: unused method 'validate_command' (60% confidence)
src/security/sandbox.py:163: unused method 'validate_file_size' (60% confidence)
src/security/sandbox.py:181: unused method 'validate_memory_usage' (60% confidence)
src/security/sandbox.py:202: unused method 'validate_network_access' (60% confidence)
src/security/sandbox.py:220: unused method 'get_violations' (60% confidence)
src/self_improvement/self_modification.py:25: unused variable 'REJECTED' (60% confidence)
src/self_improvement/self_modification.py:26: unused variable 'ROLLED_BACK' (60% confidence)
src/self_improvement/self_modification.py:64: unused variable 'proposed_by' (60% confidence)
src/self_improvement/self_modification.py:67: unused variable 'proposed_at' (60% confidence)
src/self_improvement/self_modification.py:73: unused variable 'test_results' (60% confidence)
src/self_improvement/self_modification.py:76: unused variable 'approval_request_id' (60% confidence)
src/self_improvement/self_modification.py:123: unused method 'get_depth_history' (60% confidence)
src/self_improvement/self_modification.py:167: unused method 'validate_not_on_main' (60% confidence)
src/self_improvement/self_modification.py:181: unused method 'create_feature_branch' (60% confidence)
src/self_improvement/self_modification.py:205: unused method 'commit_changes' (60% confidence)
src/self_improvement/self_modification.py:291: unused class 'IsolatedTestEnvironment' (60% confidence)
src/self_improvement/self_modification.py:307: unused method 'create_test_branch' (60% confidence)
src/self_improvement/self_modification.py:352: unused method 'cleanup' (60% confidence)
src/self_improvement/self_modification.py:359: unused method 'prepare_for_merge' (60% confidence)
src/self_improvement/self_modification.py:379: unused class 'SelfModificationApprovalGate' (60% confidence)
src/self_improvement/self_modification.py:405: unused method 'submit_self_modification' (60% confidence)
src/self_improvement/self_modification.py:453: unused attribute 'approval_request_id' (60% confidence)
src/self_improvement/self_modification.py:458: unused method 'wait_for_decision' (60% confidence)
src/testing/defeat_patterns/breaking_code.py:53: unused variable 'prev_failed' (60% confidence)
src/testing/defeat_patterns/breaking_code.py:54: unused variable 'curr_failed' (60% confidence)
src/testing/defeat_patterns/breaking_code.py:92: unused variable 'initial_failed' (60% confidence)
src/testing/defeat_patterns/breaking_code.py:93: unused variable 'final_failed' (60% confidence)
src/testing/defeat_patterns/breaking_code.py:122: unused function 'calculate_test_health_score' (60% confidence)
src/testing/defeat_patterns/context_drift.py:143: unused function 'extract_file_domain' (60% confidence)
src/testing/defeat_patterns/over_engineering.py:166: unused function 'get_abstraction_score' (60% confidence)
src/testing/defeat_patterns/retry_loop.py:87: unused function 'get_approach_diversity' (60% confidence)
src/testing/defeat_tests.py:19: unused class 'ActionOutcome' (60% confidence)
src/testing/defeat_tests.py:22: unused variable 'SUCCESS' (60% confidence)
src/testing/defeat_tests.py:23: unused variable 'FAILURE' (60% confidence)
src/testing/defeat_tests.py:24: unused variable 'PARTIAL_SUCCESS' (60% confidence)
src/testing/defeat_tests.py:25: unused variable 'SKIPPED' (60% confidence)
src/testing/defeat_tests.py:64: unused method 'add_action' (60% confidence)
src/testing/defeat_tests.py:103: unused variable 'pattern_name' (60% confidence)
src/testing/defeat_tests.py:132: unused method 'register_test' (60% confidence)
src/testing/defeat_tests.py:150: unused method 'run_all_registered_tests' (60% confidence)
src/testing/defeat_tests.py:178: unused method 'print_results' (60% confidence)
```


## Ruff Analysis (Unused Imports & Variables)

**Found:** 0
0 items

```
  - 'select' -> 'lint.select'
F401 [*] `pathlib.Path` imported but unused
 --> tests/core/test_work_history.py:5:21
  |
3 | import json
4 | import pytest
5 | from pathlib import Path
  |                     ^^^^
6 | from unittest.mock import patch, MagicMock
7 | from datetime import datetime
  |
help: Remove unused import: `pathlib.Path`

F401 [*] `pathlib.Path` imported but unused
 --> tests/orchestrator/test_roadmap_gardener.py:4:21
  |
3 | import pytest
4 | from pathlib import Path
  |                     ^^^^
5 | from unittest.mock import patch, MagicMock
  |
help: Remove unused import: `pathlib.Path`

F401 [*] `src.orchestrator.work_stream.WorkStream` imported but unused
  --> tests/orchestrator/test_roadmap_gardener.py:14:5
   |
12 | )
13 | from src.orchestrator.work_stream import (
14 |     WorkStream,
   |     ^^^^^^^^^^
15 |     WorkStreamStatus,
16 |     clear_roadmap_cache,
   |
help: Remove unused import

F401 [*] `src.orchestrator.work_stream.WorkStreamStatus` imported but unused
  --> tests/orchestrator/test_roadmap_gardener.py:15:5
   |
13 | from src.orchestrator.work_stream import (
14 |     WorkStream,
15 |     WorkStreamStatus,
   |     ^^^^^^^^^^^^^^^^
16 |     clear_roadmap_cache,
17 | )
   |
help: Remove unused import

F841 Local variable `result` is assigned to but never used
   --> tests/orchestrator/test_roadmap_gardener.py:527:13
    |
526 |         with patch.object(module, '_gardener', mock_gardener):
527 |             result = garden_roadmap()
    |             ^^^^^^
528 |
529 |         mock_gardener.garden.assert_called_once()
    |
help: Remove assignment to unused variable `result`

Found 5 errors.
[*] 4 fixable with the `--fix` option (1 hidden fix can be enabled with the `--unsafe-fixes` option).
```


## Analysis by Module

### Potentially Unused Infrastructure Code

The following modules contain code that appears unused but may be:
1. **Future infrastructure** - Implemented but not yet wired up
2. **API surface** - Public methods intended for external use
3. **Test fixtures** - Used by test discovery

| src/coordination | 73
0 items |
| src/agents | 48
0 items |
| src/core | 139
0 items |
| src/orchestrator | 44
0 items |

## Recommendations

### Safe to Remove (High Confidence)
- Unused local variables marked 100% confidence
- Unused imports in test files

### Review Before Removing (Medium Confidence)
- Enum values that may be used for type checking
- Methods that may be called via dynamic dispatch
- Classes that may be instantiated externally

### Action Items
1. Review each item in the high-confidence list
2. Check if code is genuinely unused or false positive
3. Remove confirmed dead code or add to whitelist
4. Consider adding `# noqa: vulture` comments for intentional API surface


---
*Report generated by dead_code_analysis.sh*

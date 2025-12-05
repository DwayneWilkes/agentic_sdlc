#!/usr/bin/env python3
"""
Example: Agent communication using NATS message bus

This demonstrates the core communication patterns:
1. Broadcast (pub/sub)
2. Direct messaging
3. Request/reply
4. Work queues
"""

import asyncio
from src.coordination.nats_bus import (
    NATSMessageBus,
    AgentMessage,
    MessageType,
    get_message_bus,
    cleanup_message_bus,
)


async def example_broadcast():
    """Example: Broadcasting status updates to all agents."""
    print("\n=== Example 1: Broadcast ===")

    bus = await get_message_bus()

    # Handler for status updates
    async def handle_status(msg: AgentMessage):
        print(f"[RECEIVED] {msg.from_agent} → {msg.message_type}: {msg.content}")

    # Subscribe to status updates
    await bus.subscribe(
        "orchestrator.broadcast.status_update",
        handle_status
    )

    # Broadcast a status update
    await bus.broadcast(
        from_agent="architect-001",
        message_type=MessageType.STATUS_UPDATE,
        content={
            "status": "completed",
            "component": "task_model",
            "file": "src/models/task.py"
        }
    )

    # Give time for message to be received
    await asyncio.sleep(0.1)


async def example_direct_messaging():
    """Example: Direct agent-to-agent communication."""
    print("\n=== Example 2: Direct Messaging ===")

    bus = await get_message_bus()

    # Handler for parser-dev agent
    async def parser_dev_handler(msg: AgentMessage):
        print(f"[parser-dev] Received from {msg.from_agent}: {msg.content}")

    # Subscribe parser-dev to its messages
    await bus.subscribe_to_agent_messages(
        "parser-dev-001",
        parser_dev_handler
    )

    # Architect sends question to parser-dev
    await bus.send_to_agent(
        from_agent="architect-001",
        to_agent="parser-dev-001",
        message_type=MessageType.QUESTION,
        content={
            "question": "Do you need the Task.validate() method?",
            "context": "Considering adding validation to model"
        }
    )

    await asyncio.sleep(0.1)


async def example_request_reply():
    """Example: Request/reply pattern for synchronous communication."""
    print("\n=== Example 3: Request/Reply ===")

    bus = await get_message_bus()

    # Architect agent handler (responds to requests)
    async def architect_handler(msg: AgentMessage) -> AgentMessage:
        print(f"[architect] Received request: {msg.content}")

        # Return reply
        return AgentMessage(
            from_agent="architect-001",
            to_agent=msg.from_agent,
            message_type=MessageType.RESOURCE_RESPONSE,
            content={
                "resource": "task_model",
                "status": "ready",
                "location": "src/models/task.py",
                "api": {
                    "class": "Task",
                    "fields": ["goal", "constraints", "context", "task_type"]
                }
            },
            timestamp=msg.timestamp,
            correlation_id=msg.correlation_id
        )

    # Subscribe architect to handle requests
    await bus.subscribe_to_agent_messages(
        "architect-001",
        architect_handler
    )

    # Parser-dev requests Task model from architect
    print("[parser-dev] Requesting Task model...")
    response = await bus.request(
        from_agent="parser-dev-001",
        to_agent="architect-001",
        message_type=MessageType.RESOURCE_REQUEST,
        content={
            "resource": "task_model",
            "reason": "Need to implement TaskParser"
        },
        timeout=5.0
    )

    print(f"[parser-dev] Received response: {response.content}")


async def example_work_queue():
    """Example: Work queue for parallel task execution."""
    print("\n=== Example 4: Work Queue ===")

    bus = await get_message_bus()

    # Worker function
    async def test_worker(msg: AgentMessage):
        test_name = msg.content["test"]
        print(f"[worker] Running test: {test_name}")
        await asyncio.sleep(0.1)  # Simulate test execution
        print(f"[worker] ✓ {test_name} passed")

    # Create work queue with 3 workers
    await bus.create_work_queue(
        queue_name="test_execution",
        callback=test_worker,
        num_workers=3
    )

    # Publish 10 tests to queue (load balanced across 3 workers)
    tests = [f"test_{i}" for i in range(10)]
    for test in tests:
        await bus.publish_to_queue(
            queue_name="test_execution",
            from_agent="test-coordinator",
            message_type=MessageType.TASK_ASSIGNMENT,
            content={"test": test}
        )

    # Wait for tests to complete
    await asyncio.sleep(1.0)


async def example_agent_lifecycle():
    """Example: Complete agent lifecycle with communication."""
    print("\n=== Example 5: Agent Lifecycle ===")

    bus = await get_message_bus()
    agent_id = "example-agent-001"

    # Message handler
    async def handle_message(msg: AgentMessage):
        if msg.message_type == MessageType.TASK_ASSIGNMENT:
            print(f"[{agent_id}] Received task: {msg.content['task']}")
            await asyncio.sleep(0.2)  # Simulate work

            # Broadcast completion
            await bus.broadcast(
                from_agent=agent_id,
                message_type=MessageType.TASK_COMPLETE,
                content={
                    "task": msg.content["task"],
                    "status": "success"
                }
            )

    # Subscribe to messages
    await bus.subscribe_to_agent_messages(agent_id, handle_message)

    # Heartbeat loop
    async def heartbeat():
        for _ in range(3):
            await bus.broadcast(
                from_agent=agent_id,
                message_type=MessageType.HEARTBEAT,
                content={"status": "alive"}
            )
            await asyncio.sleep(0.3)

    heartbeat_task = asyncio.create_task(heartbeat())

    # Simulate orchestrator assigning task
    await asyncio.sleep(0.1)
    await bus.send_to_agent(
        from_agent="orchestrator",
        to_agent=agent_id,
        message_type=MessageType.TASK_ASSIGNMENT,
        content={
            "task": "implement_feature_x",
            "deadline": "2025-12-06"
        }
    )

    # Wait for heartbeat and work to complete
    await heartbeat_task
    await asyncio.sleep(0.5)


async def main():
    """Run all examples."""
    print("=" * 60)
    print("NATS Message Bus Examples")
    print("=" * 60)
    print("\nMake sure NATS is running: docker-compose up -d nats\n")

    try:
        # Run examples
        await example_broadcast()
        await example_direct_messaging()
        await example_request_reply()
        await example_work_queue()
        await example_agent_lifecycle()

        # Show stats
        bus = await get_message_bus()
        stats = await bus.get_stats()
        print("\n=== NATS Stats ===")
        print(f"Connected: {stats['connected']}")
        print(f"Subscriptions: {stats['subscriptions']}")

    finally:
        # Cleanup
        await cleanup_message_bus()
        print("\n✓ Disconnected from NATS")


if __name__ == "__main__":
    asyncio.run(main())

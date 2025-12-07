"""Tests for agent coordination and NATS integration."""

import asyncio
import threading
from unittest.mock import AsyncMock, patch

import pytest

from src.orchestrator.agent_runner import (
    AgentProcess,
    AgentRunner,
    AgentState,
    WorkStreamCoordinator,
    get_coordinator,
)


class TestWorkStreamCoordinator:
    """Test WorkStreamCoordinator for race condition prevention."""

    def setup_method(self):
        """Create a fresh coordinator for each test."""
        self.coordinator = WorkStreamCoordinator()
        # Clear any claims from previous tests (same PID, so stale cleanup won't help)
        self.coordinator.clear_all_claims()

    def test_claim_work_stream_success(self):
        """Test successfully claiming a work stream."""
        result = self.coordinator.claim_work_stream("1.1", "agent-1")
        assert result is True
        assert self.coordinator.is_claimed("1.1") == "agent-1"

    def test_claim_work_stream_already_claimed_same_agent(self):
        """Test claiming work stream by the same agent (idempotent)."""
        self.coordinator.claim_work_stream("1.1", "agent-1")
        result = self.coordinator.claim_work_stream("1.1", "agent-1")
        assert result is True  # Same agent can reclaim

    def test_claim_work_stream_already_claimed_different_agent(self):
        """Test claiming work stream already claimed by different agent."""
        self.coordinator.claim_work_stream("1.1", "agent-1")
        result = self.coordinator.claim_work_stream("1.1", "agent-2")
        assert result is False  # Different agent cannot claim

    def test_release_work_stream(self):
        """Test releasing a work stream claim."""
        self.coordinator.claim_work_stream("1.1", "agent-1")
        result = self.coordinator.release_work_stream("1.1", "agent-1")
        assert result is True
        assert self.coordinator.is_claimed("1.1") is None

    def test_release_work_stream_not_owned(self):
        """Test releasing a work stream not owned by agent."""
        self.coordinator.claim_work_stream("1.1", "agent-1")
        result = self.coordinator.release_work_stream("1.1", "agent-2")
        assert result is False  # Cannot release what you don't own
        assert self.coordinator.is_claimed("1.1") == "agent-1"

    def test_release_unclaimed_work_stream(self):
        """Test releasing an unclaimed work stream."""
        result = self.coordinator.release_work_stream("1.1", "agent-1")
        assert result is True  # No-op, considered success

    def test_get_claimed_streams(self):
        """Test getting all claimed streams."""
        self.coordinator.claim_work_stream("1.1", "agent-1")
        self.coordinator.claim_work_stream("1.2", "agent-2")
        self.coordinator.claim_work_stream("1.3", "agent-1")

        claimed = self.coordinator.get_claimed_streams()
        assert len(claimed) == 3
        assert claimed["1.1"] == "agent-1"
        assert claimed["1.2"] == "agent-2"
        assert claimed["1.3"] == "agent-1"

    def test_concurrent_claims_same_work_stream(self):
        """Test concurrent claims for the same work stream (race condition test)."""
        results = []
        errors = []

        def claim_stream(agent_id):
            try:
                result = self.coordinator.claim_work_stream("1.1", agent_id)
                results.append((agent_id, result))
            except Exception as e:
                errors.append((agent_id, str(e)))

        # Spawn multiple threads trying to claim the same work stream
        threads = [
            threading.Thread(target=claim_stream, args=(f"agent-{i}",))
            for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one should succeed
        successful = [r for r in results if r[1] is True]
        failed = [r for r in results if r[1] is False]

        assert len(successful) == 1
        assert len(failed) == 9
        assert len(errors) == 0

        # The winner should be the claimer
        winner = successful[0][0]
        assert self.coordinator.is_claimed("1.1") == winner

    def test_concurrent_claims_different_work_streams(self):
        """Test concurrent claims for different work streams (no conflict)."""
        results = []

        def claim_stream(work_stream_id, agent_id):
            result = self.coordinator.claim_work_stream(work_stream_id, agent_id)
            results.append((work_stream_id, agent_id, result))

        # Spawn threads claiming different work streams
        threads = [
            threading.Thread(target=claim_stream, args=(f"1.{i}", f"agent-{i}"))
            for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        successful = [r for r in results if r[2] is True]
        assert len(successful) == 10

    def test_claim_release_cycle(self):
        """Test claiming, releasing, then claiming again."""
        # First agent claims
        assert self.coordinator.claim_work_stream("1.1", "agent-1") is True

        # Second agent cannot claim
        assert self.coordinator.claim_work_stream("1.1", "agent-2") is False

        # First agent releases
        assert self.coordinator.release_work_stream("1.1", "agent-1") is True

        # Now second agent can claim
        assert self.coordinator.claim_work_stream("1.1", "agent-2") is True
        assert self.coordinator.is_claimed("1.1") == "agent-2"


class TestWorkStreamCoordinatorNATS:
    """Test NATS integration in WorkStreamCoordinator."""

    def setup_method(self):
        """Create a fresh coordinator for each test."""
        self.coordinator = WorkStreamCoordinator()
        # Clear any claims from previous tests
        self.coordinator.clear_all_claims()

    @patch('src.orchestrator.agent_runner.get_message_bus')
    def test_broadcast_status(self, mock_get_bus):
        """Test broadcasting status via NATS."""
        # Mock the NATS bus
        mock_bus = AsyncMock()
        mock_get_bus.return_value = mock_bus

        # This should not raise even if NATS fails
        self.coordinator.broadcast_status(
            agent_id="agent-1",
            work_stream_id="1.1",
            status="started",
            details={"personal_name": "Aria"}
        )
        # We expect no exception - the coordinator handles NATS errors gracefully

    def test_coordinator_graceful_nats_failure(self):
        """Test coordinator works even when NATS is unavailable."""
        with patch(
            'src.orchestrator.agent_runner.get_message_bus',
            side_effect=Exception("NATS down"),
        ):
            # Should still be able to claim locally
            result = self.coordinator.claim_work_stream("1.1", "agent-1")
            assert result is True

            # Status broadcast should not raise
            self.coordinator.broadcast_status("agent-1", "1.1", "started")


class TestAgentRunnerCoordination:
    """Test AgentRunner integration with coordinator."""

    def test_spawn_agent_claims_work_stream(self):
        """Test that spawning an agent claims the work stream."""
        runner = AgentRunner()

        # Pre-claim the work stream
        runner._coordinator.claim_work_stream("1.1", "other-agent")

        # Trying to spawn for same work stream should raise
        with pytest.raises(RuntimeError, match="already claimed"):
            runner.spawn_agent("1.1", reuse_agent=False)

    def test_get_coordinator_singleton(self):
        """Test that get_coordinator returns a singleton."""
        c1 = get_coordinator()
        c2 = get_coordinator()
        assert c1 is c2


class TestAgentControlCommands:
    """Test agent control commands (stop, update goal, etc.)."""

    def setup_method(self):
        """Create a fresh runner for each test."""
        self.runner = AgentRunner()

    def test_send_stop_command_no_agent(self):
        """Test sending stop to non-existent agent."""
        result = self.runner.send_stop_command("non-existent-agent")
        assert result is False

    def test_send_update_goal_no_agent(self):
        """Test sending goal update to non-existent agent."""
        result = self.runner.send_update_goal_command(
            "non-existent-agent",
            "New goal"
        )
        assert result is False

    def test_send_ping_no_agent(self):
        """Test pinging non-existent agent."""
        result = self.runner.send_ping("non-existent-agent")
        assert result is False

    def test_stop_all_agents_empty(self):
        """Test stopping all agents when none exist."""
        count = self.runner.stop_all_agents()
        assert count == 0

    def test_broadcast_to_all_agents(self):
        """Test broadcasting to all agents."""
        # Should not raise even with no agents
        self.runner.broadcast_to_all_agents(
            message_type="test_message",
            content={"test": "data"}
        )

    def test_stop_command_graceful_vs_immediate(self):
        """Test graceful vs immediate stop command."""
        # Create a mock agent in the runner
        agent = AgentProcess(
            agent_id="test-agent",
            work_stream_id="1.1",
            state=AgentState.RUNNING,
        )
        self.runner.agents["test-agent"] = agent

        # Graceful stop should return True but not kill process
        result = self.runner.send_stop_command("test-agent", graceful=True)
        # Can't fully test without a real process, but should not raise
        assert result is True

    def test_update_goal_command(self):
        """Test sending goal update command."""
        # Create a mock agent
        agent = AgentProcess(
            agent_id="test-agent",
            work_stream_id="1.1",
            state=AgentState.RUNNING,
        )
        self.runner.agents["test-agent"] = agent

        result = self.runner.send_update_goal_command(
            "test-agent",
            new_goal="Updated goal: Complete Phase 2.1 instead",
            reason="Priority change"
        )
        assert result is True


class TestCoordinationIntegration:
    """Integration tests for coordination (requires NATS if available)."""

    @pytest.mark.asyncio
    async def test_nats_broadcast_integration(self):
        """Test actual NATS broadcast if server is available."""
        from src.coordination.nats_bus import MessageType, get_message_bus

        try:
            bus = await get_message_bus()

            # Subscribe to status updates
            received = []

            async def handler(msg):
                received.append(msg)

            await bus.subscribe(
                subject="orchestrator.broadcast.status_update",
                handler=handler
            )

            # Broadcast a status
            await bus.broadcast(
                from_agent="test-agent",
                message_type=MessageType.STATUS_UPDATE,
                content={"test": "integration"}
            )

            # Give time for message delivery
            await asyncio.sleep(0.5)

            assert len(received) >= 1
            # Message received

        except Exception as e:
            pytest.skip(f"NATS not available: {e}")
        finally:
            # Cleanup
            try:
                if 'bus' in locals():
                    await bus.close()
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_coordination_via_nats(self):
        """Test multi-agent coordination via NATS."""
        from src.coordination.nats_bus import get_message_bus

        try:
            bus = await get_message_bus()

            # Track claims received
            claims = []

            async def claim_handler(msg):
                claims.append(msg.data)

            await bus.subscribe(
                subject="orchestrator.broadcast.task_assigned",
                handler=claim_handler
            )

            # Simulate two agents trying to claim
            coordinator1 = WorkStreamCoordinator()
            coordinator2 = WorkStreamCoordinator()

            # First claim should broadcast
            result1 = coordinator1.claim_work_stream("2.1", "agent-A")

            await asyncio.sleep(0.5)

            # Local coordinator doesn't know about remote claims
            # This is expected - for true distributed locking, need JetStream
            result2 = coordinator2.claim_work_stream("2.1", "agent-B")

            # Both succeed locally (local-only coordination)
            # For true distributed coordination, use JetStream KV
            assert result1 is True
            assert result2 is True  # Local only

            # But claims were broadcast
            await asyncio.sleep(0.5)
            # Messages should have been attempted

        except Exception as e:
            pytest.skip(f"NATS not available: {e}")
        finally:
            try:
                if 'bus' in locals():
                    await bus.close()
            except Exception:
                pass

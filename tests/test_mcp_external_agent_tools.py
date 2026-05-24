import asyncio
import json

import openspace.external_agent_tools as external_agent_tools
import openspace.mcp_server as mcp_server


def test_mcp_list_external_agents_wrapper(monkeypatch):
    calls = []
    payload = {
        "count": 1,
        "items": [{"id": "openhuman", "available": True}],
    }

    async def fake_arun(self, available_only=False, require_handoff=False):
        calls.append((available_only, require_handoff))
        return json.dumps(payload)

    monkeypatch.setattr(external_agent_tools.ListExternalAgentsTool, "_arun", fake_arun)

    result = asyncio.run(
        mcp_server.list_external_agents(available_only=True, require_handoff=True)
    )

    assert json.loads(result) == payload
    assert calls == [(True, True)]


def test_mcp_delegate_external_agent_wrapper(monkeypatch):
    calls = []
    payload = {
        "status": "completed",
        "threadId": "openhuman-1",
        "latestTurn": {"response": "pong"},
    }

    async def fake_arun(
        self,
        agent_id,
        prompt,
        thread_id="",
        timezone="UTC",
        wait_for_completion=True,
        history_limit=10,
        poll_interval_seconds=4.0,
        timeout_seconds=90.0,
    ):
        calls.append(
            {
                "agent_id": agent_id,
                "prompt": prompt,
                "thread_id": thread_id,
                "timezone": timezone,
                "wait_for_completion": wait_for_completion,
                "history_limit": history_limit,
                "poll_interval_seconds": poll_interval_seconds,
                "timeout_seconds": timeout_seconds,
            }
        )
        return json.dumps(payload)

    monkeypatch.setattr(external_agent_tools.DelegateExternalAgentTool, "_arun", fake_arun)

    result = asyncio.run(
        mcp_server.delegate_external_agent(
            agent_id="openhuman",
            prompt="Reply with exactly: pong",
            thread_id="thread-123",
            timezone="UTC",
            wait_for_completion=False,
            history_limit=5,
            poll_interval_seconds=1.5,
            timeout_seconds=30.0,
        )
    )

    assert json.loads(result) == payload
    assert calls == [
        {
            "agent_id": "openhuman",
            "prompt": "Reply with exactly: pong",
            "thread_id": "thread-123",
            "timezone": "UTC",
            "wait_for_completion": False,
            "history_limit": 5,
            "poll_interval_seconds": 1.5,
            "timeout_seconds": 30.0,
        }
    ]


def test_mcp_get_external_agent_history_wrapper(monkeypatch):
    calls = []
    payload = {
        "threadId": "thread-123",
        "latestTurn": {"state": "completed", "response": "pong"},
    }

    async def fake_arun(self, agent_id, thread_id, limit=10):
        calls.append((agent_id, thread_id, limit))
        return json.dumps(payload)

    monkeypatch.setattr(external_agent_tools.GetExternalAgentHistoryTool, "_arun", fake_arun)

    result = asyncio.run(
        mcp_server.get_external_agent_history(
            agent_id="openhuman",
            thread_id="thread-123",
            limit=7,
        )
    )

    assert json.loads(result) == payload
    assert calls == [("openhuman", "thread-123", 7)]
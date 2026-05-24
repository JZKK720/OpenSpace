import pytest

import openspace.dashboard_server as dashboard_server


def test_dashboard_lists_external_agents_via_runtime_tool(monkeypatch):
    calls = []
    payload = {
        "count": 1,
        "items": [
            {
                "id": "openhuman",
                "name": "OpenHuman",
                "description": "Internal OpenHuman worker",
                "available": True,
                "status": "up",
                "supportsHandoff": True,
                "supportsHistory": False,
                "healthUrl": "http://openhuman:7788/health",
                "latencyMs": 12,
                "error": None,
            }
        ],
    }

    def fake_call(tool_name, arguments=None, *, timeout=30.0):
        calls.append((tool_name, arguments, timeout))
        return payload

    monkeypatch.setattr(dashboard_server, "_call_runtime_tool", fake_call)

    app = dashboard_server.create_app()
    client = app.test_client()
    response = client.get(f"{dashboard_server.API_PREFIX}/external-agents")

    assert response.status_code == 200
    assert response.get_json() == payload
    assert calls == [("list_external_agents", None, 30.0)]


def test_dashboard_proxies_external_agent_handoff_via_runtime_tool(monkeypatch):
    calls = []
    payload = {
        "status": "completed",
        "threadId": "openhuman-1",
        "latestTurn": {
            "state": "completed",
            "response": "pong",
        },
    }

    def fake_call(tool_name, arguments=None, *, timeout=30.0):
        calls.append((tool_name, arguments, timeout))
        return payload

    monkeypatch.setattr(dashboard_server, "_call_runtime_tool", fake_call)

    app = dashboard_server.create_app()
    client = app.test_client()
    response = client.post(
        f"{dashboard_server.API_PREFIX}/external-agents/openhuman/handoff",
        json={
            "prompt": "Reply with exactly pong",
            "threadId": "thread-123",
            "timezone": "UTC",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == payload
    assert calls == [
        (
            "delegate_external_agent",
            {
                "agent_id": "openhuman",
                "prompt": "Reply with exactly pong",
                "thread_id": "thread-123",
                "timezone": "UTC",
                "wait_for_completion": False,
            },
            120.0,
        )
    ]


def test_dashboard_proxies_external_agent_history_via_runtime_tool(monkeypatch):
    calls = []
    payload = {
        "threadId": "thread-123",
        "latestTurn": {
            "state": "completed",
            "response": "pong",
        },
    }

    def fake_call(tool_name, arguments=None, *, timeout=30.0):
        calls.append((tool_name, arguments, timeout))
        return payload

    monkeypatch.setattr(dashboard_server, "_call_runtime_tool", fake_call)

    app = dashboard_server.create_app()
    client = app.test_client()
    response = client.get(
        f"{dashboard_server.API_PREFIX}/external-agents/openhuman/history?thread_id=thread-123&limit=5"
    )

    assert response.status_code == 200
    assert response.get_json() == payload
    assert calls == [
        (
            "get_external_agent_history",
            {
                "agent_id": "openhuman",
                "thread_id": "thread-123",
                "limit": 5,
            },
            45.0,
        )
    ]


def test_dashboard_parses_plain_text_runtime_tool_error():
    response = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Error executing tool delegate_external_agent: "
                        "OpenHuman inference runtime is not ready (state: disabled)"
                    ),
                }
            ],
            "isError": True,
        },
    }

    with pytest.raises(dashboard_server.RuntimeMcpProxyError) as excinfo:
        dashboard_server._extract_runtime_tool_payload(response)

    assert str(excinfo.value) == "OpenHuman inference runtime is not ready (state: disabled)"
    assert excinfo.value.status_code == 503
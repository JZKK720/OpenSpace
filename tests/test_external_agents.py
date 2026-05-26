import openspace.external_agent_gateway as external_agent_gateway
from openspace.external_agents import get_external_agent, load_external_agents


def test_repo_external_agents_surface_openhuman_public_url(monkeypatch):
    monkeypatch.delenv("OPENSPACE_EXTERNAL_AGENTS_CONFIG", raising=False)
    monkeypatch.setenv("OPENHUMAN_PUBLIC_URL", "http://127.0.0.1:1420/")
    monkeypatch.setenv("OPENHUMAN_INTERNAL_URL", "http://openhuman:7788/")
    monkeypatch.setenv("OPENHUMAN_HEALTH_URL", "http://openhuman:7788/health")
    monkeypatch.setenv("OPENHUMAN_ACTION_URL", "http://openhuman:7788/rpc")

    agents = load_external_agents()
    agent_ids = {agent["id"] for agent in agents}

    assert "openhuman" in agent_ids

    openhuman = get_external_agent("openhuman")
    assert openhuman is not None
    assert openhuman["name"] == "OpenHuman"
    assert openhuman["publicUrl"] == "http://127.0.0.1:1420/"
    assert openhuman["actionUrl"] == "http://openhuman:7788/rpc"
    assert openhuman["healthUrl"] == "http://openhuman:7788/health"


def test_repo_external_agents_surface_hermes_public_url(monkeypatch):
    monkeypatch.delenv("OPENSPACE_EXTERNAL_AGENTS_CONFIG", raising=False)
    monkeypatch.setenv("HERMES_PUBLIC_URL", "http://127.0.0.1:8791/")
    monkeypatch.setenv("HERMES_INTERNAL_URL", "http://host.docker.internal:8789/")
    monkeypatch.setenv("HERMES_HEALTH_URL", "http://host.docker.internal:8789/health")
    monkeypatch.setenv("HERMES_ACTION_URL", "http://host.docker.internal:8789/v1/chat/completions")
    monkeypatch.setenv("HERMES_API_KEY", "test-hermes-token")

    agents = load_external_agents()
    agent_ids = {agent["id"] for agent in agents}

    assert "hermes" in agent_ids

    hermes = get_external_agent("hermes")
    assert hermes is not None
    assert hermes["name"] == "Hermes"
    assert hermes["publicUrl"] == "http://127.0.0.1:8791/"
    assert hermes["actionUrl"] == "http://host.docker.internal:8789/v1/chat/completions"
    assert hermes["healthUrl"] == "http://host.docker.internal:8789/health"
    assert hermes["promptTimeoutSeconds"] == 180


def test_openai_compat_gateway_honors_prompt_timeout(monkeypatch):
    calls = []

    def fake_request_json(url, *, method, payload, auth_token=None, headers=None, timeout=20.0):
        calls.append(
            {
                "url": url,
                "method": method,
                "payload": payload,
                "auth_token": auth_token,
                "timeout": timeout,
            }
        )
        return {
            "id": "chatcmpl-1",
            "choices": [
                {
                    "message": {
                        "content": "pong",
                    }
                }
            ],
        }

    monkeypatch.setattr(external_agent_gateway, "_request_json", fake_request_json)

    result = external_agent_gateway.handoff_external_agent(
        {
            "id": "hermes",
            "protocol": "openai-compat",
            "capabilities": ["handoff"],
            "actionUrl": "http://host.docker.internal:8789/v1/chat/completions",
            "_actionAuthToken": "test-hermes-token",
            "model": "hermes-agent",
            "promptTimeoutSeconds": 180,
        },
        prompt="Reply with exactly pong",
    )

    assert result["latestTurn"]["response"] == "pong"
    assert calls == [
        {
            "url": "http://host.docker.internal:8789/v1/chat/completions",
            "method": "POST",
            "payload": {
                "model": "hermes-agent",
                "messages": [{"role": "user", "content": "Reply with exactly pong"}],
            },
            "auth_token": "test-hermes-token",
            "timeout": 180.0,
        }
    ]
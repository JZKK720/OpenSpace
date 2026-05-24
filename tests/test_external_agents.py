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
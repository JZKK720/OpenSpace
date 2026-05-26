import openspace.dashboard_server as dashboard_server


def test_dashboard_lists_aionui_standalone_app(monkeypatch):
    app_status = {
        "id": "aionui",
        "name": "AgentOS / AionUi",
        "description": "Standalone AgentOS AionUi workspace exposed through the dashboard as a browser app and future workflow source.",
        "kind": "agent-app",
        "icon": "bot",
        "publicUrl": "http://127.0.0.1:3308/",
        "internalUrl": "http://host.docker.internal:3308/",
        "healthUrl": "http://host.docker.internal:3308/",
        "available": True,
        "status": "up",
        "statusCode": 200,
        "latencyMs": 5,
        "error": None,
        "tags": ["agentos", "aionui", "workspace", "workflows"],
    }

    monkeypatch.setattr(dashboard_server, "get_standalone_apps_status", lambda: [app_status])

    app = dashboard_server.create_app()
    client = app.test_client()
    response = client.get(f"{dashboard_server.API_PREFIX}/standalone-apps")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["items"][0]["id"] == "aionui"
    assert payload["items"][0]["publicUrl"] == "http://127.0.0.1:3308/"


def test_dashboard_returns_aionui_standalone_app_detail(monkeypatch):
    app_status = {
        "id": "aionui",
        "name": "AgentOS / AionUi",
        "description": "Standalone AgentOS AionUi workspace exposed through the dashboard as a browser app and future workflow source.",
        "kind": "agent-app",
        "icon": "bot",
        "publicUrl": "http://127.0.0.1:3308/",
        "internalUrl": "http://host.docker.internal:3308/",
        "healthUrl": "http://host.docker.internal:3308/",
        "available": True,
        "status": "up",
        "statusCode": 200,
        "latencyMs": 5,
        "error": None,
        "tags": ["agentos", "aionui", "workspace", "workflows"],
    }

    monkeypatch.setattr(dashboard_server, "get_standalone_app_status", lambda app_id: app_status if app_id == "aionui" else None)

    app = dashboard_server.create_app()
    client = app.test_client()

    ok_response = client.get(f"{dashboard_server.API_PREFIX}/standalone-apps/aionui")
    missing_response = client.get(f"{dashboard_server.API_PREFIX}/standalone-apps/missing")

    assert ok_response.status_code == 200
    assert ok_response.get_json()["id"] == "aionui"
    assert missing_response.status_code == 404
    assert missing_response.get_json()["error"] == "Unknown standalone app: missing"


def test_dashboard_returns_hermes_console_standalone_app_detail(monkeypatch):
    app_status = {
        "id": "hermes-console",
        "name": "Hermes Console",
        "description": "Hermes console and control interface surfaced separately from the interactive Hermes WebUI for operator status and controls.",
        "kind": "control-app",
        "icon": "spark",
        "publicUrl": "http://127.0.0.1:9119/",
        "internalUrl": "http://host.docker.internal:9119/",
        "healthUrl": "http://host.docker.internal:9119/api/status",
        "available": True,
        "status": "up",
        "statusCode": 200,
        "latencyMs": 8,
        "error": None,
        "tags": ["hermes", "console", "control"],
    }

    monkeypatch.setattr(
        dashboard_server,
        "get_standalone_app_status",
        lambda app_id: app_status if app_id == "hermes-console" else None,
    )

    app = dashboard_server.create_app()
    client = app.test_client()

    ok_response = client.get(f"{dashboard_server.API_PREFIX}/standalone-apps/hermes-console")
    missing_response = client.get(f"{dashboard_server.API_PREFIX}/standalone-apps/missing")

    assert ok_response.status_code == 200
    assert ok_response.get_json()["id"] == "hermes-console"
    assert ok_response.get_json()["publicUrl"] == "http://127.0.0.1:9119/"
    assert missing_response.status_code == 404
    assert missing_response.get_json()["error"] == "Unknown standalone app: missing"
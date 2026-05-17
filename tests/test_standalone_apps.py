from openspace.standalone_apps import get_standalone_app, load_standalone_apps


def test_repo_standalone_apps_surface_aionui(monkeypatch):
    monkeypatch.delenv("OPENSPACE_STANDALONE_APPS_CONFIG", raising=False)
    monkeypatch.setenv("AIONUI_PUBLIC_URL", "http://127.0.0.1:3308/")
    monkeypatch.setenv("AIONUI_INTERNAL_URL", "http://host.docker.internal:3308/")
    monkeypatch.setenv("AIONUI_HEALTH_URL", "http://host.docker.internal:3308/")

    apps = load_standalone_apps()
    app_ids = {app["id"] for app in apps}

    assert "aionui" in app_ids
    assert "openharness" not in app_ids

    aionui = get_standalone_app("aionui")
    assert aionui is not None
    assert aionui["name"] == "AgentOS / AionUi"
    assert aionui["publicUrl"] == "http://127.0.0.1:3308/"
    assert aionui["healthUrl"] == "http://host.docker.internal:3308/"
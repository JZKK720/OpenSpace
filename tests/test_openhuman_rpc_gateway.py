import pytest

import openspace.external_agent_gateway as external_agent_gateway
import openspace.openhuman_rpc_gateway as openhuman_rpc_gateway


def test_openhuman_rpc_helper_builds_expected_jsonrpc_requests(monkeypatch):
    captured_calls = []

    def fake_request_json(url, *, method, payload, auth_token=None, headers=None, timeout=20.0):
        captured_calls.append(
            {
                "url": url,
                "method": method,
                "payload": payload,
                "auth_token": auth_token,
                "headers": headers,
                "timeout": timeout,
            }
        )
        rpc_method = payload["method"]
        if rpc_method == "core.ping":
            return {"jsonrpc": "2.0", "id": payload["id"], "result": {"ok": True}}
        if rpc_method == "openhuman.inference_status":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "result": {"state": "ready", "provider": "ollama"},
                    "logs": ["local ai status fetched"],
                },
            }
        if rpc_method == "openhuman.inference_prompt":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "result": "Short answer from OpenHuman...",
                    "logs": ["local ai prompt completed"],
                },
            }
        raise AssertionError(f"Unexpected RPC method: {rpc_method}")

    monkeypatch.setattr(openhuman_rpc_gateway, "_request_json", fake_request_json)

    ping = openhuman_rpc_gateway.ping_openhuman_core("http://openhuman:7788/rpc", auth_token="token")
    status = openhuman_rpc_gateway.get_openhuman_inference_status("http://openhuman:7788/rpc", auth_token="token")
    prompt = openhuman_rpc_gateway.submit_openhuman_inference_prompt(
        "http://openhuman:7788/rpc",
        prompt="summarize this page",
        auth_token="token",
        max_tokens=256,
        no_think=False,
    )

    assert ping["ok"] is True
    assert status["state"] == "ready"
    assert status["provider"] == "ollama"
    assert prompt["response"] == "Short answer from OpenHuman..."
    assert len(captured_calls) == 3
    assert all(call["url"] == "http://openhuman:7788/rpc" for call in captured_calls)
    assert all(call["auth_token"] == "token" for call in captured_calls)
    assert captured_calls[0]["payload"]["jsonrpc"] == "2.0"
    assert captured_calls[0]["payload"]["method"] == "core.ping"
    assert captured_calls[1]["payload"]["method"] == "openhuman.inference_status"
    assert captured_calls[2]["payload"]["method"] == "openhuman.inference_prompt"
    assert captured_calls[2]["payload"]["params"] == {
        "prompt": "summarize this page",
        "max_tokens": 256,
        "no_think": False,
    }


def test_openhuman_adapter_blocks_disabled_runtime(monkeypatch):
    adapter = external_agent_gateway.OpenHumanRpcAdapter()

    monkeypatch.setattr(
        external_agent_gateway,
        "get_openhuman_inference_status",
        lambda *args, **kwargs: {"state": "disabled", "logs": ["local ai disabled"]},
    )

    with pytest.raises(external_agent_gateway.ExternalAgentGatewayError) as exc_info:
        adapter.handoff(
            {
                "id": "openhuman",
                "actionUrl": "http://openhuman:7788/rpc",
                "_actionAuthToken": "token",
            },
            prompt="summarize this page",
        )

    assert exc_info.value.status_code == 503
    assert "not ready" in str(exc_info.value)


def test_openhuman_adapter_normalizes_single_shot_prompt_response(monkeypatch):
    adapter = external_agent_gateway.OpenHumanRpcAdapter()
    captured_submit = {}

    monkeypatch.setattr(
        external_agent_gateway,
        "get_openhuman_inference_status",
        lambda *args, **kwargs: {"state": "degraded", "provider": "ollama", "logs": ["warming up"]},
    )

    def fake_submit(rpc_url, *, prompt, auth_token=None, headers=None, max_tokens=512, no_think=True, timeout=120.0):
        captured_submit.update(
            {
                "rpc_url": rpc_url,
                "prompt": prompt,
                "auth_token": auth_token,
                "headers": headers,
                "max_tokens": max_tokens,
                "no_think": no_think,
                "timeout": timeout,
            }
        )
        return {
            "requestId": "openspace-openhuman-1",
            "response": "Short answer from OpenHuman...",
            "logs": ["local ai prompt completed"],
        }

    monkeypatch.setattr(external_agent_gateway, "submit_openhuman_inference_prompt", fake_submit)

    result = adapter.handoff(
        {
            "id": "openhuman",
            "actionUrl": "http://openhuman:7788/rpc",
            "_actionAuthToken": "token",
            "max_tokens": 768,
            "no_think": "false",
            "promptTimeoutSeconds": 90,
        },
        prompt="summarize this page",
    )

    assert captured_submit == {
        "rpc_url": "http://openhuman:7788/rpc",
        "prompt": "summarize this page",
        "auth_token": "token",
        "headers": None,
        "max_tokens": 768,
        "no_think": False,
        "timeout": 90.0,
    }
    assert result["agentId"] == "openhuman"
    assert result["threadId"] == ""
    assert result["messageId"] == "openspace-openhuman-1"
    assert result["status"] == "completed"
    assert result["latestTurn"]["response"] == "Short answer from OpenHuman..."
    assert result["latestTurn"]["state"] == "completed"
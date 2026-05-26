"""
Smoke test for OpenSpace MCP streamable-http integration.

Level 1: Direct MCP protocol (initialize + tools/list + tools/call search_skills)
Level 2: IronClaw chat-thread integration (health + thread/new + chat/send)
Level 3: OpenHuman JSON-RPC integration (/health + core.ping + core.version + openhuman.inference_status + openhuman.inference_prompt + config.get_client_config + config.get_runtime_flags + config.agent_server_status + openhuman-rpc handoff)
Level 4: Hermes split-surface integration (dashboard API, interactive WebUI, separate console surface, OpenAI-compatible models, and openai-compat handoff)

Usage:
    python smoke_test_mcp.py
    python smoke_test_mcp.py --level 2 --ironclaw-token <token>
    python smoke_test_mcp.py --level 3 --ironclaw-token <token> --openhuman-token <token>
    python smoke_test_mcp.py --level 4 --hermes-token <token>
"""

import argparse
import json
import sys

import httpx

from openspace.external_agent_gateway import handoff_external_agent
from openspace.openhuman_rpc_gateway import (
    get_openhuman_agent_server_status,
    get_openhuman_client_config,
    get_openhuman_inference_status,
    get_openhuman_runtime_flags,
    get_openhuman_version,
    ping_openhuman_core,
    submit_openhuman_inference_prompt,
)

MCP_URL = "http://127.0.0.1:8788/mcp"
IC_URL = "http://127.0.0.1:3231"
OH_URL = "http://127.0.0.1:7181"
DASHBOARD_URL = "http://127.0.0.1:7788"
HERMES_WEB_URL = "http://127.0.0.1:8791/"
HERMES_CONSOLE_STATUS_URL = "http://127.0.0.1:9119/api/status"
HERMES_API_URL = "http://127.0.0.1:8789"

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"


def _parse_mcp_response(resp: httpx.Response) -> dict:
    ct = resp.headers.get("content-type", "")
    if "text/event-stream" in ct:
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return {"raw": resp.text[:500]}
    return resp.json()


def _extract_tool_error_text(response: dict) -> str | None:
    if "error" in response:
        error = response["error"]
        if isinstance(error, dict):
            return json.dumps(error)
        return str(error)

    content = response.get("result", {}).get("content", [])
    if not content:
        return None

    text = content[0].get("text", "")
    if not text:
        return None

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    error = payload.get("error")
    if error is None:
        return None
    if isinstance(error, str):
        return error
    return json.dumps(error)


def mcp_rpc(client: httpx.Client, method: str, params: dict | None = None, id: int = 1, session_id: str | None = None) -> tuple[dict, str | None]:
    body: dict = {"jsonrpc": "2.0", "id": id, "method": method}
    if params:
        body["params"] = params
    headers = dict(MCP_HEADERS)
    if session_id:
        headers["mcp-session-id"] = session_id
    resp = client.post(MCP_URL, json=body, headers=headers)
    resp.raise_for_status()
    new_session_id = resp.headers.get("mcp-session-id", session_id)
    return _parse_mcp_response(resp), new_session_id


def run_level1():
    ok = True
    session_id: str | None = None
    print("\n=== Level 1: Direct MCP protocol ===")

    with httpx.Client(timeout=15) as client:
        # ── initialize ───────────────────────────────────────────────────────
        try:
            r, session_id = mcp_rpc(client, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "smoke-test", "version": "1.0"},
            })
            server_name = r.get("result", {}).get("serverInfo", {}).get("name", "?")
            proto = r.get("result", {}).get("protocolVersion", "?")
            print(f"  {PASS} initialize  server={server_name!r}  protocolVersion={proto!r}  session={session_id!r}")
        except Exception as e:
            print(f"  {FAIL} initialize failed: {e}")
            return False

        # ── tools/list ───────────────────────────────────────────────────────
        try:
            r2, _ = mcp_rpc(client, "tools/list", id=2, session_id=session_id)
            tools = r2.get("result", {}).get("tools", [])
            names = [t["name"] for t in tools]
            print(f"  {PASS} tools/list  count={len(tools)}")
            for n in names:
                print(f"         • {n}")
            if not names:
                print(f"  {FAIL} No tools returned")
                ok = False
        except Exception as e:
            print(f"  {FAIL} tools/list failed: {e}")
            ok = False

        # ── tools/call  search_skills (tools on the server use un-prefixed names) ──
        try:
            r3, _ = mcp_rpc(client, "tools/call", {
                "name": "search_skills",
                "arguments": {"query": "smoke test", "source": "local"},
            }, id=3, session_id=session_id)
            error_text = _extract_tool_error_text(r3)
            content = r3.get("result", {}).get("content", [])
            text = content[0].get("text", "") if content else ""
            short = text[:120].replace("\n", " ")
            if error_text:
                print(f"  {FAIL} tools/call search_skills returned tool error: {error_text}")
                ok = False
            else:
                print(f"  {PASS} tools/call search_skills → {short!r}…")
        except Exception as e:
            print(f"  {FAIL} tools/call search_skills failed: {e}")
            ok = False

    return ok


def run_level2(token: str):
    ok = True
    print("\n=== Level 2: IronClaw chat-thread integration ===")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    with httpx.Client(timeout=15) as client:
        # ── IronClaw health ───────────────────────────────────────────────────
        try:
            r = client.get(IC_URL)
            r.raise_for_status()
            print(f"  {PASS} IronClaw root reachable  status={r.status_code}")
        except Exception as e:
            print(f"  {FAIL} IronClaw health failed: {e}")
            return False

        # ── extensions list (sanity check — new IronClaw uses MCP, not extensions) ──
        try:
            r = client.get(f"{IC_URL}/api/extensions", headers=headers)
            r.raise_for_status()
            exts = r.json().get("extensions", [])
            print(f"  {PASS} /api/extensions reachable  count={len(exts)}")
        except Exception as e:
            print(f"  {FAIL} /api/extensions failed: {e}")
            ok = False

        # ── create new chat thread ────────────────────────────────────────────
        thread_id: str | None = None
        try:
            r = client.post(f"{IC_URL}/api/chat/thread/new", headers=headers)
            r.raise_for_status()
            thread_id = r.json().get("id", None)
            if not thread_id:
                print(f"  {FAIL} /api/chat/thread/new returned no id")
                ok = False
            else:
                print(f"  {PASS} /api/chat/thread/new  thread_id={thread_id!r}")
        except Exception as e:
            print(f"  {FAIL} /api/chat/thread/new failed: {e}")
            ok = False

        # ── send a smoke-test message ─────────────────────────────────────────
        if thread_id:
            try:
                payload = {"content": "smoke-test ping", "thread_id": thread_id, "timezone": "UTC"}
                r = client.post(f"{IC_URL}/api/chat/send", headers=headers, json=payload)
                r.raise_for_status()
                msg_id = r.json().get("message_id", r.json().get("id", "?"))
                status_val = r.json().get("status", "?")
                print(f"  {PASS} /api/chat/send  message_id={msg_id!r}  status={status_val!r}")
            except Exception as e:
                print(f"  {FAIL} /api/chat/send failed: {e}")
                ok = False

    return ok


def run_level3(token: str):
    ok = True
    print("\n=== Level 3: OpenHuman JSON-RPC integration ===")

    with httpx.Client(timeout=120) as client:
        try:
            r = client.get(f"{OH_URL}/health")
            r.raise_for_status()
            print(f"  {PASS} OpenHuman health reachable  status={r.status_code}")
        except Exception as e:
            print(f"  {FAIL} OpenHuman health failed: {e}")
            return False

        try:
            ping = ping_openhuman_core(f"{OH_URL}/rpc", auth_token=token)
            if not ping.get("ok"):
                print(f"  {FAIL} core.ping returned unexpected payload: {ping!r}")
                ok = False
            else:
                print(f"  {PASS} core.ping  ok={ping['ok']!r}")
        except Exception as e:
            print(f"  {FAIL} core.ping failed: {e}")
            ok = False

        try:
            status = get_openhuman_inference_status(f"{OH_URL}/rpc", auth_token=token)
            state = str(status.get("state") or "")
            if state != "ready":
                print(f"  {FAIL} openhuman.inference_status returned state={state!r}")
                ok = False
            else:
                print(f"  {PASS} openhuman.inference_status  state={state!r}  provider={status.get('provider')!r}")
        except Exception as e:
            print(f"  {FAIL} openhuman.inference_status failed: {e}")
            ok = False

        try:
            prompt_result = submit_openhuman_inference_prompt(
                f"{OH_URL}/rpc",
                prompt="Reply with exactly: pong",
                auth_token=token,
                max_tokens=64,
                no_think=True,
            )
            reply = str(prompt_result.get("response") or "").strip()
            if reply != "pong":
                print(f"  {FAIL} openhuman.inference_prompt returned unexpected reply: {reply!r}")
                ok = False
            else:
                print(f"  {PASS} openhuman.inference_prompt  reply={reply!r}")
        except Exception as e:
            print(f"  {FAIL} openhuman.inference_prompt failed: {e}")
            ok = False

        try:
            agent = {
                "id": "openhuman",
                "protocol": "openhuman-rpc",
                "capabilities": ["handoff"],
                "actionUrl": f"{OH_URL}/rpc",
                "_actionAuthToken": token,
            }
            result = handoff_external_agent(
                agent,
                prompt="Reply with exactly: pong",
            )
            latest_turn = result.get("latestTurn") or {}
            mirrored_reply = str(latest_turn.get("response") or "").strip()
            if mirrored_reply != "pong":
                print(f"  {FAIL} OpenSpace adapter handoff returned unexpected reply: {mirrored_reply!r}")
                ok = False
            else:
                print(f"  {PASS} openhuman-rpc handoff  reply={mirrored_reply!r}")
        except Exception as e:
            print(f"  {FAIL} OpenSpace OpenHuman adapter failed: {e}")
            ok = False

        # ── config surfaces ───────────────────────────────────────────────────
        try:
            ver_result = get_openhuman_version(f"{OH_URL}/rpc", auth_token=token)
            ver = ver_result.get("version", "")
            if not ver:
                print(f"  {FAIL} core.version returned empty string")
                ok = False
            else:
                print(f"  {PASS} core.version  version={ver!r}")
        except Exception as e:
            print(f"  {FAIL} core.version failed: {e}")
            ok = False

        try:
            cfg = get_openhuman_client_config(f"{OH_URL}/rpc", auth_token=token)
            if not isinstance(cfg, dict):
                print(f"  {FAIL} config.get_client_config returned non-dict: {cfg!r}")
                ok = False
            else:
                key_set = cfg.get("api_key_set")
                print(f"  {PASS} config.get_client_config  api_key_set={key_set!r}  keys={sorted(cfg.keys())}")
        except Exception as e:
            msg = str(e)
            if "unknown method" in msg.lower():
                print(f"  ~ config.get_client_config not available on this build  ({msg})")
            else:
                print(f"  {FAIL} config.get_client_config failed: {e}")
                ok = False

        try:
            flags = get_openhuman_runtime_flags(f"{OH_URL}/rpc", auth_token=token)
            if not isinstance(flags, dict):
                print(f"  {FAIL} config.get_runtime_flags returned non-dict: {flags!r}")
                ok = False
            else:
                print(f"  {PASS} config.get_runtime_flags  keys={sorted(flags.keys())}")
        except Exception as e:
            msg = str(e)
            if "unknown method" in msg.lower():
                print(f"  ~ config.get_runtime_flags not available on this build  ({msg})")
            else:
                print(f"  {FAIL} config.get_runtime_flags failed: {e}")
                ok = False

        try:
            srv = get_openhuman_agent_server_status(f"{OH_URL}/rpc", auth_token=token)
            if not isinstance(srv, dict):
                print(f"  {FAIL} config.agent_server_status returned non-dict: {srv!r}")
                ok = False
            else:
                running = srv.get("running")
                print(f"  {PASS} config.agent_server_status  running={running!r}  keys={sorted(srv.keys())}")
        except Exception as e:
            msg = str(e)
            if "unknown method" in msg.lower():
                print(f"  ~ config.agent_server_status not available on this build  ({msg})")
            else:
                print(f"  {FAIL} config.agent_server_status failed: {e}")
                ok = False

    return ok


def run_level4(token: str):
    ok = True
    model_id = ""
    print("\n=== Level 4: Hermes split-surface integration ===")

    with httpx.Client(timeout=60) as client:
        try:
            r = client.get(HERMES_WEB_URL)
            r.raise_for_status()
            print(f"  {PASS} Hermes WebUI reachable  status={r.status_code}")
        except Exception as e:
            print(f"  {FAIL} Hermes WebUI failed: {e}")
            ok = False

        try:
            r = client.get(HERMES_CONSOLE_STATUS_URL)
            r.raise_for_status()
            print(f"  {PASS} Hermes console reachable  status={r.status_code}")
        except Exception as e:
            print(f"  {FAIL} Hermes console failed: {e}")
            ok = False

        try:
            r = client.get(f"{DASHBOARD_URL}/api/v1/standalone-apps/hermes-console")
            r.raise_for_status()
            payload = r.json()
            public_url = payload.get("publicUrl")
            if public_url != "http://127.0.0.1:9119/":
                print(f"  {FAIL} hermes-console app returned unexpected publicUrl: {public_url!r}")
                ok = False
            else:
                print(f"  {PASS} dashboard standalone app hermes-console  publicUrl={public_url!r}")
        except Exception as e:
            print(f"  {FAIL} dashboard standalone app hermes-console failed: {e}")
            ok = False

        try:
            r = client.get(f"{DASHBOARD_URL}/api/v1/external-agents")
            r.raise_for_status()
            items = r.json().get("items", [])
            hermes = next((item for item in items if item.get("id") == "hermes"), None)
            public_url = (hermes or {}).get("publicUrl")
            if not hermes:
                print(f"  {FAIL} dashboard external-agents list missing hermes entry")
                ok = False
            elif public_url != "http://127.0.0.1:8791/":
                print(f"  {FAIL} Hermes external agent returned unexpected publicUrl: {public_url!r}")
                ok = False
            else:
                print(f"  {PASS} dashboard external agent hermes  publicUrl={public_url!r}")
        except Exception as e:
            print(f"  {FAIL} dashboard external-agents hermes check failed: {e}")
            ok = False

        try:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            r = client.get(f"{HERMES_API_URL}/v1/models", headers=headers)
            r.raise_for_status()
            payload = r.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            model_count = len(data) if isinstance(data, list) else 0
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and str(item.get("id") or "").strip():
                        model_id = str(item.get("id") or "").strip()
                        break
            print(f"  {PASS} Hermes OpenAI-compatible models reachable  count={model_count}")
        except Exception as e:
            print(f"  {FAIL} Hermes /v1/models failed: {e}")
            ok = False

        try:
            agent = {
                "id": "hermes",
                "protocol": "openai-compat",
                "capabilities": ["handoff"],
                "actionUrl": f"{HERMES_API_URL}/v1/chat/completions",
                "_actionAuthToken": token,
                "model": model_id,
                "promptTimeoutSeconds": 180,
            }
            result = handoff_external_agent(agent, prompt="Reply with one short word.")
            latest_turn = result.get("latestTurn") or {}
            reply = str(latest_turn.get("response") or "").strip()
            if not reply:
                print(f"  {FAIL} Hermes handoff returned an empty response")
                ok = False
            else:
                print(f"  {PASS} Hermes openai-compat handoff  reply={reply!r}")
        except Exception as e:
            print(f"  {FAIL} Hermes openai-compat handoff failed: {e}")
            ok = False

    return ok


def main():
    parser = argparse.ArgumentParser(description="OpenSpace MCP smoke test")
    parser.add_argument("--level", type=int, choices=[1, 2, 3, 4], default=1)
    parser.add_argument("--ironclaw-token", default=None, help="IronClaw auth token for level 2")
    parser.add_argument("--openhuman-token", default=None, help="OpenHuman auth token for level 3")
    parser.add_argument("--hermes-token", default=None, help="Hermes auth token for level 4")
    args = parser.parse_args()

    passed = True
    passed = run_level1() and passed
    if args.level >= 2:
        if not args.ironclaw_token:
            print("\n[!] Pass --ironclaw-token for level 2")
        else:
            passed = run_level2(args.ironclaw_token) and passed
    if args.level >= 3:
        if not args.openhuman_token:
            print("\n[!] Pass --openhuman-token for level 3")
        else:
            passed = run_level3(args.openhuman_token) and passed
    if args.level >= 4:
        if not args.hermes_token:
            print("\n[!] Pass --hermes-token for level 4")
        else:
            passed = run_level4(args.hermes_token) and passed

    print()
    if passed:
        print(f"{PASS} All checks passed")
        sys.exit(0)
    else:
        print(f"{FAIL} Some checks failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

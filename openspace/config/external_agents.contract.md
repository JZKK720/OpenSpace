# External Agent Contract

OpenSpace treats external agents as a separate integration surface from standalone apps.

Use `openspace/config/external_agents.json` to register delegateable runtimes.

The registry also supports a top-level `mcp_servers` section for actual MCP tool servers that should be mounted into OpenSpace independently of any agent handoff adapter.

## Required fields

- `id`: stable agent identifier used by dashboard APIs and delegation tools.
- `name`: human-readable label.
- `kind`: category such as `acting-agent`.

## URL fields

- `public_url`: browser-facing URL for the user.
- `internal_url`: container-to-container URL for internal probes.
- `health_url`: probe URL for availability checks.
- `action_url`: handoff endpoint for delegated execution.
- `mcp_url`: MCP endpoint only when the agent itself exposes MCP.

Each URL field may use a matching `*_env` override.

## Shared MCP server entries

Top-level `mcp_servers` entries describe real MCP servers that OpenSpace should mount into its normal MCP provider config.

- `id`: stable server identifier.
- `name`: human-readable label.
- `server_name`: optional final MCP provider name. Defaults to `external-<id>`.
- `url` / `url_env`: HTTP or SSE MCP endpoint.
- `ws_url` / `ws_url_env`: websocket MCP endpoint.
- `health_url` / `health_url_env`: optional health probe URL when the MCP endpoint itself is not probe-friendly.
- `auth_token` / `auth_token_env`: optional bearer token.
- `headers` / `headers_env`: optional JSON object of HTTP headers.
- `command`, `args`, `cwd`, `env` / `env_env`: optional local command-based MCP server definition.

Use shared `mcp_servers` when the runtime is a tool surface, not a delegated worker.

## Contract fields

- `protocol`: adapter protocol name. Current supported delegate protocols include `chat-thread`, `http-json`, `openclaw-gateway`, and `openai-compat`.
- `capabilities`: any of `handoff`, `history`, `mcp`.
- `handoff_mode`: expected handoff pattern such as `chat_thread` or `request_response`.
- `history_mode`: expected history pattern such as `thread_history`, `poll`, or `none`.
- `standalone_app_id`: optional link to a standalone app entry when the runtime also has a UI surface.
- `linked_mcp_servers`: optional list of shared `mcp_servers` ids that this external agent should consume or be paired with.

## Supported protocols

- `chat-thread`: threaded chat handoff using `action_url` plus the companion `/api/chat/thread/new` and `/api/chat/history` endpoints.
- `http-json`: generic JSON-over-HTTP handoff. Use `action_url` plus optional field maps.
- `openclaw-gateway`: OpenClaw-specific adapter over `/v1/chat/completions`. OpenSpace replays prior thread turns back into the `messages` array and mirrors completed history locally for dashboard refreshes.
- `openai-compat`: stateless OpenAI-compatible handoff using `action_url`, typically `/v1/chat/completions`.
- `mcp`: MCP-only runtime with no handoff adapter; tools are mounted through `mcp_url`.

## Optional protocol mapping fields

- `request_fields`: map logical keys like `prompt`, `threadId`, `timezone` to protocol-specific request field names.
- `response_fields`: map logical keys like `messageId`, `status`, `threadId`, `response` to response JSON paths.
- `history_url`: optional history endpoint for adapters that support polling.
- `history_request_fields`: map `threadId` and `limit` for the history request.
- `history_response_fields`: map `threadId`, `turns`, `latestTurn`, and `hasMore` for history payloads.

## Optional auth fields

- `action_auth_token` / `action_auth_token_env`
- `history_auth_token` / `history_auth_token_env`
- `mcp_auth_token` / `mcp_auth_token_env`
- `action_headers` / `action_headers_env`
- `history_headers` / `history_headers_env`
- `mcp_headers` / `mcp_headers_env`

## Current adapter behavior

- Dashboard APIs dispatch through `openspace/external_agent_gateway.py`.
- The core executor exposes `list_external_agents`, `delegate_external_agent`, and `get_external_agent_history` as internal system tools.
- `chat-thread` is the first registered threaded adapter and bridges to `openspace/chat_thread_gateway.py`.
- Shared `mcp_servers` and MCP-native external agents are mounted into the normal MCP provider config during `OpenSpace.initialize()`.

## Separation of concerns

- External agents: delegateable runtimes that can accept work.
- Shared MCP servers: actual tool servers mounted into OpenSpace, optionally linked to one or more external agents.
- Standalone apps: UI/app surfaces shown in Spotlight.
- OpenSpace core execution: the internal `execute_task` and `GroundingAgent` loop.
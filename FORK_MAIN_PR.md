# Fork Main PR Draft

Use this draft when opening or updating a pull request against your own fork's `main` branch.

## Suggested Title

Cubecloud derivative: restore external agents, showcase apps, and protected branding policy

## Suggested PR Body

### Summary

This PR keeps the full Cubecloud derivative build as the canonical state of this fork.

It restores the live external-agent and showcase surfaces, preserves the Cubecloud-facing UI, and documents the repository's open-code but brand-protected licensing boundary.

### What this PR includes

- restores the default external-agent registry with `ironclaw` as the delegated external agent
- restores the shared `openspace-remote` MCP runtime wiring
- restores `my-daily-monitor` as the default standalone app in Showcase
- keeps Agents Monitor and Showcase as first-class product surfaces in this fork
- keeps dashboard handoff and thread-history polling for connected agents
- keeps shared MCP runtime mounting inside the OpenSpace tool graph
- restores Cubecloud-facing wording in the dashboard and showcase UI
- documents the contribution, branding, and brand-asset rules for this fork

### Runtime and product changes

- registry-driven external-agent loading and status reporting
- dashboard APIs for external agents and standalone apps
- gateway-based `chat-thread` handoff and history support for IronClaw
- internal runtime tools for listing, delegating to, and polling external agents
- Showcase route and connected-agent cards in the frontend
- production packaging for Agents Monitor alongside the dashboard
- Compose bind mounts for registry JSON files so running containers always follow host-side config

### License and branding boundary

The software code remains available under the MIT license in [LICENSE](LICENSE).

Cubecloud branding remains reserved and is documented in:

- [TRADEMARKS.md](TRADEMARKS.md)
- [BRAND_ASSETS.md](BRAND_ASSETS.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

This means others may use, fork, modify, and contribute to the code, but no rights are granted to use the `Cubecloud` name, the `cubecloud.io` domain, Cubecloud logos, or other Cubecloud source-identifying brand assets without permission.

### Validation

- Python compile completed successfully
- dashboard frontend build completed successfully
- My Daily Monitor build completed successfully
- Docker Compose config validated successfully
- live dashboard container responds successfully on `http://127.0.0.1:7788`
- live dashboard API reports external agent `ironclaw`
- live dashboard API reports standalone app `my-daily-monitor`
- live handoff through `/api/v1/external-agents/ironclaw/handoff` completed end-to-end after restoration

### Fork intent

This PR is intended for my fork's `main` branch as the maintained Cubecloud derivative build.

It is not framed as an upstream-clean contribution to `HKUDS/OpenSpace`. The goal is to preserve the full branded product surface, runtime wiring, and integration behavior in this fork while keeping the code open for contribution under MIT.
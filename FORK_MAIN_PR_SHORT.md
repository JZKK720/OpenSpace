# Fork Main PR Draft (Short)

## Title

Cubecloud derivative: restore connected agents, showcase apps, and brand policy

## Body

### Summary

This PR preserves this fork as the canonical Cubecloud derivative build.

It restores the live connected-agent and showcase surfaces, keeps the Cubecloud-facing UI intact, and documents the repo's MIT code plus reserved Cubecloud branding boundary.

### Includes

- restore `ironclaw` as the default delegated external agent
- restore the shared `openspace-remote` MCP runtime wiring
- restore `my-daily-monitor` as the default Showcase app
- keep Agents Monitor, Showcase, dashboard handoff, and history polling active in this fork
- keep shared MCP runtime mounting in the OpenSpace tool graph
- add repo-level trademark, brand-asset, and contribution rules

### License and branding

Code remains MIT under [LICENSE](LICENSE).

Cubecloud branding remains reserved under [TRADEMARKS.md](TRADEMARKS.md), [BRAND_ASSETS.md](BRAND_ASSETS.md), and [CONTRIBUTING.md](CONTRIBUTING.md).

Others may use, fork, modify, and contribute to the code, but no right is granted to use the `Cubecloud` name, the `cubecloud.io` domain, or Cubecloud source-identifying brand assets without permission.

### Validation

- Python compile passed
- dashboard frontend build passed
- My Daily Monitor build passed
- Docker Compose config validated
- live dashboard API reports `ironclaw` and `my-daily-monitor`
- live handoff through `/api/v1/external-agents/ironclaw/handoff` completed successfully

### Intent

This PR targets my fork's `main` branch and is not framed as an upstream-clean contribution to `HKUDS/OpenSpace`.
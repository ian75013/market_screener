# Incident Report - OVH Deployment Turbulence (2026-04-11)

## Scope
- Repo: market_screener
- Environment: OVH VPS (Apache reverse proxy + Docker Compose)
- Services impacted: frontend `market.screener.doctumconsilium.com`, API `api.market.screener.doctumconsilium.com`, startup refresh pipeline

## Executive Summary
A sequence of rapid changes was applied to deployment, data-provider fallback, and runtime troubleshooting in production.
The main user-visible issue became a blank/empty frontend experience and unstable deployment behavior after multiple retries.
No confirmed database volume deletion occurred, but repeated stack teardown behavior (containers/network) created confusion and risk perception.

## Customer Impact
- Frontend intermittently unusable/blank from browser point of view.
- Stock refresh not providing expected data quality (Yahoo rate limiting, fallback failures).
- Operational trust degraded due to repeated deployment attempts and unstable behavior.

## Timeline (fact-based)
1. Deployment automation iterations with many reruns (`deploy.ovh.sh`).
2. Provider fallback introduced (Yahoo -> Finnhub).
3. In production logs, Finnhub quote endpoint returned HTTP 401 repeatedly.
4. Frontend bundle in production contained `http://localhost:8000/api/v1` instead of public API domain.
5. Deploy script behavior included automatic `docker compose down --remove-orphans` before `up`.
6. Corrective actions landed via commits:
   - `3adebb6`: remove automatic compose down before up.
   - `1227c10`: keep Yahoo-only provider path and remove compose-down behavior in deployment flow.
   - `9a6a5e5`: allow in-place port reuse when ports are already bound by running Docker containers.

## What Went Wrong (Root Causes)
1. Change batching in production
- Deployment mechanics, provider behavior, and runtime debugging were changed concurrently instead of one axis at a time.

2. Fallback assumption drift
- Finnhub quote path was enabled without validating production token/authorization behavior (401 in real environment).

3. Build-time API config mismatch
- Frontend static bundle had localhost API URL baked in, causing client-side failures outside the host context.

4. Deployment teardown side effects
- Automatic pre-up `compose down --remove-orphans` increased churn/risk and made behavior harder to reason about.

5. Guardrails too rigid after removing down
- Port conflict checks then blocked valid in-place redeploys because existing stack ports were legitimately occupied.

## What Did NOT Happen (important)
- No `-v/--volumes` deletion command was executed in deployment flow.
- Docker volume `market_screener_postgres_data` existed on VPS during diagnostics.

## Corrective Actions Applied
1. Reverted provider path to Yahoo-only in multi-pass refresh (no provider-level Finnhub fallback path).
2. Removed automatic `compose down` in deployment flow (both local and remote paths where relevant).
3. Added safe port reuse logic for ports already published by running Docker containers.
4. Forced OVH deployment env usage to avoid accidental `.env` drift.

## Preventive Controls (mandatory for future deploys)
1. One-change-per-deploy rule
- Never ship provider changes + deployment mechanic changes in same production push.

2. Preflight checks before deploy
- Verify `VITE_API_URL` target, provider credentials, and active env file.

3. Non-destructive deployment policy
- Ban `down -v`, `--volumes`, `volume rm`, and prune commands in routine deploy scripts.

4. Post-deploy smoke tests (blocking)
- Frontend HTML loads
- JS bundle reachable
- Bundle contains expected API domain
- API health endpoint returns 200
- One functional endpoint test (`/api/v1/screen`)

5. Incident-mode communication
- Report impact + ETA + rollback state first.
- Avoid customer-facing phrasing like "just cold start" without SLO context and mitigation.

## Immediate Next Steps (operational)
1. Keep Yahoo-only provider path until a validated fallback token and contract are in place.
2. Add deployment pipeline stage that extracts bundle URL and greps baked API origin before promoting.
3. Add automated post-deploy script to fail fast if frontend bundle references localhost.
4. Define Market Insights latency SLO with warmup strategy and readiness gate.

## Appendix - Key Commits
- `58632f3` feat(finnhub): add fallback provider
- `9fc5f89` fix(finnhub): ticker cleanup/logging
- `3adebb6` fix(deploy): remove automatic compose down before up
- `1227c10` fix(deploy): keep yahoo-only provider path and remove compose down
- `9a6a5e5` fix(deploy): allow in-place port reuse and keep yahoo-only pipeline

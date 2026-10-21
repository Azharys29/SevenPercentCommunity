# Alpha Vantage Reference Layer — rollout plan

## Principle

Alpha Vantage is an optional external reference layer. It must not replace SPC's
internal calculation or become a prerequisite for the existing pipeline.

- SPC Technical Score and signals remain internally calculated.
- External prices are used for cross-checking only until coverage and agreement
  rules have been validated.
- Fundamental, news/sentiment, and macro fields remain unavailable unless the
  relevant endpoint, symbol/region, plan entitlement, and returned data pass checks.
- Missing, stale, malformed, rate-limited, or unsupported external data must never
  be converted into a zero or a negative signal.
- Every usable external value should carry provider, endpoint, observed/source date,
  fetched timestamp, and validation status.
- Never expose the API key in frontend code, static JSON, logs, or commits.

## Phase 1 — low-volume diagnostic

Run the manually triggered GitHub Actions workflow **Alpha Vantage Reference Check**.
It uses one SYMBOL_SEARCH request and tests TIME_SERIES_DAILY compact responses for
BBCA, BBRI, ANTM, MEDC, and PTBA both without a suffix and with the .JK suffix (11
requests total). This distinguishes symbol-format issues from endpoint/entitlement
issues. It writes only sanitized metadata to
data/alpha-vantage-reference-status.json.

The check is deliberately isolated from existing screeners and market-analysis
workflows. A response from one symbol does not establish support for every IDX
ticker. Any notice/error means endpoint access or symbol support remains
unconfirmed and must be investigated before integration.

## Phase 2 — coverage and entitlement audit

Before enabling a data family, establish:
1. Whether IDX tickers are supported and how the symbol is formatted.
2. Whether the specific endpoint is available under the account's plan.
3. Whether the response includes sufficient valid observations.
4. Request cost per run and daily quota headroom.
5. Timestamp/freshness and comparison rules against SPC's current source.
6. Applicable provider terms and permitted redistribution/display.

The first check intentionally does not call premium-oriented endpoints or test all
universe tickers, and it does not alter any existing data or calculations.

## Phase 3 — separate reference artifacts

Only after Phase 2 succeeds, add a dedicated, sanitized JSON artifact for each
reference family as appropriate:
- Price cross-check → Stock Detail and Screener.
- Fundamental reference → Value Gap and Dividend Intelligence.
- News/sentiment → Market Intelligence and AI Research.
- Macro reference → Sector Rotation and Commodity Play.

Each artifact should distinguish available, unavailable, not_checked, stale, and
invalid states; include source, endpoint, source_date, fetched_at_utc, and validation
notes; and preserve the last known good value without representing it as freshly
updated. External references do not modify SPC's internal scores unless a separately
reviewed specification explicitly says so.

## Operational notes

- The diagnostic workflow can be run manually and runs when its own diagnostic script/workflow changes; it does not add calls to the existing hourly screener pipeline.
- Keep ALPHA_VANTAGE_API_KEY in GitHub Actions repository secrets.
- The diagnostic report does not store raw API payloads or the secret.

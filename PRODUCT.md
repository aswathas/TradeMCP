# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: plain static HTML, CSS and vanilla JavaScript with no build step and no runtime
dependencies. The user left the stack to me. Reason: the page's content is a generated artefact
(`showcase/SPEC.md` and `showcase/DEMO.md` are produced from the live server), so it is static by
nature; a static folder opens in a browser with no install, deploys to any static host, and can be
handed to a person as a zip and still work in five years. A framework would add an npm install and a
build step without buying anything, because there is no state, no routing and no data fetching.

## Users

Two audiences on one page, in this order.

1. **Developers and AI-agent builders evaluating an MCP to adopt.** Their job is to decide whether
   this server is worth wiring into their agent, then wire it in. They need the tool list, the data
   sources, the install snippet, and above all proof that the thing returns real Indian market data
   rather than a plausible-looking stub.
2. **Indian retail traders and investors.** Their job is to judge whether the numbers are
   trustworthy and useful before they act on them. They need the metric catalogue, the ratio
   definitions, and evidence the figures reconcile.

The page has to work for both without splitting into two sites. The proof of working serves the
first audience; the metric catalogue serves the second.

## Product Purpose

TradeMCP is a free Model Context Protocol server for Indian equities (NSE and BSE). It gives an AI
agent live quotes, price history, 57 technical indicators, 54 fundamental ratios, financial
statements, a stock screener and portfolio analytics.

The page exists to convince a visitor that this works, and then get them to install it. Success is
a visitor reading live captured output, understanding what the server can show, and copying the
MCP client configuration into their own editor. The page is not a product demo in the sense of
pretending to be a trading terminal; it is proof plus an install path.

## Positioning

The mechanism that distinguishes this from a neighbouring product is that **every ratio is computed
locally from raw statement lines rather than copied off a screen**. The raw lines come from Yahoo's
fundamentals-timeseries endpoint, symbol identity comes from NSE's static listings, and the
India-specific ratios come from Screener.in. Because the arithmetic is ours, the figures reconcile
with each other: DuPont ROE reproduces computed ROE, and a Yahoo-derived ROE lands within a fraction
of a percent of Screener.in's independently stated figure.

Two supporting claims a competitor could not truthfully copy without rebuilding it: the server needs
**no API key and no account on any of its three data sources**, and it depends on **two runtime
packages** (`mcp` and `httpx`), with no pandas, no numpy and no scraping framework.

## Operating Context

- The server speaks MCP over stdio and is launched as a subprocess by the client's MCP runtime.
- Clients in active use are Claude Desktop, MiniMax Code, Cursor and VS Code.
- Install is a virtual environment plus `pip install -e .`, then a JSON block in the client's config
  file. The npm package is written and tested but not yet published, so `npx -y @aswathas/trademcp`
  does not resolve yet; the source path is the one that works today.
- Market data is delayed, not tick. Prices update on the exchange day; fundamentals update
  quarterly.
- Responses are cached on disk with per-type TTLs, so repeat screener and quote calls stay off the
  free endpoints.
- A cold NIFTY 500 fundamentals scan takes roughly 30 to 60 seconds; a NIFTY 100 scan takes about 9.

## Capabilities and Constraints

**Confirmed capabilities.** 14 tools. 57 technical indicators. 54 fundamental ratios across six
groups. 18 candlestick patterns. 5 pivot point styles. 15 Indian indices in the default index
snapshot. 3 free data sources. 2 runtime dependencies. 64 tool parameters, 11 of them required.
The screener's `min_pe` is a floor (P/E at or above it) and `max_pe` a ceiling (P/E at or below
it), matching every other `min_`/`max_` parameter.

**Confirmed constraints.**
- Prices are delayed. This is a research tool, not an order-routing system.
- No intraday fundamental data; the screener reflects the last reported period.
- Banks and financials have no current-asset split, so the current ratio is legitimately blank for
  them rather than failing.
- ROCE is computed here as EBIT divided by invested capital. Screener.in uses its own capital base,
  so the two figures differ slightly. Both are shown separately and never merged.
- Screener.in is a scraped source. If its markup changes, that section degrades to fewer fields and
  the rest of the server keeps working.
- The free endpoints rate-limit. Requests are retried with backoff and cached.

**Published.** The page is live at https://aswathas.github.io/TradeMCP/. It is static, so it
serves a saved snapshot of the server's own output and labels itself SNAPSHOT on screen; the
local server (`scripts/serve_showcase.py`) is what makes it live.

## Brand Commitments

- **Name:** TradeMCP.
- **Voice:** plain, specific, unembellished. The product's own behaviour is the proof, so the page
  quotes real output rather than describing capability in the abstract.
- **Free is a commitment, not a feature.** The MIT licence, the no-key promise and the two
  dependencies are stated on the page, not buried.
- **Indian market focus is the identity.** NSE and BSE, crore and lakh units, Indian indices,
  ISIN, promoter and FII/DII holding, and India-specific ratios such as ROCE are the subject, not
  localisation applied to a global product.
- The user shared a reference for a rigorous structured design prompt, with sections for goal,
  roles, principles, inputs, outputs, verification, delivery and caveats. The design plan follows
  that structure.

## Evidence on Hand

Real, verified, and reproducible.

- `showcase/SPEC.md` — generated from the running server by `scripts/make_showcase_docs.py`. Tool
  reference, parameter tables, metric counts, data-source table, configuration table.
- `showcase/DEMO.md` — generated by the same script from live calls. 14 of 14 tool calls succeeded.
- `README.md` — install, client configuration, tool reference, limitations.
- `tests/` — 109 offline unit tests covering indicator maths, ratio derivation, symbol matching,
  formatting and the tool surface.
- `scripts/verify_all_tools.py` — calls every tool against live data.
- `scripts/smoke_stdio.py` — launches the server as a subprocess and talks to it with a real MCP
  client session. Server reports `trademcp v0.1.0` and advertises 14 tools.
- `evals/evaluation.xml` — 10 evaluation questions with verified answers.

**Absences that must not be fabricated.** No testimonials. No user or download counts. No
star-count or "trusted by" claims. No latency claims beyond the measured figures above. No
comparison against named commercial products.

## Product Principles

1. **Show the real output, never a description of it.** A visitor should be able to see a number
   the server actually produced on the day they looked, not a claim that it can produce numbers.
2. **Free means free.** Every claim on the page about cost, keys and dependencies is checkable
   against the source in the same repository.
3. **One page, two readers.** The developer and the trader each find their evidence without
   either audience being asked to wade through the other's material.
4. **Derived, not scraped.** Ratios are computed and reconcilable, and the page says which numbers
   come from where.
5. **Say what is missing.** Delayed prices, quarterly fundamentals, the blank current ratio for
   banks and the screener-source caveat are stated plainly. A showcase that hides its limits is
   selling something other than this server.

## Accessibility & Inclusion

- Full keyboard operation, with visible focus on every interactive element.
- Text contrast meeting WCAG AA against every background the page uses, in both light and dark
  rendering.
- Motion limited to a small number of purposeful transitions, and disabled under
  `prefers-reduced-motion`.
- Every chart or sparkline carries a text equivalent, so no information exists only in a graphic.
- The page remains usable at 320 CSS pixels wide, since a large share of Indian market traffic is
  mobile.

RESEARCH NOTE · MOTION STUDIO PROMPT · TRADEMCP SHOWCASE
# TradeMCP — Manga HUD direction

TradeMCP · direction seed `fdbf62f1` · comp `manga-hud-a.webp` · 15 regions measured (1 texture, 2 plates, 12 text)
Live page: `showcase/site/` · server: `scripts/serve_showcase.py`

<prompt>
<goal>
Turn {{TOPIC}} into a finished {{SECONDS}}-second motion film for {{AUDIENCE}} that mixes a real 3D world with designed 2D motion. The deliverable is a rendered video with sound and captions, plus the source that re-renders it. A plan, a moodboard or a still frame is not the deliverable.

For TradeMCP the topic is a free Model Context Protocol server for Indian equities, and the deliverable is a one-page showcase that a visitor can read in ninety seconds and install in ten. The page must be proof, not marketing: every number on it is fetched from the server that is being sold.
</goal>

<roles>
Two models, one film.
- Claude Opus 5.5 is the director and editor: brief, script, look, timeline, sound, captions, review. It owns the final cut.
- Gemini 4 Argon is the 3D department: scenes, cameras, light and spatial moves in Three.js, or in Blender through Blender MCP. It hands over code and frame sequences, never the cut.
When the brief is thin, Opus makes the call, logs it in one line in DECISIONS.md and keeps moving.
</roles>

<principles>
Work the way George Kenwright, Creative Producer at Google DeepMind, describes making films with AI:
- A tool is a tool. It has no merit until you use it. Prototype before you debate. [Cinemafile]
- Make the new form, not a copy of the old one. Electric guitars gave new sounds, not fake acoustic ones. Do what only code and 3D can do. [Cinemafile]
- Tell the human story behind the tech. A person and a problem come before the model. [Cinemafile]
- Mix generated with captured. Ground generated imagery in real captured space: photography, footage, real screens. [LinkedIn]
- The page is the product demo. If the screener is a mock, the server is a mock. Ship the real tool output or ship nothing.
</principles>

<inputs>
Topic: A free MCP server that gives an AI agent live NSE and BSE quotes, 57 technical indicators, 54 fundamental ratios and a stock screener, over plain MCP stdio, with no API key and no account.
Audience, and what they already believe: {{AUDIENCE}} — engineers who have already tried paid market-data APIs, believe every free source is a scraped toy, and have never seen Indian equities tooling that speaks to their agent natively.
After watching they can: paste one config block into their MCP client, call one tool, and see a real NIFTY 50 screen come back.
Length: {{SECONDS}} s (30-90)
Format: 16:9 master, then 9:16
Brand and references: ./brand, ./refs, ./captures
</inputs>

<split>
- Argon: 3D scenes, camera paths, physics, light, spatial layout, procedural geometry. Output: Three.js modules or .blend files plus PNG sequences at the master frame rate.
- Opus: story, type, 2D graphics, transitions, timing, sound, composition in Remotion, verification.
- Hand-off: scene id, frames, fps, resolution, camera keyframes as JSON, alpha or not.
- Opus never redraws Argon's 3D by hand. Argon never sets timing. Timing lives in one TIMELINE.
</split>

<story_arc>
- Hook (0-15%): the problem, in the engineer's words. "My agent cannot see NSE." The word LIVE hits as a brushed impact burst.
- Setup (15-35%): the world the tool lives in. A manga page: panel grid, screentone, ink. The HUD panel wakes up and pulls the first quote.
- Inside (35-75%): the machine reveals how it works, one element per beat. The tape scrolls. The chart draws. The indicators land. The screener filters fifty real NIFTY constituents down to eleven.
- Change (75-100%): back to the person. The page is still there, still live. Copy the config, install, done.
</story_arc>

<visual_system>
- Pull palette, type and spacing from ./brand into tokens before drawing anything.
- 3D and 2D share one palette and one light direction.
- Warm neutral ground, one accent, two typefaces, one grid.
- Measured from comp `manga-hud-a.webp` (15 regions):

  | Token | Value | Share | Use |
  |---|---|---|---|
  | `--paper` | `#f4f5f5` | 76% | Page ground, panel fill |
  | `--ink` | `#100f10` | 13% | Rule, type, panel edge |
  | `--tone` | `#b7b8ba` | 6% | Screentone plate, hairlines |
  | `--cyan-bright` | `#c1f1f2` | 3% | Accent, HUD fill, aura |
  | `--ink-3` | `#79797a` | 3% | Caption, unit, meta |
  | `--cyan` | `#0d7f95` | — | Links, focus ring, gauge fill |
  | `--verm` | `#c53a20` | — | SFX, sell zone, down tick |
  | `--green` | `#14724a` | — | Buy zone, up tick |

  Night theme remaps the same roles to `#15161a` / `#f1f2f3` / `#3d3e45` / `#10333b` / `#63d6e8`. One click. No mid-tone drift.
- Type — four voices, one grid:

  | Voice | Family | Use |
  |---|---|---|
  | Brush | Kaushan Script | Wordmark, panel hand-lettering |
  | Shout | Permanent Marker | SFX, impact bursts, badge type |
  | UI | Saira Condensed | Labels, nav, table headers |
  | Body | Saira | Paragraphs, tool descriptions |
  | Data | Martian Mono | Every number, ticker, timestamp |

- Screentone is a 45° dot lattice, not a gradient. Three densities — light (alpha 70), mid (110), dark (170) — generated as pure-stdlib RGBA PNG so the plates are deterministic and diffable.
- Panel edge is a hard 3px ink rule with a hard offset shadow. Never a soft shadow, never a radius above 18px on a body panel.
- Rule: green is up, red is down. Always paired with ▲ or ▼ so nothing depends on colour alone.
- Banned: neon glow, stock 3D blobs, chrome robots, floating particles, fake metrics.
</visual_system>

<motion_language>
- The camera moves only to reveal. One move per shot.
- Transitions carry: a 2D shape becomes a 3D object, or the camera flies through the scene into a 2D card.
- Ease out on entrances. Hold the key idea still while text is read.
- The manga vocabulary is drawn in code, never licensed. Focus lines, ink slashes, charge bars, impact bursts and aura rings are all original CSS.
- Focus lines: radial speed lines bloom behind a hovered panel over 180ms, then retract. Never loop while idle.
- Ink slash: a 3px diagonal rule sweeps left to right in 420ms, `cubic-bezier(.16,.84,.44,1)`. It divides, it does not decorate.
- Charge bar: a segmented energy bar fills left to right on data arrival, 60ms per segment, with a 2px ink cap. A full bar means a full response.
- Impact burst: the word LIVE carries a hard 4px ink offset and a vermilion drop shadow. It appears once, at the hook, and never pulses again.
- Aura ring: a single cyan ring expands from the figure's centre and fades over 1.2s when the panel it belongs to updates. One ring per update.
- 3D tilt: pointer-driven, ±6° max, `transform-style: preserve-3d`, planes at `translateZ`. It settles on leave. It is never on scroll.
- Scroll dolly: one continuous `--dolly` variable drives hero depth from 1.0 to 0.92. The page is a printed sheet that recedes as you read into it.
- Holo ring: the LIVE badge carries a slow 12s rotation. It is the only infinite animation on the page.
- Ticker tape: continuous marquee, 60s loop, pauses on hover so a number can actually be read.
</motion_language>

<render_contract>
- Every frame is a pure function of its frame number. Seeded randomness only.
- Argon's Three.js scenes take the frame as input. No clock time.
- Remotion composes 3D sequences and 2D layers. ffmpeg encodes H.264, crf 16, yuv420p.
- The live page obeys the same contract. Every number on screen is fetched from `/api/*`, which is backed by `mcp.call_tool` against the real server. When the API is absent the page falls back to `data/snapshot.json`, which was also written by those tools. There is no third-party relay and no hard-coded price.
</render_contract>

<workflow>
1. One-sentence idea and the viewer outcome.
2. Script and storyboard (Opus).
3. Tokens and 2D style frames, one of them a 3D frame from Argon.
4. Argon builds every 3D scene to the hand-off spec.
5. Animatic in Remotion with 3D placeholders.
6. Final 3D renders swapped in.
7. Sound and captions. 8. Verification. 9. Export.
</workflow>

<verification>
Run these, do not just claim them.
- Render one frame twice and diff it: identical.
- At every cut, 3D and 2D light match in the composite.
- Contact sheet at 1 fps. Read every line at 390 px wide.
- Match it muted, then listen audio-only.
- Every number on screen has a source in SOURCES.md.
- The TradeMCP pass adds four more: the screener returns 50 of 50 named constituents from the server; the chart's RSI matches the server's RSI for the same symbol and window, or the page says which window it used; the P/E on the hero and the P/E in the screener column come from different endpoints and are labelled as such; and the page loads with the network tab offline and still shows numbers, from the snapshot.
</verification>

<delivery>
out/master_16x9.mp4, out/cut_9x16.mp4, captions.srt, contact.png, scenes/ (Argon), source, and a README that lists only what was tested.
For the web build the same contract reads: `showcase/site/` is a static folder with no build step and no package dependencies. `scripts/serve_showcase.py` adds the live `/api/*` layer for local runs. `showcase/PROMPT.md` is this file. `showcase/SPEC.md` and `showcase/DEMO.md` are the written brief and the transcript of fourteen live tool calls.
</delivery>

<caution>
Do not stop for approval on creative calls. Stop only for irreversible actions, and then only for one line: what changed, in plain words, for an ambiguity that changes the result.

For TradeMCP the irreversible actions are: publishing the page to a public URL, and registering the MCP server in a client config. Both wait. Everything else is reversible and keeps moving.
</caution>
</prompt>

---

## What this prompt produced

A single static page at `showcase/site/` — `index.html`, `styles.css`, `app.js`, `live.js`, `screener.js`, `cursor.js`, `call.js`, nine assets, two JSON snapshots.

**Live, not mocked.** `scripts/serve_showcase.py` exposes `/api/quote`, `/api/history`, `/api/fundamentals`, `/api/indicators` and `/api/tape`, each backed by `mcp.call_tool` against the TradeMCP server on a background asyncio loop. The page falls back to `data/snapshot.json` when those endpoints are absent, so it still works on a static host and offline. That fallback exists because Yahoo sends no `Access-Control-Allow-Origin` header — a browser cannot call it directly, and every public CORS relay tried returned 401, 520 or 522.

**The indicators are recomputed in the browser** from the server's own candles — RSI, MACD, Stochastic, ATR, SMA20, SMA50, Bollinger %B, VWAP, OBV, volume ratio — so the page can state its provenance instead of claiming a number it was handed. The server's own `get_technical_indicators` is shown alongside, and the two differ because they read different windows; the page says which window it used.

**The screener is the real one.** Fifty NIFTY 50 constituents come from `screen_stocks` and `compare_stocks`, filtered client-side by six preset tabs, a name search and ten range filters, with the equivalent `trademcp_screen_stocks` call printed underneath. Server-side filtering stays authoritative; the page re-applies the same predicates.

**Three original manga figures** — developer, trader, analyst — generated as original art and cut out over the page. No licensed character from any existing series appears anywhere.

**Fonts** load from Google Fonts; the page falls back to system stacks without them. The plate textures are deterministic PNGs, not gradients, so the manga look survives a screenshot.

**The call.** A section between the metrics and the mechanism shows one MCP handshake as it happens. The agent stands on the left, the market on the right, and a single packet crosses the wire, waits, and comes back with the answer — a diagram in CSS 3D, with no library and nothing fetched from a CDN. Beside it are the two halves of the handshake verbatim: the JSON-RPC request (`tools/call` → `trademcp_get_quote`) and the JSON the server returned, plus the measured round trip and where the answer came from. The answer is real: the panel calls `/api/quote`, which the showcase server turns into one MCP `tools/call` over stdio against the real server. With no server to ask, the panel falls back to the bundled snapshot and says so in the source line instead of pretending the number is live. The flight is theatre on a fixed beat; the clock under it is `performance.now()` around the fetch.

**The touch.** The cursor is a fountain-pen nib drawn in `cursor.js` and handed the pointer. It transfigures what it touches — a panel it passes over softens into an organic seam, lifts a hair off the page and takes a cyan outline. That part is pure CSS `:hover`, so it still works where pointer events never reach the page; the script only adds the nib and the angle. The native arrow is handed over on the first real pointer move and given back the moment the pointer leaves the window, so a page where the script never runs still has a working cursor. `?cursor=system` brings the native cursor back on demand, and touch devices, reduced motion and still capture never lose it.

**The chart ignites.** The price line on the live board is not a static drawing. A front runs along it, and the ink behind the front is drawn while ahead of the front there is nothing. Which way the front runs depends on what happened. The first time the board comes into view the chart is born: the front starts at the oldest close and runs right, so the series is written in reading order, with a cyan ember and a short tail riding the head. A refresh is the opposite. The newest close, the current price, ignites first and the heat runs back through the history, so the chart never re-writes itself from the left edge. The front is an SVG dash, and every path that carries it declares `pathLength="1"`, so the dash travels from one to zero or from minus one to zero without measuring a pixel; the area fill and the Bollinger band are revealed by a mask stroked along the same path, so the edge of the reveal follows the line instead of cutting a vertical. The chart is never half drawn in plain sight: the blank state is only used while the board is completely off the page, the base CSS is the whole chart, and reduced motion keeps the data arriving without the travel.

## Measured tokens

From `comp-spec --grid` on `manga-hud-a.webp`: `#f4f5f5` 76%, `#100f10` 13%, `#b7b8ba` 6%, `#c1f1f2` 3%, `#79797a` 3%. Type was matched region by region with `font-match`; the five families above won on fit, not on taste.

## Craft notes

Three fixes came out of the build that are worth keeping in any version of this prompt.

**The page must be able to scroll.** `scroll-behavior: smooth` on the root, combined with a sticky masthead and a stack of infinite CSS animations, capped the scrollable range at roughly 40px in Chromium. Every nav link and every anchor looked broken. The root now scrolls instantly (`scroll-behavior: auto`, `overflow-anchor: none`) and the anchors are instant jumps. Smooth scrolling is not worth a broken page.

**The canvas needs an explicit colour.** The root element must paint its own background. Without it the canvas fell back to a tinted default and the page edge read blue in both themes, which broke the paper. `html { background-color: var(--paper) }` pins it.

**Accessibility overrides the measured palette.** The comp measured `--ink-3` at `#77767a` and `--verm` at `#c53a20`. Both fail WCAG AA at the sizes this page uses them. They ship as `#636366` and `#b8361d`: the same roles, the same hue family, enough contrast to read. Nothing functional is set below 11px, and no body text below 12px.

## Open

- The page is **not published**. A static host would lose the `/api/*` layer and fall back to the snapshot.
- The MCP server is **not registered** in any client config.
- The 3D tilt, scroll dolly and aura rings were verified in-browser with zero console errors; they have not been checked in Safari or Firefox, and `prefers-reduced-motion` collapses them to near-zero duration but does not remove the transforms.
- The call's CSS 3D diagram has been verified in headless Chrome — the slab planes, the wire and the packet are real — but not in Safari or Firefox, and the packet flight has not been watched at 60fps on real hardware.
- The custom cursor has been verified in Chrome only. It hides the native arrow by design, so it is worth a look on a trackpad and on a touch laptop before the page is published.

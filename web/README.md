# FlightCast — Next.js Dashboard

Path B of the migration: a Next.js + React port of the Streamlit dashboard,
delivering the **VESPER-pattern guided tour** (spotlight overlay + popover
positioned next to the active element) for the pitch.

The Streamlit dashboard at port 8501 stays running in parallel — both
talk to the same MariaDB through the FastAPI thin layer at port 8000.

---

## What's already done

- `web/` Next.js 14 (App Router) + TypeScript + Tailwind scaffold
- Design tokens ported from `src/flightcast/ui/style.py` to
  `tailwind.config.ts` + `globals.css` (palette, fonts, gradients, pills, stat cards)
- VESPER tour engine: direct port of `GuidedTour.js` →
  `web/src/components/tour/GuidedTour.tsx` with the **9 FlightCast tour steps**
  in `TOUR_STEPS.ts`. Tour CSS at `tour.css` (spotlight punch-through,
  popover with directional caret, 3 placements: bottom/right/left)
- API client at `src/lib/api.ts` typed against `src/lib/types.ts`
- FastAPI extended at `src/flightcast/api/main.py` with the missing
  `/sampled-routes`, `/forecasts/all`, `/coverage/series`, `/winkler` endpoints
- `docker-compose.yml` runs 3 services: `db` + `api` (port 8000) + `web`
  (port 3000) + the existing `app` (Streamlit, port 8501)
- **Time Travel page** complete — use this as the reference for porting the
  other 3 pages

## What's left (vibe-code these with AI)

| Page | Status | Reference (Streamlit) |
|---|---|---|
| Time Travel | DONE | `src/flightcast/ui/pages/02_time_travel.py` |
| Forecast Explorer | STUB | `src/flightcast/ui/pages/01_forecast.py` |
| Coverage Drift | PARTIAL (cards done, charts TODO) | `src/flightcast/ui/pages/03_coverage_drift.py` |
| How It Works | STRUCTURE DONE (5 SQL accordions TODO) | `src/flightcast/ui/pages/04_about.py` |

Each stub page has a docstring at the top with:
1. The Streamlit file to port from
2. The data hooks already wired (just `useQuery({ queryFn: api.X })`)
3. A copy-pasteable AI prompt for Cursor / Copilot

---

## Run it

```bash
# From repo root
docker compose up -d --build

# Endpoints
#   http://localhost:8501  — Streamlit dashboard (existing)
#   http://localhost:8000  — FastAPI thin layer
#   http://localhost:3000  — Next.js dashboard (this app)
#
# Smoke tests
curl http://localhost:8000/healthz
curl http://localhost:8000/batches | jq length          # → 6
curl http://localhost:8000/coverage | jq '.[].mean_coverage'
```

For local dev (without Docker rebuild on every change):

```bash
cd web
npm install --legacy-peer-deps
NEXT_PUBLIC_API_BASE=http://localhost:8000 \
  API_BASE_INTERNAL=http://localhost:8000 \
  npm run dev
```

---

## Architecture

```
Browser
   │
   │  http://localhost:3000
   ▼
┌──────────────────────────────┐
│ web (Next.js, port 3000)     │
│  - 4 pages (App Router)      │
│  - VESPER-pattern tour       │
│  - react-plotly.js charts    │
│  - TanStack Query data flow  │
└──────────────────────────────┘
   │
   │  /api/* rewritten to api:8000 (next.config.js rewrites)
   ▼
┌──────────────────────────────┐
│ api (FastAPI, port 8000)     │
│  - reuses every flightcast.* │
│    Python module unchanged   │
│  - 8 read-only endpoints     │
└──────────────────────────────┘
   │
   │  mariadb driver
   ▼
┌──────────────────────────────┐
│ db (MariaDB 11.8, port 3306) │
│  - same schema, same data    │
│  - same FOR SYSTEM_TIME      │
│    queries Streamlit uses    │
└──────────────────────────────┘
```

The API layer **does not write any new SQL**. Every endpoint calls an
existing Python function from `flightcast.db.repositories`,
`flightcast.temporal_queries`, or `flightcast.audit`. This guarantees the
React dashboard's numbers are bit-identical to Streamlit's.

---

## Tour anchors — how the spotlight finds the right element

Each tour step in `TOUR_STEPS.ts` declares a CSS selector like
`.tour-anchor-slider`. Pages add that class to a wrapping `<div>`:

```tsx
<div className="tour-anchor-slider fc-audit-card">
  ...
</div>
```

The tour engine calls `document.querySelector(".tour-anchor-slider")`,
`scrollIntoView({block: 'center'})`, then `getBoundingClientRect()` to
position the popover. If the selector returns no match, the engine falls
back to screen-center and shows the "element not visible" hint instead of
crashing — this is the soft-fail behavior from `pitch-tour-template.md` §4.5.

**The 9 anchors used by the tour:**

| Step | Page | Anchor class |
|---|---|---|
| 1 | /time-travel | `.tour-anchor-audit-gap` |
| 2 | /time-travel | `.tour-anchor-callout` |
| 3 | /time-travel | `.tour-anchor-slider` |
| 4 | /time-travel | `.tour-anchor-stats` |
| 5 | /time-travel | `.tour-anchor-forecast` |
| 6 | /coverage-drift | `.tour-anchor-drift-chart` |
| 7 | /how-it-works | `.tour-anchor-architecture` |
| 8 | /how-it-works | `.tour-anchor-comparison` |
| 9 | /how-it-works | `.tour-anchor-close` |

If you rename or delete a target element, update the anchor class first
to keep the tour working.

---

## AI-prompt cheat sheet (paste these into Cursor / Copilot)

**Forecast Explorer (the easiest):**
> Implement Forecast Explorer page mirroring `src/flightcast/ui/pages/01_forecast.py`. Use `api.forecastsAll(route_id)` to fetch every historical batch. Render one Plotly trace per `forecast_run_id`, with `model_version` in the legend. Use violet for predicted line, lighter violet shaded fill for the conformal interval. Reference `web/src/app/time-travel/page.tsx` for query/state patterns.

**Coverage Drift (medium effort):**
> Finish Coverage Drift page mirroring `src/flightcast/ui/pages/03_coverage_drift.py`. The per-batch coverage cards are already implemented. Add: (1) a Winkler interval score chart from `api.winkler()`, (2) a rolling coverage chart from `api.coverageSeries()`, (3) a prediction-diff chart from `api.diff()`. Use Plotly. Match the Streamlit page's section headers and captions verbatim.

**How It Works (just the SQL accordions):**
> Add the remaining 4 hero SQL accordions to `/how-it-works`. Reference Streamlit lines 125-280 of `src/flightcast/ui/pages/04_about.py`. Each accordion uses `<details><summary>` with the SQL in a `<pre><code>` block, monospace, blue text on dark background.

---

## Submission notes

For the hackathon submission, point judges at **both** dashboards:

- **`http://localhost:3000` — primary demo surface.** This is the polished
  React build with the VESPER tour. Pitch around this.
- **`http://localhost:8501` — fallback / parity check.** If anything breaks
  in the React build during the live demo, judges can verify the same
  numbers from the Streamlit dashboard.

The architecture diagram and all hero documents (`Elegant.md`,
`JUDGES_TESTING_GUIDE.md`) reference both surfaces. You don't need to
delete the Streamlit code.

---

## Why the iframe-overlay approach was rejected

The earlier "Path A" proposal would have built the spotlight overlay in
Streamlit using `streamlit.components.v1.html()` + iframe message-bus.
That approach delivers ~95% of VESPER's UX but with edge-case fragility
under strict browsers and Streamlit version upgrades. The Next.js port
delivers 100% of the pattern with no platform-specific hacks, at the
cost of a multi-day rebuild — which is the trade-off accepted here.

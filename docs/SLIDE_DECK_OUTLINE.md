# Slide Deck Outline — FlightCast

**Built by:** Low Yan Cheng (TP070056), APU Malaysia
**Submission:** MariaDB Hackathon Malaysia 2026 · Innovation Track
**Recommended length:** 12 main slides + 3 optional backup slides
**Spoken length:** ~5 minutes (for live pitch) or self-skim in ~60 seconds
**Aspect ratio:** 16:9 widescreen
**Aesthetic:** dark background (`#0A0F1F`), white text, violet (`#8B5CF6`) and amber (`#F59E0B`) accents — match the dashboard

---

## Why 12 slides?

- **8–10** is too few to support both problem statement and live demo screenshots.
- **15+** loses judges who skim portfolios.
- **12** maps cleanly onto a 5-minute pitch (≈25 seconds per slide) and onto the four-act story arc:
  - **Act 1 — Problem** (slides 1–3)
  - **Act 2 — Solution / Demo** (slides 4–7)
  - **Act 3 — Proof / Differentiation** (slides 8–10)
  - **Act 4 — Open infra / Close** (slides 11–12)

---

## Design rules

- **One core idea per slide.** If you cannot describe a slide in one sentence, split it.
- **Big numbers, short labels.** "92.1%" with subline "calibrated" beats a paragraph.
- **One screenshot per content slide max.** Two screenshots per slide is too dense.
- **Match the dashboard's font stack:** Inter / SF Pro / system-ui for body, same for headings.
- **No raw SQL on slides** — explain in English, save SQL for the demo video itself.
- **Footer on every slide:** small "FlightCast · MariaDB Hackathon MY 2026" + slide number, bottom-right.

---

## How to capture screenshots

For each slide that needs a screenshot, run the dashboard at `http://localhost:3000` and:

1. Navigate to the page and state described under "Screenshot to capture" below.
2. Press **F11** for fullscreen browser (no browser chrome distractions).
3. Use **Snipping Tool** (Win+Shift+S) to capture only the relevant card or section, not the entire page.
4. Save as PNG, name it `slide-NN-name.png` so the deck file order matches.

---

## The 12 main slides

### Slide 1 — Title

**Headline:** FlightCast
**Sub-headline:** Self-auditing ML predictions on MariaDB temporal tables.
**Visual:** large airplane icon (the same one used in the sidebar), or the FlightCast logo if you have one. Center-aligned.
**Footer text (small):** Low Yan Cheng (TP070056) · APU Malaysia · Innovation Track
**Spoken (~15 sec):**
> "FlightCast — self-auditing machine learning predictions, built on MariaDB temporal tables. By Low Yan Cheng, APU Malaysia, for the Innovation Track."

---

### Slide 2 — The Problem

**Headline:** What did your AI predict last month?
**Sub-headline:** Most ML systems can't answer that question.
**Visual:** stylised illustration or stock photo of an airline operations centre — OR just dark slide with the headline in massive type.
**Body bullets (kept short):**
- AI retrains every week.
- Last quarter's predictions get **overwritten**.
- Auditors, regulators, post-mortems → **cannot reconstruct the past**.
- Industry workaround: bolt on MLflow + Weights & Biases + custom audit log = fragile and expensive.

**Spoken (~30 sec):**
> "Production AI retrains every week. Each retrain overwrites the previous predictions. So three months later, when an auditor asks 'what did your model predict on January 15?', most companies cannot answer. The industry workaround is to bolt on three external services. FlightCast solves it inside the database."

---

### Slide 3 — The Insight

**Headline:** Five SQL keywords only MariaDB has.
**Sub-headline:** `FOR SYSTEM_TIME AS OF`
**Visual:** a screenshot of the violet "Ask MariaDB" hero callout from the Time Travel page, OR a clean code chip on a dark background showing:
```sql
SELECT * FROM forecasts FOR SYSTEM_TIME AS OF '2026-01-15';
```

**Comparison row (small text):**
| Database | Native support? |
|---|---|
| MariaDB 11.8 | ✅ ships natively |
| MySQL | ❌ syntax error |
| PostgreSQL | ⚠️ third-party extension |
| SQLite | ❌ no equivalent |

**Spoken (~30 sec):**
> "MariaDB has a feature called system-versioned tables. Five English-like words — FOR SYSTEM TIME AS OF a date — let you query any past state of any row. MySQL gives a syntax error. PostgreSQL needs an add-on. SQLite has nothing. MariaDB is the only mainstream database that ships this out of the box."

---

### Slide 4 — Solution: Database-Native ML Audit

**Headline:** The audit trail IS the database.
**Sub-headline:** Every prediction the model ever made, queryable forever.
**Visual:** screenshot of the **FlightCast page header** with the four status pills ("Live", "MariaDB 11.8", "MAPIE conformal · 90% coverage", "6 model versions indexed").
**Body bullets:**
- No MLflow tracking server.
- No Weights & Biases dashboards.
- No application-side audit log.
- Just **MariaDB system-versioned tables** + **MAPIE conformal prediction**.

**Spoken (~25 sec):**
> "The audit trail isn't a service we add later — it's structural. Every prediction is system-versioned at INSERT time. We layer a math result called MAPIE conformal prediction on top to guarantee 90% coverage. Two ideas combined: temporal SQL plus conformal math."

---

### Slide 5 — Demo: Time Travel

**Headline:** Drag the slider. Travel through model versions.
**Sub-headline:** Each tick is a real committed transaction.
**Screenshot to capture:** Time Travel page showing the **"Audit point in time" slider card + the forecast chart below it**. Slider position should be on Run 4 or 5 so the chart shows realistic data. Crop to just these two cards so the deck slide isn't visually cluttered.
**File name:** `slide-05-time-travel.png`

**Body bullets:**
- 6 committed model versions live in MariaDB.
- Slider position = real `ROW_START` timestamp.
- Chart re-queries the database on every drag.

**Spoken (~30 sec):**
> "Drag the slider and the dashboard re-queries the database at that exact micro-second. Six committed model versions, all live, all queryable through one SQL statement. No log replay, no shadow tables, no external service."

---

### Slide 6 — Demo: All-History Rainbow

**Headline:** Six model versions, one SQL query.
**Sub-headline:** `FOR SYSTEM_TIME ALL` returns every version of every row.
**Screenshot to capture:** Forecast Explorer page in **"All history" mode**, with the rainbow chart showing all six bands. Crop to just the chart card. Make sure the chart has finished rendering (six distinct colors visible).
**File name:** `slide-06-rainbow.png`

**Body bullets:**
- One query → 6 versions × 30 days = 180 rows.
- Standard MLOps: 6 separate API calls + Python join.
- Bands stacked tightly = healthy. Bands diverging = drift.

**Spoken (~30 sec):**
> "Six committed model versions, each in a different colour, each with its own confidence band, all on one chart. Behind it: a single MariaDB query. In a normal MLflow setup you would issue six API calls and stitch them together in Python."

---

### Slide 7 — Demo: Drift Caught Live · ⭐ THE PUNCHLINE

**Headline:** Drift caught by ONE SQL query.
**Sub-headline (big numbers):**
- **4 / 6 calibrated · 91.2% coverage** _(blue)_
- **2 / 6 drifted · 58.7% coverage** _(amber)_

**Screenshot to capture:** Coverage Drift page showing the **two big headline tiles side by side** ("4/6 calibrated" vs "2/6 drift"). Crop tightly. Ensure the percentage values are clearly visible.
**File name:** `slide-07-drift.png`

**Body bullets (very short):**
- One `GROUP BY` against `FOR SYSTEM_TIME ALL`.
- 30+ percentage point gap = unmistakable drift signal.
- No MLflow. No tracking server. No data engineer.

**Spoken (~50 sec):**
> "This is the punchline. We trained six batches. The first four use normal noise — the world is calm. Batches five and six simulate a fuel-price shock, with much louder noise. Result: the first four hit 91.2% coverage, dead on target. The last two collapse to 58.7%. That is more than thirty percentage points off. The database itself caught it, with one SQL query, in real time."

---

### Slide 8 — The Math Layer

**Headline:** A guarantee, not a claim.
**Sub-headline:** MAPIE conformal prediction · published 2005, peer-reviewed.
**Visual:** the conformal interval formula, big and clean:
```
[ f̂(x) − q̂₁₋α ,  f̂(x) + q̂₁₋α ]

P( y ∈ C(x) ) ≥ 1 − α
```
You can also screenshot the **Conformal Prediction math section** from `/how-it-works` and crop the formula box.
**File name:** `slide-08-math.png` (if using a screenshot)

**Body bullets:**
- Vovk 2005, Lei 2018 — peer-reviewed coverage theorem.
- Used in finance, insurance, drug trials.
- We didn't invent it; we **applied it on top of MariaDB**.

**Spoken (~30 sec):**
> "The 90% coverage isn't marketing. It's a published theorem from 2005, used by major banks and insurance firms. We didn't invent it. We applied it on top of MariaDB so the math and the audit trail live in the same place."

---

### Slide 9 — Architecture

**Headline:** Five layers. Zero external dependencies.
**Sub-headline:** The audit trail is structural, not bolted on.
**Screenshot to capture:** the **architecture diagram from `/how-it-works`** (the system architecture PNG that's already in the repo at `web/public/architecture.png`). You can drop the PNG straight into the slide.
**File name:** use the existing `architecture.png` as-is.

**Body bullets (small caption):**
- Ingestion → MariaDB → ML pipeline → Query layer → Dashboard.
- **Notably absent:** MLflow, Weights & Biases, DataDog, Evidently.

**Spoken (~25 sec):**
> "Five layers. Notably absent from this diagram: MLflow, Weights and Biases, DataDog, Evidently. The forecasts table is system-versioned at INSERT time, so the audit trail is structural — not a service you bolt on later."

---

### Slide 10 — vs. The Standard MLOps Stack

**Headline:** The moat is the math layer, not the slider.
**Sub-headline:** What FlightCast replaces.
**Screenshot to capture:** the **comparison table from `/how-it-works`** ("What makes FlightCast different from standard MLOps tooling?"). Crop tightly to the 5-row table only.
**File name:** `slide-10-comparison.png`

**Body bullets (optional, only if you don't use the screenshot):**
| What | Standard stack | FlightCast |
|---|---|---|
| Audit substrate | External tracking server | Database-native |
| Versioning latency | Sync gap | Atomic at INSERT |
| Coverage guarantee | Not enforced | MAPIE ≥ 90% |
| Drift detection | Custom dashboards | One SQL query |
| Time-travel SQL | Replay logs | `FOR SYSTEM_TIME` |

**Spoken (~30 sec):**
> "Compared to the standard stack: external tracking server, replaced by atomic INSERT-time versioning. Custom drift dashboards, replaced by one SQL query. Replay infrastructure, replaced by FOR SYSTEM TIME. The moat is the math layer, not the slider."

---

### Slide 11 — Open Infrastructure

**Headline:** MIT-licensed. Fork it. Build on it.
**Sub-headline:** Public infrastructure for the MariaDB ecosystem.
**Visual:** a screenshot of the **Hero SQL Queries section header** from `/how-it-works` ("All five use MariaDB-exclusive syntax. None of these run on MySQL or PostgreSQL.") OR a clean text slide.
**File name:** `slide-11-open.png` (if using a screenshot)

**Body bullets:**
- 5 reusable MariaDB-only SQL queries.
- 3 open issues: per-tier MAPIE recalibration, real-data prototypes, Apache Airflow integration.
- Whitepaper: `Elegant.md` (~6,300 words).

**Spoken (~20 sec):**
> "FlightCast is MIT-licensed. Five reusable MariaDB-only SQL queries. Three open issues for the next contributor. The temporal-tables × conformal-prediction intersection is now public infrastructure for the MariaDB ecosystem."

---

### Slide 12 — Closing & Links

**Headline:** Thank you.
**Sub-headline (your name):** Low Yan Cheng (TP070056) · APU Malaysia
**Body — three rows of links, one per row:**
- 🔗 **Live demo:** github.com/imycc1221/flightcast
- 📦 **Hackathon submission:** github.com/MariaDB-Hackathon-MY-2026/flightcast
- 📄 **Whitepaper:** `Elegant.md` (~6,300 words)

**Optional fourth row:**
- 🎬 **5-min demo video:** [paste your Loom or YouTube URL after recording]

**Spoken (~15 sec):**
> "Thank you for watching. The repo is open, the whitepaper is in the repo, and the live demo runs locally with one Docker command. I'm happy to answer questions."

---

## Optional backup slides (for Q&A only)

These don't appear in the main flow. Have them ready in case judges ask follow-ups.

### Backup A — Synthetic data methodology

**Headline:** "How realistic is the synthetic demand?"
**Body:** log-normal noise, tier-aware sigmas (hub/mid/thin), 50 sampled OpenFlights routes × 730 days = ~36,500 rows of training data. Drift simulation: σ = 0.10 → σ = 0.22, a documented regime-shift recipe.

### Backup B — Performance benchmarks

**Headline:** "Will it scale?"
**Body:** include `docs/benchmark_chart.png` if it exists. Reference the benchmark JSON in the repo. Talk through query latency for `FOR SYSTEM_TIME AS OF` at 1k / 10k / 100k row scales.

### Backup C — The five hero queries

**Headline:** "Show me the actual SQL."
**Body:** screenshot of the five SqlPanel accordions from `/how-it-works`. Each one is MariaDB-only. Use this slide if a judge asks for code-level proof; otherwise skip.

---

## Ordering tips

1. **Build the deck in the order above.** Don't reorder Slide 7 — the drift demo is your strongest moment and earns its emphasis by appearing right after the demo screenshots build up to it.
2. **If you only have 4 minutes:** drop slides 8 and 11 (math + open infra). Keep 1, 2, 3, 4, 5, 6, 7, 9, 10, 12 = 10 slides, ~4:00 spoken.
3. **If you have 7 minutes:** add Backup A right after slide 9 to give judges depth on the experimental design.

## Where to put the screenshots

Save all screenshots in `docs/screenshots/` (the folder already exists in the repo). You can name them:

```
docs/screenshots/
  slide-05-time-travel.png
  slide-06-rainbow.png
  slide-07-drift.png
  slide-08-math.png
  slide-10-comparison.png
  slide-11-open.png
```

If your slide-deck tool stores its own copies (PowerPoint embeds them, Google Slides uploads them), you don't strictly need to commit these to git — but committing them gives reviewers a sneak preview without opening the .pptx file.

---

## Tools that produce a professional deck quickly

If you don't have a preferred slide tool:

- **PowerPoint** (built-in if you have Office) — easiest for Windows; use the **"Berlin" or "Frame" theme** in dark mode.
- **Google Slides** — free; use the **"Coral" or "Material 2"** theme, then change background to dark navy.
- **Pitch.com** — purpose-built for startup decks, free tier; great for hackathons.
- **Marp** (open source, markdown-based) — if you prefer to stay in your text editor; has a "Gaia" dark theme that matches the dashboard.

For consistency with the dashboard, copy these brand colours into your slide template:
- Background: `#0A0F1F`
- Text primary: `#F8FAFC`
- Text secondary: `#94A3B8`
- Violet accent: `#8B5CF6`
- Blue accent: `#60A5FA`
- Amber accent: `#F59E0B`
- Emerald (success): `#34D399`

---

## Final QA checklist before submission

- [ ] Every slide is readable from 2 meters away (no font smaller than 24 pt body, 36 pt headline).
- [ ] Slide numbers in bottom-right.
- [ ] Repo URLs all point to `imycc1221/flightcast` and `MariaDB-Hackathon-MY-2026/flightcast` — never `TP070056/flightcast`.
- [ ] Your name and student ID appear on slides 1 and 12.
- [ ] No "Built with Claude" / no AI attribution anywhere.
- [ ] Killer numbers correct: 91.2 / 58.7 (drift), 7,300 / 24,000 (Winkler).
- [ ] Spell-check pass.
- [ ] Export as PDF for the submission portal (most portals reject .pptx).

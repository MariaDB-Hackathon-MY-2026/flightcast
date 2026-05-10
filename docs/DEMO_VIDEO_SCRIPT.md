# 5-Minute Demo Video Script — FlightCast

**Built by:** Low Yan Cheng (TP070056), APU Malaysia
**Submission:** MariaDB Hackathon Malaysia 2026 · Innovation Track
**Total runtime target:** 4:50 – 5:10
**Recording:** Loom or OBS Studio, 1920 × 1080, voice-over live
**Dashboard:** http://localhost:3000 (Next.js) — fallback http://localhost:8501 (Streamlit)

> **The pitch tour IS the storyboard.** Click "Start Pitch Tour" in the sidebar, then click "Next" while reading each scene's voice-over. The popover stays visible the whole time and never overlaps the highlighted card.
>
> **The full tour has 19 steps; this video uses the strongest 9.** Steps 4 (route picker), 7 (Live SQL), 9 (rainbow detail), 10 (MariaDB feature card), 11 (drift methodology), 13 (Winkler), 14 (prediction diff), 17 (hero SQL), and 18 (conformal math) are bonus-depth steps for self-paced exploration after the video. While recording, click **Next** until the popover title matches the scene below — skip past the bonus steps.

---

## Pre-recording checklist (10 min)

| Check | How |
|---|---|
| All services healthy | `docker compose ps` — db, api, app, web all `Up (healthy)` |
| Dashboard loads | Browser tab open at `http://localhost:3000/time-travel` |
| Plotly charts hydrated | Scroll to the chart at least once before recording so it's already mounted |
| Killer numbers correct | Coverage Drift shows 92.1 / 92.2 / 91.7 / 92.6 / 57.1 / 60.2 |
| Forecast Explorer pre-toggled | Click "All history" on /forecast-explorer once to warm the rainbow chart |
| No notifications | Slack / Outlook / system tray closed |
| Display scale | Windows 100% (avoid blurry recording) |
| Mic level | 30-second practice voice-over to set gain |
| Browser zoom | Ctrl+0 to reset to 100% |
| Pitch tour cold start | Click "Start Pitch Tour" once, click X to dismiss — confirms the engine is warm |

---

## The 9 video scenes (≈ 30 seconds each)

Click **Start Pitch Tour** in the sidebar. Step numbering below refers to the **video scene**, not the underlying tour step (the tour has 19 steps; the video uses 9).

> Tip: while the tour is active, the page underneath is fully interactive. Drag the slider, click a chart, change the route — tour state stays put. Use this for the live moments in scenes 3 and 5.

---

### Scene 1 · The hook (00:00 – 00:30)

**Tour step:** 1 of 19 — *The ML audit problem*
**Visible:** Time Travel page header (FlightCast title + subtitle + status pills)
**Action:** none — let the page sit while you speak

**Voice-over** (≈ 28 seconds):

> "Production ML systems retrain every week. Last quarter's predictions get overwritten. The audit trail dies. So when a regulator, an auditor, or a post-mortem asks 'what did your model predict on January 15th?' — that question becomes unanswerable. FlightCast solves this by storing every prediction inside MariaDB, system-versioned at the moment the model writes."

---

### Scene 2 · The MariaDB primitive (00:30 – 01:00)

**Tour step:** 2 of 19 — *Ask MariaDB*
**Visible:** "Ask MariaDB" violet hero callout
**Action:** mouse hovers the `FOR SYSTEM_TIME AS OF` code chip inside the callout

**Voice-over** (≈ 28 seconds):

> "FOR SYSTEM_TIME AS OF — five SQL keywords from the SQL:2011 standard. MySQL parses this as a syntax error. PostgreSQL needs a third-party extension. SQLite has nothing equivalent. MariaDB ships it natively as part of System-Versioned Tables. This single keyword is the entire foundation of FlightCast's audit story."

---

### Scene 3 · Live time travel — DRAG THE SLIDER (01:00 – 01:35)

**Tour step:** 3 of 19 — *Drag the audit slider*
**Visible:** "Audit point in time" card with date pill + slider
**Action:** **drag the slider from the latest batch (right) to the earliest (left), then back to the right.** The chart updates each step. *(First live-interaction moment — do it slowly.)*

**Voice-over** (≈ 30 seconds — match pace to slider drag):

> "This slider is not a mock. Each tick is a real ROW_START timestamp from a committed MariaDB transaction. As I drag it, the dashboard re-issues an actual FOR SYSTEM_TIME AS OF query at that exact micro-second. No replays. No snapshots. No shadow tables. The database itself is the time machine — and you're seeing the model's mind change as we move backward through history."

---

### Scene 4 · The math layer (01:35 – 02:05)

**Tour step:** 5 of 19 — *Coverage you can verify* (skip past tour step 4 — bonus route picker)
**Visible:** the 4 KPI cards (Model version / Empirical coverage / Median 90% CI / Forecast horizon)
**Action:** mouse hovers the "Empirical coverage" KPI card

**Voice-over** (≈ 28 seconds):

> "MAPIE conformal prediction — Vovk 2005, Lei 2018 — carries a finite-sample coverage theorem. At least 90% of actual demand will fall inside the predicted band, for exchangeable data. We don't claim 90% — we measure it, every single batch. Calibrated runs land at 91 to 92%. The mathematics is empirically validated, not just asserted on a slide."

---

### Scene 5 · 30-day forecast — TOGGLE ACTUALS (02:05 – 02:35)

**Tour step:** 6 of 19 — *30 day forecast and band*
**Visible:** the chart card showing the predicted-demand line + violet conformal band
**Action:** **toggle "Show actuals"** in the chart-card top-right. Amber dots appear over the band. Then toggle it off.

**Voice-over** (≈ 30 seconds):

> "A real LightGBM 30-day forecast, with the 90% conformal band drawn on top. When I toggle 'Show actuals', the dashboard fetches the ground-truth values that were measured AFTER the prediction was made — and you can see them landing inside the band. That's the coverage guarantee, in real time. Six committed model versions live in this database, and you're looking at one of them right now."

---

### Scene 6 · All-history rainbow — SIX VERSIONS, ONE QUERY (02:35 – 03:10)

**Tour step:** 8 of 19 — *Six versions, one query* (skip past tour step 7 — bonus). Optional: also click **Next** once into step 9 to read the per-ribbon explanation.
**Visible:** Forecast Explorer · "All history" view with six overlaid forecast bands in six colors
**Action:** if not already on history view, **click "All history"** in the View mode picker. Let the rainbow render.

**Voice-over** (≈ 33 seconds):

> "Switch to the all-history view. Six committed model versions, each with its own 90% conformal band, overlaid in six colors on the same chart. This is one MariaDB query — FOR SYSTEM_TIME ALL returns every historical version of every prediction row. In MLflow or Weights & Biases, you'd issue six separate API calls and join them in Python. Here, six versions times thirty days equals one SELECT statement."

---

### Scene 7 · DRIFT — the killer demo (03:10 – 04:05)

**Tour step:** 12 of 19 — *Drift caught by one query* (skip past tour steps 10 and 11 — bonus). After the voice-over, optionally click further to step 13 (Winkler) and step 14 (Prediction diff) if you have time.
**Visible:** Coverage Drift page — audit headline tiles ("4 / 6 calibrated · 91.2%" vs "2 / 6 drift · 58.7%")
**Action:** scroll down once so the per-batch RunStatusCards are also visible. Optional: also briefly show the Winkler section (3.3× jump).

**Voice-over** (≈ 53 seconds — longest scene, the punchline of the pitch):

> "Now the killer demo. Six bootstrap batches. The first four were calibrated — 91 to 92% empirical coverage, on target. Then on batch 5, we simulated a distribution shift — a regime change, like a fuel-price shock or a new low-cost carrier on the route. Coverage collapsed to 57%. The Winkler interval score tripled. And here's the punch line — this entire drift detection is ONE SQL query against FOR SYSTEM_TIME ALL. No MLflow tracking server. No Weights & Biases. No shadow tables. No application-side audit log. The database itself caught the drift. That's the moat."

---

### Scene 8 · Architecture + differentiation (04:05 – 04:35)

**Tour steps:** 15 of 19 (*Five layers, zero deps*) → 16 of 19 (*Vs. the standard MLOps stack*) — skip past tour steps 13 (Winkler) and 14 (Prediction diff), both bonus. Optional: also click into step 17 (Hero SQL queries) to highlight the moat-in-code section.
**Visible:** How It Works page — the architecture diagram, then scroll up to the comparison table
**Action:** let the architecture sit on screen, then click Next once to land on the comparison table; mouse trace down the right-hand "FlightCast" column

**Voice-over** (≈ 28 seconds):

> "Five layers: ingestion, MariaDB with system versioning, ML pipeline, query layer, dashboard. Notably absent: MLflow, Weights & Biases, DataDog, Evidently. The audit trail is structural, not bolted on. Versus the standard MLOps stack — external tracking server replaced by atomic INSERT-time versioning, custom drift dashboards replaced by one SQL query, replay infrastructure replaced by FOR SYSTEM_TIME."

---

### Scene 9 · Open infrastructure — close (04:35 – 05:00)

**Tour step:** 19 of 19 — *Open infrastructure* (skip past tour step 18 — bonus)
**Visible:** "For judges & reviewers" section + footer
**Action:** click **Finish** in the popover after you've finished speaking. Tour closes cleanly.

**Voice-over** (≈ 25 seconds):

> "FlightCast is MIT-licensed. Per-tier MAPIE recalibration, real-data prototypes, Apache Airflow integration — all listed as open issues. The temporal-tables × conformal-prediction intersection is now public infrastructure for the MariaDB ecosystem. Built by Low Yan Cheng at APU Malaysia, for the MariaDB Hackathon Malaysia 2026. Thanks for watching."

---

## Production tips

**Pacing:** if you can read the voice-over comfortably, you're at the right speed. Hackathon judges watch on 1.25× anyway.

**Don't apologise on camera.** No "uh, sorry, let me find the…", no "the chart is loading slowly". If you fluff a take, mute, restart from the same scene boundary. Cuts between scenes are fine and invisible.

**Mouse cursor:** keep it small (Windows default), and when highlighting something, hover *near* it, not on top of it. The tour popover already has the violet glow ring — your cursor shouldn't compete.

**Audio:** record voice-over in a quiet room, microphone close. Even a Logitech BRIO or AirPods Pro mic outperforms anything done while the dishwasher is on.

**Backup take:** record scene 7 twice — it's the most important 53 seconds and the one most likely to need a retake.

**Captions:** add captions in post (Loom does this automatically). International judges will skim faster with captions.

---

## Bonus tour steps (NOT in the video, but on the live demo)

If a judge clicks through the tour themselves on the live dashboard, they get ten extra depth-steps the video skips:

| # | Title | Anchor | What it adds |
|---|---|---|---|
| 4 | Pick the route to audit | Route card on /time-travel | 50 sampled OpenFlights routes (hub/mid/thin tier), the second axis of the audit query |
| 7 | Live SQL bridge | Live SQL panel on /time-travel | Shows the SQL that produced the chart, copy/paste-able |
| 9 | What the rainbow shows | All-history chart on /forecast-explorer | Per-ribbon read of which run drifted vs held |
| 10 | MariaDB exclusive primitives | Feature card on /forecast-explorer | FOR SYSTEM_TIME AS OF vs ALL, the MySQL/PG/SQLite gap |
| 11 | The drift methodology | Methodology strip on /coverage-drift | σ = 0.10 for runs 1 to 4, σ = 0.22 for 5 and 6, the exact recipe |
| 13 | Winkler interval score | Winkler section on /coverage-drift | The 3.3× jump that catches drift before coverage breaks |
| 14 | Prediction diff between batches | Diff section on /coverage-drift | One self-join across two FOR SYSTEM_TIME AS OF snapshots, no Python needed |
| 17 | Five MariaDB only queries | Hero SQL section on /how-it-works | The five copy-and-run queries that fail on MySQL or PostgreSQL |
| 18 | The conformal math | Math section on /how-it-works | The MAPIE theorem for stats-literate judges |

These are deliberate additions for jurors who want depth without pausing the video.

---

## What if something breaks live

| Symptom | Recovery |
|---|---|
| Chart doesn't update on slider drag | F5 the page (clears React Query cache, forces refetch). Re-cue from scene 3. |
| API returns 503 | `docker compose restart api`. Wait 5 sec. Re-cue. |
| Pitch tour gets stuck on a step | Click X on the popover, click "Start Pitch Tour" again, then "Next" past completed scenes. |
| All-history rainbow doesn't render | The view-mode toggle didn't fire — click "All history" again, wait 1 sec for the query. |
| Browser auto-zooms | Ctrl+0 resets. |
| Wrong page when starting a step | Tour will auto-navigate when you click Next/Back. If it doesn't, click the sidebar nav manually — tour state persists. |

---

## Submission package alongside the video

When you upload, include a one-line description and these links:

- **Live demo:** http://localhost:3000 (or your hosted URL)
- **Pitch tour:** click "Start Pitch Tour" in the sidebar — 19 steps, walks the same 9 scenes plus 10 bonus depth-steps (route picker, Live SQL, rainbow detail, feature card, drift methodology, Winkler, prediction diff, hero SQL, conformal math)
- **Whitepaper:** `Elegant.md` — ~6,300 words including the conformal-coverage theorem, MariaDB feature audit, performance benchmarks
- **Judge guide:** `docs/JUDGES_TESTING_GUIDE.md` — four time-budget options (2 / 5 / 15 / 45 min)
- **Repo:** https://github.com/TP070056/flightcast

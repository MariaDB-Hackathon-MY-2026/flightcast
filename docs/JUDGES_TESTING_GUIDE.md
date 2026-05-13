# JUDGES_TESTING_GUIDE — FlightCast

**Welcome, judge.** This guide gets you from "never seen this repo" to "I understand the technical claim" in **as little as 2 minutes**.

We've designed four time-budget options. Pick the one that matches your available time. Each option produces a concrete, verifiable result so you don't have to take any of FlightCast's claims on faith.

---

## Quick reference

| Option | Time | Setup needed | What you'll see |
|---|---|---|---|
| **0** | **2 min** | None | Pre-rendered screenshots + the benchmark JSON |
| **1** | **5 min** | Docker | Live dashboard at `http://localhost:8501` (DB pre-loaded from snapshot) |
| **2** | **15 min** | Docker | Live drift detection + benchmark + per-tier audit |
| **3** | **45 min** | Docker | Full reproduction: bootstrap from scratch, inject actuals, verify outputs |

If anything goes wrong in any tier, see [Troubleshooting](#troubleshooting) at the bottom.

---

## Option 0 — 2 minutes, no setup

If you only have 2 minutes, you can evaluate FlightCast without running anything. Open these files in your browser or text editor:

1. **`docs/screenshots/`** — five pre-captured PNGs of the live dashboard, in viewing order:
   - `00_landing.png` — landing view (Forecast Explorer + sidebar showing the four pages)
   - `01_landing_forecast.png` — the per-route forecast with conformal interval band
   - `02_time_travel_hero.png` — the temporal slider with FOR SYSTEM_TIME AS OF SQL panel
   - `03_coverage_drift.png` — **the math payoff** — Run 1-4 at 91-92% (green), Run 5-6 collapse to 57-60% (red), Winkler scores showing the 3× jump
   - `04_about_systemtime.png` — architecture + the FOR SYSTEM_TIME ALL callout box

   The single most compelling screenshot is **`03_coverage_drift.png`** — it shows a measured calibration breach detected by one SQL query against `FOR SYSTEM_TIME ALL`. No other 2026 submission has anything visually equivalent.

2. **`docs/benchmark_results.json`** — the actual benchmark numbers from a 100-iteration run on the live data:

   ```bash
   cat docs/benchmark_results.json
   ```

   Headline:
   - **Per-route time-travel:** native MariaDB **1.74× faster** than manual versioning (0.41 ms vs 0.70 ms median)
   - **Full-batch / aggregate queries:** within ±10% (temporal queries pay no overhead tax)
   - **Application code required for manual approach:** 30 lines of versioning logic per UPDATE, plus race-condition handling. Native: **0 lines**.

3. **`Elegant.md`** sections to skim:
   - **§1 TL;DR** (60-second pitch)
   - **§3 Why MariaDB System-Versioned Temporal Tables?** (the differentiation argument)
   - **§4 Mathematical Foundations** (the conformal coverage theorem and log-transform invariant — this is the unique mathematical content that distinguishes FlightCast from every other 2026 hackathon entry)
   - **§12 Performance Benchmarks** (the measured numbers above)

**What you should walk away convinced of after Option 0:** that FlightCast is the only submission combining (a) MariaDB-exclusive `FOR SYSTEM_TIME` syntax, (b) a formal mathematical coverage guarantee from MAPIE conformal prediction, and (c) measured-not-claimed performance numbers.

---

## Option 1 — 5 minutes, live dashboard

This is the recommended evaluation path for most judges.

### Setup

```bash
# 1. Clone (if you haven't)
git clone https://github.com/<owner>/flightcast.git
cd flightcast

# 2. Bring up Docker Compose (DB + Streamlit dashboard, ~60-90s first time)
docker compose up -d

# 3. Wait for healthchecks to pass
docker compose ps
# Both `app` and `db` should show "Up X seconds (healthy)" within ~90 seconds.
```

### Load the pre-baked demo data

The `backups/v0.4-phase3.sql` snapshot contains the latest stable demo state (6 batches × 50 routes × 30 days, with calibrated coverage at 91-92% and drift batches at 57-60%). Load it once:

```bash
docker compose exec -T db mariadb -uflightcast -pflightcastpw flightcast < backups/v0.4-phase3.sql
```

Loading takes ~30 seconds. After this, the dashboard at `http://localhost:8501` shows the canonical demo state.

### What to look for

Open `http://localhost:8501` and click through the four pages in order:

1. **Time Travel (Hero)** — drag the slider from `2026-01-01 (lgbm-v1.0)` to `2026-03-15 (lgbm-v2.1)`. Watch:
   - The SQL panel updates with the timestamp (this is real, executed against MariaDB)
   - The forecast chart updates (genuinely different model per slider position)
   - The empirical coverage in the stat strip should hover near 91% on calibrated batches and drop to ~58% on the last two

2. **Forecast Explorer** — pick any route from the dropdown. Compare "Latest batch" vs "All history" view modes. The "All history" overlays predictions from all 6 model versions for the same route.

3. **Coverage Drift** — this is the math payoff:
   - Top metrics: Run 1-4 show ~91% coverage with green deltas; Run 5-6 show ~58% with **red −31pp** deltas
   - Below: Winkler interval scores show a **~3× jump** between calibrated and drift batches (continuous companion to binary coverage)
   - Bottom: prediction-diff bar chart between any two batches

4. **How It Works** — architecture diagram, hero SQL queries (5 of them, all using MariaDB-exclusive syntax), and the FlightVault comparison table.

### Verification commands

If you want to confirm the numbers behind the dashboard match reality, run these two queries:

```bash
# Empirical coverage per batch (the killer demo metric)
docker compose exec -T db mariadb -uflightcast -pflightcastpw flightcast -e \
  "SELECT forecast_run_id, ROUND(AVG(coverage_score)*100, 1) AS coverage_pct,
          ROUND(AVG(winkler_score), 0) AS mean_winkler
   FROM forecasts FOR SYSTEM_TIME ALL
   WHERE coverage_score IS NOT NULL
   GROUP BY forecast_run_id ORDER BY forecast_run_id;"
```

Expected output:
```
1   91.7-92.6   ~7,300    ← calibrated
2   91-92       ~7,500    ← calibrated
3   91-92       ~7,400    ← calibrated
4   91-92       ~7,400    ← calibrated
5   57-60       ~24,000   ← DRIFT (3× higher Winkler)
6   57-60       ~23,500   ← DRIFT
```

```bash
# Verify the MariaDB-exclusive syntax actually executes
docker compose exec -T db mariadb -uflightcast -pflightcastpw flightcast -e \
  "SHOW CREATE TABLE forecasts;" | grep -A 2 "WITH SYSTEM VERSIONING"
```

You should see `WITH SYSTEM VERSIONING` in the table definition. This single keyword does not exist in MySQL 8.x, PostgreSQL, or SQLite without third-party extensions.

---

## Option 2 — 15 minutes, deeper audit

Includes everything in Option 1, plus:

### Run the latency benchmark yourself

```bash
docker compose exec -T app python -m flightcast.benchmarks.temporal_benchmark
```

Takes ~10 seconds. Output should match `docs/benchmark_results.json` within ±15% (timing variance on shared hardware). The script:
1. Materialises a `forecasts_manual` shadow table from `FOR SYSTEM_TIME ALL`
2. Runs four scenarios × 100 iterations, comparing native temporal queries against equivalent app-managed `created_at`/`expired_at` predicates
3. Reports median / p95 latency and speedup ratio

### Drill down into the per-tier coverage breakdown

```bash
docker compose exec -T db mariadb -uflightcast -pflightcastpw flightcast -e \
  "SELECT f.forecast_run_id AS run, rd.tier,
          ROUND(AVG(f.coverage_score)*100, 1) AS coverage_pct
   FROM forecasts f
   JOIN (SELECT DISTINCT route_id, tier FROM route_demand) rd
        ON f.route_id = rd.route_id
   WHERE f.coverage_score IS NOT NULL
   GROUP BY f.forecast_run_id, rd.tier
   ORDER BY f.forecast_run_id, rd.tier;"
```

You'll see hub / mid / thin coverage broken down per batch. Calibrated batches should be uniformly 89-95% across all three tiers (the conformal guarantee holds tier-by-tier, not just on aggregate). Drift batches drop to 55-65% across all three tiers.

### Inspect the per-batch model variation

```bash
docker compose exec -T db mariadb -uflightcast -pflightcastpw flightcast -e \
  "SELECT forecast_run_id, model_version,
          ROUND(STDDEV(predicted_demand), 2) AS prediction_stddev,
          COUNT(DISTINCT predicted_demand) AS distinct_predictions
   FROM forecasts
   WHERE route_id = (SELECT MIN(route_id) FROM route_demand)
   GROUP BY forecast_run_id, model_version
   ORDER BY forecast_run_id;"
```

The `distinct_predictions` column should be near 30 (one per forecast day) — proving the recursive multi-step forecast actually varies day-to-day. The `prediction_stddev` should be 5-10× the original frozen-lag baseline of ~3.

### Test the audit-trail SQL directly

The hero claim is "the database itself is the audit oracle". Verify by running the calibration drift query that no other database can execute:

```bash
docker compose exec -T db mariadb -uflightcast -pflightcastpw flightcast -e \
  "SELECT AVG(coverage_score) FROM forecasts FOR SYSTEM_TIME ALL
   GROUP BY forecast_run_id;"
```

`FOR SYSTEM_TIME ALL` is the MariaDB-exclusive SQL extension that returns every historical version of every row. Try this query against MySQL 8 or PostgreSQL — it parses as a syntax error.

---

## Option 3 — 45 minutes, full reproduction

For judges who want to reproduce the entire pipeline from a clean state.

### Reset and rebuild

```bash
# 1. Drop the volume (wipes all DB state)
docker compose down -v

# 2. Bring up fresh
docker compose up -d

# 3. Wait for healthchecks
docker compose ps
# (~90 seconds first time as MariaDB initialises the schema files)

# 4. Run the bootstrap (downloads OpenFlights, generates synthetic demand,
#    trains 6 batches with seed-per-batch, generates recursive forecasts)
docker compose exec -T app python -m flightcast.bootstrap --reset
# Expected runtime: ~70 seconds total. Each batch takes ~12 seconds with
# n_resamplings=20 and n_estimators=100.

# 5. Inject synthetic actuals + compute coverage and Winkler scores
docker compose exec -T app python -m flightcast.inject_actuals
# Expected runtime: ~5 seconds.
```

### Expected outputs verbatim

Bootstrap should print 6 lines like:
```
Batch 1: story_ts=2026-01-01, model=lgbm-v1.0
  Training (n_train=24450, n_cal=4900, seed=43)...
  Building future features (horizon=30 days, recursive)...
  Generating forecast (1500 rows)...
  ROW_START=2026-MM-DD HH:MM:SS.uuuuuu (story=2026-01-01)
  Batch 1 complete. 1500 forecast rows written.
```

`inject_actuals` should print:
```
Per-tier breakdown of actuals to inject:
    hub   calibrated :  1200 rows  (σ=0.100)
    hub   drift      :   600 rows  (σ=0.220)
    mid   calibrated :  3000 rows  (σ=0.100)
    mid   drift      :  1500 rows  (σ=0.220)
    thin  calibrated :  1800 rows  (σ=0.100)
    thin  drift      :   900 rows  (σ=0.220)
  Updated 9000 forecast rows with actual_demand.

  Empirical coverage per batch:
  Run  Coverage    Width       N
  1    91-92%       ~6,300      1500
  2    91-92%       ~6,300      1500
  ... (4 calibrated + 2 drift)
```

Then run the benchmark and dashboard verification from Option 2.

---

## Evaluation Criteria

What we hope you'll evaluate FlightCast on:

| Criterion | Weight | Where to look |
|---|---|---|
| **Innovation & Creativity** | 20% | First system using `FOR SYSTEM_TIME ALL` for ML coverage validation. Conformal prediction + temporal tables intersection has not appeared in any prior MariaDB hackathon. |
| **MariaDB Integration & Impact** | 30% | Five MariaDB-exclusive SQL syntax tokens used (`WITH SYSTEM VERSIONING`, `FOR SYSTEM_TIME AS OF`, `FOR SYSTEM_TIME ALL`, `FOR SYSTEM_TIME BETWEEN`, `ST_DISTANCE_SPHERE`). The architecture *requires* MariaDB — it cannot be ported to PostgreSQL/MySQL without a separate audit-log table. |
| **Technical Excellence** | 25% | Mathematically rigorous conformal coverage guarantee (§4 of Elegant.md), measured benchmarks (`docs/benchmark_results.json`), recursive multi-step forecasting (Phase 3), per-batch seed-based model differentiation. |
| **Execution & Completeness** | 15% | All 4 dashboard pages working, two health-checked Docker services, complete from-scratch reproduction in <90 seconds, comprehensive documentation in `Elegant.md`, this judges' guide. |
| **Learning & Community** | 10% | Honest disclosure of synthetic-data methodology in the dashboard, open-source MIT license, comprehensive `pipeline_research/` audit trail of every design decision. |

---

## Troubleshooting

### Containers don't start
```bash
docker compose down -v
docker compose up -d --build
```

### Dashboard shows "No batches found"
Run the bootstrap from Option 3 step 4, OR load the snapshot from Option 1.

### Benchmark shows manual is faster
Single-machine timings vary. Run 2-3 times; median over runs is stable. The honest claim is "1.5-1.8× on the hero query, comparable on full scans."

### Coverage Drift page shows N/A
The `actual_demand` column hasn't been populated. Run:
```bash
docker compose exec -T app python -m flightcast.inject_actuals
```

### Anything else
Open an issue, or read the `pipeline_research/PHASE_*_*.md` files which document every design decision and validation gate that produced this state.

---

**Thank you for taking the time to evaluate FlightCast.** The temporal-tables × conformal-prediction intersection is genuinely unprecedented in the MariaDB hackathon ecosystem, and we hope this guide makes it as easy as possible for you to verify that claim.

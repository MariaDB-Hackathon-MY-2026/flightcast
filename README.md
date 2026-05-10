# FlightCast

**Database-Native ML Audit for Aviation Demand Forecasting**

> *MariaDB Hackathon Malaysia 2026 — Innovation Track*

FlightCast is the first system using MariaDB's `FOR SYSTEM_TIME ALL` to mathematically validate that an ML model's prediction-coverage guarantee held in production — proving with one SQL query whether your model was still trustworthy six months ago.

```sql
-- One SQL query. The entire ML calibration audit. MariaDB-exclusive.
SELECT forecast_run_id,
       AVG(coverage_score)            AS empirical_coverage,
       AVG(upper_bound - lower_bound) AS mean_interval_width
FROM forecasts FOR SYSTEM_TIME ALL
WHERE coverage_score IS NOT NULL
GROUP BY forecast_run_id;
```

This syntax does not exist in MySQL. PostgreSQL needs a third-party extension. SQLite cannot do it at all.

📸 **2-minute evaluation, no setup:** see [`docs/screenshots/`](docs/screenshots/) — five PNGs of the live dashboard. The killer image is [`03_coverage_drift.png`](docs/screenshots/03_coverage_drift.png), where Run 1-4 sit at 91-92% empirical coverage (green) and Run 5-6 collapse to 57-60% (red) — a calibration breach detected by one `FOR SYSTEM_TIME ALL` query. Full no-setup walkthrough in [`docs/JUDGES_TESTING_GUIDE.md`](docs/JUDGES_TESTING_GUIDE.md) Option 0.

---

## What you'll see

A 4-page Streamlit dashboard that lets you slide back through time across six versioned ML model batches:

1. **Time Travel (Hero)** — drag a slider; watch the model's predictions and 90% conformal interval change as you scrub through six committed batches. The SQL block updates live with the audit timestamp. This is the demo.
2. **Forecast Explorer** — per-route deep-dive. Compare a single route's forecasts across all 6 model versions in one chart.
3. **Coverage Drift** — the math payoff. Empirical 90% conformal coverage *measured* per batch. Calibrated batches: 91–92%. Drift batches (simulated distribution shift): 57–60%. Winkler interval scores 3× higher on drift batches.
4. **How It Works** — architecture, hero SQL queries, FlightVault comparison, the head-to-head MariaDB vs PostgreSQL/MySQL/SQLite table.

---

## Five-minute quickstart

```bash
git clone https://github.com/imycc1221/flightcast.git
cd flightcast
cp .env.example .env

# Bring up MariaDB + Streamlit (Docker, ~60–90s first time)
docker compose up -d

# Generate 6 prediction batches with recursive multi-step forecasting
# (~70 seconds; downloads OpenFlights, generates synthetic demand,
# trains 6 LightGBM models with seed-per-batch, fits MAPIE)
docker compose exec -T app python -m flightcast.bootstrap

# Inject synthetic actuals + compute coverage and Winkler scores
docker compose exec -T app python -m flightcast.inject_actuals
```

Open `http://localhost:8501`.

For judges who want the most efficient evaluation path, see **[`docs/JUDGES_TESTING_GUIDE.md`](docs/JUDGES_TESTING_GUIDE.md)** — four time-budget options from 2 minutes to 45 minutes.

---

## What it demonstrates (MariaDB-exclusive features)

| MariaDB feature | Where used | Available elsewhere? |
|---|---|---|
| `WITH SYSTEM VERSIONING` | `forecasts`, `model_metrics` tables | PostgreSQL extension; not MySQL/SQLite |
| `FOR SYSTEM_TIME AS OF '...'` | Temporal slider on hero page | No (parses as syntax error) |
| `FOR SYSTEM_TIME ALL` | Calibration drift audit | No |
| `FOR SYSTEM_TIME BETWEEN x AND y` | Window queries on history | No |
| `ST_DISTANCE_SPHERE` | Great-circle distance as a route feature | PostgreSQL has it via PostGIS |
| Covering index on versioned table | `idx_route_fdate_run` | n/a |
| VIRTUAL generated column | `interval_width` | n/a |

---

## Architecture

![FlightCast Architecture](src/flightcast/ui/assets/architecture.png)

Five-layer architecture organised around MariaDB as the central state store. The `forecasts` table — written by the ML pipeline — is system-versioned, so the dashboard's `FOR SYSTEM_TIME AS OF` queries reconstruct any prediction state in the past without a separate audit log.

The [whitepaper (Elegant.md)](Elegant.md) carries the full §1–§17: mathematical foundations, head-to-head MariaDB comparison, performance benchmarks, FlightVault comparison, anti-Vector framing, and honest limitations.

---

## Performance

100-iteration benchmark, native temporal queries vs. equivalent hand-rolled `created_at` / `expired_at` versioning on a `forecasts_manual` shadow table populated with identical data:

| Scenario | Rows | Native | Manual | Speedup |
|---|---:|---:|---:|---:|
| Per-route time-travel (`AS OF`) | 30 | **0.41 ms** | 0.70 ms | **1.74×** |
| Full-batch time-travel | 1,500 | 6.65 ms | 6.13 ms | comparable |
| Full audit history (`ALL`) | 9,000 | 18.0 ms | 16.9 ms | comparable |
| Coverage-drift aggregate | 6 | 5.06 ms | 4.54 ms | comparable |

Native MariaDB is 1.74× faster on the hero query and **requires zero application versioning code** (the manual approach needs ~30 lines per UPDATE plus race-condition handling). Reproduce with `docker compose exec app python -m flightcast.benchmarks.temporal_benchmark`.

---

## Repository layout

```
flightcast/
├── Elegant.md                          # Whitepaper (~6,300 words)
├── docs/
│   ├── JUDGES_TESTING_GUIDE.md         # 4-tier evaluation path
│   └── benchmark_results.json          # Captured 100-iteration timings
├── initdb/
│   ├── 01-openflights-create.sql       # OpenFlights schema + data_version stamps
│   ├── 03-flightcast-schema.sql        # forecasts, route_demand, model_metrics
│   ├── 04-system-versioning.sql        # ALTER TABLE ... ADD SYSTEM VERSIONING
│   └── 05-benchmark-schema.sql         # forecasts_manual shadow for benchmarks
├── src/flightcast/
│   ├── synth_demand.py                 # Per-tier multiplicative log-normal demand
│   ├── data_pipeline.py                # Stratified route sampler (hub/mid/thin)
│   ├── features.py                     # FROZEN-LAG (legacy) + RECURSIVE multi-step
│   ├── forecaster.py                   # LightGBM + MAPIE TimeSeriesRegressor
│   ├── audit.py                        # coverage_score + winkler_score backfill
│   ├── inject_actuals.py               # Synthetic actuals with drift simulation
│   ├── bootstrap.py                    # End-to-end pipeline (6 batches)
│   ├── benchmarks/temporal_benchmark.py  # Native vs manual versioning
│   ├── db/                             # Connection + repository pattern
│   ├── api/                            # FastAPI service (not in compose; reference)
│   └── ui/                             # Streamlit (4 pages, custom CSS)
├── tests/                              # Unit + integration suites
├── pipeline_research/                  # Per-stage research + audit + execution plan
├── competitor_analysis/                # Deep dive on 2025 winners + 2026 entries
└── backups/                            # SQL dumps for each phase rollback point
```

---

## License & acknowledgements

MIT License. Built on the open MariaDB Foundation, MAPIE (Inria), LightGBM (Microsoft), Streamlit, Plotly, and the OpenFlights dataset by Jani Patokallio. The conformal prediction theory is due to Vovk, Shafer, Gammerman, Romano, Candès, and Barber.

For the full technical writeup, read **[Elegant.md](Elegant.md)** (~6,300 words covering math, architecture, benchmarks, and honest limitations).

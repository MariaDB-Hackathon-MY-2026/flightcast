"""
Page 4: About / How It Works
Architecture diagram, all 5 hero SQL snippets, MLOps-stack differentiation.
"""
from pathlib import Path

import streamlit as st

from flightcast.ui.style import page_header
from flightcast.ui.tour import (
    PAGE_ABOUT,
    render_tour_banner,
    render_sidebar_trigger,
    tour_anchor,
    ANCHOR_ARCHITECTURE,
    ANCHOR_COMPARISON,
    ANCHOR_CLOSE,
)

_ARCH_IMG = Path(__file__).resolve().parent.parent / "assets" / "architecture.png"

render_sidebar_trigger()
render_tour_banner(PAGE_ABOUT)

page_header(
    eyebrow="MariaDB Hackathon Malaysia 2026 · Innovation Track",
    title="How FlightCast works",
    subtitle="The architecture, the math, and the MariaDB-exclusive primitives behind the audit trail.",
    pills=[
        ("Architecture", "default"),
        ("MariaDB 11.8", "blue"),
        ("Conformal prediction", "violet"),
    ],
)

st.markdown(
    """
**FlightCast** is an aviation demand forecasting system that uses
[MariaDB System-Versioned Temporal Tables](https://mariadb.com/kb/en/system-versioned-tables/)
as its audit backbone and
[MAPIE conformal prediction](https://mapie.readthedocs.io/) to provide
**mathematically guaranteed 90% coverage intervals**.

<div id="tour-comparison" class="fc-tour-anchor"></div>

### What makes FlightCast different from standard MLOps tooling?

| | Standard MLOps stack (MLflow / W&B + app audit log) | FlightCast |
|---|---|---|
| Audit substrate | External tracking server + shadow tables | Database-native, zero extra infra |
| Versioning latency | Sync gap between write and log | Atomic at `INSERT` time |
| Coverage guarantee | Not enforced | MAPIE conformal · ≥90% finite-sample |
| Drift detection | Custom dashboards / Python jobs | One SQL query: `FOR SYSTEM_TIME ALL` |
| Time-travel SQL | Not available — must replay logs | 5 MariaDB-exclusive temporal queries |

**The moat is the math layer, not the slider.**
"""
)

# ─── MariaDB-exclusive syntax callout ──────────────────────────────────────
# Make the SQL extension that ONLY MariaDB supports visually unmissable.
# This is the single line of SQL that cannot be reproduced on MySQL,
# PostgreSQL, or any other database without third-party extensions.
st.markdown(
    """
    <div style="
        background: linear-gradient(135deg, rgba(96,165,250,0.10), rgba(167,139,250,0.06));
        border: 1px solid rgba(96,165,250,0.30);
        border-left: 4px solid #60A5FA;
        border-radius: 10px;
        padding: 1.1rem 1.3rem;
        margin: 1rem 0 1.4rem 0;
    ">
      <div style="
          text-transform: uppercase;
          letter-spacing: 0.18em;
          font-size: 0.72rem;
          font-weight: 600;
          color: #60A5FA;
          margin-bottom: 0.5rem;
      ">The MariaDB-exclusive syntax</div>
      <code style="
          display: block;
          font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
          font-size: 1.05rem;
          color: #E2E8F0;
          background: rgba(8,12,22,0.65);
          padding: 0.7rem 0.95rem;
          border-radius: 6px;
          border: 1px solid rgba(148,163,184,0.15);
      ">SELECT AVG(coverage_score) FROM forecasts FOR SYSTEM_TIME ALL GROUP BY forecast_run_id;</code>
      <div style="
          color: #94A3B8;
          font-size: 0.92rem;
          margin-top: 0.7rem;
          line-height: 1.55;
      ">
        <strong style="color:#F1F5F9;">FOR SYSTEM_TIME ALL</strong> returns every historical version of every row —
        a SQL extension defined in the SQL:2011 standard. MariaDB implements it natively;
        <strong style="color:#94A3B8;">MySQL does not, PostgreSQL needs an extension,</strong>
        and SQLite has no equivalent at all.
        This single keyword is what lets FlightCast audit prediction coverage with one query
        instead of an external MLflow / W&amp;B service.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()
tour_anchor(ANCHOR_ARCHITECTURE)
st.subheader("System Architecture")

if _ARCH_IMG.exists():
    st.image(str(_ARCH_IMG), use_container_width=True)
    st.caption(
        "Layered architecture with MariaDB as the central state store. "
        "The `forecasts` table — written by the ML pipeline — is system-versioned, "
        "so the dashboard can query any past prediction state with "
        "`FOR SYSTEM_TIME AS OF`. No external audit log required."
    )
else:
    st.warning(
        "Architecture diagram not found at "
        f"`{_ARCH_IMG}`. Drop the image there to render it inline."
    )

st.divider()
st.subheader("Hero SQL Queries")
st.caption("All five use MariaDB-exclusive syntax. None of these run on MySQL or PostgreSQL.")

with st.expander("1 — Time-travel: what did the model predict on a given date?"):
    st.code(
        """SELECT route_id, forecast_date,
       predicted_demand, lower_bound, upper_bound, model_version,
       ROW_START, ROW_END
FROM forecasts FOR SYSTEM_TIME AS OF '2026-02-01 10:32:14.000000'
WHERE route_id = 123
ORDER BY forecast_date;""",
        language="sql",
    )

with st.expander("2 — Prediction diff: how did forecasts change between two model versions?"):
    st.code(
        """SELECT a.forecast_date,
       a.predicted_demand AS predicted_v1,
       b.predicted_demand AS predicted_v2,
       b.predicted_demand - a.predicted_demand AS delta
FROM
  (SELECT * FROM forecasts FOR SYSTEM_TIME AS OF '2026-01-15 09:00:00' WHERE route_id = 123) a
JOIN
  (SELECT * FROM forecasts FOR SYSTEM_TIME AS OF '2026-02-15 09:00:00' WHERE route_id = 123) b
  ON a.forecast_date = b.forecast_date
ORDER BY a.forecast_date;""",
        language="sql",
    )

with st.expander("3 — Full audit log: every version of every prediction row"):
    st.code(
        """SELECT forecast_run_id, forecast_date,
       predicted_demand, lower_bound, upper_bound,
       model_version, ROW_START, ROW_END
FROM forecasts FOR SYSTEM_TIME ALL
WHERE route_id = 123
ORDER BY ROW_START, forecast_date;""",
        language="sql",
    )

with st.expander("4 — Calibration drift: empirical coverage vs target across batches"):
    st.code(
        """SELECT forecast_run_id,
       AVG(coverage_score)              AS empirical_coverage,
       0.90                             AS target,
       AVG(coverage_score) - 0.90       AS drift,
       AVG(upper_bound - lower_bound)   AS mean_interval_width
FROM forecasts FOR SYSTEM_TIME ALL
WHERE coverage_score IS NOT NULL
GROUP BY forecast_run_id
ORDER BY forecast_run_id;""",
        language="sql",
    )

with st.expander("5 — MariaDB ST_DISTANCE_SPHERE: great-circle distance as a feature"):
    st.code(
        """SELECT r.id AS route_id,
       CONCAT(r.src_airport, ' → ', r.dst_airport) AS route,
       ROUND(ST_DISTANCE_SPHERE(
           POINT(a1.longitude, a1.latitude),
           POINT(a2.longitude, a2.latitude)
       ) / 1000, 1) AS distance_km
FROM routes r
JOIN airports a1 ON r.src_airport = a1.iata
JOIN airports a2 ON r.dst_airport = a2.iata
ORDER BY distance_km DESC
LIMIT 10;""",
        language="sql",
    )

st.divider()
st.subheader("Conformal Prediction — the math")
st.markdown(
    r"""
Given a calibration set $\{(x_i, y_i)\}_{i=1}^n$ with non-conformity scores
$s_i = |y_i - \hat{f}(x_i)|$, the MAPIE conformal interval at level $1-\alpha$ is:

$$[\hat{f}(x) - \hat{q}_{1-\alpha}, \; \hat{f}(x) + \hat{q}_{1-\alpha}]$$

where $\hat{q}_{1-\alpha}$ is the $\lceil (1-\alpha)(1 + 1/n) \rceil$-th empirical quantile
of $\{s_i\}$.

**Coverage guarantee:** $P(y_{n+1} \in C(x_{n+1})) \geq 1 - \alpha$ for exchangeable data.

FlightCast trains on `log(1+demand)` and inverts with `exp−1`: the log transform is a
monotone bijection that preserves quantile ordering and enforces non-negativity without
asymmetric clipping (which would break the coverage guarantee).
"""
)

st.divider()
tour_anchor(ANCHOR_CLOSE)
st.subheader("For judges & reviewers")
st.markdown(
    """
The repository ships two documents specifically for evaluators:

- **[`docs/JUDGES_TESTING_GUIDE.md`](https://github.com/imycc1221/flightcast/blob/main/docs/JUDGES_TESTING_GUIDE.md)**
  — four time-budget options (2 min / 5 min / 15 min / 45 min) for verifying every claim on this page.
- **[`Elegant.md`](https://github.com/imycc1221/flightcast/blob/main/Elegant.md)**
  — the technical whitepaper (~6,300 words), including the head-to-head MariaDB-vs-PostgreSQL/MySQL
  comparison (§3), the conformal coverage theorem (§4), the performance benchmark (§12), and
  honest limitations (§16).

For a 2-minute zero-setup evaluation: open `docs/benchmark_results.json` and §1, §3, §12 of
`Elegant.md` — that covers the three most defensible technical claims.
"""
)

st.divider()
st.caption(
    "Built by TP070056 · APU Malaysia · MariaDB Hackathon 2026 · "
    "[github.com/imycc1221/flightcast](https://github.com)"
)

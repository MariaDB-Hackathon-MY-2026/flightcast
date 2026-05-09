"""
Page 3: Coverage Drift — THE MATH PAYOFF.
Rolling 30-day empirical coverage vs the 90% conformal target.
"""
import streamlit as st
import pandas as pd

from flightcast.ui.state import get_conn, load_batch_mapping
from flightcast.audit import compute_calibration_drift
from flightcast.ui.charts import build_coverage_drift_figure, build_diff_figure
from flightcast.temporal_queries import query_diff, query_coverage_series
from flightcast.ui.style import page_header
from flightcast.ui.tour import (
    PAGE_COVERAGE,
    render_tour_banner,
    render_sidebar_trigger,
    tour_anchor,
    ANCHOR_DRIFT,
)

render_sidebar_trigger()
render_tour_banner(PAGE_COVERAGE)

page_header(
    eyebrow="The math payoff",
    title="Coverage Drift Audit",
    subtitle="Empirical coverage vs. the 90% conformal guarantee — proven across every model version.",
    pills=[
        ("LIVE", "default"),
        ("MAPIE conformal", "violet"),
        ("FOR SYSTEM_TIME ALL", "blue"),
        ("Drift detection", "amber"),
    ],
)

batches = load_batch_mapping()

if batches.empty:
    st.warning("No batches loaded. Run bootstrap to populate data.")
    st.stop()

# Honesty disclosure — what the actuals are, exactly.
# Pre-empts "are these real?" questions during demo and audit.
with st.expander("How are the empirical coverage numbers computed?", expanded=False):
    st.markdown(
        """
        **Synthetic-actuals methodology** (full transparency):

        Real airline reservation data is proprietary, so FlightCast generates a
        deterministic synthetic ground truth for each forecasted day:

        - **Calibrated batches (Runs 1–4):** `actual = predicted × exp(N(0, σ=0.10))`
          — same noise scale used during model training. Empirical coverage
          should land near 90% if the conformal calibration is correct.

        - **Drift batches (Runs 5–6):** `actual = predicted × exp(N(0, σ=0.22))`
          — wider noise simulates a regime change (new low-cost carrier, fuel
          shock, regulatory shift). Coverage is expected to collapse, and
          `FOR SYSTEM_TIME ALL` lets us prove it did.

        **What this validates:** that MAPIE's conformal interval calibration
        is correct under exchangeable noise (Runs 1–4) AND that the
        temporal-table audit detects distribution shift (Runs 5–6).

        **What this does NOT claim:** real-world prediction performance on
        proprietary airline data. The ML pipeline is generic; replacing
        synthetic actuals with real reservations is a one-line change in
        `inject_actuals.py`.
        """
    )

# Per-batch calibration drift
with st.spinner("Computing calibration drift..."):
    drift_df = compute_calibration_drift(get_conn())

if not drift_df.empty:
    tour_anchor(ANCHOR_DRIFT)
    st.subheader("Empirical Coverage per Batch")
    cols = st.columns(len(drift_df))
    for i, row in drift_df.iterrows():
        run_id = int(row["forecast_run_id"])
        coverage = row["mean_coverage"]
        if pd.isna(coverage):
            cov_str = "N/A"
            delta_str = None
        else:
            cov_str = f"{coverage:.1%}"
            delta_pp = (coverage - 0.90) * 100  # percentage points
            delta_str = f"{delta_pp:+.1f}pp"
        cols[i % len(cols)].metric(f"Run {run_id}", cov_str, delta_str)
    st.caption("Delta shown in percentage points vs. the 90% conformal target.")

    # ── Winkler interval score (continuous companion to binary coverage) ──
    st.subheader("Winkler Interval Score per Batch · lower = better")
    st.caption(
        "Winkler score (Winkler 1972) penalises both *over-wide* intervals and "
        "*missed coverage* in proportion to the miss distance. "
        "On calibrated batches it converges to ~ interval width; on drift batches "
        "the miss-penalty term dominates. Watch the **3× jump** between Run 4 and Run 5 — "
        "drift detection in one continuous metric."
    )
    if "mean_winkler" in drift_df.columns:
        wcols = st.columns(len(drift_df))
        baseline_winkler = float(drift_df["mean_winkler"].iloc[:4].mean())
        for i, row in drift_df.iterrows():
            run_id = int(row["forecast_run_id"])
            winkler = row["mean_winkler"]
            if pd.isna(winkler):
                w_str = "N/A"
                delta_str = None
            else:
                w_str = f"{int(winkler):,}"
                ratio = float(winkler) / baseline_winkler
                # Show "+/- vs calibrated baseline" delta (NEGATIVE delta is good
                # because lower Winkler is better — invert sign so red = drift).
                delta_str = (
                    f"{(ratio - 1.0) * 100:+.0f}% vs calibrated"
                    if ratio > 1.0 else
                    f"{(ratio - 1.0) * 100:+.0f}%"
                )
            # Streamlit metric: positive delta is green, negative is red. We want
            # high winkler (= bad) to show red, so we pass delta_color="inverse".
            wcols[i % len(wcols)].metric(
                f"Run {run_id}", w_str, delta_str, delta_color="inverse"
            )

with st.expander("View SQL — calibration drift"):
    st.code(
        """SELECT forecast_run_id,
       AVG(coverage_score)              AS mean_coverage,
       AVG(upper_bound - lower_bound)   AS mean_width,
       COUNT(*)                         AS n_rows
FROM forecasts FOR SYSTEM_TIME ALL
WHERE coverage_score IS NOT NULL
GROUP BY forecast_run_id
ORDER BY forecast_run_id;""",
        language="sql",
    )

st.divider()

# Prediction diff between two batches
st.subheader("Prediction Diff between Two Batches")

batch_labels = [
    f"Run {int(b.forecast_run_id)}: {pd.Timestamp(b.story_ts):%Y-%m-%d} ({b.model_version})"
    for b in batches.itertuples()
]
label_to_ts = {lbl: b.row_start_ts for lbl, b in zip(batch_labels, batches.itertuples())}

from flightcast.ui.state import load_routes, route_label as _route_label
from flightcast.ui.state import route_options as _route_options

routes = load_routes()
route_ids = routes["route_id"].tolist()

c1, c2, c3 = st.columns(3)
with c1:
    label_a = st.selectbox("Batch A (earlier)", batch_labels, index=0)
with c2:
    # Default to the NEXT batch — consecutive batches share ~16 days of overlap
    label_b = st.selectbox("Batch B (later)", batch_labels, index=min(1, len(batch_labels) - 1))
with c3:
    diff_route = st.selectbox(
        "Route",
        route_ids,
        format_func=lambda rid: _route_label(rid, routes),
    )

ts_a = label_to_ts[label_a]
ts_b = label_to_ts[label_b]

if str(ts_a) == str(ts_b):
    st.warning("Select two different batches to see a diff.")
else:
    with st.spinner("Running temporal diff query..."):
        diff_df = query_diff(get_conn(), ts_a, ts_b, diff_route)

    if diff_df.empty:
        st.info("No overlapping forecast dates between the two batches.")
    else:
        st.plotly_chart(
            build_diff_figure(diff_df, _route_label(diff_route, routes)),
            use_container_width=True,
        )
        st.caption(
            f"Delta = batch B predicted − batch A predicted. "
            f"Green = demand increased. Orange = demand decreased."
        )

    with st.expander("View SQL — temporal diff"):
        ts_a_str = str(ts_a)
        ts_b_str = str(ts_b)
        st.code(
            f"""SELECT a.forecast_date,
       a.predicted_demand AS predicted_a,
       b.predicted_demand AS predicted_b,
       b.predicted_demand - a.predicted_demand AS delta,
       a.model_version AS model_a,
       b.model_version AS model_b
FROM
  (SELECT * FROM forecasts FOR SYSTEM_TIME AS OF '{ts_a_str}'
   WHERE route_id = {diff_route}) a
JOIN
  (SELECT * FROM forecasts FOR SYSTEM_TIME AS OF '{ts_b_str}'
   WHERE route_id = {diff_route}) b
  ON a.forecast_date = b.forecast_date
ORDER BY a.forecast_date;""",
            language="sql",
        )

st.info(
    "**Why this matters:** Conformal prediction guarantees ≥90% empirical coverage "
    "if the calibration distribution is exchangeable. Drift above ±5pp signals "
    "distribution shift — the model needs recalibration. "
    "`FOR SYSTEM_TIME ALL` makes this audit zero-cost: no shadow tables, no log tables."
)

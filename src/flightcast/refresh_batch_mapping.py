"""
DEPRECATED — DO NOT RUN AGAINST PHASE 2+ DATA.
==============================================

This script worked around a side-effect of `vary_batch_predictions.py`:
applying the post-hoc multiplicative shift created new ROW_START timestamps
on every forecast row, but `batch_run_mapping.row_start_ts` still pointed
at the original (pre-shift) bootstrap commit time. The slider and Prediction
Diff queries therefore resolved `FOR SYSTEM_TIME AS OF row_start_ts` to the
*original* (un-shifted) prediction set, making the dashboard look unchanged.

This script bumped `row_start_ts` to the latest ROW_START of each batch so
the dashboard would see the shifted predictions.

After Phase 2B (seed-per-batch), the shift hack is gone and the bootstrap
records `batch_run_mapping.row_start_ts` correctly at write time. There is
nothing left to refresh.

DO NOT INVOKE this script after Phase 2C bootstrap rerun. It would point
the slider at the actuals-injection commit time, making the dashboard show
post-actuals state when the slider is at any historical batch — which is
exactly the wrong behaviour for time-travel demos.

Original docstring follows for reference:
=========================================

Refresh batch_run_mapping.row_start_ts to point at the *latest* version
of each batch's rows.

Why this matters (DEPRECATED — see above):
  After every UPDATE on the system-versioned `forecasts` table (inject actuals,
  backfill coverage, vary predictions), each forecast row gains a new version
  with a fresh ROW_START. The Time Travel slider and the Prediction Diff chart
  use `FOR SYSTEM_TIME AS OF batch_run_mapping.row_start_ts` to read each
  batch — but those timestamps were captured at bootstrap time and still
  resolve to the *original* version of every row.

  After this script runs, AS OF resolves to the post-update state, so the
  charts reflect the actuals/coverage/shift changes.
"""
from __future__ import annotations

import sys
import warnings as _warnings
from flightcast.db.connection import get_connection

_warnings.warn(
    "flightcast.refresh_batch_mapping is DEPRECATED. "
    "Per-batch row_start_ts is recorded correctly at bootstrap write time "
    "since the seed-per-batch fix removed the shift hack (Phase 2B). "
    "Running this script will misalign the Time Travel slider.",
    DeprecationWarning,
    stacklevel=2,
)


def main() -> int:
    print("Connecting to MariaDB...")
    conn = get_connection()
    cur = conn.cursor()

    # MAX(ROW_START) of the *current* version of each batch's rows.
    # Bare SELECT (no FOR SYSTEM_TIME) returns only the active rows.
    cur.execute(
        """
        UPDATE batch_run_mapping bm
        JOIN (
            SELECT forecast_run_id, MAX(ROW_START) AS latest_rs
            FROM forecasts
            GROUP BY forecast_run_id
        ) curr ON bm.forecast_run_id = curr.forecast_run_id
        SET bm.row_start_ts = curr.latest_rs
        """
    )
    conn.commit()
    print(f"  Updated {cur.rowcount} mapping rows.")

    cur.execute(
        """
        SELECT forecast_run_id, story_ts, row_start_ts, model_version
        FROM batch_run_mapping
        ORDER BY forecast_run_id
        """
    )
    print("\n  Updated batch_run_mapping:")
    print("  " + "-" * 75)
    print(f"  {'Run':<5}{'Story TS':<14}{'Latest ROW_START':<32}{'Model'}")
    print("  " + "-" * 75)
    for run_id, story_ts, row_start_ts, model_ver in cur.fetchall():
        print(f"  {run_id:<5}{str(story_ts):<14}{str(row_start_ts):<32}{model_ver}")
    print("  " + "-" * 75)

    conn.close()
    print(
        "\nDone. Restart the Streamlit app to clear cached batch_run_mapping:"
        "\n  docker compose restart app"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

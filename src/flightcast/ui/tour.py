"""
Pitch tour engine — guided narration across the 4 dashboard pages.

Pattern adapted from VESPER's GuidedTour (React) to Streamlit:
- TOUR_STEPS = single source of truth for pitch copy (version-controlled)
- Multi-page navigation via st.switch_page()
- Each step declares an `anchor_id`. Pages place an invisible anchor div
  next to the target element (via `tour_anchor()`); the banner injects a
  small same-origin iframe that calls scrollIntoView() on the parent
  document.

Public API:
    init_tour_state()           — call at top of each page
    render_tour_banner(page_id) — call at top of each page
    tour_anchor(anchor_id)      — call before each target element
    render_sidebar_trigger()    — call once per page (places sidebar button)
    start_tour()                — sidebar button handler
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components


# Page identifiers — match st.Page() paths in app.py
PAGE_TIME_TRAVEL = "pages/02_time_travel.py"
PAGE_FORECAST = "pages/01_forecast.py"
PAGE_COVERAGE = "pages/03_coverage_drift.py"
PAGE_ABOUT = "pages/04_about.py"

PAGE_LABELS = {
    PAGE_TIME_TRAVEL: "Time Travel",
    PAGE_FORECAST: "Forecast Explorer",
    PAGE_COVERAGE: "Coverage Drift",
    PAGE_ABOUT: "How It Works",
}


@dataclass(frozen=True)
class TourStep:
    page: str
    title: str
    body: str
    anchor_id: Optional[str] = None  # DOM id to scroll into view; None = top of page
    look_for: Optional[str] = None   # plain-text caption shown in the banner


# Anchor identifiers — kept in one place so page authors and tour authors
# stay in sync. Each constant matches a tour_anchor() call in a page file.
ANCHOR_AUDIT_GAP   = "tour-audit-gap"
ANCHOR_CALLOUT     = "tour-callout"
ANCHOR_SLIDER      = "tour-slider"
ANCHOR_STATS       = "tour-stats"
ANCHOR_FORECAST    = "tour-forecast"
ANCHOR_DRIFT       = "tour-drift-chart"
ANCHOR_ARCHITECTURE = "tour-architecture"
ANCHOR_COMPARISON  = "tour-comparison"
ANCHOR_CLOSE       = "tour-close"


TOUR_STEPS: list[TourStep] = [
    # ─── Beat 1+2: Hook + problem ─────────────────────────────────────
    TourStep(
        page=PAGE_TIME_TRAVEL,
        anchor_id=ANCHOR_AUDIT_GAP,
        title="The ML Audit Gap",
        body=(
            "Production ML systems retrain every two weeks. Last quarter's predictions "
            "get overwritten. When a regulator, an auditor, or a post-mortem asks "
            "<em>“what did the model predict on January 15th?”</em>, the answer is "
            "fragmented across MLflow runs, model registries, and inference logs in "
            "three different systems. <strong>FlightCast collapses that question to "
            "one SQL query against MariaDB.</strong>"
        ),
        look_for="This banner sits above the hero question this dashboard answers.",
    ),
    # ─── Beat 3: The MariaDB primitive ────────────────────────────────
    TourStep(
        page=PAGE_TIME_TRAVEL,
        anchor_id=ANCHOR_CALLOUT,
        title="One SQL Question, One Database",
        body=(
            "<code>FOR SYSTEM_TIME AS OF</code> is a SQL:2011 keyword. "
            "<strong>MySQL parses it as a syntax error. PostgreSQL needs an "
            "extension. SQLite has nothing equivalent.</strong> MariaDB ships it "
            "natively as part of System-Versioned Tables. This single keyword is "
            "the entire foundation of FlightCast's audit story."
        ),
        look_for="The blue callout names the question this database answers.",
    ),
    # ─── Beat 4: Live demonstration (3 steps) ─────────────────────────
    TourStep(
        page=PAGE_TIME_TRAVEL,
        anchor_id=ANCHOR_SLIDER,
        title="This Slider Is Not A Mock",
        body=(
            "Each step on this slider is a real <code>ROW_START</code> timestamp "
            "from a committed MariaDB transaction. Drag it — the dashboard "
            "re-queries past predictions through actual <code>FOR SYSTEM_TIME AS OF</code> "
            "SQL. <strong>No replays, no snapshots, no shadow tables.</strong> "
            "The database itself is the time machine."
        ),
        look_for="The AUDIT POINT IN TIME slider — drag it to feel real temporal SQL.",
    ),
    TourStep(
        page=PAGE_TIME_TRAVEL,
        anchor_id=ANCHOR_STATS,
        title="Empirical Coverage — Verified, Not Asserted",
        body=(
            "MAPIE conformal prediction (Vovk et al. 2005, Lei et al. 2018) carries "
            "a finite-sample coverage theorem: <strong>P(Y ∈ C(X)) ≥ 1 − α for "
            "exchangeable data.</strong> We don't claim 90% coverage — we measure "
            "it, every batch. Calibrated runs land at 91–92%. The mathematics is "
            "empirically validated against held-out actuals."
        ),
        look_for="The Empirical Coverage stat card shows the live measurement.",
    ),
    TourStep(
        page=PAGE_TIME_TRAVEL,
        anchor_id=ANCHOR_FORECAST,
        title="30-Day Forecast With 90% Conformal Bands",
        body=(
            "A real LightGBM forecast for the selected route, with the conformal "
            "prediction band drawn on top. Move the slider back in time — the chart "
            "re-renders the historical band exactly as the model wrote it on that "
            "day. <strong>Six committed model versions live in this database. "
            "You're looking at one of them right now.</strong>"
        ),
        look_for="The chart is reconstructed live from MariaDB temporal history.",
    ),
    # ─── Beat 5: The killer moment ────────────────────────────────────
    TourStep(
        page=PAGE_COVERAGE,
        anchor_id=ANCHOR_DRIFT,
        title="Drift Detection — One SQL Query",
        body=(
            "Six bootstrap batches. Four calibrated near 91–92%. <strong>On batch 5, "
            "a simulated distribution shift crashed coverage to 58%. On batch 6, it "
            "stayed broken.</strong> The detection itself is one line of SQL: "
            "<code>SELECT AVG(coverage_score) FROM forecasts FOR SYSTEM_TIME ALL "
            "GROUP BY forecast_run_id</code>. No external monitoring service. No "
            "custom dashboard. <strong>The database itself caught the drift.</strong>"
        ),
        look_for="The chart shows coverage by batch — watch the cliff at batch 5.",
    ),
    # ─── Beat 6: Architecture & differentiation (2 steps) ────────────
    TourStep(
        page=PAGE_ABOUT,
        anchor_id=ANCHOR_ARCHITECTURE,
        title="Five Layers, Zero External Dependencies",
        body=(
            "Ingestion, MariaDB with system versioning, ML pipeline, query layer, "
            "Streamlit. <strong>Notably absent: MLflow, Weights & Biases, DataDog, "
            "any external tracking server.</strong> The <code>forecasts</code> "
            "table is system-versioned at write time — the audit trail is "
            "structural, not bolted-on."
        ),
        look_for="The architecture diagram shows every component end to end.",
    ),
    TourStep(
        page=PAGE_ABOUT,
        anchor_id=ANCHOR_COMPARISON,
        title="Vs. The Standard MLOps Stack",
        body=(
            "A typical pipeline = MLflow + Evidently AI + custom dashboards + app "
            "audit log. <strong>Sync gaps. Custom drift code. Replay infrastructure.</strong> "
            "FlightCast: atomic at <code>INSERT</code>, drift in one SQL query, "
            "time-travel via <code>FOR SYSTEM_TIME</code>. <strong>The moat is the "
            "math layer, not the slider.</strong> Coverage of 91% is provable; "
            "collapse to 58% is one query away."
        ),
        look_for="The comparison table makes the differentiation explicit.",
    ),
    # ─── Beat 7: Close ────────────────────────────────────────────────
    TourStep(
        page=PAGE_ABOUT,
        anchor_id=ANCHOR_CLOSE,
        title="Open Infrastructure",
        body=(
            "FlightCast is MIT-licensed. Real-data prototypes, per-tier MAPIE "
            "recalibration, and Apache Airflow integration are open issues — any "
            "team can fork. <strong>The temporal-tables × conformal-prediction "
            "intersection is now public infrastructure for the MariaDB ecosystem.</strong> "
            "That's what FlightCast hopes to add. Click <em>Finish</em> to return "
            "to the dashboard."
        ),
        look_for=None,
    ),
]


# ─── State management ────────────────────────────────────────────────


def init_tour_state() -> None:
    """Initialise tour state keys. Idempotent — safe to call on every rerun."""
    st.session_state.setdefault("tour_active", False)
    st.session_state.setdefault("tour_step", 0)


def start_tour() -> None:
    """Begin the tour from step 0. Switches to the first step's page."""
    st.session_state.tour_active = True
    st.session_state.tour_step = 0
    st.switch_page(TOUR_STEPS[0].page)


def stop_tour() -> None:
    """End the tour and reset progress."""
    st.session_state.tour_active = False
    st.session_state.tour_step = 0


def _advance(delta: int) -> None:
    """Internal: move step by ±1 and switch page if needed."""
    new_idx = st.session_state.tour_step + delta
    if new_idx < 0 or new_idx >= len(TOUR_STEPS):
        return
    st.session_state.tour_step = new_idx
    next_page = TOUR_STEPS[new_idx].page
    try:
        st.switch_page(next_page)
    except Exception:
        st.rerun()


# ─── DOM helpers ─────────────────────────────────────────────────────


def tour_anchor(anchor_id: str) -> None:
    """
    Place an invisible scroll-target marker. Call this in a page file
    just before the element a tour step should scroll to.

        from flightcast.ui.tour import tour_anchor, ANCHOR_SLIDER
        tour_anchor(ANCHOR_SLIDER)
        st.select_slider(...)

    The CSS rule .fc-tour-anchor (in style.py) gives the anchor a
    scroll-margin-top so the target lands below the tour banner instead
    of behind it.
    """
    st.markdown(
        f'<div id="{anchor_id}" class="fc-tour-anchor"></div>',
        unsafe_allow_html=True,
    )


def _scroll_to_anchor(anchor_id: str) -> None:
    """
    Inject a same-origin iframe that calls scrollIntoView() on the
    parent document. The iframe is invisible (height=0). The retry
    loop handles the case where this script runs before the anchor
    div has been mounted.
    """
    components.html(
        f"""
        <script>
            (function() {{
                let attempts = 0;
                function tryScroll() {{
                    const doc = window.parent.document;
                    const el = doc.getElementById("{anchor_id}");
                    if (el) {{
                        el.scrollIntoView({{block: 'start', behavior: 'smooth'}});
                        return;
                    }}
                    attempts += 1;
                    if (attempts < 30) {{
                        setTimeout(tryScroll, 100);
                    }}
                }}
                setTimeout(tryScroll, 200);
            }})();
        </script>
        """,
        height=0,
    )


# ─── Banner rendering ────────────────────────────────────────────────


def render_tour_banner(current_page: str) -> None:
    """
    Render the sticky tour banner if a tour is active. Call at the top of
    each page, BEFORE any other content, with the page identifier (one of
    the PAGE_* constants).
    """
    init_tour_state()
    if not st.session_state.tour_active:
        return

    step_idx: int = st.session_state.tour_step
    step = TOUR_STEPS[step_idx]
    total = len(TOUR_STEPS)

    # If the active step belongs to a different page, navigate there.
    if step.page != current_page:
        try:
            st.switch_page(step.page)
            return
        except Exception:
            return

    eyebrow = (
        f"PITCH TOUR · STEP {step_idx + 1} OF {total} · "
        f"{PAGE_LABELS.get(step.page, '')}"
    )
    look_for_html = (
        f'<div class="fc-tour-hint">{step.look_for}</div>' if step.look_for else ""
    )
    st.markdown(
        f"""
        <div class="fc-tour-banner">
          <div class="fc-tour-eyebrow">{eyebrow}</div>
          <div class="fc-tour-title">{step.title}</div>
          <div class="fc-tour-body">{step.body}</div>
          {look_for_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    is_first = step_idx == 0
    is_last = step_idx == total - 1

    c_back, c_skip, _, c_next = st.columns([1, 1, 2, 1])
    with c_back:
        if st.button(
            "Back",
            disabled=is_first,
            key=f"tour_back_{step_idx}",
            use_container_width=True,
        ):
            _advance(-1)
    with c_skip:
        if st.button(
            "Skip Tour",
            key=f"tour_skip_{step_idx}",
            use_container_width=True,
        ):
            stop_tour()
            st.rerun()
    with c_next:
        next_label = "Finish" if is_last else "Next"
        if st.button(
            next_label,
            type="primary",
            key=f"tour_next_{step_idx}",
            use_container_width=True,
        ):
            if is_last:
                stop_tour()
                st.toast("Tour complete — thanks for exploring FlightCast.")
                st.rerun()
            else:
                _advance(1)

    st.markdown("---")

    # Trigger the scroll AFTER the banner + buttons render, so the
    # iframe has time to mount and the anchor below is in the DOM.
    if step.anchor_id:
        _scroll_to_anchor(step.anchor_id)


# ─── Sidebar trigger ─────────────────────────────────────────────────


def render_sidebar_trigger() -> None:
    """
    Render the 'Start Pitch Tour' button. Call once per page (the
    function uses st.sidebar.* directly so it doesn't need to be inside
    a `with st.sidebar:` block).
    """
    init_tour_state()
    if st.session_state.tour_active:
        step_idx = st.session_state.tour_step
        st.sidebar.markdown(
            f'<div class="fc-tour-sidebar-active">Tour in progress · step '
            f"{step_idx + 1} of {len(TOUR_STEPS)}</div>",
            unsafe_allow_html=True,
        )
        if st.sidebar.button("End Tour", use_container_width=True, key="tour_end_sidebar"):
            stop_tour()
            st.rerun()
    else:
        if st.sidebar.button(
            "Start Pitch Tour",
            type="primary",
            use_container_width=True,
            key="tour_start_sidebar",
        ):
            start_tour()
        st.sidebar.caption("9 steps · ~5 min · click-through narration")

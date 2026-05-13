"""
FlightCast Streamlit entry point.
Run: streamlit run src/flightcast/ui/app.py
"""
import streamlit as st

from flightcast.ui.style import apply_global_styles

st.set_page_config(
    page_title="FlightCast — Database-Native ML Audit",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": (
            "**FlightCast** — Aviation demand forecasting with MariaDB "
            "system-versioned temporal tables and MAPIE conformal prediction. "
            "MariaDB Hackathon Malaysia 2026 · Innovation Track."
        ),
    },
)

apply_global_styles()

pages = [
    st.Page("pages/02_time_travel.py",    title="Time Travel",       default=True),
    st.Page("pages/01_forecast.py",       title="Forecast Explorer"),
    st.Page("pages/03_coverage_drift.py", title="Coverage Drift"),
    st.Page("pages/04_about.py",          title="How It Works"),
]

st.navigation(pages).run()

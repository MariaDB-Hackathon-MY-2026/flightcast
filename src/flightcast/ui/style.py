"""
Global Streamlit polish layer for FlightCast.

`apply_global_styles()` injects:
  - Inter / JetBrains Mono web fonts
  - Refined dark theme overrides on top of Streamlit's default dark mode
  - Sharper typography hierarchy (h1/h2/h3 + small-caps eyebrow text)
  - Card-style metric containers, badges, and code blocks
  - Subtle background gradient for depth on the hero page

Call once from `app.py` before navigation. Each page calls `page_header()`
to render the small-caps eyebrow + title + subtitle block.
"""
from __future__ import annotations

import streamlit as st


_GLOBAL_CSS = """
<style>
  /* ───────────── Web fonts ───────────── */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

  /* ───────────── Page chrome ───────────── */
  html, body, [class*="st-"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  .stApp {
    background:
      radial-gradient(1200px 600px at 0% 0%, rgba(96,165,250,0.08), transparent 60%),
      radial-gradient(900px 500px at 100% 0%, rgba(167,139,250,0.06), transparent 55%),
      #0B1220;
  }

  /* Tighten top padding */
  .main .block-container {
    padding-top: 2rem;
    padding-bottom: 4rem;
    max-width: 1200px;
  }

  /* Hide Streamlit's "Deploy" button and hamburger redundancies */
  [data-testid="stToolbar"] { right: 0.5rem; }
  [data-testid="stDecoration"] { display: none; }
  footer { visibility: hidden; }
  #MainMenu { visibility: visible; }

  /* ───────────── Sidebar ───────────── */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0E172A 0%, #0B1220 100%);
    border-right: 1px solid rgba(148,163,184,0.10);
  }
  [data-testid="stSidebarNav"] ul li a {
    border-radius: 8px;
    margin: 2px 4px;
  }
  [data-testid="stSidebarNav"] ul li a:hover {
    background: rgba(96,165,250,0.08);
  }

  /* ───────────── Typography ───────────── */
  h1, .fc-h1 {
    font-family: 'Inter', sans-serif;
    font-weight: 800;
    letter-spacing: -0.025em;
    line-height: 1.05;
    color: #F8FAFC;
    margin: 0;
  }
  h2, .fc-h2 {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #E5E7EB;
  }
  h3 {
    font-weight: 600;
    color: #CBD5E1;
  }

  .fc-eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-size: 0.72rem;
    font-weight: 600;
    color: #60A5FA;
    margin-bottom: 0.4rem;
  }
  .fc-subtitle {
    color: #94A3B8;
    font-size: 1.02rem;
    font-weight: 400;
    margin-top: 0.4rem;
  }

  /* ───────────── Hero header ───────────── */
  .fc-hero {
    padding: 1.4rem 0 1.2rem 0;
    border-bottom: 1px solid rgba(148,163,184,0.10);
    margin-bottom: 1.6rem;
  }

  /* ───────────── Status pills ───────────── */
  .fc-pills { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.8rem; }
  .fc-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.28rem 0.7rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 500;
    border: 1px solid rgba(148,163,184,0.18);
    background: rgba(15,23,42,0.6);
    color: #CBD5E1;
  }
  .fc-pill .fc-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #34D399;
    box-shadow: 0 0 8px rgba(52,211,153,0.7);
  }
  .fc-pill.fc-pill-blue   { border-color: rgba(96,165,250,0.35); color: #93C5FD; background: rgba(30,58,138,0.18); }
  .fc-pill.fc-pill-violet { border-color: rgba(167,139,250,0.35); color: #C4B5FD; background: rgba(76,29,149,0.18); }
  .fc-pill.fc-pill-amber  { border-color: rgba(251,191,36,0.30); color: #FCD34D; background: rgba(120,53,15,0.18); }

  /* ───────────── Metrics ───────────── */
  [data-testid="stMetric"] {
    background: linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0.0));
    border: 1px solid rgba(148,163,184,0.12);
    border-radius: 12px;
    padding: 0.7rem 0.85rem;
    overflow: hidden;
  }
  [data-testid="stMetricLabel"] {
    color: #94A3B8 !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  [data-testid="stMetricValue"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: #F8FAFC !important;
    letter-spacing: -0.02em;
    white-space: nowrap;
  }
  [data-testid="stMetricDelta"] {
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    white-space: nowrap;
  }
  [data-testid="stMetricDelta"] > div {
    white-space: nowrap !important;
    overflow: visible !important;
  }

  /* ───────────── Code blocks ───────────── */
  pre, code, .stCode, [data-testid="stCode"] {
    font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace !important;
  }
  [data-testid="stCode"] {
    border-radius: 10px;
    border: 1px solid rgba(148,163,184,0.12);
    background: rgba(8,12,22,0.65) !important;
  }
  [data-testid="stCode"] pre {
    background: transparent !important;
    padding: 1rem 1.1rem !important;
    font-size: 0.82rem !important;
    line-height: 1.55 !important;
  }

  /* ───────────── Expanders ───────────── */
  [data-testid="stExpander"] {
    border: 1px solid rgba(148,163,184,0.12);
    border-radius: 10px;
    background: rgba(15,23,42,0.35);
  }
  [data-testid="stExpander"] summary {
    font-weight: 500;
    color: #CBD5E1;
  }

  /* ───────────── Inputs ───────────── */
  [data-baseweb="select"] > div {
    background: rgba(15,23,42,0.6) !important;
    border: 1px solid rgba(148,163,184,0.18) !important;
    border-radius: 8px !important;
  }
  [data-baseweb="select"] > div:hover {
    border-color: rgba(96,165,250,0.45) !important;
  }

  /* ───────────── Slider (bordered card to match .fc-stat / .fc-callout) ───────────── */
  [data-testid="stSlider"] {
    border: 1px solid rgba(148,163,184,0.12);
    border-radius: 10px;
    padding: 1.0rem 1.2rem 1.2rem 1.2rem;
    background: rgba(15,23,42,0.45);
    margin: 0.6rem 0 0.4rem 0;
    width: 100% !important;
    box-sizing: border-box !important;
  }
  /* Force the slider's parent block AND inner BaseWeb slider to span full width */
  [data-testid="stSlider"] > div,
  [data-testid="stSlider"] > div > div,
  [data-testid="stSlider"] [data-baseweb="slider"],
  div:has(> [data-testid="stSlider"]),
  [data-testid="stElementContainer"]:has([data-testid="stSlider"]) {
    width: 100% !important;
    max-width: 100% !important;
  }
  [data-testid="stSlider"] [role="slider"] {
    background: #60A5FA !important;
    box-shadow: 0 0 0 4px rgba(96,165,250,0.18) !important;
  }
  /* Slider label "Audit point in time" — match .fc-stat-label small-caps */
  [data-testid="stSlider"] label {
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94A3B8 !important;
  }

  /* ───────────── Info / warning / success boxes ───────────── */
  .stAlert {
    border-radius: 10px;
    border: 1px solid rgba(148,163,184,0.15);
  }

  /* ───────────── Pitch tour: scroll-target anchors ───────────── */
  .fc-tour-anchor {
    height: 0;
    pointer-events: none;
    visibility: hidden;
    /* Browser scrolls so the anchor lands this many px from viewport top —
       leaves room for the page header above the target element */
    scroll-margin-top: 80px;
  }

  /* ───────────── Pitch tour banner ───────────── */
  .fc-tour-banner {
    background: linear-gradient(135deg, rgba(167,139,250,0.14), rgba(96,165,250,0.08));
    border: 1px solid rgba(167,139,250,0.35);
    border-left: 4px solid #A78BFA;
    border-radius: 12px;
    padding: 1.1rem 1.3rem 1.2rem 1.3rem;
    color: #E2E8F0;
    margin: 0.4rem 0 0.8rem 0;
    box-shadow: 0 4px 18px rgba(167,139,250,0.10);
  }
  .fc-tour-eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    color: #C4B5FD;
    text-transform: uppercase;
    margin-bottom: 0.55rem;
  }
  .fc-tour-title {
    font-size: 1.35rem;
    font-weight: 700;
    color: #F8FAFC;
    line-height: 1.25;
    margin: 0 0 0.55rem 0;
  }
  .fc-tour-body {
    color: #CBD5E1;
    font-size: 0.96rem;
    line-height: 1.6;
  }
  .fc-tour-body strong { color: #F1F5F9; }
  .fc-tour-body em { color: #DDD6FE; font-style: normal; }
  .fc-tour-body code {
    background: rgba(15,23,42,0.7);
    color: #C4B5FD;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 0.86em;
    font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
  }
  .fc-tour-hint {
    margin-top: 0.85rem;
    padding: 0.5rem 0.8rem;
    background: rgba(245,158,11,0.10);
    border-left: 3px solid #F59E0B;
    border-radius: 4px;
    color: #FCD34D;
    font-size: 0.88rem;
    font-weight: 500;
  }
  .fc-tour-sidebar-active {
    padding: 0.5rem 0.7rem;
    background: rgba(167,139,250,0.12);
    border: 1px solid rgba(167,139,250,0.30);
    border-radius: 8px;
    color: #C4B5FD;
    font-size: 0.82rem;
    font-weight: 600;
    text-align: center;
    margin-bottom: 0.6rem;
  }

  /* ───────────── Hero callout box ───────────── */
  .fc-callout {
    background: linear-gradient(135deg, rgba(96,165,250,0.10), rgba(167,139,250,0.06));
    border: 1px solid rgba(96,165,250,0.22);
    border-radius: 12px;
    padding: 0.95rem 1.1rem;
    color: #E2E8F0;
    font-size: 0.94rem;
    margin-top: 1rem;
  }
  .fc-callout strong { color: #F1F5F9; }
  .fc-callout code {
    background: rgba(15,23,42,0.7);
    color: #93C5FD;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 0.84em;
  }

  /* ───────────── Stats strip ───────────── */
  .fc-statstrip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.7rem;
    margin: 1.2rem 0 0.6rem 0;
  }
  .fc-stat {
    border: 1px solid rgba(148,163,184,0.12);
    border-radius: 10px;
    padding: 0.8rem 0.95rem;
    background: rgba(15,23,42,0.45);
  }
  .fc-stat .fc-stat-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #94A3B8;
    font-weight: 600;
  }
  .fc-stat .fc-stat-value {
    font-size: 1.35rem;
    font-weight: 700;
    color: #F8FAFC;
    margin-top: 0.2rem;
    letter-spacing: -0.02em;
  }
  .fc-stat .fc-stat-hint {
    font-size: 0.78rem;
    color: #94A3B8;
    margin-top: 0.15rem;
  }

  /* ───────────── Section divider ───────────── */
  hr {
    border-color: rgba(148,163,184,0.10);
    margin: 1.8rem 0;
  }

  /* ───────────── Tooltips on Plotly ───────────── */
  .modebar { opacity: 0.35 !important; }
  .modebar:hover { opacity: 1 !important; }
</style>
"""


def apply_global_styles() -> None:
    """Inject the global CSS once at app boot."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def page_header(
    eyebrow: str,
    title: str,
    subtitle: str | None = None,
    pills: list[tuple[str, str]] | None = None,
) -> None:
    """
    Render a polished page header.

    `pills` is a list of (label, variant) tuples where variant is one of:
    'default', 'blue', 'violet', 'amber'. The first pill always shows a
    pulsing live-status dot.
    """
    pills_html = ""
    if pills:
        rendered = []
        for i, (label, variant) in enumerate(pills):
            cls = "fc-pill"
            if variant in {"blue", "violet", "amber"}:
                cls += f" fc-pill-{variant}"
            dot = '<span class="fc-dot"></span>' if i == 0 else ""
            rendered.append(f'<span class="{cls}">{dot}{label}</span>')
        pills_html = f'<div class="fc-pills">{"".join(rendered)}</div>'

    subtitle_html = (
        f'<div class="fc-subtitle">{subtitle}</div>' if subtitle else ""
    )

    st.markdown(
        f"""
        <div class="fc-hero">
          <div class="fc-eyebrow">{eyebrow}</div>
          <h1 class="fc-h1">{title}</h1>
          {subtitle_html}
          {pills_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def callout(html: str) -> None:
    """Render a hero callout box (used for the value-prop one-liner)."""
    st.markdown(f'<div class="fc-callout">{html}</div>', unsafe_allow_html=True)


def stat_strip(stats: list[tuple[str, str, str | None]]) -> None:
    """
    Render a horizontal strip of stat cards.

    `stats` is a list of (label, value, hint) tuples. hint may be None.
    """
    items = []
    for label, value, hint in stats:
        hint_html = f'<div class="fc-stat-hint">{hint}</div>' if hint else ""
        items.append(
            f'<div class="fc-stat">'
            f'<div class="fc-stat-label">{label}</div>'
            f'<div class="fc-stat-value">{value}</div>'
            f'{hint_html}'
            f'</div>'
        )
    st.markdown(
        f'<div class="fc-statstrip">{"".join(items)}</div>',
        unsafe_allow_html=True,
    )

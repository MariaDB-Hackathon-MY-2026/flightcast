/**
 * Source-of-truth pitch copy for the FlightCast guided tour.
 * Treat as marketing copy under version control — review in PRs.
 *
 * THE TOUR IS THE DEMO VIDEO STORYBOARD.
 * Each step = one scene. Click "Next" while recording voice-over.
 *
 * 18 steps total. Bodies are intentionally short (max 2 sentences) so
 * the popover is glanceable; the page itself does the heavy explaining.
 *
 * Pattern: each step declares the route to navigate to, a CSS selector
 * for the element to highlight, and the popover copy. The tour engine
 * (GuidedTour.tsx) auto-picks the popover position based on available
 * viewport space — no manual placement needed.
 *
 * Editing principles:
 *   1. Every body is at most 2 sentences. Short, plain language.
 *   2. No em-dashes or en-dashes in the body copy. Use periods, commas,
 *      semicolons, parentheses, or colons instead.
 *   3. Every step surfaces the MariaDB advantage at least once.
 *   4. Anchors wrap the FULL element being explained (heading +
 *      diagram, heading + table, heading + math) so the white ring
 *      surrounds what the user is reading about.
 */

export interface TourStep {
  route: string | null;            // null = stay on current page
  target: string;                  // CSS selector, prefer .tour-anchor-* classes
  title: string;                   // ≤ 6 words, pitch-grade
  content: string;                 // 1-2 sentences, plain text (no HTML)
  fallback?: { top: number; left: number };
}

export const TOUR_STEPS: TourStep[] = [
  // ─── 1 ─────────────────────────────────────────────────────────────
  {
    route: "/time-travel",
    target: ".tour-anchor-audit-gap",
    title: "The ML audit problem",
    content:
      "Production ML retrains every week and overwrites yesterday's predictions. Most teams cannot answer 'what did the model predict on January 15th?'; FlightCast answers it with one SQL query.",
  },

  // ─── 2 ─────────────────────────────────────────────────────────────
  {
    route: "/time-travel",
    target: ".tour-anchor-callout",
    title: "Ask MariaDB",
    content:
      "FOR SYSTEM_TIME AS OF is five SQL keywords from the SQL:2011 standard. MariaDB ships it natively, while MySQL fails to parse it and PostgreSQL needs a third party extension.",
  },

  // ─── 3 ─────────────────────────────────────────────────────────────
  {
    route: "/time-travel",
    target: ".tour-anchor-slider",
    title: "Drag the audit slider",
    content:
      "Each tick on this slider is a real ROW_START timestamp from a committed MariaDB transaction. Drag it left and the chart re-issues the query at that exact moment in history.",
  },

  // ─── 4 ─────────────────────────────────────────────────────────────
  {
    route: "/time-travel",
    target: ".tour-anchor-stats",
    title: "Coverage you can verify",
    content:
      "Four KPIs from the selected batch, including empirical coverage measured against ground truth. MAPIE guarantees that at least 90% of actual demand falls inside the band, and calibrated runs land at 91 to 92%.",
  },

  // ─── 5 ─────────────────────────────────────────────────────────────
  {
    route: "/time-travel",
    target: ".tour-anchor-forecast",
    title: "30 day forecast and band",
    content:
      "A real LightGBM 30 day forecast for the selected route, with the violet 90% conformal band drawn on top. Toggle 'Show actuals' and amber dots appear inside the band, validating the coverage guarantee live.",
  },

  // ─── 6 ─────────────────────────────────────────────────────────────
  {
    route: "/time-travel",
    target: ".tour-anchor-live-sql",
    title: "Live SQL bridge",
    content:
      "This is not a render of the SQL; it is the exact query that just produced the chart above. Copy it into any MariaDB 11.8 client and you get back the same 30 rows.",
  },

  // ─── 7 ─────────────────────────────────────────────────────────────
  {
    route: "/forecast-explorer",
    target: ".tour-anchor-all-history",
    title: "Six versions, one query",
    content:
      "Click 'All history' in the View mode picker above to overlay six committed model versions in six colors. Behind it is a single FOR SYSTEM_TIME ALL query, no Python loop and no MLflow API calls.",
  },

  // ─── 8 ─────────────────────────────────────────────────────────────
  {
    route: "/forecast-explorer",
    target: ".tour-anchor-all-history",
    title: "What the rainbow shows",
    content:
      "Each colored ribbon is one committed model version with its own 90% confidence band. Where the bands stack tightly together coverage held; where they spread apart you are seeing drift in real time.",
  },

  // ─── 9 ─────────────────────────────────────────────────────────────
  {
    route: "/forecast-explorer",
    target: ".tour-anchor-feature-card",
    title: "MariaDB exclusive primitives",
    content:
      "FOR SYSTEM_TIME AS OF and FOR SYSTEM_TIME ALL are both native to MariaDB. MySQL has neither, PostgreSQL needs the temporal_tables extension, and SQLite has nothing equivalent.",
  },

  // ─── 10 ────────────────────────────────────────────────────────────
  {
    route: "/coverage-drift",
    target: ".tour-anchor-methodology",
    title: "The drift methodology",
    content:
      "Runs 1 to 4 use σ = 0.10 noise on the synthetic actuals; runs 5 and 6 use σ = 0.22, simulating a fuel price shock. Expected outcome: 1 to 4 hold near 90% coverage, 5 and 6 collapse, and the data below confirms it.",
  },

  // ─── 11 ────────────────────────────────────────────────────────────
  {
    route: "/coverage-drift",
    target: ".tour-anchor-drift-chart",
    title: "Drift caught by one query",
    content:
      "4 of 6 runs sit at 91.2% coverage; 2 of 6 collapsed to 58.7%. Behind these tiles is one GROUP BY against FOR SYSTEM_TIME ALL, with no MLflow tracking server and no shadow tables.",
  },

  // ─── 12 ────────────────────────────────────────────────────────────
  {
    route: "/coverage-drift",
    target: ".tour-anchor-winkler",
    title: "Winkler interval score",
    content:
      "Coverage tells you whether actuals fell inside the band; Winkler tells you how good the band was, with lower being better. Runs 1 to 4 sit around 7,300; runs 5 and 6 jump to 24,000, a 3.3 times escalation caught before coverage breaks.",
  },

  // ─── 13 NEW ────────────────────────────────────────────────────────
  {
    route: "/coverage-drift",
    target: ".tour-anchor-diff",
    title: "Prediction diff between batches",
    content:
      "Pick two committed model versions and a route to see what changed day by day. The bars show the per-date delta, and the SQL behind it is one self join across two FOR SYSTEM_TIME AS OF snapshots, no Python diffing required.",
  },

  // ─── 14 ────────────────────────────────────────────────────────────
  {
    route: "/how-it-works",
    target: ".tour-anchor-architecture",
    title: "Five layers, zero deps",
    content:
      "Five layers: ingestion, MariaDB with system versioning, ML pipeline, query layer, dashboard. Notably absent: MLflow, Weights & Biases, DataDog, Evidently; the audit trail is structural, not bolted on.",
  },

  // ─── 15 ────────────────────────────────────────────────────────────
  {
    route: "/how-it-works",
    target: ".tour-anchor-comparison",
    title: "Vs. the standard MLOps stack",
    content:
      "The right column shows what FlightCast replaces: tracking servers, custom drift dashboards, replay infrastructure, and shadow tables. The bottom line: the moat is the math layer, not the slider.",
  },

  // ─── 16 NEW ────────────────────────────────────────────────────────
  {
    route: "/how-it-works",
    target: ".tour-anchor-hero-sql",
    title: "Five MariaDB only queries",
    content:
      "Five copy and run queries: time travel, prediction diff, full audit log, calibration drift, and great circle distance. Every one of them fails to parse on MySQL or PostgreSQL, so this section is the moat in code form.",
  },

  // ─── 17 ────────────────────────────────────────────────────────────
  {
    route: "/how-it-works",
    target: ".tour-anchor-math",
    title: "The conformal math",
    content:
      "The formula on screen is MAPIE's conformal interval and its coverage theorem. For exchangeable data, at least 90% of actual values land inside the predicted band; that is what 'guaranteed 90% coverage' means.",
  },

  // ─── 18 ────────────────────────────────────────────────────────────
  {
    route: "/how-it-works",
    target: ".tour-anchor-close",
    title: "Open infrastructure",
    content:
      "FlightCast is MIT licensed; per tier MAPIE recalibration, real data prototypes, and Apache Airflow integration are listed open issues. Built by Low Yan Cheng (TP070056) at APU Malaysia, for the MariaDB Hackathon Malaysia 2026.",
  },
];

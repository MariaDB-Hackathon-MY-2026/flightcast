import Image from "next/image";
import { PageHeader } from "@/components/layout/PageHeader";
import { SqlPanel } from "@/components/common/SqlPanel";

/**
 * HOW IT WORKS — port of src/flightcast/ui/pages/04_about.py.
 *
 * Tour anchors (matching TOUR_STEPS steps 7, 8, 9):
 *   .tour-anchor-architecture  → the architecture diagram
 *   .tour-anchor-comparison    → "Vs. Standard MLOps" table
 *   .tour-anchor-close         → "For judges & reviewers" closing section
 *
 * Sections (top → bottom):
 *   1. Intro paragraph
 *   2. Comparison table vs. the standard MLOps stack
 *   3. MariaDB-exclusive syntax callout (FOR SYSTEM_TIME ALL)
 *   4. System architecture diagram
 *   5. Five hero SQL queries (collapsible)
 *   6. Conformal Prediction math section
 *   7. "For judges & reviewers" links + credits
 */
export default function HowItWorksPage() {
  return (
    <>
      <PageHeader
        eyebrow="MariaDB Hackathon Malaysia 2026 · Innovation Track"
        title="How FlightCast works"
        subtitle="The architecture, the math, and the MariaDB-exclusive primitives behind the audit trail."
        pills={[
          { label: "Architecture" },
          { label: "MariaDB 11.8", variant: "blue" },
          { label: "Conformal prediction", variant: "violet" },
        ]}
      />

      <p className="text-slate-300 leading-relaxed mb-6">
        <strong className="text-slate-100">FlightCast</strong> is an aviation
        demand forecasting system that uses{" "}
        <a
          href="https://mariadb.com/kb/en/system-versioned-tables/"
          className="text-accent-blue underline"
        >
          MariaDB System-Versioned Temporal Tables
        </a>{" "}
        as its audit backbone and{" "}
        <a
          href="https://mapie.readthedocs.io/"
          className="text-accent-blue underline"
        >
          MAPIE conformal prediction
        </a>{" "}
        to provide <strong>mathematically guaranteed 90% coverage intervals</strong>.
      </p>

      {/* Comparison — wrapper covers heading + table so the tour highlight surrounds both */}
      <div className="tour-anchor-comparison mt-2">
      <h2 className="text-xl font-semibold text-slate-100 mb-3">
        What makes FlightCast different from standard MLOps tooling?
      </h2>
      <div className="overflow-x-auto fc-stat mb-8">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400">
              <th className="text-left py-2 px-2"></th>
              <th className="text-left py-2 px-2">
                Standard MLOps stack (MLflow / W&B + app audit log)
              </th>
              <th className="text-left py-2 px-2 text-slate-100">FlightCast</th>
            </tr>
          </thead>
          <tbody className="text-slate-300">
            {[
              ["Audit substrate", "External tracking server + shadow tables", "Database-native, zero extra infra"],
              ["Versioning latency", "Sync gap between write and log", "Atomic at INSERT time"],
              ["Coverage guarantee", "Not enforced", "MAPIE conformal · ≥90% finite-sample"],
              ["Drift detection", "Custom dashboards / Python jobs", "One SQL query: FOR SYSTEM_TIME ALL"],
              ["Time-travel SQL", "Not available — must replay logs", "5 MariaDB-exclusive temporal queries"],
            ].map((row, i) => (
              <tr key={i} className="border-t border-white/5">
                <td className="py-2 px-2 text-slate-400">{row[0]}</td>
                <td className="py-2 px-2">{row[1]}</td>
                <td className="py-2 px-2 text-slate-100">{row[2]}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-4 text-slate-100 font-semibold">
          The moat is the math layer, not the slider.
        </p>
      </div>
      </div>

      {/* MariaDB-exclusive syntax callout */}
      <div className="fc-callout mb-8" style={{ borderLeft: "4px solid #60A5FA" }}>
        <div className="fc-eyebrow mb-2">The MariaDB-exclusive syntax</div>
        <code className="block bg-bg-deep text-slate-200 p-3 rounded text-sm border border-white/10 font-mono">
          SELECT AVG(coverage_score) FROM forecasts FOR SYSTEM_TIME ALL GROUP BY forecast_run_id;
        </code>
        <p className="mt-3 text-slate-300 text-sm leading-relaxed">
          <strong className="text-slate-100">FOR SYSTEM_TIME ALL</strong> returns
          every historical version of every row — a SQL extension defined in
          the SQL:2011 standard. MariaDB implements it natively;{" "}
          <strong>MySQL does not, PostgreSQL needs an extension,</strong> and
          SQLite has no equivalent at all. This single keyword is what lets
          FlightCast audit prediction coverage with one query instead of an
          external MLflow / W&amp;B service.
        </p>
      </div>

      {/* Architecture — wrapper covers heading + diagram so the tour highlight surrounds both */}
      <div className="tour-anchor-architecture mt-8">
      <h2 className="text-xl font-semibold text-slate-100 mb-3">
        System Architecture
      </h2>
      <div className="fc-stat overflow-hidden">
        <Image
          src="/architecture.png"
          alt="FlightCast system architecture: Ingestion → MariaDB → ML pipeline → Repository → Streamlit"
          width={1920}
          height={1080}
          className="w-full h-auto rounded"
          priority
        />
        <p className="text-sm text-slate-400 mt-3">
          Layered architecture with MariaDB as the central state store. The
          forecasts table is system-versioned, so the dashboard can query any
          past prediction state with <code>FOR SYSTEM_TIME AS OF</code>. No
          external audit log required.
        </p>
      </div>
      </div>

      {/* ── 5 hero SQL accordions — wrapped so the tour highlight covers heading + queries ── */}
      <hr className="border-white/10 my-10" />
      <div className="tour-anchor-hero-sql">
      <h2 className="text-xl font-semibold text-slate-100 mb-1">
        Hero SQL Queries
      </h2>
      <p className="text-sm text-slate-400 mb-4">
        All five use MariaDB-exclusive syntax. None of these run on MySQL or
        PostgreSQL.
      </p>

      {[
        {
          title:
            "1 — Time-travel: what did the model predict on a given date?",
          sql: `SELECT route_id, forecast_date,
       predicted_demand, lower_bound, upper_bound, model_version,
       ROW_START, ROW_END
FROM forecasts FOR SYSTEM_TIME AS OF '2026-02-01 10:32:14.000000'
WHERE route_id = 123
ORDER BY forecast_date;`,
        },
        {
          title:
            "2 — Prediction diff: how did forecasts change between two model versions?",
          sql: `SELECT a.forecast_date,
       a.predicted_demand AS predicted_v1,
       b.predicted_demand AS predicted_v2,
       b.predicted_demand - a.predicted_demand AS delta
FROM
  (SELECT * FROM forecasts FOR SYSTEM_TIME AS OF '2026-01-15 09:00:00' WHERE route_id = 123) a
JOIN
  (SELECT * FROM forecasts FOR SYSTEM_TIME AS OF '2026-02-15 09:00:00' WHERE route_id = 123) b
  ON a.forecast_date = b.forecast_date
ORDER BY a.forecast_date;`,
        },
        {
          title: "3 — Full audit log: every version of every prediction row",
          sql: `SELECT forecast_run_id, forecast_date,
       predicted_demand, lower_bound, upper_bound,
       model_version, ROW_START, ROW_END
FROM forecasts FOR SYSTEM_TIME ALL
WHERE route_id = 123
ORDER BY ROW_START, forecast_date;`,
        },
        {
          title:
            "4 — Calibration drift: empirical coverage vs target across batches",
          sql: `SELECT forecast_run_id,
       AVG(coverage_score)              AS empirical_coverage,
       0.90                             AS target,
       AVG(coverage_score) - 0.90       AS drift,
       AVG(upper_bound - lower_bound)   AS mean_interval_width
FROM forecasts FOR SYSTEM_TIME ALL
WHERE coverage_score IS NOT NULL
GROUP BY forecast_run_id
ORDER BY forecast_run_id;`,
        },
        {
          title:
            "5 — MariaDB ST_DISTANCE_SPHERE: great-circle distance as a feature",
          sql: `SELECT r.id AS route_id,
       CONCAT(r.src_airport, ' → ', r.dst_airport) AS route,
       ROUND(ST_DISTANCE_SPHERE(
           POINT(a1.longitude, a1.latitude),
           POINT(a2.longitude, a2.latitude)
       ) / 1000, 1) AS distance_km
FROM routes r
JOIN airports a1 ON r.src_airport = a1.iata
JOIN airports a2 ON r.dst_airport = a2.iata
ORDER BY distance_km DESC
LIMIT 10;`,
        },
      ].map((q, i) => (
        <div key={i} className="mb-2">
          <SqlPanel title={q.title} sql={q.sql} defaultOpen={false} />
        </div>
      ))}
      </div>

      {/* ── Conformal prediction math ──────────────────────────────── */}
      <hr className="border-white/10 my-10" />
      {/* Conformal math — wrapper covers heading + math content for tour highlight */}
      <div className="tour-anchor-math">
      <h2 className="text-xl font-semibold text-slate-100 mb-3">
        Conformal Prediction — the math
      </h2>
      <div className="fc-stat text-slate-300 leading-relaxed space-y-3">
        <p>
          Given a calibration set{" "}
          <code className="text-amber-300">
            {"{(xᵢ, yᵢ)}"} for i = 1…n
          </code>{" "}
          with non-conformity scores{" "}
          <code className="text-amber-300">sᵢ = |yᵢ − f̂(xᵢ)|</code>, the MAPIE
          conformal interval at confidence level{" "}
          <code className="text-amber-300">1 − α</code> is:
        </p>
        <pre className="text-center text-amber-300 font-mono text-sm py-3 my-2 bg-bg-deep rounded border border-white/10">
{`[ f̂(x) − q̂₁₋α ,  f̂(x) + q̂₁₋α ]`}
        </pre>
        <p>
          where <code className="text-amber-300">q̂₁₋α</code> is the{" "}
          <code className="text-amber-300">⌈(1−α)(1 + 1/n)⌉</code>-th empirical
          quantile of the non-conformity scores.
        </p>
        <p>
          <strong className="text-slate-100">Coverage guarantee:</strong>{" "}
          <code className="text-amber-300">
            P(y_{`{n+1}`} ∈ C(x_{`{n+1}`})) ≥ 1 − α
          </code>{" "}
          for exchangeable data. (Vovk et al. 2005, Lei et al. 2018.)
        </p>
        <p className="text-slate-400">
          FlightCast trains on <code>log(1 + demand)</code> and inverts with{" "}
          <code>exp − 1</code>: the log transform is a monotone bijection that
          preserves quantile ordering and enforces non-negativity without
          asymmetric clipping (which would break the coverage guarantee).
        </p>
      </div>
      </div>

      {/* Close — wrapper covers heading + reviewer block for tour highlight */}
      <div className="tour-anchor-close mt-10">
      <h2 className="text-xl font-semibold text-slate-100 mb-3">
        For judges &amp; reviewers
      </h2>
      <div className="text-slate-300 leading-relaxed">
        <p className="mb-3">
          The repository ships two documents specifically for evaluators:
        </p>
        <ul className="list-disc list-inside space-y-1 text-slate-300">
          <li>
            <a
              href="https://github.com/TP070056/flightcast/blob/main/docs/JUDGES_TESTING_GUIDE.md"
              className="text-accent-blue underline"
            >
              docs/JUDGES_TESTING_GUIDE.md
            </a>{" "}
            — four time-budget options (2 min / 5 min / 15 min / 45 min)
          </li>
          <li>
            <a
              href="https://github.com/TP070056/flightcast/blob/main/Elegant.md"
              className="text-accent-blue underline"
            >
              Elegant.md
            </a>{" "}
            — the technical whitepaper (~6,300 words)
          </li>
        </ul>
        <p className="text-slate-400 text-sm mt-6">
          Built by Low Yan Cheng (TP070056) · APU Malaysia · MariaDB Hackathon
          2026
        </p>
      </div>
      </div>
    </>
  );
}

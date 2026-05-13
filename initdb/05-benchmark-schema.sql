-- ============================================================
-- 05-benchmark-schema.sql
-- forecasts_manual: a NON-versioned shadow table that simulates how a
-- team would build prediction history WITHOUT MariaDB system versioning
-- (i.e., manual created_at / expired_at columns + application-level
-- inserts on every UPDATE).
--
-- Used by tests/benchmarks/temporal_benchmark.py to compare
-- FOR SYSTEM_TIME AS OF (native) vs application-managed versioning
-- (manual) on identical data.
-- ============================================================

CREATE TABLE IF NOT EXISTS `forecasts_manual` (
  `manual_id`         BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
  `forecast_run_id`   INT UNSIGNED     NOT NULL,
  `forecast_run_ts`   DATETIME(6)      NOT NULL,
  `route_id`          INT              NOT NULL,
  `forecast_date`     DATE             NOT NULL,
  `predicted_demand`  DOUBLE           NOT NULL,
  `lower_bound`       DOUBLE           NOT NULL,
  `upper_bound`       DOUBLE           NOT NULL,
  `confidence_level`  DOUBLE           NOT NULL DEFAULT 0.90,
  `model_version`     VARCHAR(32)      NOT NULL,
  `coverage_score`    DOUBLE                    DEFAULT NULL,
  `actual_demand`     DOUBLE                    DEFAULT NULL,
  -- Manual versioning: created_at when the row was first written;
  -- expired_at set to the moment a "newer version" supersedes it,
  -- NULL if this is the current version.
  `created_at`        DATETIME(6)      NOT NULL,
  `expired_at`        DATETIME(6)               DEFAULT NULL,
  PRIMARY KEY (`manual_id`),
  -- Same indexes the native forecasts table has, so the benchmark
  -- comparison is fair (no "manual is slow because it lacks indexes").
  INDEX `idx_manual_run_id`         (`forecast_run_id`),
  INDEX `idx_manual_route_fdate`    (`route_id`, `forecast_date`),
  -- The crucial index for time-travel: covers the WHERE created_at <= ts
  -- AND (expired_at > ts OR expired_at IS NULL) lookup pattern.
  INDEX `idx_manual_validity`       (`created_at`, `expired_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Manual application-level versioning. Used for benchmark vs native temporal tables.';

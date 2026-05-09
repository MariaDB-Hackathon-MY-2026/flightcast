-- ============================================================
-- 03-flightcast-schema.sql
-- FlightCast production schema with all critic patches applied.
-- System versioning is added in 04-system-versioning.sql.
-- ============================================================

SET NAMES utf8mb4;
-- Required to preserve temporal history during any future ALTER TABLE
SET SESSION system_versioning_alter_history = KEEP;

-- ============================================================
-- route_demand: NOT versioned — immutable ground truth
-- ============================================================
CREATE TABLE IF NOT EXISTS `route_demand` (
  `demand_id`         BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
  `route_id`          INT              NOT NULL,
  `demand_date`       DATE             NOT NULL,
  `demand_volume`     DOUBLE           NOT NULL,
  `day_of_week`       TINYINT          NOT NULL COMMENT '0=Mon 6=Sun',
  `month`             TINYINT          NOT NULL,
  `is_holiday`        TINYINT(1)       NOT NULL DEFAULT 0,
  `hub_score_source`  DOUBLE           NOT NULL DEFAULT 0.0,
  `hub_score_dest`    DOUBLE           NOT NULL DEFAULT 0.0,
  `tier`              ENUM('hub','mid','thin') NOT NULL DEFAULT 'mid'
                       COMMENT 'Volatility tier: hub (smooth), mid (typical), thin (volatile)',
  PRIMARY KEY (`demand_id`),
  UNIQUE KEY `uq_route_date`    (`route_id`, `demand_date`),
  INDEX `idx_demand_date`       (`demand_date`),
  INDEX `idx_tier`              (`tier`),
  CONSTRAINT `fk_rd_route` FOREIGN KEY (`route_id`) REFERENCES `routes` (`id`)
      ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Synthetic daily demand. Multiplicative log-normal decomposition. Immutable. Per-tier volatility.';

-- ============================================================
-- forecasts: HERO TABLE — system-versioned (see 04-*.sql)
-- ============================================================
CREATE TABLE IF NOT EXISTS `forecasts` (
  `forecast_id`       BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
  `forecast_run_id`   INT UNSIGNED     NOT NULL,
  `forecast_run_ts`   DATETIME(6)      NOT NULL  COMMENT 'Story/business timestamp of this batch',
  `route_id`          INT              NOT NULL,
  `forecast_date`     DATE             NOT NULL,
  `predicted_demand`  DOUBLE           NOT NULL,
  `lower_bound`       DOUBLE           NOT NULL,
  `upper_bound`       DOUBLE           NOT NULL,
  `confidence_level`  DOUBLE           NOT NULL DEFAULT 0.90,
  -- VIRTUAL: never stored, never UPDATEd, creates no phantom version rows
  `interval_width`    DOUBLE           GENERATED ALWAYS AS (`upper_bound` - `lower_bound`) VIRTUAL,
  `model_version`     VARCHAR(32)      NOT NULL,
  `coverage_score`    DOUBLE                    DEFAULT NULL
      COMMENT 'Binary 1.0/0.0: 1 if actual is inside [lower, upper] interval, else 0',
  `winkler_score`     DOUBLE                    DEFAULT NULL
      COMMENT 'Winkler interval score (lower = better). Penalises both wide intervals and missed coverage.',
  `actual_demand`     DOUBLE                    DEFAULT NULL,
  PRIMARY KEY (`forecast_id`),
  INDEX `idx_run_id`            (`forecast_run_id`),
  INDEX `idx_model_version`     (`model_version`),
  INDEX `idx_run_ts`            (`forecast_run_ts`),
  -- Covering index: index-only scan for the hero time-travel query
  INDEX `idx_route_fdate_run`   (`route_id`, `forecast_date`, `forecast_run_id`,
                                  `predicted_demand`, `lower_bound`, `upper_bound`,
                                  `model_version`),
  -- RESTRICT not CASCADE: cascading into a versioned table creates dangling history rows
  CONSTRAINT `fk_fc_route` FOREIGN KEY (`route_id`) REFERENCES `routes` (`id`)
      ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='ML predictions. FOR SYSTEM_TIME AS OF returns past versions.';

-- ============================================================
-- model_metrics: system-versioned per-batch metrics (see 04-*.sql)
-- ============================================================
CREATE TABLE IF NOT EXISTS `model_metrics` (
  `metric_id`           INT UNSIGNED      NOT NULL AUTO_INCREMENT,
  `evaluation_date`     DATE              NOT NULL,
  `model_version`       VARCHAR(32)       NOT NULL,
  `forecast_run_id`     INT UNSIGNED      NOT NULL,
  `mean_coverage`       DOUBLE            NOT NULL COMMENT 'Empirical interval coverage rate',
  `mean_interval_width` DOUBLE            NOT NULL,
  `mape`                DOUBLE            NOT NULL COMMENT 'Mean absolute percentage error',
  `route_count`         SMALLINT UNSIGNED NOT NULL,
  `horizon_days`        TINYINT UNSIGNED  NOT NULL DEFAULT 30,
  PRIMARY KEY (`metric_id`),
  UNIQUE KEY `uq_run_model_date`  (`forecast_run_id`, `model_version`, `evaluation_date`),
  INDEX `idx_model_eval`          (`model_version`, `evaluation_date`),
  INDEX `idx_mm_run_id`           (`forecast_run_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Per-run model evaluation. Calibration drift visible across versions.';

-- ============================================================
-- batch_run_mapping: NOT versioned.
-- Maps story timestamps (forecast_run_ts) to real MariaDB
-- ROW_START values. Both bootstrap and Streamlit containers
-- read from here — no shared filesystem or JSON file needed.
-- ============================================================
CREATE TABLE IF NOT EXISTS `batch_run_mapping` (
  `forecast_run_id`  INT UNSIGNED  NOT NULL,
  `story_ts`         DATETIME      NOT NULL,
  `row_start_ts`     DATETIME(6)   NOT NULL,
  `model_version`    VARCHAR(32)   NOT NULL,
  PRIMARY KEY (`forecast_run_id`),
  INDEX `idx_story_ts`     (`story_ts`),
  INDEX `idx_row_start_ts` (`row_start_ts`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Story timestamp <-> MariaDB ROW_START mapping for the temporal slider.';

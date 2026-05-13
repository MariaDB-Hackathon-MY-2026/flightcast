-- ============================================================
-- 01-openflights-create.sql
-- Creates the three static OpenFlights tables.
-- Source: github.com/MariaDB/openflights  sql/create.sql
-- Runs automatically on first container start via
-- /docker-entrypoint-initdb.d — do NOT run manually.
-- ============================================================

SET NAMES utf8mb4;
SET character_set_client = utf8mb4;

-- ─────────────────────────────────────────────────────────────────────
-- Reference tables are NOT system-versioned: OpenFlights snapshots are
-- immutable, so versioning would only inflate storage. Each row carries
-- a `data_version` provenance stamp so any forecast can be traced back
-- to the exact OpenFlights snapshot it was trained on.
-- ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `airlines` (
  `id`           INT           NOT NULL AUTO_INCREMENT,
  `name`         VARCHAR(255)  NOT NULL DEFAULT '',
  `alias`        VARCHAR(255)           DEFAULT '',
  `iata`         VARCHAR(3)             DEFAULT '',
  `icao`         VARCHAR(4)             DEFAULT '',
  `callsign`     VARCHAR(255)           DEFAULT '',
  `country`      VARCHAR(255)           DEFAULT '',
  `active`       CHAR(1)       NOT NULL DEFAULT 'Y',
  `data_version` VARCHAR(32)   NOT NULL DEFAULT 'openflights-2024-09'
                  COMMENT 'OpenFlights snapshot identifier — immutable provenance stamp',
  PRIMARY KEY (`id`),
  INDEX `idx_airlines_data_version` (`data_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `airports` (
  `id`           INT           NOT NULL AUTO_INCREMENT,
  `name`         VARCHAR(255)  NOT NULL DEFAULT '',
  `city`         VARCHAR(255)           DEFAULT '',
  `country`      VARCHAR(255)           DEFAULT '',
  `iata`         CHAR(3)                DEFAULT '',
  `icao`         CHAR(4)                DEFAULT '',
  `latitude`     DOUBLE                 DEFAULT NULL,
  `longitude`    DOUBLE                 DEFAULT NULL,
  `altitude`     INT                    DEFAULT NULL,
  `timezone`     FLOAT                  DEFAULT NULL,
  `dst`          CHAR(1)                DEFAULT '',
  `tz`           VARCHAR(64)            DEFAULT '',
  `type`         VARCHAR(64)            DEFAULT '',
  `source`       VARCHAR(64)            DEFAULT '',
  `data_version` VARCHAR(32)   NOT NULL DEFAULT 'openflights-2024-09'
                  COMMENT 'OpenFlights snapshot identifier — immutable provenance stamp',
  PRIMARY KEY (`id`),
  INDEX `idx_airports_data_version` (`data_version`),
  -- idx_airports_iata: required for the /sampled-routes endpoint's
  -- 4-way join (route_demand → routes → airports × 2). Without this
  -- the join planner falls back to two full scans of airports
  -- (~7,700 rows each), turning a 50-row endpoint into a ~30s call.
  INDEX `idx_airports_iata` (`iata`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `routes` (
  `id`                  INT          NOT NULL AUTO_INCREMENT,
  `airline`             VARCHAR(3)   DEFAULT '',
  `airline_id`          INT          DEFAULT NULL,
  `src_airport`         VARCHAR(4)   DEFAULT '',
  `src_airport_id`      INT          DEFAULT NULL,
  `dst_airport`         VARCHAR(4)   DEFAULT '',
  `dst_airport_id`      INT          DEFAULT NULL,
  `codeshare`           CHAR(1)      DEFAULT '',
  `stops`               INT          DEFAULT 0,
  `equipment`           VARCHAR(255) DEFAULT '',
  `data_version`        VARCHAR(32)  NOT NULL DEFAULT 'openflights-2024-09'
                         COMMENT 'OpenFlights snapshot identifier — immutable provenance stamp',
  PRIMARY KEY (`id`),
  INDEX `idx_routes_src` (`src_airport`),
  INDEX `idx_routes_dst` (`dst_airport`),
  INDEX `idx_routes_data_version` (`data_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

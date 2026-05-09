-- ============================================================
-- 04-system-versioning.sql
-- Applies WITH SYSTEM VERSIONING to the FlightCast tables that
-- need a full audit trail of every prediction batch.
--
-- Using ALTER TABLE here (rather than CREATE TABLE … WITH
-- SYSTEM VERSIONING) because:
--   1. The tables were just created in 03-flightcast-schema.sql
--      without versioning so the schema is readable on its own.
--   2. ALTER TABLE makes the activation step explicit and easy
--      to grep for in the codebase.
--
-- MariaDB 11.8 activates versioning in-place with zero data
-- loss.  No extra InnoDB configuration is required.
-- ============================================================

-- Activate temporal versioning on the forecasts table.
-- Every subsequent INSERT / UPDATE / DELETE will generate a
-- row version queryable via FOR SYSTEM_TIME AS OF / BETWEEN /
-- FROM...TO / ALL.
ALTER TABLE `forecasts` ADD SYSTEM VERSIONING;

-- Activate temporal versioning on the model_metrics table.
ALTER TABLE `model_metrics` ADD SYSTEM VERSIONING;

-- Sanity check: verify versioning is active on both tables.
-- The output appears in docker logs on first container start.
SELECT
  TABLE_NAME,
  ROW_FORMAT,
  CREATE_OPTIONS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('forecasts', 'model_metrics');

-- Example time-travel queries included as documentation.
-- These are commented out — the Streamlit app runs them at
-- runtime via parameterised mariadb connector calls.
--
-- What did the model predict on Jan 15?
--   SELECT * FROM forecasts FOR SYSTEM_TIME AS OF '2026-01-15';
--
-- How did predictions change between Jan and Feb?
--   SELECT * FROM forecasts
--     FOR SYSTEM_TIME BETWEEN '2026-01-01' AND '2026-02-01';
--
-- Full audit log:
--   SELECT * FROM forecasts FOR SYSTEM_TIME ALL;

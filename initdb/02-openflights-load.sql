-- ============================================================
-- 02-openflights-load.sql
-- Loads the three OpenFlights static CSV data files into the
-- tables created in 01-openflights-create.sql.
-- Source: github.com/MariaDB/openflights  sql/load-data.sql
--
-- The actual LOAD DATA statements reference paths inside the
-- MariaDB container.  The bootstrap script (flightcast.bootstrap)
-- is the preferred way to load data because LOAD DATA INFILE
-- requires the CSV files to be present inside the container at
-- a known path.  This file is kept as a placeholder so the init
-- numbering is unambiguous — the bootstrap module handles the
-- actual LOAD DATA calls after copying CSV data into place.
-- ============================================================

-- Placeholder: bulk CSV loading is handled by
-- `docker compose exec app python -m flightcast.bootstrap`
-- which calls LOAD DATA LOCAL INFILE via the mariadb connector.
-- This approach avoids the need to COPY large CSV files into the
-- db image and avoids secure_file_priv path constraints.

SELECT 'OpenFlights CSV data will be loaded by the bootstrap script.' AS status;

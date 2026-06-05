-- Active: 1766815588447@@dpg-d0fmo7adbo4c73ako1o0-a.oregon-postgres.render.com@5432@genx_dev_db@Agent
-- Active: 1766815588447@@dpg-d0fmo7adbo4c73ako1o0-a.oregon-postgres.render.com@5432@genx_dev_db@Agent
-- Migration: add label column to agents table
ALTER TABLE "Agent".agents ADD COLUMN IF NOT EXISTS label VARCHAR;

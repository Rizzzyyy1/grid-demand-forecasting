# ADR-0002: DuckDB + Parquet + dbt; no Spark, Iceberg, Kafka or feature store

Status: Accepted · 2026-09-23

## Context
Ten regions × ~8,760 hours × ~7 years is roughly 0.6 M demand rows (≈ 4 M for all 62 BAs) plus
weather of similar size — megabytes to low gigabytes. Data arrives once a day.

## Decision
Store raw files immutably, transform with dbt on the DuckDB adapter, and keep marts as
DuckDB/Parquet. Orchestrate with Dagster (daily partitions match the data's cadence).

## Rejected
* **Spark** — a cluster engine for data that fits in memory many times over.
* **Iceberg / lakehouse** — valuable for multi-writer, large, evolving tables; here append-only
  forecasts in DuckDB with immutable raw files give the same auditability.
* **Kafka / streaming** — the source updates daily; streaming would be decoration.
* **Feast** — one model family, one training/serving path in one codebase; point-in-time
  correctness is enforced by `available_at` and a property test instead.

## Revisit when
Sub-hourly or real-time sources are added, data exceeds ~100 GB, or multiple teams write tables.

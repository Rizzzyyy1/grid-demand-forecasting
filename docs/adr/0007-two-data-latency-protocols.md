# ADR-0007: Two demand-latency protocols — "realtime" for research, "bulk" for the keyless live loop

Status: Accepted · 2026-09-23

## Context
The research protocol (ADR-0001) lets a forecast issued at 10:00 D-1 use demand up to 06:00 D-1,
i.e. a 4-hour publication delay. That matches an hourly feed such as the EIA API, which needs a
(free) key tied to a personal account.

Checked on 2026-09-23: EIA's keyless six-month bulk file is regenerated once a day (Last-Modified
2026-09-22 14:40 UTC) and then contains demand only up to the end of the previous local day
(e.g. PJM through 2026-09-22 04:00 UTC = midnight EDT). At 10:00 Eastern (14:00 UTC) on D-1 the
newest bulk file therefore reaches only the end of D-3.

## Decision
`ProtocolConfig` carries the cutoff as (days before D, local time):

| Protocol | Cutoff | Delay at issue | Most recent full day | Used for |
|---|---|---|---|---|
| `realtime` (default) | 06:00 on D-1 | 4 h | D-2 | research backtests, headline results |
| `bulk` | 00:00 on D-2 (end of D-3) | 34 h (33/35 on DST days) | D-3 | the live loop without an API key |

Features are protocol-aware (`lag_recent` = the most recent complete day, the level window ends
there, the partial day is empty under `bulk`). Demand availability is computed per origin as
`source hour + (issued_at − demand_cutoff)`, which is exact across DST changes; a fixed 34 h
offset was tried first and the leakage check caught it being one hour wrong on DST days.

## Consequences
* Live forecasts are made by a model trained under the `bulk` protocol, so training and serving
  see the same information (no train/serve skew).
* "What does 30 hours of data latency cost?" becomes a measured ablation, not a guess.
* With an EIA API key the live loop could switch to `realtime`; that needs the owner's account.

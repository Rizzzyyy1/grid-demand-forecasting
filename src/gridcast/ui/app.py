"""Streamlit dashboard. Talks only to the GridCast API (``GRIDCAST_API_URL``)."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

API = os.environ.get("GRIDCAST_API_URL", "http://127.0.0.1:8000")
BENCHMARK_STYLE = {"operator": "#9aa0a6", "operator_debiased": "#5f6368"}


@st.cache_data(ttl=60)
def get(path: str, **params: Any) -> Any:
    """GET an API path; returns JSON or None on 404."""
    r = httpx.get(f"{API}{path}", params=params, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def page_tomorrow(regions: list[dict[str, Any]]) -> None:
    st.subheader("Latest live forecast")
    code = st.selectbox("Balancing authority", [r["code"] for r in regions], key="live_ba")
    day = st.date_input("Target day", value=datetime.now(UTC).date() + timedelta(days=1))
    fc = get(f"/v1/forecasts/{code}", day=str(day))
    if not fc:
        st.info("No stored forecast for this day yet. The daily job issues one at 12:30 UTC.")
        return
    hours = pd.DataFrame(fc["hours"])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=hours.hour_ending_utc, y=hours.q975, line={"width": 0}, showlegend=False)
    )
    fig.add_trace(
        go.Scatter(
            x=hours.hour_ending_utc,
            y=hours.q025,
            fill="tonexty",
            line={"width": 0},
            name="95 % interval",
            fillcolor="rgba(66,133,244,0.15)",
        )
    )
    fig.add_trace(
        go.Scatter(x=hours.hour_ending_utc, y=hours.q90, line={"width": 0}, showlegend=False)
    )
    fig.add_trace(
        go.Scatter(
            x=hours.hour_ending_utc,
            y=hours.q10,
            fill="tonexty",
            line={"width": 0},
            name="80 % interval",
            fillcolor="rgba(66,133,244,0.3)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hours.hour_ending_utc, y=hours.yhat, name="forecast", line={"color": "#1a73e8"}
        )
    )
    fig.update_layout(yaxis_title="MW", xaxis_title="hour ending (UTC)", height=420)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"Model v{fc['model_version']} · protocol `{fc['protocol']}` · issued {fc['issued_at']} · "
        f"created {fc['created_at']}{' · LATE' if fc['late'] else ''}"
    )


def page_leaderboard() -> None:
    st.subheader("Live track record")
    st.caption(
        "Only forecasts stored before their issue time and scored against published actuals. "
        "Backtest numbers are never mixed in."
    )
    rows = get("/v1/leaderboard") or []
    if not rows:
        st.info("No scored live forecasts yet: actuals publish about two days after each day.")
        return
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def page_backtest(regions: list[dict[str, Any]]) -> None:
    st.subheader("Backtest explorer")
    runs = get("/v1/backtests") or []
    if not runs:
        st.info("No backtest runs yet: `gridcast backtest`.")
        return
    runs = [r for r in runs if not r.get("superseded")] or runs
    run_id = st.selectbox("Run", [r["run_id"] for r in runs])
    col1, col2 = st.columns(2)
    code = col1.selectbox("Balancing authority", [r["code"] for r in regions], key="bt_ba")
    run = next(r for r in runs if r["run_id"] == run_id)
    start = date.fromisoformat(run["window"][0])
    first = col2.date_input("Week starting", value=start + timedelta(days=21))
    series = get(
        f"/v1/backtests/{run_id}/series",
        ba=code,
        start=str(first),
        end=str(first + timedelta(days=6)),
    )
    if series:
        df = pd.DataFrame(series)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df.hour_ending_utc,
                y=df.actual,
                name="actual",
                line={"color": "#f9ab00", "width": 3},
            )
        )
        for col in df.columns:
            if col in {"hour_ending_utc", "target_day", "actual"}:
                continue
            style = {"dash": "dot", "color": BENCHMARK_STYLE[col]} if col in BENCHMARK_STYLE else {}
            fig.add_trace(go.Scatter(x=df.hour_ending_utc, y=df[col], name=col, line=style))
        fig.update_layout(yaxis_title="MW", height=420)
        st.plotly_chart(fig, use_container_width=True)
    summary = get(f"/v1/backtests/{run_id}/summary")
    if summary:
        with st.expander("Run summary (generated)", expanded=True):
            st.markdown(summary["markdown"])


def page_data() -> None:
    st.subheader("Data profile")
    report = get("/v1/reports/data-profile")
    st.markdown(report["markdown"] if report else "Run `gridcast profile` first.")


def main() -> None:
    st.set_page_config(page_title="GridCast", layout="wide")
    st.title("GridCast")
    st.caption(
        "Day-ahead electricity demand for ten US grid regions, benchmarked against the operators."
    )
    try:
        regions = get("/v1/regions")
    except httpx.HTTPError as exc:
        st.error(f"API unreachable at {API}: {exc}")
        return
    tabs = st.tabs(["Live forecast", "Leaderboard", "Backtests", "Data"])
    with tabs[0]:
        page_tomorrow(regions)
    with tabs[1]:
        page_leaderboard()
    with tabs[2]:
        page_backtest(regions)
    with tabs[3]:
        page_data()


main()

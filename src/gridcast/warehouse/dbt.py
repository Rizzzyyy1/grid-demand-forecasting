"""Run dbt programmatically (``dbtRunner``) against the configured warehouse and raw directory."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import gridcast
from gridcast.core.settings import Settings

TRANSFORM_DIR = Path(gridcast.__file__).parents[2] / "transform"


@dataclass(frozen=True)
class DbtResult:
    """Outcome of one dbt invocation."""

    success: bool
    passed: int
    failed: int
    messages: list[str]


def dbt_env(settings: Settings) -> dict[str, str]:
    """Environment dbt needs to find the warehouse and raw files."""
    return {
        "GRIDCAST_WAREHOUSE": str(settings.warehouse_path.resolve()),
        "GRIDCAST_RAW_DIR": str(settings.raw_dir.resolve()),
    }


def run_dbt(settings: Settings, args: list[str], project_dir: Path = TRANSFORM_DIR) -> DbtResult:
    """Run ``dbt <args>`` in-process and summarise node results."""
    from dbt.cli.main import dbtRunner  # noqa: PLC0415 - heavy import, pipeline extra only

    os.environ.update(dbt_env(settings))
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    result = dbtRunner().invoke(
        [*args, "--project-dir", str(project_dir), "--profiles-dir", str(project_dir)]
    )
    passed = failed = 0
    messages: list[str] = []
    for node in getattr(result.result, "results", None) or []:
        status = str(node.status).lower()
        if status in {"pass", "success"}:
            passed += 1
        elif status in {"fail", "error"}:
            failed += 1
            messages.append(f"{node.node.name}: {node.message}")
    if result.exception is not None:
        messages.append(str(result.exception))
    return DbtResult(bool(result.success), passed, failed, messages)


def run_dbt_subprocess(
    settings: Settings, args: list[str], project_dir: Path = TRANSFORM_DIR
) -> DbtResult:
    """Run ``dbt <args>`` in a child process.

    In-process dbt keeps its read-write DuckDB connection open until the process exits, which
    makes later read-only connections in the same process fail. Long-lived callers that read the
    warehouse afterwards (the daily live run) use this instead of ``run_dbt``.
    """
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415

    exe = Path(sys.executable).parent / "dbt"
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(  # noqa: S603 - fixed executable next to the interpreter
        [str(exe), *args, "--project-dir", str(project_dir), "--profiles-dir", str(project_dir)],
        env={**os.environ, **dbt_env(settings)},
        capture_output=True,
        text=True,
        check=False,
    )
    lines = proc.stdout.splitlines()
    done = next((ln for ln in reversed(lines) if "PASS=" in ln), "")
    passed = int(done.split("PASS=")[1].split()[0]) if "PASS=" in done else 0
    failed = sum(
        int(done.split(f"{k}=")[1].split()[0]) for k in ("ERROR", "FAIL") if f"{k}=" in done
    )
    messages = [ln.strip() for ln in lines if "ERROR" in ln or "FAIL " in ln][:20]
    if proc.returncode and not messages:
        messages = (proc.stderr or proc.stdout).splitlines()[-10:]
    return DbtResult(proc.returncode == 0, passed, failed, messages)

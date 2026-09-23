"""Production model: train on all history under the live protocol, register it in MLflow.

The model is a ``LightGBMForecaster`` wrapped as an MLflow ``pyfunc`` so it is versioned in the
model registry (name ``gridcast-lgbm-live``) and served by alias ``champion``. The live protocol
is ``bulk`` (ADR-0007) so training and serving see identical information.
"""

from __future__ import annotations

import pickle
import tempfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import polars as pl
import structlog

from gridcast.core.domain import ProtocolConfig
from gridcast.core.regions import all_regions
from gridcast.core.settings import Settings, ensure_offline
from gridcast.features.build import FeatureConfig, build_features, check_point_in_time
from gridcast.models.gbm import LightGBMForecaster
from gridcast.warehouse.duck import read_demand, read_weather

log = structlog.get_logger(__name__)
MODEL_NAME = "gridcast-lgbm-live"
ALIAS = "champion"
LIVE_PROTOCOL = ProtocolConfig.bulk()


def tracking_uri(settings: Settings) -> str:
    """The local MLflow tracking/registry database."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(settings.data_dir / 'mlflow.db').resolve()}"


class _Pyfunc:
    """Built lazily so importing this module does not require mlflow."""

    @staticmethod
    def cls() -> type[Any]:
        import mlflow.pyfunc  # noqa: PLC0415 - ml extra

        base: Any = mlflow.pyfunc.PythonModel

        class GridcastModel(base):  # type: ignore[misc]
            def load_context(self, context: Any) -> None:
                with Path(context.artifacts["forecaster"]).open("rb") as fh:
                    self.forecaster = pickle.load(fh)  # noqa: S301 - our own registry artefact

            def predict(self, context: Any, model_input: Any, params: Any = None) -> Any:  # noqa: ARG002 - pyfunc signature
                frame = pl.from_pandas(model_input)
                return self.forecaster.predict(frame).to_pandas()

        return GridcastModel


@dataclass(frozen=True)
class TrainedModel:
    """What ``train_production`` produced."""

    version: str
    train_rows: int
    last_train_day: date
    run_id: str


def train_production(
    settings: Settings, today: date, train_start: date = date(2021, 4, 1)
) -> TrainedModel:
    """Fit on every row whose actual is published under the live protocol, and register it."""
    import mlflow  # noqa: PLC0415 - ml extra

    ensure_offline(settings, "training")

    config = FeatureConfig(protocol=LIVE_PROTOCOL)
    last_day = today - timedelta(days=LIVE_PROTOCOL.recent_day_offset)
    demand = read_demand(settings.warehouse_path)
    weather = read_weather(settings.warehouse_path)
    features = build_features(demand, weather, all_regions(), train_start, last_day, config=config)
    leak = check_point_in_time(features)
    if not leak.ok:
        raise AssertionError(f"leakage in training features: {leak.violating_features}")
    train = features.filter(pl.col("y").is_not_null())
    model = LightGBMForecaster()
    model.fit(train)

    mlflow.set_tracking_uri(tracking_uri(settings))
    mlflow.set_experiment("gridcast-production")
    with tempfile.TemporaryDirectory() as tmp, mlflow.start_run(run_name=f"live-{today}") as run:
        path = Path(tmp) / "forecaster.pkl"
        with path.open("wb") as fh:
            pickle.dump(model, fh)
        mlflow.log_params(
            {
                "protocol": LIVE_PROTOCOL.name,
                "train_start": str(train_start),
                "population_weighted": config.population_weighted,
                "last_train_day": str(last_day),
                "train_rows": train.height,
            }
        )
        mlflow.log_dict(model.feature_importance, "feature_importance.json")
        info = mlflow.pyfunc.log_model(
            name="model",
            python_model=_Pyfunc.cls()(),
            artifacts={"forecaster": str(path)},
            registered_model_name=MODEL_NAME,
        )
        version = str(info.registered_model_version)
        client = mlflow.MlflowClient()
        client.set_registered_model_alias(MODEL_NAME, ALIAS, version)
        log.info("production.registered", version=version, rows=train.height)
        return TrainedModel(version, train.height, last_day, run.info.run_id)


def load_champion(settings: Settings) -> tuple[LightGBMForecaster, str]:
    """Load the ``champion`` model and its registry version."""
    import mlflow  # noqa: PLC0415 - ml extra

    mlflow.set_tracking_uri(tracking_uri(settings))
    client = mlflow.MlflowClient()
    mv = client.get_model_version_by_alias(MODEL_NAME, ALIAS)
    loaded = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@{ALIAS}")
    forecaster = loaded.unwrap_python_model().forecaster
    return forecaster, str(mv.version)

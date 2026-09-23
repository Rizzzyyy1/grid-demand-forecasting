"""Portable production-model artefact: a pickled forecaster plus a manifest that pins it.

The scheduled GitHub Actions job cannot see the local MLflow registry, and it must never train
(ADR-0009). The champion model is therefore exported once, locally, as
``model/<name>-v<version>.pkl`` with ``model/manifest.json`` recording its sha256, training window,
protocol, feature list and library versions. ``load_artifact`` refuses to run if the file's hash,
the feature list or the feature configuration no longer matches the code - so a model can never
be silently served with features it was not trained on.
"""

from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import asdict, dataclass
from datetime import datetime
from importlib import metadata
from pathlib import Path

from gridcast.core.time import utc_now
from gridcast.features.build import FeatureConfig
from gridcast.live.production import LIVE_PROTOCOL, MODEL_NAME
from gridcast.models.gbm import GBM_FEATURES, LightGBMForecaster

MANIFEST = "manifest.json"


class ArtifactMismatchError(RuntimeError):
    """The model artefact does not match its manifest or the current code."""


@dataclass(frozen=True)
class ModelManifest:
    """Everything needed to trust and reproduce a served model."""

    name: str
    version: str
    file: str
    sha256: str
    exported_at: datetime
    protocol: str
    population_weighted: bool
    features: tuple[str, ...]
    train_start: str
    last_train_day: str
    lightgbm: str
    polars: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _feature_config() -> FeatureConfig:
    return FeatureConfig(protocol=LIVE_PROTOCOL)


def export_artifact(
    model: LightGBMForecaster,
    version: str,
    out_dir: Path,
    train_start: str,
    last_train_day: str,
) -> ModelManifest:
    """Write the model file and its manifest into ``out_dir`` (usually ``<live>/model``)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    file = f"{MODEL_NAME}-v{version}.pkl"
    path = out_dir / file
    with path.open("wb") as fh:
        pickle.dump(model, fh, protocol=pickle.HIGHEST_PROTOCOL)
    cfg = _feature_config()
    manifest = ModelManifest(
        name=MODEL_NAME,
        version=version,
        file=file,
        sha256=_sha256(path),
        exported_at=utc_now(),
        protocol=cfg.protocol.name,
        population_weighted=cfg.population_weighted,
        features=GBM_FEATURES,
        train_start=train_start,
        last_train_day=last_train_day,
        lightgbm=metadata.version("lightgbm"),
        polars=metadata.version("polars"),
    )
    body = asdict(manifest) | {"exported_at": manifest.exported_at.isoformat()}
    (out_dir / MANIFEST).write_text(json.dumps(body, indent=2) + "\n")
    # older model files are removed from the working tree; git history keeps them
    for old in out_dir.glob(f"{MODEL_NAME}-v*.pkl"):
        if old.name != file:
            old.unlink()
    return manifest


def load_artifact(model_dir: Path) -> tuple[LightGBMForecaster, ModelManifest]:
    """Load and verify the model described by ``model_dir/manifest.json``."""
    raw = json.loads((model_dir / MANIFEST).read_text())
    manifest = ModelManifest(
        **(
            raw
            | {
                "features": tuple(raw["features"]),
                "exported_at": datetime.fromisoformat(raw["exported_at"]),
            }
        )
    )
    path = model_dir / manifest.file
    if _sha256(path) != manifest.sha256:
        raise ArtifactMismatchError(f"{path.name}: sha256 does not match the manifest")
    if manifest.features != GBM_FEATURES:
        missing = set(manifest.features) ^ set(GBM_FEATURES)
        raise ArtifactMismatchError(f"feature list differs from the code: {sorted(missing)}")
    cfg = _feature_config()
    if (manifest.protocol, manifest.population_weighted) != (
        cfg.protocol.name,
        cfg.population_weighted,
    ):
        raise ArtifactMismatchError(
            f"model trained with protocol={manifest.protocol}, "
            f"population_weighted={manifest.population_weighted}; the code now uses "
            f"protocol={cfg.protocol.name}, population_weighted={cfg.population_weighted}"
        )
    running = metadata.version("lightgbm")
    if manifest.lightgbm.split(".")[0] != running.split(".")[0]:
        raise ArtifactMismatchError(
            f"model pickled with lightgbm {manifest.lightgbm}, running {running}"
        )
    with path.open("rb") as fh:
        model = pickle.load(fh)  # noqa: S301 - verified by sha256 above; our own artefact
    if not isinstance(model, LightGBMForecaster):
        raise ArtifactMismatchError(f"{path.name} does not contain a LightGBMForecaster")
    return model, manifest

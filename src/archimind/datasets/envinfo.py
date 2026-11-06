"""Environment receipt: what ran, where, and how much disk remained. No secrets."""

import datetime
import os
import platform
import sys
from importlib import metadata
from pathlib import Path

from archimind.datasets.contracts import SCHEMA_VERSION
from archimind.datasets.safe_io import free_bytes

SECRET_NAMES = ("GH_TOKEN", "HF_TOKEN", "KAGGLE_USERNAME", "KAGGLE_KEY")


def _version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def environment_receipt(data_root: Path, *, floor_bytes: int) -> dict:
    """Describe the runtime. Secrets are reported only as present/absent."""
    free = free_bytes(Path(data_root))
    return {
        "schema_version": SCHEMA_VERSION,
        "observed_utc": datetime.datetime.now(datetime.UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "archimind_commit": os.environ.get("ARCHIMIND_COMMIT"),
        "archimind_version": _version("archimind"),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "machine": platform.machine(),
        "colab": "COLAB_RELEASE_TAG" in os.environ,
        "packages": {n: _version(n) for n in ("pydantic", "numpy")},
        "free_bytes": free,
        "floor_bytes": floor_bytes,
        "above_floor": free >= floor_bytes,
        "secrets_present": {n: bool(os.environ.get(n)) for n in SECRET_NAMES},
    }

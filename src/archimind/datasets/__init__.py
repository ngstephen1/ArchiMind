"""Offline dataset-reference tooling (SSR-3DFRONT, MIDI-3D, 3D-FUTURE).

Importing this package performs no I/O, downloads nothing and pulls in no UI,
geometry-engine or model-provider dependencies. A future app integration can read
verified packs through :func:`archimind.datasets.pack.load_pack`; no UI is wired yet.
"""

from archimind.datasets.contracts import SCHEMA_VERSION
from archimind.datasets.pack import PackStatus, load_pack, verify_pack

__all__ = ["SCHEMA_VERSION", "PackStatus", "load_pack", "verify_pack"]

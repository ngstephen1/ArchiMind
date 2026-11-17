"""P2b: 3D-FUTURE ``model_info.json`` -> per-model categories.

Rules (from the P1 probe, docs/data/DATASET_PROBE_P1.md):

* ``model_info.json`` is a list of objects with a unique 36-character ``model_id``,
  a ``super-category`` (8 values) and a finer ``category`` (50 values, sometimes
  null). ``style``, ``theme`` and ``material`` are ignored.
* Super-categories are normalized to the MIDI spelling (``Cabinet/Shelf/Desk`` ->
  ``Cabinet_Shelf_Desk``) so one category map serves both sources.
* 3D-FUTURE is the primary category source. MIDI furniture ids are a cross-check:
  any disagreement on a shared model id stops the build, and models only MIDI knows
  are kept.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from archimind.datasets.midi import SUPER_CATEGORIES

MAX_MODELS = 100_000
_MODEL_ID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_UUID_PREFIX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
_FINE_CATEGORY = re.compile(r"^[A-Za-z][A-Za-z0-9 /&'-]{0,79}$")


class FutureInfoError(ValueError):
    """``model_info.json`` is malformed or contradicts the MIDI furniture ids."""


@dataclass(frozen=True)
class FutureCategories:
    super_categories: Mapping[str, str]  # model id -> MIDI-spelled super-category
    fine_categories: Mapping[str, str]  # model id -> 3D-FUTURE category (non-null only)


def normalize_super_category(value: str) -> str:
    """3D-FUTURE spelling -> MIDI spelling; unknown values are rejected."""
    normalized = value.replace("/", "_") if isinstance(value, str) else None
    if normalized not in SUPER_CATEGORIES:
        raise FutureInfoError(f"Unknown 3D-FUTURE super-category {value!r}")
    return normalized


def parse_model_info(rows: Sequence) -> FutureCategories:
    """Validate ``model_info.json`` rows and index their categories by model id."""
    if not isinstance(rows, list) or not 0 < len(rows) <= MAX_MODELS:
        raise FutureInfoError("model_info.json must be a non-empty list")
    supers: dict[str, str] = {}
    fines: dict[str, str] = {}
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            raise FutureInfoError(f"Row {index} is not an object")
        model_id = item.get("model_id")
        if not isinstance(model_id, str) or not _MODEL_ID.fullmatch(model_id):
            raise FutureInfoError(f"Row {index} has an invalid model_id")
        if model_id in supers:
            raise FutureInfoError(f"Duplicate model_id {model_id}")
        supers[model_id] = normalize_super_category(item.get("super-category"))
        fine = item.get("category")
        if fine is not None:
            if not isinstance(fine, str) or not _FINE_CATEGORY.fullmatch(fine):
                raise FutureInfoError(f"Row {index} has an invalid category")
            fines[model_id] = fine
    return FutureCategories(super_categories=supers, fine_categories=fines)


def merge_categories(
    future: Mapping[str, str], midi: Mapping[str, str]
) -> tuple[dict[str, str], dict]:
    """3D-FUTURE categories plus MIDI-only models, after a strict cross-check.

    MIDI keys may carry a scale-variant suffix; they are compared through their
    36-character model id. Returns the merged map and a deterministic report.
    """
    merged = dict(future)
    agree = midi_only = 0
    for jid, category in sorted(midi.items()):
        prefix = _UUID_PREFIX.match(jid)
        model_id = prefix.group(0) if prefix else jid
        known = future.get(model_id)
        if known is None:
            midi_only += 1
            merged.setdefault(jid, category)
        elif known != category:
            raise FutureInfoError(
                f"MIDI says {category} but 3D-FUTURE says {known} for {model_id}"
            )
        else:
            agree += 1
    report = {
        "future_models": len(future),
        "midi_jids": len(midi),
        "midi_agrees_with_future": agree,
        "midi_only_jids": midi_only,
        "merged_jids": len(merged),
    }
    return merged, report

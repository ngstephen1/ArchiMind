"""MIDI-3D (huanngzh/3D-Front): identity lists, categories and archive layout.

Verified at revision 156fc5312ea613d4e92cbf5da1fddfa61bbad3b2:

* ``midi_room_ids.json`` and ``midi_furniture_ids.json`` are parallel lists: the
  i-th room owns the i-th furniture list. The test split is the LAST 1,000 rooms,
  and ``midi_test_room_ids.json`` equals that tail exactly.
* Room IDs are ``<house uuid>/<room id>``, the same identity as
  :func:`archimind.datasets.ssr.room_key`.
* Furniture IDs are ``<3D-FUTURE super-category>_<jid>_<instance>``.
* Scene geometry exists only inside gzip-compressed tar archives (split parts of
  ~43 GB each); there is no random access. In the archive, each house directory
  holds ``<room>.glb``, ``<room>_full.glb`` and ``<room>/<furniture id>.glb``.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

TEST_ROOMS = 1000
SUPER_CATEGORIES = (
    "Bed",
    "Cabinet_Shelf_Desk",
    "Chair",
    "Lighting",
    "Others",
    "Pier_Stool",
    "Sofa",
    "Table",
)
_ROOM = re.compile(
    r"^(?P<house>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    r"/(?P<room>[A-Za-z]+(?:-\d+)?)$"  # 5 real rooms are bare "OtherRoom"
)
_FURNITURE = re.compile(
    r"^(?P<category>" + "|".join(SUPER_CATEGORIES) + r")_"
    r"(?P<jid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"(?:-\([^)/]{1,64}\))?)_(?P<instance>\d+)$"
)


class MidiIdentityError(ValueError):
    """The ID lists are inconsistent or contain an unrecognized identifier."""


@dataclass(frozen=True)
class FurnitureId:
    category: str
    jid: str
    instance: int


def parse_room_id(value: str) -> tuple[str, str]:
    match = _ROOM.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise MidiIdentityError("Unrecognized MIDI room id")
    return match["house"], match["room"]


def parse_furniture_id(value: str) -> FurnitureId:
    match = _FURNITURE.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise MidiIdentityError("Unrecognized MIDI furniture id")
    return FurnitureId(match["category"], match["jid"], int(match["instance"]))


@dataclass(frozen=True)
class MidiIndex:
    rooms: dict[str, tuple[FurnitureId, ...]]
    splits: dict[str, str]
    jid_categories: dict[str, str]


def build_index(
    room_ids: Sequence[str],
    furniture_ids: Sequence[Sequence[str]],
    *,
    test_room_ids: Sequence[str] | None = None,
) -> MidiIndex:
    """Associate rooms with furniture by position and verify the split convention."""
    if len(room_ids) != len(furniture_ids):
        raise MidiIdentityError("Room and furniture lists differ in length")
    if len(set(room_ids)) != len(room_ids):
        raise MidiIdentityError("Duplicate MIDI room id")
    if test_room_ids is not None and list(room_ids[-TEST_ROOMS:]) != list(
        test_room_ids
    ):
        raise MidiIdentityError("Test rooms are not the last 1,000 listed rooms")
    rooms: dict[str, tuple[FurnitureId, ...]] = {}
    splits: dict[str, str] = {}
    categories: dict[str, str] = {}
    test_start = len(room_ids) - TEST_ROOMS
    for index, (room, items) in enumerate(zip(room_ids, furniture_ids, strict=True)):
        parse_room_id(room)
        parsed = tuple(parse_furniture_id(f) for f in items)
        if len({(f.jid, f.instance) for f in parsed}) != len(parsed):
            raise MidiIdentityError("Duplicate furniture instance in a room")
        for f in parsed:
            if categories.setdefault(f.jid, f.category) != f.category:
                raise MidiIdentityError("A jid has conflicting categories")
        rooms[room] = parsed
        splits[room] = "test" if index >= test_start else "train"
    return MidiIndex(rooms=rooms, splits=splits, jid_categories=categories)


def archive_member_room(name: str) -> str | None:
    """``3D-FRONT-*-SCENE/<house>/<room>[...]`` -> ``<house>/<room>`` or ``None``."""
    parts = name.split("/")
    if len(parts) < 3:
        return None
    room = parts[2]
    for suffix in ("_full.glb", ".glb"):
        if room.endswith(suffix):
            room = room[: -len(suffix)]
            break
    key = f"{parts[1]}/{room}"
    return key if _ROOM.fullmatch(key) else None


def join_report(ssr_rooms, index: MidiIndex) -> dict:
    """Cross-source identity report.

    ``ssr_rooms`` yields ``(room_key, ssr_split, tier, jids)`` per SSR row. Joins use
    the documented 3D-FRONT identity only; nothing is matched by name or shape.
    """
    from collections import Counter

    splits: Counter = Counter()
    tiers: Counter = Counter()
    jids: set[str] = set()
    joined_jids: set[str] = set()
    rows = joined = 0
    for key, split, tier, row_jids in ssr_rooms:
        rows += 1
        jids.update(row_jids)
        midi_split = index.splits.get(key)
        if midi_split is None:
            continue
        joined += 1
        splits[f"ssr_{split}|midi_{midi_split}"] += 1
        tiers[tier] += 1
        joined_jids.update(row_jids)
    categorized = {j for j in jids if j in index.jid_categories}
    disagree = sum(
        n for k, n in splits.items() if k.split("|")[0][4:] != k.split("|")[1][5:]
    )
    return {
        "ssr_rows": rows,
        "joined_rows": joined,
        "split_pairs": dict(sorted(splits.items())),
        "split_disagreements": disagree,
        "joined_tiers": dict(sorted(tiers.items())),
        "ssr_unique_jids": len(jids),
        "ssr_jids_with_midi_category": len(categorized),
        "midi_categories_of_ssr_jids": dict(
            sorted(Counter(index.jid_categories[j] for j in categorized).items())
        ),
    }

"""A prompt-variation suite for the chat interpreter, built from reference rooms.

Each case is one real bedroom (size and furniture from the pack's ``val`` split)
written in one style: complete metric spec, feet, typos, casual wording, real
quantities, a missing fact, an unsized bed or an unsupported shape. Every case
carries the outcome a correct interpreter should give, so prompt robustness is
measured rather than judged from one-off tries.

The source records no doors or windows, so every prompt uses the same synthetic
south door and "no windows". Prompts contain no source text or identifiers
beyond the case id. Scoring is duck-typed against ``CatalogConversationResult``.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from random import Random

from archimind.datasets.habits import fold_aliases, pack_group

STYLES = (
    "full_metric",
    "feet",
    "typos",
    "casual",
    "multiples",
    "missing_door",
    "missing_windows",
    "missing_ceiling",
    "no_bed_size",
    "l_shaped",
    "twin_beds",
)
EXPECTED = {
    "twin_beds": ("needs_clarification", "quantity"),
    "full_metric": ("ready", None),
    "feet": ("ready", None),
    "typos": ("ready", None),
    "casual": ("ready", None),
    "multiples": ("needs_clarification", "quantity"),
    "missing_door": ("needs_clarification", "door"),
    "missing_windows": ("needs_clarification", "windows"),
    "missing_ceiling": ("needs_clarification", "ceiling"),
    "no_bed_size": ("needs_clarification", "bed_size"),
    "l_shaped": ("unsupported", "shape"),
}
REASON_TERMS = {
    "quantity": r"quantit|one instance",
    "door": r"door|entrance",
    "windows": r"window",
    "ceiling": r"ceiling|height",
    "bed_size": r"bed size",
    "shape": r"shape|rectangular",
}
ROOM_TOLERANCE_M = 0.05
FT = 0.3048
DOOR = (0.5, 0.85, 2.1)  # offset, width, height on the south wall
NUMBER = {1: "one", 2: "two", 3: "three"}
PLURAL = {
    "nightstand": "nightstands",
    "wardrobe": "wardrobes",
    "bookcase": "bookcases",
    "desk": "desks",
    "chair": "chairs",
    "bed": "beds",
}
TYPOS = {
    "bedroom": "bedrom",
    "wardrobe": "wadrobe",
    "nightstand": "nighstand",
    "chair": "chiar",
    "desk": "deks",
}
ORDER = ("bed", "nightstand", "wardrobe", "bookcase", "desk", "chair")
BED_SIZE = {
    "king": "king",
    "single": "single",
    "kid": "single",
    "bunk": "single",
    "double": "double",
}


@dataclass(frozen=True)
class PromptCase:
    case_id: str
    style: str
    prompt: str
    expected_status: str
    expected_reason: str | None
    expected_functions: dict = field(hash=False)
    expected_room: tuple[float, float, float]
    snapshot_id: str | None = None
    source: str | None = None
    provider_disclosure: str | None = None


def _furniture(scene) -> tuple[Counter, str]:
    from archimind.datasets.search import tokens

    counts: Counter = Counter()
    bed_size = "queen"
    for o in scene.objects:
        if o.exclusion is not None:
            continue
        group = pack_group(o.category, o.raw_category)
        words = tokens(o.raw_category)
        if group == "bed":
            counts["bed"] += 1
            bed_size = next((v for k, v in BED_SIZE.items() if k in words), "queen")
        elif group == "storage":
            counts["wardrobe" if "wardrobe" in words else "bookcase"] += 1
        elif group in ("nightstand", "desk", "chair"):
            counts[group] += 1
    return counts, bed_size


def _eligible(scene) -> bool:
    room = scene.room
    counts, _ = _furniture(scene)
    return (
        counts["bed"] == 1
        and 2.5 <= room.width_m <= 9
        and 2.5 <= room.depth_m <= 9
        and 2.4 <= room.height_m <= 4
    )


def _items(
    counts: Counter,
    bed_size: str,
    *,
    real_counts: bool,
    sized: bool,
    twin: bool = False,
) -> str:
    parts = []
    for name in ORDER:
        n = counts[name] if real_counts else min(counts[name], 1)
        if not n:
            continue
        if name == "bed":
            parts.append(
                "two twin beds" if twin else f"one {bed_size} bed" if sized else "a bed"
            )
        else:
            parts.append(f"{NUMBER.get(n, str(n))} {name if n == 1 else PLURAL[name]}")
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _prompt(style: str, dims, counts: Counter, bed_size: str) -> str:
    w, d, h = dims
    offset, door_w, door_h = DOOR
    unit = "m"
    if style == "feet":
        w, d, h = (round(v / FT, 1) for v in dims)
        offset, door_w, door_h = (round(v / FT, 1) for v in DOOR)
        unit = "ft"
    items = _items(
        counts,
        bed_size,
        real_counts=style == "multiples",
        sized=style != "no_bed_size",
        twin=style == "twin_beds",
    )
    if style == "casual":
        return (
            f"Hi! My bedroom is a simple rectangle, {w} by {d} metres (width by depth) "
            f"with a {h} m ceiling. There's one door on the south wall, {offset} m from "
            f"the west corner, {door_w} m wide and {door_h} m tall, and no windows at "
            f"all. I'd like {items}."
        )
    shape = "An L-shaped bedroom" if style == "l_shaped" else "A rectangular bedroom"
    sentences = [f"{shape} {w} {unit} wide, {d} {unit} deep"]
    if style != "missing_ceiling":
        sentences[0] += f", ceiling {h} {unit}"
    sentences[0] += "."
    if style != "missing_door":
        sentences.append(
            f"South door: offset {offset} {unit}, width {door_w} {unit}, height {door_h} {unit}."
        )
    if style != "missing_windows":
        sentences.append("No windows.")
    sentences.append(f"I need {items}.")
    text = " ".join(sentences)
    if style == "typos":
        for word, typo in TYPOS.items():
            text = re.sub(rf"\b{word}", typo, text)
    return text


def build_prompt_suite(
    scenes, *, per_style: int = 3, seed: int = 0
) -> list[PromptCase]:
    """``per_style`` rooms per style, drawn deterministically from eligible scenes."""
    scenes, _ = fold_aliases(list(scenes))
    eligible = [s for s in scenes if _eligible(s)]
    cases = []
    for style in STYLES:
        pool = eligible
        if style == "multiples":
            pool = [s for s in eligible if max(_furniture(s)[0].values()) > 1]
        rng = Random(f"{seed}:{style}")
        for scene in rng.sample(pool, min(per_style, len(pool))):
            counts, bed_size = _furniture(scene)
            dims = tuple(
                round(v, 1)
                for v in (scene.room.width_m, scene.room.depth_m, scene.room.height_m)
            )
            status, reason = EXPECTED[style]
            functions = {
                k: (counts[k] if style == "multiples" else 1)
                for k in ORDER
                if counts[k]
            }
            if style == "twin_beds":
                functions["bed"] = 2
            cases.append(
                PromptCase(
                    case_id=f"{style}:{scene.reference_id}",
                    style=style,
                    prompt=_prompt(style, dims, counts, bed_size),
                    expected_status=status,
                    expected_reason=reason,
                    expected_functions=functions,
                    expected_room=dims,
                )
            )
    return cases


# ------------------------------------------------------------- scoring


def score_case(case: PromptCase, result) -> dict:
    got = result.status
    status_ok = got == case.expected_status
    functions_ok = None
    extraction = getattr(result, "extraction", None)
    if extraction is not None and case.expected_status != "unsupported":
        got_functions = Counter()
        for intent in extraction.furniture:
            got_functions[intent.function] += intent.quantity or 0
        functions_ok = dict(got_functions) == case.expected_functions
    room_ok = None
    if got == "ready" and case.expected_status == "ready" and result.draft is not None:
        room = result.draft.room()
        room_ok = all(
            abs(a - b) <= ROOM_TOLERANCE_M
            for a, b in zip(
                (room.width_m, room.depth_m, room.ceiling_height_m), case.expected_room
            )
        )
    reason_ok = None
    if case.expected_reason and got == "needs_clarification":
        text = " ".join(result.clarifications)
        reason_ok = bool(re.search(REASON_TERMS[case.expected_reason], text, re.I))
    error = getattr(result, "error", None)
    return {
        "case_id": case.case_id,
        "style": case.style,
        "expected_status": case.expected_status,
        "got_status": got,
        "status_ok": status_ok,
        "functions_ok": functions_ok,
        "room_ok": room_ok,
        "reason_ok": reason_ok,
        "error": None if error is None else error.code,
        "clarifications": list(result.clarifications)[:4],
        "passed": status_ok and functions_ok is not False and room_ok is not False,
    }


def summarize(rows: list[dict]) -> dict:
    by_style = {}
    for style in STYLES:
        mine = [r for r in rows if r["style"] == style]
        if not mine:
            continue
        reasons = [r["reason_ok"] for r in mine if r["reason_ok"] is not None]
        by_style[style] = {
            "cases": len(mine),
            "passed": sum(r["passed"] for r in mine),
            "got_status": dict(sorted(Counter(r["got_status"] for r in mine).items())),
            "reason_named": f"{sum(reasons)}/{len(reasons)}" if reasons else None,
        }
    return {
        "cases": len(rows),
        "passed": sum(r["passed"] for r in rows),
        "pass_rate": round(sum(r["passed"] for r in rows) / len(rows), 4)
        if rows
        else 0.0,
        "by_style": by_style,
    }


def bind_case(case, pack):
    """Attach disclosure evidence from the verified source of this scene."""
    from dataclasses import replace

    scene_id = case.case_id.split(":", 1)[1]
    scene = next(s for s in pack.scenes if s.reference_id == scene_id)
    source = next(s for s in pack.sources if s.source == scene.source)
    return replace(
        case,
        snapshot_id=pack.manifest.snapshot_id,
        source=scene.source,
        provider_disclosure=source.permission.provider_disclosure,
    )


def live_cases_allowed(cases, pack):
    """Reconstruct each prompt using current pack evidence before any live call."""
    by_id = {s.reference_id: s for s in pack.scenes}
    for case in cases:
        scene = by_id.get(case.case_id.partition(":")[2])
        if scene is None or case.provider_disclosure != "allowed":
            return False
        originals = build_prompt_suite([scene], per_style=1)
        if not any(
            bind_case(original, pack) == case
            for original in originals
            if original.style == case.style
        ):
            return False
    return True


def case_to_json(case: PromptCase) -> dict:
    data = dict(case.__dict__)
    data["expected_room"] = list(case.expected_room)
    return data


def case_from_json(data: dict) -> PromptCase:
    return PromptCase(**{**data, "expected_room": tuple(data["expected_room"])})

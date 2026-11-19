"""A furnishing plan -> bounded recipes -> Python-validated A/B concept rooms."""

import json
import time
from concurrent.futures import ThreadPoolExecutor

from pydantic import Field, model_validator

from archimind.assets.designer_concepts import (
    BEDROOM_SIZES,
    resolve_chair,
    resolve_collection,
)
from archimind.geometry import (
    LayoutGenerationResult,
    generate_layout_candidates,
    validate_accessibility,
)
from archimind.models import Furniture, Room, RoomDesign
from archimind.studio import provider
from archimind.studio.contracts import (
    MAX_ASSETS,
    MAX_INSTANCES,
    Frozen,
    FurnishingPlan,
    Recipe,
    StudioDraft,
    StudioError,
    digest,
)
from archimind.studio.fixtures import example_plan, example_recipe
from archimind.style_packs import StyleId, load_pack
from archimind.style_packs.scene import asset_hashes, style_payload


def propose_room(
    room: Room,
    kind: str,
    brief: str,
    *,
    allow_live=False,
    client_factory=None,
    offline=False,
) -> StudioDraft:
    try:
        room = Room.model_validate_json(room.model_dump_json())
    except (ValueError, AttributeError):
        raise StudioError("Room measurements or openings are invalid.") from None
    if (
        not room.doors
        or len(room.doors) + len(room.windows) > 16
        or any(
            not 0.1 <= v <= 20
            for v in (room.width_m, room.depth_m, room.ceiling_height_m)
        )
    ):
        raise StudioError(
            "Provide a bounded rectangular room, at least one entrance, and at most 16 openings."
        )
    if not brief.strip() or len(brief) > 4000:
        raise StudioError("Provide a design brief of 1–4,000 characters.")
    if kind not in ("Bedroom", "Living room", "Home office"):
        raise StudioError("Choose a supported rectangular interior.")
    model = None
    if offline:
        plan = example_plan(kind)
    else:
        config = provider.configuration(allow_live)
        model = config[1]
        prompt = json.dumps(
            {"room": room.model_dump(mode="json"), "kind": kind, "brief": brief}
        )
        plan = provider.request(
            FurnishingPlan,
            "Propose furnishings and a coherent palette for this measured room. "
            "Room measurements/openings are fixed. Furniture dimensions are proposed concepts, not product facts. "
            "Use at most 8 unique floor-standing objects and 12 instances. Leave room for circulation. "
            "Include the complete object height, including its decorative parts. "
            "No wall-mounted, ceiling-mounted, stacked or animated objects. Do not invent satisfaction of mandatory placement goals. "
            + prompt,
            config=config,
            deadline=time.monotonic() + provider.TIMEOUT,
            client_factory=client_factory,
        )
    try:
        return StudioDraft(
            room_json=room.model_dump_json(),
            room_kind=kind,
            brief=brief,
            plan=plan,
            source="offline_demo" if offline else "ai_concept",
            model=model,
        )
    except ValueError:
        raise StudioError(
            "The proposed furnishings exceed the room or supported concept limits. Revise the brief."
        ) from None


DESIGNER_CHAIR_SLOT = "studio:designer-chair"


class ChairBinding(Frozen):
    concept_id: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=32)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


BEDROOM_CATEGORIES = {"upholstered-linen-bed": "bed", "oak-bedside-lamp": "table"}


def _remaining_items(draft, collection):
    ids = [binding.concept_id for binding in collection]
    if len(set(ids)) != len(ids) or any(key not in BEDROOM_CATEGORIES for key in ids):
        raise StudioError("Choose each released bedroom concept at most once.")
    if ids and draft.room_kind != "Bedroom":
        raise StudioError("The bedroom collection requires a bedroom plan.")
    items = draft.plan.items
    if "upholstered-linen-bed" in ids:
        beds = sum(item.quantity for item in items if item.category == "bed")
        if beds > 1:
            raise StudioError("A single designer bed cannot replace a multi-bed plan.")
        items = tuple(item for item in items if item.category != "bed")
    return items


def specification(
    draft: StudioDraft,
    *,
    designer_chair: ChairBinding | None = None,
    designer_collection: tuple[ChairBinding, ...] = (),
) -> RoomDesign:
    draft = StudioDraft.model_validate_json(draft.model_dump_json())
    items = _remaining_items(draft, designer_collection)
    furniture = [
        Furniture(
            id=f"studio:{index}:{instance}",
            name=item.name,
            category=item.category,
            x_m=0.0,
            y_m=0.0,
            width_m=item.width_m,
            depth_m=item.depth_m,
            height_m=item.height_m,
        )
        for index, item in enumerate(items, 1)
        for instance in range(1, item.quantity + 1)
    ]
    extras = len(designer_collection) + int(designer_chair is not None)
    if len(furniture) + extras > MAX_INSTANCES or len(items) + extras > MAX_ASSETS:
        raise StudioError(
            "Adding designer furniture would exceed the Studio furnishing limit."
        )
    room = draft.room()
    for binding in designer_collection:
        try:
            asset = resolve_collection(**binding.model_dump())
        except ValueError:
            raise StudioError(
                "The selected bedroom release is unavailable. Review the current options."
            ) from None
        if (
            asset.width_m > room.width_m
            or asset.depth_m > room.depth_m
            or asset.height_m > room.ceiling_height_m
        ):
            raise StudioError(
                "The selected bedroom concept exceeds this room's measurements."
            )
        furniture.append(
            Furniture(
                id=f"studio:{asset.concept_id}",
                name=asset.name,
                category=BEDROOM_CATEGORIES[asset.concept_id],
                x_m=0,
                y_m=0,
                width_m=asset.width_m,
                depth_m=asset.depth_m,
                height_m=asset.height_m,
            )
        )
    if designer_chair is not None:
        try:
            chair = resolve_chair(
                designer_chair.concept_id, designer_chair.version, designer_chair.sha256
            )
        except ValueError:
            raise StudioError(
                "The selected designer chair is unavailable. Review the current options."
            ) from None
        room = draft.room()
        if (
            chair.width_m > room.width_m
            or chair.depth_m > room.depth_m
            or chair.height_m > room.ceiling_height_m
        ):
            raise StudioError("The designer chair exceeds this room's measurements.")
        furniture.append(
            Furniture(
                id=DESIGNER_CHAIR_SLOT,
                name=chair.name,
                category="chair",
                x_m=0.0,
                y_m=0.0,
                width_m=chair.width_m,
                depth_m=chair.depth_m,
                height_m=chair.height_m,
            )
        )
    return RoomDesign(
        room=draft.room(),
        name=f"{draft.room_kind} — procedural concepts",
        furniture=furniture,
    )


class StudioBuild(Frozen):
    draft: StudioDraft
    recipes: tuple[Recipe, ...]
    designer_chair: ChairBinding | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    designer_collection: tuple[ChairBinding, ...] = Field(
        default=(), max_length=2, exclude_if=lambda v: not v
    )
    result_json: str
    seed: int = Field(ge=0, le=2**32 - 1)
    model_calls: int = Field(ge=0, le=8)
    # Snapshots built before style packs carry neither field and render as before.
    style: StyleId | None = Field(default=None, exclude_if=lambda v: v is None)
    style_assets: dict[str, tuple[str, ...]] | None = Field(
        default=None, exclude_if=lambda v: v is None
    )

    def result(self):
        return LayoutGenerationResult.model_validate_json(self.result_json)

    @property
    def snapshot_id(self):
        return digest(self)

    @model_validator(mode="after")
    def consistent(self):
        result = self.result()
        if result.seed != self.seed or (
            result.candidates
            and len(self.recipes)
            != len(_remaining_items(self.draft, self.designer_collection))
        ):
            raise ValueError("Incomplete or inconsistent concept snapshot")
        for candidate in result.candidates:
            expected = {f"studio:{b.concept_id}" for b in self.designer_collection}
            native = [
                item
                for item in candidate.design.furniture
                if item.id.removeprefix("studio:") in BEDROOM_CATEGORIES
            ]
            if {item.id for item in native} != expected:
                raise ValueError("Inconsistent bedroom collection binding")
            for item in native:
                key = item.id.removeprefix("studio:")
                if (
                    (item.width_m, item.depth_m, item.height_m) != BEDROOM_SIZES[key]
                    or item.category != BEDROOM_CATEGORIES[key]
                    or item.rotation_deg != 0
                ):
                    raise ValueError("Invalid bedroom furniture reservation")
            chairs = [
                f for f in candidate.design.furniture if f.id == DESIGNER_CHAIR_SLOT
            ]
            if len(chairs) != int(self.designer_chair is not None) or any(
                f.category != "chair" or f.rotation_deg != 0 for f in chairs
            ):
                raise ValueError("Inconsistent designer chair binding")
        if (self.style is None) != (self.style_assets is None):
            raise ValueError("A styled snapshot lists its bound asset hashes")
        return self


def _studio_style(design, pack, seed, chair, collection):
    reserved = {f"studio:{binding.concept_id}" for binding in collection}
    if chair is not None:
        reserved.add(DESIGNER_CHAIR_SLOT)
    return style_payload(design, pack, seed, designer_ids=reserved)


def build_room(
    draft: StudioDraft,
    seed: int = 42,
    *,
    allow_live=False,
    client_factory=None,
    designer_chair: ChairBinding | None = None,
    designer_collection: tuple[ChairBinding, ...] = (),
    style: StyleId | None = None,
) -> StudioBuild:
    draft = StudioDraft.model_validate_json(draft.model_dump_json())
    config = (
        None if draft.source == "offline_demo" else provider.configuration(allow_live)
    )
    if config and config[1] != draft.model:
        raise StudioError(
            "The configured model changed. Propose the plan again before building."
        )
    design = specification(
        draft, designer_chair=designer_chair, designer_collection=designer_collection
    )
    items = _remaining_items(draft, designer_collection)
    result = generate_layout_candidates(
        design.room, design.furniture, seed=seed, max_candidates=2, max_attempts=500
    )
    for c in result.candidates:
        actual = validate_accessibility(
            c.design, config=result.config, area_tolerance_m2=0.0
        )
        if actual.status != "passed" or actual != c.validation:
            raise StudioError(
                "The generated geometry failed independent acceptance checks."
            )
    recipes, calls = (), 0
    if result.candidates:
        if draft.source == "offline_demo":
            recipes = tuple(example_recipe(i.category) for i in items)
        else:
            deadline = time.monotonic() + provider.DEADLINE

            def make(item):
                return provider.request(
                    Recipe,
                    "Build recognizable detailed furniture from box, cylinder, cone and sphere parts. "
                    "All parts are axis-aligned and CENTERED, with size and center normalized to [0,1] "
                    "inside the whole object's local width(X), height(Y), depth(Z) reservation. "
                    "Each size component must be at least 0.001. Use at most eight color/roughness combinations. "
                    "A cylinder/cone's Y axis is vertical; sphere size supports ellipsoids. "
                    "Use 8–40 parts where useful (hard maximum 64). At least one part must touch Y=0; "
                    "all parts, cushions, trim and props must fit entirely inside the reservation. "
                    "Use the same coherent palette as the plan. No code, groups, rotations, lights or URLs. "
                    + json.dumps(
                        {
                            "item": item.model_dump(mode="json"),
                            "style": draft.plan.description,
                            "palette": {
                                "walls": draft.plan.wall_color,
                                "floor": draft.plan.floor_color,
                            },
                            "brief": draft.brief,
                        }
                    ),
                    config=config,
                    deadline=deadline,
                    client_factory=client_factory,
                )

            # Two bounded requests at a time; no repair loops or automatic retries.
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(make, item) for item in items]
                try:
                    recipes = tuple(f.result() for f in futures)
                except Exception:
                    for f in futures:
                        f.cancel()
                    raise
            calls = len(recipes)
    style_assets = None
    if style is not None:
        pack = load_pack(style)
        style_assets = asset_hashes(
            b["asset_id"]
            for c in result.candidates
            for b in _studio_style(
                c.design, pack, seed, designer_chair, designer_collection
            )["bindings"]
        )
    return StudioBuild(
        draft=draft,
        designer_chair=designer_chair,
        designer_collection=designer_collection,
        recipes=recipes,
        result_json=result.model_dump_json(),
        seed=seed,
        model_calls=calls,
        style=style,
        style_assets=style_assets,
    )


def scene_payload(build: StudioBuild, candidate) -> dict:
    """Only an actual candidate from this immutable snapshot can be rendered."""
    build = StudioBuild.model_validate_json(build.model_dump_json())
    if not any(candidate == c for c in build.result().candidates):
        raise StudioError(
            "The selected candidate does not belong to this concept snapshot."
        )
    payload = {
        "schema_version": 4,
        "design": candidate.design.model_dump(mode="json"),
        "asset_bindings": [
            {"furniture_id": f.id, "asset_id": None} for f in candidate.design.furniture
        ],
        "unavailable_assets": [],
        "concept_assets": [
            {"recipe_id": f"concept-{i}", "parts": r.model_dump(mode="json")["parts"]}
            for i, r in enumerate(build.recipes, 1)
        ],
        "concept_bindings": [
            {"furniture_id": f"studio:{i}:{n}", "recipe_id": f"concept-{i}"}
            for i, item in enumerate(
                _remaining_items(build.draft, build.designer_collection), 1
            )
            for n in range(1, item.quantity + 1)
        ],
        "surfaces": {
            "wall_color": build.draft.plan.wall_color,
            "floor_color": build.draft.plan.floor_color,
        },
    }
    if build.designer_chair is not None:
        payload["schema_version"] = 5
        payload["designer_chair"] = build.designer_chair.model_dump(mode="json")
    if build.designer_collection:
        payload["schema_version"] = 6
        payload["designer_collection"] = [
            b.model_dump(mode="json") for b in build.designer_collection
        ]
    if build.style is not None:
        payload["style"] = _studio_style(
            candidate.design,
            load_pack(build.style),
            build.seed,
            build.designer_chair,
            build.designer_collection,
        )
    if len(json.dumps(payload).encode()) > 262144:
        raise StudioError("The complete scene exceeds the recipe byte budget.")
    return payload

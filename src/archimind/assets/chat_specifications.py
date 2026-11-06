"""Explicit chat selections resolved through current catalog authority and 08E."""

from collections.abc import Mapping

from archimind.agents.catalog_conversation import (
    measurement,
    reconcile_catalog_extraction,
    text_value,
)
from archimind.agents.catalog_requirements import (
    CatalogChatDraft,
    CatalogFurnitureIntent,
    Frozen,
)
from archimind.assets.specifications import (
    PreparedCatalogSpecification,
    SpecificationError,
    prepare_catalog_specification,
)
from archimind.examples.sample_bedroom import create_sample_bedroom
from archimind.models import RoomDesign
from archimind.retrieval import (
    FurnitureSearchFilters,
    FurnitureSearchRequest,
    FurnitureSearchResult,
    LexicalRetrievalProvider,
    resolve_result,
)

FUNCTIONS = {
    "bed": ("bed", "bed"),
    "desk": ("desk", "desk"),
    "wardrobe": ("wardrobe", "wardrobe"),
    "chair": ("chair", "chair"),
    "armchair": ("chair", "armchair"),
    "bookcase": ("storage", "bookcase"),
    "nightstand": ("table", "nightstand"),
}


class ChatRetrieval(Frozen):
    request_id: str
    intent: CatalogFurnitureIntent
    result: FurnitureSearchResult


def validated_chat_draft(draft) -> CatalogChatDraft:
    draft = CatalogChatDraft.model_validate(draft)
    fresh = reconcile_catalog_extraction(draft.extraction, draft.turns)
    if fresh.status != "ready" or fresh.draft.room_json != draft.room_json:
        raise SpecificationError(
            "Chat draft is not ready or has altered room evidence."
        )
    return draft


def retrieve_chat_candidates(draft) -> tuple[ChatRetrieval, ...]:
    """Current lexical retrieval only. No model, generation or mesh inspection."""
    draft = validated_chat_draft(draft)
    provider = LexicalRetrievalProvider()
    found = []
    for i, intent in enumerate(draft.extraction.furniture, 1):
        category, query = FUNCTIONS[intent.function]
        fields = dict(category=category)
        for name in ("variant", "product_id", "required_use"):
            fields[name] = text_value(getattr(intent, name), draft.turns)
        # A reviewed function qualifier can be extracted into variant by the
        # provider. Retain its meaning as an exact intended-use constraint.
        # Actual finish variants (Oak, Espresso, etc.) remain exact filters.
        if intent.function == "desk" and (fields["variant"] or "").casefold() in {
            "writing",
            "writing desk",
        }:
            query = "writing desk"
            fields["variant"] = None
            if fields["required_use"] is None:
                fields["required_use"] = "writing"
        for name in ("materials", "styles", "colors"):
            fields[name] = tuple(
                text_value(v, draft.turns) for v in getattr(intent, name)
            )
        for name in ("width", "depth", "height"):
            value = getattr(intent, "max_" + name)
            fields["max_" + name + "_m"] = (
                measurement(value, draft.turns) if value else None
            )
        request = FurnitureSearchRequest(
            query=query,
            filters=FurnitureSearchFilters(**fields),
            dimension_basis="generation_reservation",
            required_qualification="metadata",
            top_k=5,
        )
        result = provider.search(request)
        if result.status not in ("empty", "matches"):
            raise SpecificationError(
                "Current furniture search evidence is unavailable."
            )
        resolve_result(result)
        found.append(
            ChatRetrieval(request_id=f"request-{i}", intent=intent, result=result)
        )
    return tuple(found)


def procedural_options(intent, turns):
    """Only existing templates, explicitly accepted; no invented product facts."""
    key = {"bed": "queen-bed", "desk": "desk", "wardrobe": "wardrobe"}.get(
        intent.function
    )
    if key is None or intent.quantity != 1:
        return ()
    if intent.function == "bed" and "queen" not in intent.source.text.casefold():
        return ()
    variant = text_value(intent.variant, turns)
    if intent.function == "bed" and (variant or "").casefold() == "queen":
        variant = None  # Exact size label of this explicitly offered template.
    if any(
        (
            variant,
            intent.product_id,
            intent.materials,
            intent.styles,
            intent.colors,
        )
    ):
        return ()
    use = text_value(intent.required_use, turns)
    accepted = {
        "bed": {"bed", "queen bed", "sleeping"},
        "desk": {"desk", "writing", "writing desk", "study"},
        "wardrobe": {"wardrobe", "clothing storage"},
    }
    if use is not None and use.casefold() not in accepted[intent.function]:
        return ()
    item = next(f for f in create_sample_bedroom().furniture if f.id == key)
    for axis in ("width", "depth", "height"):
        limit = getattr(intent, "max_" + axis)
        if limit is not None and getattr(item, axis + "_m") > measurement(limit, turns):
            return ()
    return (item,)


def prepare_chat_specification(
    draft, *, selections, procedural_ids
) -> PreparedCatalogSpecification:
    """Mappings use request-N keys. Explicit None means omit, absence is unresolved."""
    try:
        draft = validated_chat_draft(draft)
        if not isinstance(selections, Mapping) or not isinstance(
            procedural_ids, Mapping
        ):
            raise ValueError
        matches = retrieve_chat_candidates(draft)
        expected = {x.request_id for x in matches}
        if (
            set(selections) & set(procedural_ids)
            or set(selections) | set(procedural_ids) != expected
        ):
            raise SpecificationError("Resolve every requested item explicitly.")
        products, templates = [], []
        for match in matches:
            key = match.request_id
            if key in procedural_ids:
                selected = procedural_ids[key]
                if type(selected) is not str or selected not in {
                    f.id for f in procedural_options(match.intent, draft.turns)
                }:
                    raise SpecificationError(
                        "Procedural selection contradicts current requirements."
                    )
                templates.append(selected)
            else:
                selected = selections[key]
                if selected is None:
                    continue
                if type(selected) is not str or selected not in {
                    o.record.asset_id for o in resolve_result(match.result)
                }:
                    raise SpecificationError(
                        "Selected product is stale or fails the request constraints."
                    )
                products.append(selected)
        if len(set(products)) != len(products) or len(set(templates)) != len(templates):
            raise SpecificationError("One instance per product/template is supported.")
        furniture = [
            f.model_copy(update={"x_m": 0.0, "y_m": 0.0})
            for f in create_sample_bedroom().furniture
        ]
        base = RoomDesign(
            room=draft.room(), furniture=furniture, name="Chat bedroom specification"
        )
        return prepare_catalog_specification(
            base, retained_manual_ids=tuple(templates), product_ids=tuple(products)
        )
    except SpecificationError:
        raise
    except (ValueError, TypeError, KeyError, OSError):
        raise SpecificationError(
            "Chat specification failed current evidence/selection checks."
        ) from None

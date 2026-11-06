"""Clearly synthetic, evidence-grounded conversation fixtures; no model requests."""

from archimind.agents.catalog_requirements import (
    CatalogChatTurn,
    CatalogConversationExtraction,
    CatalogFurnitureIntent,
    ChatMeasurement,
    ChatOpening,
    SourceQuote,
)

TEXT = (
    "A rectangular bedroom 5 m wide, 4 m deep, ceiling 2.7 m. "
    "South door: offset 0.6 m, width 0.85 m, height 2.1 m. "
    "No windows. A queen bed and a writing desk."
)


def quote(text, turn=1):
    return SourceQuote(turn_id=turn, text=text)


def measure(value, unit="m", turn=1):
    q = quote(f"{value:g} {unit}", turn)
    return ChatMeasurement(value=float(value), unit=unit, value_source=q, unit_source=q)


def intent(function, source):
    return CatalogFurnitureIntent(
        function=function,
        source=quote(source),
        quantity=1,
        variant=None,
        product_id=None,
        required_use=None,
        materials=(),
        styles=(),
        colors=(),
        max_width=None,
        max_depth=None,
        max_height=None,
    )


def extraction():
    return CatalogConversationExtraction(
        room_type="bedroom",
        room_source=quote("bedroom"),
        shape="rectangular",
        shape_source=quote("rectangular"),
        width=measure(5),
        depth=measure(4),
        ceiling_height=measure(2.7),
        doors=(
            ChatOpening(
                wall="south",
                wall_source=quote("South door"),
                offset=measure(0.6),
                width=measure(0.85),
                height=measure(2.1),
                sill_height=None,
            ),
        ),
        windows_state="none",
        windows_source=quote("No windows"),
        windows=(),
        furniture=(intent("bed", "queen bed"), intent("desk", "writing desk")),
        hard_constraints=(),
        soft_preferences=(),
        missing_or_ambiguous=(),
        unsupported_features=(),
    )


def turns(text=TEXT):
    return (CatalogChatTurn(id=1, role="user", content=text),)

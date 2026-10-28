"""Explicit offline extraction fixture, never a fallback for an API failure."""

from archimind.agents.requirements_schemas import RequirementsSchema

SAMPLE_REQUEST = (
    "Create a 5 m by 4 m bedroom with a 2.7 m ceiling, a queen bed, desk, and wardrobe. "
    "Add a south-wall door 0.85 m wide at offset 0.6 m, height 2.1 m, "
    "and a north-wall window 1.5 m wide at offset 2.7 m, sill 0.9 m, height 1.2 m."
)


def sample_extraction() -> RequirementsSchema:
    def length(value: float, quote: str) -> dict:
        return {"value": value, "unit": "m", "source_text": quote}

    return RequirementsSchema.model_validate(
        {
            "room_type": "bedroom",
            "room_type_source": "bedroom",
            "shape": "rectangular",
            "width": length(5.0, "5 m by 4 m"),
            "depth": length(4.0, "5 m by 4 m"),
            "ceiling_height": length(2.7, "2.7 m ceiling"),
            "furniture": [
                {
                    "catalog_key": key,
                    "source_text": mention,
                    "quantity": 1,
                    "width": None,
                    "depth": None,
                    "height": None,
                }
                for key, mention in [
                    ("queen_bed", "queen bed"),
                    ("desk", "desk"),
                    ("wardrobe", "wardrobe"),
                ]
            ],
            "doors": [
                {
                    "wall": "south",
                    "source_text": "south-wall door",
                    "width": length(0.85, "0.85 m wide"),
                    "offset": length(0.6, "offset 0.6 m"),
                    "height": length(2.1, "height 2.1 m"),
                }
            ],
            "windows": [
                {
                    "wall": "north",
                    "source_text": "north-wall window",
                    "width": length(1.5, "1.5 m wide"),
                    "offset": length(2.7, "offset 2.7 m"),
                    "sill_height": length(0.9, "sill 0.9 m"),
                    "height": length(1.2, "height 1.2 m"),
                }
            ],
            "style": None,
            "hard_constraints": [],
            "soft_preferences": [],
            "missing_or_ambiguous": [],
            "assumptions": [],
            "unsupported_features": [],
        }
    )

"""OFFLINE MOCK catalog-color preview; no live model client or external assets."""

import argparse
import json
from pathlib import Path

from archimind.examples.style_bedroom import offline_style_bedroom
from archimind.render import render_design_3d, render_styled_design_3d


def offline_color_preview():
    workflow, advice = offline_style_bedroom()
    before = workflow.model_dump_json(), advice.model_dump_json()
    original = render_design_3d(workflow.approved_design)
    preview = render_styled_design_3d(workflow.approved_design, advice)
    for source, colored in zip(original.data, preview.data, strict=True):
        left, right = source.to_plotly_json(), colored.to_plotly_json()
        if source.meta["kind"] in ("wall", "floor", "furniture"):
            right["color"] = left["color"]
        assert left == right
    left, right = original.layout.to_plotly_json(), preview.layout.to_plotly_json()
    del right["meta"]["style_preview"]
    assert left == right
    assert (workflow.model_dump_json(), advice.model_dump_json()) == before
    return workflow, advice, preview


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional self-contained HTML preview; no CDN required.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    workflow, advice, figure = offline_color_preview()
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Offline mock — catalog colors</title></head><body><h1>Offline mock — catalog-color preview</h1><p>Existing Layout A, unchanged score 67.721925. Colors only; no physical materials, textures or live model request. Accents remain metadata.</p>'
            + figure.to_html(
                full_html=False,
                include_plotlyjs=True,
                config={"scrollZoom": True, "displaylogo": False},
            )
            + "</body></html>",
            encoding="utf-8",
        )
    if args.json:
        print(
            json.dumps(
                {
                    "mode": "offline_mock",
                    "selected_candidate_index": workflow.selected_candidate_index,
                    "score": workflow.generation.candidates[0].score.total,
                    "geometry_unchanged": True,
                    "metadata_rendered": advice.plan.rendered,
                    "figure": json.loads(figure.to_json()),
                    "output": str(args.output) if args.output is not None else None,
                }
            )
        )
    else:
        print(
            "OFFLINE MOCK — catalog colors on existing Plotly geometry; zero live model requests"
        )
        print(
            "Layout A/index 0; original score 67.721925; geometry, camera, dimensions, openings and reports unchanged."
        )
        print(
            f"Palette: {advice.plan.palette_id}; wall {advice.plan.wall_finish.base_color_hex}; floor {advice.plan.floor_finish.base_color_hex}."
        )
        print(
            "One flat finish per furniture object; original glass, outlines, opacity and lighting retained. Accents are not placed."
        )
        if args.output is not None:
            print(f"Self-contained HTML: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Button-driven layout comparison; geometry and search stay in their APIs.

The result, last error, and selected label belong to the browser's Streamlit
session. Only a Generate Layouts click performs generation and acceptance checks.
Radio changes and seed edits read the stored result. An exception keeps the prior
result/selection; a normal response replaces them, even when it has no candidates.
Browser refresh/disconnect can clear session state; there is no durable storage.
"""

import logging

import streamlit as st

from archimind.geometry import (
    LayoutGenerationResult,
    generate_layout_candidates,
    validate_accessibility,
)
from archimind.models import RoomDesign
from archimind.render import render_design_3d, render_floorplan

RESULT_KEY = "layout_generation_result"
ERROR_KEY = "layout_generation_error"
SELECTION_KEY = "selected_layout"


def _generate(specification: RoomDesign, seed: int) -> LayoutGenerationResult:
    """Validate once at the UI boundary, including the actual candidate geometry."""
    result = LayoutGenerationResult.model_validate(
        generate_layout_candidates(
            specification.room,
            specification.furniture,
            seed=seed,
            max_candidates=2,
            max_attempts=500,
        )
    )
    for candidate in result.candidates:
        actual = validate_accessibility(
            candidate.design, config=result.config, area_tolerance_m2=0.0
        )
        if actual.status != "passed" or actual != candidate.validation:
            raise ValueError("Candidate geometry and its passing report disagree")
    return result


def _show_outcome(result: LayoutGenerationResult) -> None:
    count = len(result.candidates)
    if result.status == "complete":
        noun = "alternative" if count == 1 else "alternatives"
        st.success(f"Generation complete: {count} validated {noun}.")
    elif result.status == "search_exhausted":
        st.warning(
            f"Search exhausted: {count} of {result.requested_candidates} requested "
            "alternatives found. This does not prove the request is infeasible."
        )
    elif result.status == "infeasible":
        st.error("Infeasible under the current dimensions and clearance assumptions.")
    elif result.status == "unsupported":
        st.error("This request cannot be evaluated by the current generator.")
    st.caption(result.message)
    st.caption(
        f"Showing results generated with seed {result.seed} · "
        f"{result.attempts_used} search attempts."
    )


def render_layout_generator(specification: RoomDesign) -> None:
    """Compare stored layouts; one selected candidate supplies both renderers.

    Selection does not copy, regenerate, or spatially revalidate candidate data.
    Renderer schema checks remain part of their existing public contracts.
    """
    st.subheader("AI-Assisted Room Layout Generator")
    st.write(
        "Generate reproducible furniture arrangements with deterministic seeded "
        "placement and spatial checks. Multi-agent reasoning is planned for a "
        "later phase."
    )
    st.markdown("### Room Information")
    room = specification.room
    st.write(
        f"**{room.name}** · {room.width_m:g} m wide × {room.depth_m:g} m deep "
        f"× {room.ceiling_height_m:g} m high"
    )
    st.write(
        "Requested furniture: "
        + ", ".join(item.name for item in specification.furniture)
    )
    st.write(
        "Openings: "
        + "; ".join(
            [f"{door.wall.capitalize()}-wall door" for door in room.doors]
            + [f"{window.wall.capitalize()}-wall window" for window in room.windows]
        )
    )

    st.markdown("### Layout Generation Controls")
    seed = int(
        st.number_input(
            "Random seed",
            min_value=0,
            max_value=2**32 - 1,
            value=42,
            step=1,
            key="layout_seed",
            help="The seed is used the next time you click Generate Layouts.",
        )
    )
    st.caption(
        "Up to two alternatives. Furniture dimensions and openings are preserved; rotation is 0°."
    )
    if st.button("Generate Layouts", type="primary", key="generate_layouts"):
        try:
            with st.spinner("Generating and checking layouts…"):
                result = _generate(specification, seed)
        except Exception:
            logging.getLogger(__name__).exception("Layout generation failed")
            st.session_state[ERROR_KEY] = (
                "Could not generate layouts. Please try again."
            )
        else:
            st.session_state[RESULT_KEY] = result
            st.session_state[SELECTION_KEY] = "Layout A"
            st.session_state.pop(ERROR_KEY, None)

    st.markdown("### Generated Alternatives")
    result = st.session_state.get(RESULT_KEY)
    if st.session_state.get(ERROR_KEY):
        st.error(st.session_state[ERROR_KEY])
        if result is not None:
            st.info("The previous generation result and selection have been kept.")
    if result is None:
        st.info("Choose a seed and click Generate Layouts to create alternatives.")
        return

    _show_outcome(result)
    if seed != result.seed:
        st.info(
            f"Seed {seed} is ready for the next generation. The displayed results "
            f"still use seed {result.seed}; click Generate Layouts to replace them."
        )
    if not result.candidates:
        st.info("No validated alternatives are available to display.")
        return

    labels = [f"Layout {letter}" for letter in "AB"[: len(result.candidates)]]
    st.dataframe(
        [
            {
                "Layout": label,
                "Score (0–100)": candidate.score.total,
                "Validation": candidate.validation.status,
                "Reported issues": len(candidate.validation.violations),
                "Advisory warnings": sum(
                    issue.severity == "warning"
                    for issue in candidate.validation.violations
                ),
            }
            for label, candidate in zip(labels, result.candidates, strict=True)
        ],
        hide_index=True,
        width="stretch",
        column_config={"Score (0–100)": st.column_config.NumberColumn(format="%.6f")},
        key="layout_comparison",
    )
    st.caption(
        "Heuristic comparison score: 80% usable-space ratio + 20% advisory door "
        "clearance ratio. Reported issues include advisory warnings."
    )
    if st.session_state.get(SELECTION_KEY) not in labels:
        st.session_state[SELECTION_KEY] = labels[0]
    selected = st.radio(
        "Select an alternative", labels, horizontal=True, key=SELECTION_KEY
    )
    candidate = result.candidates[labels.index(selected)]
    if candidate.validation.status != "passed":
        st.error(
            "This alternative has no passing spatial report and cannot be displayed."
        )
        return

    st.markdown("### Selected 2D Floor Plan")
    st.write(f"**{selected}** · Heuristic score: **{candidate.score.total:.6f} / 100**")
    st.plotly_chart(
        render_floorplan(candidate.design),
        width="stretch",
        theme=None,
        key="generated-floorplan",
        config={"scrollZoom": True, "displaylogo": False},
        alt=f"{selected}: generated bedroom floor plan with labeled furniture and wall openings.",
    )
    st.dataframe(
        [
            {
                "Furniture": item.name,
                "X (m)": item.x_m,
                "Y (m)": item.y_m,
                "Width (m)": item.width_m,
                "Depth (m)": item.depth_m,
            }
            for item in candidate.design.furniture
        ],
        hide_index=True,
        width="stretch",
        key="layout_positions",
    )

    with st.container(key="selected_design_3d"):
        st.markdown("### Selected 3D Furnished Room")
        st.caption(
            f"{selected} · Same furniture and room data as the selected 2D floor plan. "
            "Drag to orbit; use the modebar to zoom, pan, or reset. "
            "Toggle Walls if a hover target is obscured."
        )
        st.plotly_chart(
            render_design_3d(candidate.design),
            width="stretch",
            theme=None,
            key="generated-design-3d",
            config={"scrollZoom": True, "displaylogo": False},
            alt=f"{selected}: synchronized 3D bedroom with the selected furniture positions and unchanged room openings.",
        )

    st.markdown("### Spatial Validation Summary")
    report = candidate.validation
    warnings = [issue for issue in report.violations if issue.severity == "warning"]
    st.write(
        f"Validation status: **{report.status}** · Reported violations: "
        f"**{len(report.violations)}** · Advisory warnings: **{len(warnings)}**"
    )
    st.dataframe(
        [
            {"Check": name.replace("_", " ").capitalize(), "Result": check.status}
            for name, check in report.checks.items()
        ],
        hide_index=True,
        width="stretch",
        key="layout_validation",
    )
    for issue in warnings:
        st.warning(issue.message)
    st.caption(
        f"Usable-space ratio: {candidate.score.usable_space_ratio:.6f} · "
        f"Advisory-clearance ratio: {candidate.score.advisory_clearance_ratio:.6f}. "
        f"Walking clearance: {report.config.walking_clearance_m:g} m square. "
        "Door approaches are rectangular approximations; actual swing geometry "
        "and building-code compliance are outside this prototype."
    )

"""ArchiMind AI sample preview and generated-layout comparison."""

import streamlit as st

from archimind.examples import create_sample_bedroom
from archimind.render import render_design_3d, render_floorplan, render_room_3d
from archimind.ui import render_layout_generator


def main() -> None:
    """Preserve the sample preview and add button-driven layout alternatives."""
    st.set_page_config(page_title="ArchiMind AI", layout="centered")

    st.title("ArchiMind AI")
    st.subheader("Multi-Agent Interior Design & 3D Spatial Planning")
    st.write(
        "ArchiMind AI is an interior design prototype being developed to turn "
        "natural-language room requirements into validated floor plans and "
        "interactive 3D interiors."
    )

    phase, status = st.columns(2)
    phase.metric("Current development phase", "Task 06B")
    status.metric("Application status", "Running")

    st.divider()
    st.subheader("Planned capabilities")
    st.markdown(
        "- AI-assisted room planning\n"
        "- Selected 2D/3D layout synchronization\n"
        "- Multi-agent collaboration\n"
        "- Versioned projects and export"
    )
    st.caption(
        "These capabilities are planned. Deterministic layout generation, "
        "spatial validation, 2D comparison, and structural/furnished 3D previews are available below."
    )

    st.divider()
    st.subheader("2D Floor Plan Preview")
    design = create_sample_bedroom()
    st.plotly_chart(
        render_floorplan(design),
        width="stretch",
        theme=None,
        key="sample-floorplan",
        config={"scrollZoom": True, "displaylogo": False},
        alt="Top-down 5 by 4 meter bedroom with a south door, north window, bed, desk, and wardrobe.",
    )
    st.caption(
        "Manually specified Task 03 demonstration. Generate and compare "
        "validated alternatives below."
    )

    st.divider()
    with st.container(key="layout_generator"):
        render_layout_generator(design)

    st.divider()
    with st.container(key="room_3d_preview"):
        st.subheader("Interactive 3D Room Preview")
        st.plotly_chart(
            render_room_3d(design.room),
            width="stretch",
            theme=None,
            key="room-3d",
            config={"scrollZoom": True, "displaylogo": False},
            alt="3D sample room structure with a floor, four walls, a south door opening, and a north window.",
        )
        st.caption(
            "Structural-only preview of the fixed sample room. "
            "See the furnished sample below; selected-layout synchronization is planned."
        )

    st.divider()
    with st.container(key="design_3d_preview"):
        st.subheader("Interactive 3D Furnished Room Preview")
        st.plotly_chart(
            render_design_3d(design),
            width="stretch",
            theme=None,
            key="design-3d",
            config={"scrollZoom": True, "displaylogo": False},
            alt="Fixed 3D sample bedroom with a queen bed, desk, wardrobe, four walls, south door opening, and north window.",
        )
        st.caption(
            "Fixed sample bedroom — independent of the selected Layout A/B. "
            "Rendering does not establish spatial validity. "
            "Selected-layout synchronization belongs to Task 06C."
        )


if __name__ == "__main__":
    main()

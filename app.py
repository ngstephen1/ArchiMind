"""ArchiMind AI Foundation screen and canonical-model 2D preview."""

import streamlit as st

from archimind.examples import create_sample_bedroom
from archimind.render import render_floorplan


def main() -> None:
    """Display Foundation content and a manually specified sample floor plan."""
    st.set_page_config(page_title="ArchiMind AI", layout="centered")

    st.title("ArchiMind AI")
    st.subheader("Multi-Agent Interior Design & 3D Spatial Planning")
    st.write(
        "ArchiMind AI is an interior design prototype being developed to turn "
        "natural-language room requirements into validated floor plans and "
        "interactive 3D interiors."
    )

    phase, status = st.columns(2)
    phase.metric("Current development phase", "Foundation")
    status.metric("Application status", "Running")

    st.divider()
    st.subheader("Planned capabilities")
    st.markdown(
        "- AI-assisted room planning\n"
        "- 2D/3D visualization\n"
        "- Spatial validation\n"
        "- Multi-agent collaboration"
    )
    st.caption(
        "These capabilities are planned. The current release provides the "
        "Python package and application foundation."
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
        "Demonstration layout — spatial validation and automatic placement "
        "are not yet implemented."
    )


if __name__ == "__main__":
    main()

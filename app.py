"""Streamlit entry point for the ArchiMind AI foundation screen."""

import streamlit as st


def main() -> None:
    """Display the current development status and planned capabilities."""
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


if __name__ == "__main__":
    main()

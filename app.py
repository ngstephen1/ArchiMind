"""ArchiMind AI sample preview and generated-layout comparison."""

import streamlit as st

from archimind.examples import create_sample_bedroom
from archimind.render import render_design_3d, render_floorplan, render_room_3d
from archimind.ui import render_layout_generator
from archimind.ui.design_agent_chat import render_design_agent


def main() -> None:
    """Preserve the sample preview and add button-driven layout alternatives."""
    st.set_page_config(page_title="ArchiMind AI", layout="centered")

    st.title("ArchiMind AI")
    st.subheader("AI Interior Design & 3D Spatial Planning")
    st.write(
        "ArchiMind AI is an interior design prototype being developed to turn "
        "natural-language room requirements into validated floor plans and "
        "interactive 3D interiors."
    )

    phase, status = st.columns(2)
    phase.metric("Current development phase", "Task 09A")
    status.metric("Application status", "Running")

    st.divider()
    st.subheader("Planned capabilities")
    st.markdown(
        "- Richer AI-assisted room planning and targeted revisions\n"
        "- Full 3D furniture asset catalog\n"
        "- Versioned projects and export"
    )
    st.caption(
        "The capabilities above remain future work. Opt-in Chat bedroom, the optional design agent, qualified catalog retrieval, deterministic layout generation, "
        "spatial validation, synchronized selected 2D/3D layouts, optional interior styling, and standalone sample previews are available below."
    )

    st.divider()
    with st.container(key="design_agent"):
        render_design_agent()

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
            "Independent of Layout A/B; synchronized views appear in the generator section."
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
            "Synchronized selected-layout views appear in the generator section above."
        )

    st.divider()
    st.subheader("Realistic 3D Viewer — Experimental")
    st.caption(
        "Independent architectural room experiment with shared textured chairs "
        "and labeled procedural placeholders. It does not follow generated layouts. "
        "Detailed mesh geometry has not been spatially validated."
    )
    st.markdown(
        "Asset: [Sheen Chair](https://github.com/KhronosGroup/glTF-Sample-Assets/tree/"
        "8f492390ddc7a2ae221a1369ef560589cf8c70fb/Models/SheenChair) · "
        "Eric Chadwick, © 2020 Wayfair, LLC · CC0-1.0 · 4.13 MB."
    )
    # Preserve the existing opt-in preference for current sessions.
    if st.checkbox(
        "Load experimental realistic viewer", key="experimental_chair_enabled"
    ):
        from archimind.examples.sample_chair import create_sample_chair
        from archimind.render.realistic_viewer import (
            ViewerAssetError,
            render_realistic_viewer,
        )

        mode = st.radio(
            "Experimental scene",
            ["Architectural room", "Single chair (06D)", "Charles product (08C-R2)"],
            key="experimental_scene_mode",
        )
        try:
            if mode == "Architectural room":
                from archimind.examples.sample_realistic_room import (
                    create_sample_realistic_room,
                )
                from archimind.render.realistic_scene import render_realistic_scene

                st.caption(
                    "Fixed sample: two instances of the existing chair GLB and a desk "
                    "placeholder. Front walls are translucent; turn them off for a cutaway view."
                )
                render_realistic_scene(create_sample_realistic_room())
            elif mode == "Charles product (08C-R2)":
                from archimind.ui.product_fixture import (
                    render_validated_product_fixture,
                )

                st.caption(
                    "Fixed product demonstration, independent of A/B layouts: two Charles "
                    "armchairs at native scale 1.0 in approved planning envelopes, plus a desk "
                    "placeholder. Published product dimensions remain unchanged. "
                    "This scene is not an optimized or architecturally certified layout."
                )
                st.markdown(
                    "[Charles, Sod — ABO B075X2X4XS](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/original/S/B075X2X4XS.glb) · "
                    "Amazon.com and ABO contributors · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · "
                    "Original GLB unchanged, 4.25 MB. Full attribution accompanies the packaged asset."
                )
                st.caption(
                    "Dataset builders: Matthieu Guillaumin, Thomas Dideriksen, Kenan Deng, "
                    "Himanshu Arora, Jasmine Collins and Jitendra Malik. No endorsement implied."
                )
                render_validated_product_fixture()
            else:
                st.caption(
                    "Original Task 06D single-chair studio; independent of the room experiment."
                )
                render_realistic_viewer(create_sample_chair())
        except (ViewerAssetError, ValueError):
            st.error(
                "The experimental viewer's local asset or configuration is unavailable. "
                "The existing Plotly views remain available."
            )
    else:
        st.info("Enable the experiment to load the local architectural room viewer.")


if __name__ == "__main__":
    main()

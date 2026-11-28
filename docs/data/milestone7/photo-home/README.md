# Photo intake and room alignment

In local Town, choose **Photo home**. Use two to four rectangular rooms in a west-to-east row with a shared depth. This version supports one measured connecting doorway at each shared wall, exterior or shared interior windows and a south entry in the first room. Each image is attached to one room. Enter measured metres and check each doorway's clear width and offset independently from both sides. Interior glazing must agree on offset, width, sill and height in both rooms. Apply the scale confirmation after the final correction.

Optionally send a single photo to OpenAI for a rough depth-to-width ratio and opening observations. Treat the suggestion as a hypothesis and correct it before confirming. Manual intake makes no model requests. Town saves the cleaned, resized source JPEGs in the private local project database. A reopened project's **Photo home** dialog shows the linked images, confirmed dimensions and recorded uncertainty.

The browser receipt uses labeled synthetic source images and user-entered geometry. It covers a rejected doorway mismatch, a corrected two-room project, reopening the private sources and walking through the join in both directions. The test exercises the ordinary UI with providers disabled; it makes no claim about photo-derived measurement accuracy. [Receipt](receipt.json) · [3D cutaway](house.png) · [Walk view](walk.png)

In **Walk**, frame a room, open **Compare revisions**, and bookmark the walking view. In **Finish chat**, apply a room wall color or whole-home floor finish and save another revision. Reopen Compare for a same-camera wipe of both revisions. With local Blender configured, select **3D / Blender HD** to render the confirmed shell directly with Cycles. The photo-home render uses modeled surfaces, confirmed openings and saved finishes. It does not project the uploaded photos onto walls or claim to reconstruct furnishings.

The browser applied dark green paint to the Studio, reopened revision 2, compared it with revision 1 and rendered the same camera with Blender. [Integration receipt](integration.json) · [Room finish revision comparison](r1-r2.jpg) · [Town and Cycles](cycles.jpg)

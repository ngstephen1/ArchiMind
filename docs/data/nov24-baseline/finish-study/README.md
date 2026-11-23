# Bedroom and salon finish study

The [hosted run](https://github.com/ngstephen1/ArchiMind/actions/runs/45115827131) rendered the same revision-2 bedroom doorway, desk and salon cameras in Blender 5.1.2 Cycles CPU at 1920 × 1080 and up to 96 samples. The three frames took 432, 427 and 392 seconds. The pinned baseline supplies the same camera pose, architectural shift and exposure. The [receipt](receipt.json) identifies the manifest, cameras, source PNGs, rendered PNGs, paired JPEGs and editable scene. The full artifact includes the editable Blender model and the render's detailed changes.

In each JPEG, the baseline appears on the left.

| View | Comparison | Observed improvement |
| --- | --- | --- |
| Doorway | [Same crop](bedroom-doorway-detail.jpg) | The mullion and linen folds are readable in highlights. The duvet and throw separate from the wall and bed frame. |
| Desk | [Same crop](bedroom-desk-detail.jpg) | Belaya's oak and the sage chair stay readable. The display preserves the chair pullout and furniture contact at the floor. |
| Salon | [Same full frame](salon-overview-full.jpg) | Window trim, curtains and the route between conversation and dining read more clearly. |

| Frozen rubric | Doorway | Desk | Salon |
| --- | --- | --- | --- |
| Believable bedding and materials | 1 | 1 | 1 |
| Window highlight detail | 2 | — | 2 |
| Grounded furniture | 2 | 2 | 2 |
| Coherent furnishing | 1 | 1 | 1 |
| Visible circulation | 2 | 2 | 2 |

The throw silhouette is softer, but most of the bedding remains visually flat at room scale. The salon's upholstery and practical lamp need a clearer material and lighting contribution. The frozen material criterion stays open, and the final client-book print check belongs to the fresh revision.

The run confirmed all original 40 file-image dependencies were packed at load. It preserved 647 meshes exactly and kept the revised duvet and throw inside their original world-space envelopes. The existing furniture, openings and floor-standing decorations stayed in their saved locations. All added surface detail and the light at the existing salon lamp are procedural. The run acquired no meshes, photographs or textures. The [source study](../../../../scripts/studio_finish_study.py) identifies the procedural overrides.

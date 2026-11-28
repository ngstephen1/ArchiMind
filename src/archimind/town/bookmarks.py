"""Project-owned, revision-independent walk camera bookmarks."""

import json
import math
import threading
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from . import service

_render_slot = threading.BoundedSemaphore(1)

Component = Annotated[float, Field(ge=-500, le=500, allow_inf_nan=False)]


class Camera(BaseModel):
    model_config = ConfigDict(extra="forbid")
    room: str = Field(min_length=1, max_length=80)
    eye: tuple[Component, Component, Component]
    target: tuple[Component, Component, Component]
    fov: float = Field(ge=10, le=120)
    aspect: float = Field(ge=0.15, le=8)


def validate_room(home, pose):
    part = next(
        (p for p in home["rooms"] if p["design"]["room"]["id"] == pose.room), None
    )
    if part is None or math.dist(pose.eye, pose.target) < 0.01:
        raise service.Problem("Select a room and a valid camera.")
    x, y = part["origin"]
    r = part["design"]["room"]
    if not (
        x <= pose.eye[0] <= x + r["width_m"]
        and y <= -pose.eye[2] <= y + r["depth_m"]
        and 0 < pose.eye[1] < r["ceiling_height_m"]
    ):
        raise service.Problem(
            "The saved camera falls outside the room in this revision."
        )


def handle(q, owner, project, method, body):
    head = service.project(q, owner, project)
    if method == "GET":
        return {
            "views": [
                json.loads(r[0])
                for r in q(
                    "SELECT pose FROM town_bookmarks WHERE project=? ORDER BY room",
                    (project,),
                ).fetchall()
            ]
        }
    if method != "POST" or body.get("revision") != head:
        raise service.Problem("Open the latest revision to bookmark a view.", 409)
    pose = Camera.model_validate(body["pose"])
    home = service.revision(q, project, head)
    validate_room(home, pose)
    value = pose.model_dump()
    q(
        "INSERT INTO town_bookmarks(project,room,pose) VALUES(?,?,?) ON CONFLICT(project,room) DO UPDATE SET pose=excluded.pose",
        (project, pose.room, json.dumps(value)),
    )
    return value


def photograph(snapshot, pose, blender):
    """Use the same verified proof as Town HD. Publish only a complete image."""
    import hashlib
    import subprocess
    import tempfile
    from pathlib import Path

    from . import render_queue
    from .design import digest

    validate_room(snapshot["home"], Camera.model_validate(pose))
    proof = render_queue._paths(snapshot, blender) / "proof"
    key = digest([snapshot["home"]["id"], pose])
    output = proof.parent / ("camera-" + key + ".png")
    if output.is_file():
        return output
    imported = bool(snapshot["home"].get("photo_home"))
    if not imported and not render_queue._completed(proof, "proof"):
        raise service.Problem(
            "Generate a Blender proof for this revision in the presentation first.", 409
        )
    if not _render_slot.acquire(blocking=False):
        raise service.Problem(
            "Another bookmarked view is rendering. Try again when it finishes.", 429
        )
    try:
        proof.parent.mkdir(exist_ok=True, parents=True)
        with tempfile.TemporaryDirectory(dir=proof.parent) as temp:
            temp = Path(temp)
            spec = temp / "camera.json"
            manifest = proof / "manifest.json"
            scene_args = [str(proof / "home.blend")]
            if imported:
                source, manifest = temp / "source.json", temp / "manifest.json"
                source.write_text(json.dumps(snapshot))
                subprocess.run(
                    [
                        "node",
                        render_queue.FRONTEND / "export-home.mjs",
                        source,
                        manifest,
                    ],
                    check=True,
                    timeout=30,
                    stdout=subprocess.DEVNULL,
                )
                scene_args = ["--factory-startup"]
            spec.write_text(
                json.dumps(
                    {
                        **pose,
                        "manifest_sha256": hashlib.sha256(
                            manifest.read_bytes()
                        ).hexdigest(),
                    }
                )
            )
            subprocess.run(
                [
                    str(blender),
                    "-b",
                    "--disable-autoexec",
                    *scene_args,
                    "--python-exit-code",
                    "1",
                    "-P",
                    str(render_queue.SCRIPTS / "render_bookmarked_view.py"),
                    "--",
                    str(spec),
                    str(temp / "view.png"),
                    *([str(manifest)] if imported else []),
                ],
                check=True,
                timeout=300,
                stdout=subprocess.DEVNULL,
            )
            (temp / "view.png").replace(output)
    except (OSError, subprocess.SubprocessError) as exc:
        raise service.Problem(
            "The bookmarked render failed. The saved camera is available for retry.",
            503,
        ) from exc
    finally:
        _render_slot.release()
    return output

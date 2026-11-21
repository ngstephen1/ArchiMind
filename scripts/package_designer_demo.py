"""Assemble the two saved conference revisions and their checked Blender outputs."""

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from archimind.designer_handoff.drawings import write_drawings
from archimind.designer_handoff.schedule import write_schedule
from archimind.designer_handoff.survey import Survey, write_survey_dxf

ROOT = Path(__file__).resolve().parents[1]
R1 = "2f50b4194433484014d91df723601c9dbe7f93b914f44bbbc1fe1aa1fa03fb42"
R2 = "51730091069609ac32035ef80b113974ae1d32f448f073479ccf1cdc92d313d2"
BOOK = "8d55758cf9735993d7dc3ce68735e7e848272eba68e5c6075fd2795811d1f8ae"


def sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def verified(path, expected):
    if sha(path) != expected:
        raise ValueError(f"Digest mismatch for {path.name}")
    return path


def demo_shell(room):
    w, d = room["width_m"], room["depth_m"]
    openings = []
    for kind in ("door", "window"):
        for o in room[kind + "s"]:
            wall = ["south", "east", "north", "west"].index(o["wall"])
            offset = o["offset_m"]
            if wall in (2, 3):
                offset = (w if wall == 2 else d) - offset - o["width_m"]
            openings.append(
                dict(
                    id=o["id"],
                    kind=kind,
                    wall=wall,
                    offset_m=offset,
                    width_m=o["width_m"],
                    height_m=o["height_m"],
                    sill_m=o.get("sill_height_m", 0),
                    source="board",
                )
            )
    return Survey(
        source_kind="demonstration",
        vertices_m=[(0, 0), (w, 0), (w, d), (0, d)],
        height_m=room["ceiling_height_m"],
        sources=[
            dict(
                id="board",
                description="Saved Studio House bedroom concept, revision 2.",
            )
        ],
        geometry_source="board",
        height_source="board",
        openings=openings,
        field_checks=[
            "Existing conditions, structural elements, services, opening reveals, sill and hinge positions require an actual site survey."
        ],
    )


def build(boards, scene, photos, out):
    before = verified(boards / "before.json", R1)
    after = verified(boards / "manifest.json", R2)
    verified(scene / "manifest.json", R2)
    old, board = [json.loads(p.read_bytes()) for p in (before, after)]
    receipt = json.loads((scene / "receipt.json").read_bytes())
    eyes = json.loads((photos / "eye-view-receipt.json").read_bytes())
    if old["project"] != board["project"] or (old["revision"], board["revision"]) != (
        1,
        2,
    ):
        raise ValueError("Expected the consecutive revisions of one saved project.")
    for evidence in (eyes, receipt):
        if (evidence["home_id"], evidence["revision"], evidence["manifest_sha256"]) != (
            board["home_id"],
            board["revision"],
            R2,
        ):
            raise ValueError("Render and board identities disagree.")
    if eyes["camera_manifest_sha256"] != R1:
        raise ValueError("Expected camera positions from the first revision.")
    native = verified(scene / "home.blend", receipt["files"]["home.blend"])
    verified(native, eyes["proof_blend_sha256"])
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as scratch:
        root = Path(scratch) / "package"
        root.mkdir()

        def copy(source, member):
            dest = root / member
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)

        copy(ROOT / "docs/developer/STUDIO_HOUSE_DESIGNER_TRANSFER.md", "START-HERE.md")
        copy(before, "revisions/before.json")
        copy(after, "revisions/manifest.json")
        for name in (
            "README.md",
            "chair-comparison.jpg",
            "live-jobs.json",
            "doorway-r1.jpg",
            "doorway-r2.jpg",
            "desk-r1.jpg",
            "desk-r2.jpg",
        ):
            copy(boards / name, "revisions/" + name)
        for record in (old, board):
            write_drawings(
                record,
                root / f"drawings/r{record['revision']}",
                provenance="demonstration",
            )
        room = next(r for r in board["rooms"] if r["room"]["id"] == "bedroom")
        shell = demo_shell(room["room"])
        (root / "drawings/bedroom-concept-shell.json").write_text(
            shell.model_dump_json(indent=2) + "\n"
        )
        write_survey_dxf(shell, root / "drawings/bedroom-concept-shell.dxf")
        write_schedule(
            room,
            {
                "exclusions": [
                    "Freight, installation, labor, tax, permits and contractor scope require separate quotes."
                ]
            },
            root / "procurement",
            project=board["project"],
            revision=board["revision"],
            home_id=board["home_id"],
        )
        copy(native, "native/home.blend")
        copy(scene / "receipt.json", "native/receipt.json")
        copy(photos / "eye-view-receipt.json", "presentation/eye-view-receipt.json")
        copy(
            verified(photos / "Studio-House-Presentation.pdf", BOOK),
            "presentation/Studio-House-Presentation.pdf",
        )
        shots = {s["file"]: s["sha256"] for s in eyes["shots"]}
        for name in ("bedroom-desk.png", "bedroom-doorway.png", "salon-overview.png"):
            copy(verified(photos / name, shots[name]), "presentation/" + name)
        for name in (
            "BELAYA_ATTRIBUTION.txt",
            "ABO_LICENSE_CC_BY_4.0.txt",
            "saved-style-receipt.json",
            "surface-sources.json",
        ):
            copy(
                verified(photos / name, eyes["source_notices"][name]), "sources/" + name
            )
        members = sorted(
            p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
        )
        digests = {p: sha(root / p) for p in members}
        digest_file = root / "SHA256SUMS.txt"
        digest_file.write_text("".join(f"{v}  {k}\n" for k, v in digests.items()))
        digests[digest_file.name] = sha(digest_file)
        staged = Path(scratch) / "checked.zip"
        with zipfile.ZipFile(staged, "w") as archive:
            for member in digests:
                info = zipfile.ZipInfo(member)
                info.compress_type = zipfile.ZIP_DEFLATED
                with archive.open(info, "w") as dest, (root / member).open("rb") as src:
                    shutil.copyfileobj(src, dest)
        with zipfile.ZipFile(staged) as archive:
            for name, expected in digests.items():
                with archive.open(name) as src:
                    if hashlib.file_digest(src, "sha256").hexdigest() != expected:
                        raise ValueError(f"Packaged digest mismatch: {name}")
        staged.replace(out)
    print(f"{out}  {out.stat().st_size} bytes  SHA-256 {sha(out)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--boards", type=Path, default=ROOT / "docs/data/conference-sprint"
    )
    parser.add_argument(
        "--scene", type=Path, default=ROOT / "output/designer-inputs/scene"
    )
    parser.add_argument(
        "--photos", type=Path, default=ROOT / "output/designer-inputs/photos"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "output/designer-handoff/Studio-House-Designer-Handoff.zip",
    )
    args = parser.parse_args()
    build(args.boards, args.scene, args.photos, args.output)

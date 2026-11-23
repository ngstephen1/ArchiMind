"""Validate and package a two-revision Town release, without conference-specific pins."""

import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path

from package_designer_demo import demo_shell, sha, verified
from publish_revision_study import load_revision, measurements
from publish_studio_board import portfolio_cover

from archimind.designer_handoff.drawings import write_drawings
from archimind.designer_handoff.schedule import write_schedule
from archimind.designer_handoff.survey import write_survey_dxf

BEDROOM_VIEWS = ("bedroom-doorway.png", "bedroom-desk.png")
STYLE_NOTICE = "saved-style-receipt.json"
NOTICES = (
    "BELAYA_ATTRIBUTION.txt",
    "ABO_LICENSE_CC_BY_4.0.txt",
    "surface-sources.json",
)


def read_json(path):
    return json.loads(path.read_bytes())


def views_for(board):
    cover = portfolio_cover(board)
    if not re.fullmatch(r"salon-[a-z0-9-]+", cover):
        raise ValueError("The handoff requires a named saved salon cover.")
    return (*BEDROOM_VIEWS, cover + ".png")


def check_photos(photos, board, proof, before_digest):
    receipt = photos / "eye-view-receipt.json"
    eyes = read_json(receipt)
    if (
        eyes["home_id"] != board["home_id"]
        or eyes["revision"] != board["revision"]
        or eyes["manifest_sha256"] != proof["manifest_sha256"]
        or eyes["camera_manifest_sha256"]
        not in {before_digest, proof["manifest_sha256"]}
        or eyes["proof_blend_sha256"] != proof["files"]["home.blend"]
        or eyes["resolution"] != [1920, 1080]
    ):
        raise ValueError(
            "The matched 1080p views must identify the approved edited scene."
        )
    by_view = {shot["file"]: shot["sha256"] for shot in eyes["shots"]}
    views = views_for(board)
    if set(by_view) != set(views) or len(eyes["shots"]) != len(views):
        raise ValueError("Expected exactly three named eye-level views.")
    inputs = {receipt.name: receipt}
    for name in views:
        path = verified(photos / name, by_view[name])
        with path.open("rb") as image:
            header = image.read(24)
        if (
            len(header) != 24
            or header[:8] != b"\x89PNG\r\n\x1a\n"
            or header[12:16] != b"IHDR"
            or struct.unpack(">II", header[16:24]) != (1920, 1080)
        ):
            raise ValueError(f"{name} is not a 1920 × 1080 PNG.")
        inputs[name] = path
    required_notices = set(NOTICES)
    if STYLE_NOTICE in proof["files"]:
        required_notices.add(STYLE_NOTICE)
    if required_notices - eyes["source_notices"].keys():
        raise ValueError("The render receipt is missing a required source notice.")
    for name in sorted(required_notices):
        inputs[name] = verified(photos / name, eyes["source_notices"][name])
    return inputs


def check_book(book, receipt, board, proofs, after, photos):
    inspected = read_json(receipt)
    expected = (
        board["project"],
        board["revision"],
        board["home_id"],
        [proof["manifest_sha256"] for proof in proofs],
        sha(after / "receipt.json"),
    )
    actual = (
        inspected["project"],
        inspected["revision"],
        inspected["home_id"],
        [r["manifest_sha256"] for r in inspected["revisions"]],
        inspected["source_receipt_sha256"],
    )
    if actual != expected:
        raise ValueError(
            "The inspected book must contain this project's two exact revisions."
        )
    expected_images = {
        "doorway": sha(photos["bedroom-doorway.png"]),
        "desk": sha(photos["bedroom-desk.png"]),
    }
    for name, digest in expected_images.items():
        view = inspected["images"][name]
        if isinstance(view, dict):
            if not view.get("fixed_camera"):
                raise ValueError("The book comparison requires fixed bedroom cameras.")
            view = view["sha256"]
        if len(view) != 2 or view[1] != digest:
            raise ValueError("The book receipt refers to different edited photographs.")
    if inspected.get("hero_sha256") != sha(photos[views_for(board)[-1]]):
        raise ValueError("The book receipt refers to different edited photographs.")
    verified(book, inspected["book_sha256"])
    metadata = subprocess.check_output(["pdfinfo", str(book)], text=True)
    count = int(re.search(r"^Pages:\s+(\d+)$", metadata, re.MULTILINE)[1])
    if [row["page"] for row in inspected["inspection"]] != list(range(1, count + 1)):
        raise ValueError("The inspection receipt must cover every PDF page in order.")
    return count


def build(before, after, photos, book, book_receipt, destination, commit):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Provide the declared release commit as a 40-hex Git SHA.")
    if destination.exists():
        raise FileExistsError("Choose a fresh destination for this release.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as stage:
        stage = Path(stage)

        def snapshot(source, folder, names):
            target = stage / folder
            target.mkdir()
            for name in names:
                shutil.copyfile(source / name, target / name)
            return target

        before = snapshot(before, "before", ("manifest.json", "receipt.json"))
        after = snapshot(
            after, "after", ("manifest.json", "receipt.json", "home.blend")
        )
        old, first = load_revision(before)
        board, second = load_revision(after)
        notices = (
            (*NOTICES, STYLE_NOTICE) if (photos / STYLE_NOTICE).is_file() else NOTICES
        )
        photos = snapshot(
            photos, "photos", ("eye-view-receipt.json", *views_for(board), *notices)
        )
        staged_book, staged_inspection = stage / "book.pdf", stage / "inspection.json"
        shutil.copyfile(book, staged_book)
        shutil.copyfile(book_receipt, staged_inspection)
        book, book_receipt = staged_book, staged_inspection

        if old["project"] != board["project"] or [
            old["revision"],
            board["revision"],
        ] != [
            1,
            2,
        ]:
            raise ValueError("Expected a single Town project's first two revisions.")
        movement = [measurements(record) for record in (old, board)]
        if (
            movement[0]["desk_id"] != movement[1]["desk_id"]
            or movement[0]["chair_id"] != movement[1]["chair_id"]
        ):
            raise ValueError(
                "The compared revisions must retain the same chair and desk."
            )
        if movement[0]["chair_home_xy_m"] == movement[1]["chair_home_xy_m"]:
            raise ValueError("The handoff needs a visible chair edit.")
        native = verified(after / "home.blend", second["files"]["home.blend"])
        photo_inputs = check_photos(photos, board, second, first["manifest_sha256"])
        pages = check_book(
            book, book_receipt, board, (first, second), after, photo_inputs
        )

        root = stage / "handoff"
        root.mkdir()

        def copy(source, member):
            target = root / member
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

        for record, source in ((old, before), (board, after)):
            revision = record["revision"]
            copy(source / "manifest.json", f"revisions/r{revision}-manifest.json")
            copy(source / "receipt.json", f"revisions/r{revision}-proof.json")
            write_drawings(
                record, root / f"drawings/r{revision}", provenance="demonstration"
            )
        room = next(part for part in board["rooms"] if part["room"]["id"] == "bedroom")
        shell = demo_shell(
            room["room"],
            description=f"Town project {board['project']}, revision 2 bedroom concept.",
        )
        shell_path = root / "drawings/bedroom-concept-shell"
        shell_path.with_suffix(".json").write_text(
            shell.model_dump_json(indent=2) + "\n"
        )
        write_survey_dxf(shell, shell_path.with_suffix(".dxf"))
        write_schedule(
            room,
            {
                "exclusions": [
                    "Pricing, installation, site measurements and supplier approval require separate checks."
                ]
            },
            root / "procurement",
            project=board["project"],
            revision=2,
            home_id=board["home_id"],
        )
        copy(native, "native/home.blend")
        copy(book, "presentation/Client-Book.pdf")
        copy(book_receipt, "presentation/book-inspection.json")
        for name, source in photo_inputs.items():
            category = "sources" if name in {*NOTICES, STYLE_NOTICE} else "presentation"
            copy(source, f"{category}/{name}")
        evidence = {
            "declared_release_commit": commit,
            "project": board["project"],
            "revision": 2,
            "home_id": board["home_id"],
            "book_pages": pages,
            "manifests_sha256": [first["manifest_sha256"], second["manifest_sha256"]],
            "chair_and_desk": movement,
            "site_status": "demonstration geometry",
        }
        (root / "release.json").write_text(json.dumps(evidence, indent=2) + "\n")
        (root / "START-HERE.md").write_text(
            f"# Town designer handoff\n\nProject `{board['project']}`, revision 2.\n\n"
            "Start with the client book in `presentation/`. Compare the dimensioned "
            "plans in `drawings/` and open the editable Cycles scene in `native/`. "
            "The bedroom DXF uses metres. Review finish evidence and the furniture schedule "
            "before requesting supplier quotes.\n\n"
            "Measure actual openings, site conditions and fit before ordering or construction. "
            "From this directory, verify the files with `shasum -a 256 -c SHA256SUMS.txt`.\n"
        )
        members = {
            path.relative_to(root).as_posix(): sha(path)
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }
        checksums = root / "SHA256SUMS.txt"
        checksums.write_text(
            "".join(f"{digest}  {name}\n" for name, digest in members.items())
        )
        members[checksums.name] = sha(checksums)
        archive = stage / "handoff.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as packed:
            for name, digest in members.items():
                if sha(root / name) != digest:
                    raise ValueError(f"Staged file changed: {name}")
                packed.write(root / name, name)
        with zipfile.ZipFile(archive) as packed:
            for name, digest in members.items():
                with packed.open(name) as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                        raise ValueError(f"ZIP checksum mismatch: {name}")
        destination.hardlink_to(archive)
    print(f"{destination}  SHA-256 {sha(destination)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("before", "after", "photos", "book", "book_receipt", "destination"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--commit", required=True)
    options = parser.parse_args()
    build(**vars(options))

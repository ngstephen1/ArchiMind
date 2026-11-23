"""Create a printable, revision-bound bedroom comparison from two Blender proof folders."""

import argparse
import base64
import hashlib
import json
import math
from html import escape
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_revision(directory):
    path = directory / "manifest.json"
    board = json.loads(path.read_bytes())
    proof = json.loads((directory / "receipt.json").read_bytes())
    if (
        digest(path) != proof["manifest_sha256"]
        or proof["files"]["manifest.json"] != proof["manifest_sha256"]
        or (board["home_id"], board["revision"])
        != (proof["home_id"], proof["revision"])
        or board["project"] != board["bedroom"]["project"]
        or board["home_id"] != board["bedroom"]["home_id"]
        or board["revision"] != board["bedroom"]["revision"]
    ):
        raise ValueError(
            "The render receipt and bedroom must identify the exported revision."
        )
    return board, proof


def measurements(board):
    parts = [p for p in board["rooms"] if p["room"]["id"] == "bedroom"]
    if len(parts) != 1:
        raise ValueError("Expected one bedroom.")
    room = parts[0]["room"]
    items = {f["id"]: f for f in parts[0]["furniture"]}
    chair, desk = items["desk-chair"], items["belaya"]
    if chair["rotation_deg"] or desk["rotation_deg"]:
        raise ValueError(
            "Rotated furniture requires a different footprint calculation."
        )
    gap = math.hypot(
        *[
            max(
                0,
                chair[pos] - desk[pos] - desk[size],
                desk[pos] - chair[pos] - chair[size],
            )
            for pos, size in (("x_m", "width_m"), ("y_m", "depth_m"))
        ]
    )
    (window,) = [w for w in room["windows"] if w["id"] == "bedroom-window"]
    mid = window["offset_m"] + window["width_m"] / 2
    wall = window["wall"]
    midpoint = {
        "west": (0, mid),
        "east": (room["width_m"], mid),
        "north": (mid, room["depth_m"]),
        "south": (mid, 0),
    }[wall]
    centre = (desk["x_m"] + desk["width_m"] / 2, desk["y_m"] + desk["depth_m"] / 2)
    return {
        "chair_xy_m": [chair["x_m"], chair["y_m"]],
        "chair_home_xy_m": [
            parts[0]["origin"][0] + chair["x_m"],
            parts[0]["origin"][1] + chair["y_m"],
        ],
        "chair_desk_gap_m": gap,
        "desk_center_to_window_midpoint_m": math.dist(centre, midpoint),
        "window_wall": wall,
        "desk_id": desk["id"],
        "chair_id": chair["id"],
        "window_id": window["id"],
    }


def matched_frames(boards, receipts, directories, eyes):
    """Use actual camera transforms for each image, including independent proof views."""
    frames = {k: [] for k in ("doorway", "desk")}
    if bool(eyes[0]) != bool(eyes[1]):
        raise ValueError("Supply both eye-view directories for a matched HD study.")
    camera_sources = {receipt["manifest_sha256"] for receipt in receipts}
    camera_source = None
    for board, proof, directory, eye in zip(
        boards, receipts, directories, eyes, strict=True
    ):
        (room,) = [r for r in board["rooms"] if r["room"]["id"] == "bedroom"]
        hd = json.loads((eye / "eye-view-receipt.json").read_bytes()) if eye else None
        if hd and (
            hd["home_id"] != board["home_id"]
            or hd["revision"] != board["revision"]
            or hd["manifest_sha256"] != proof["manifest_sha256"]
            or hd["camera_manifest_sha256"] not in camera_sources
            or camera_source not in (None, hd["camera_manifest_sha256"])
            or hd["proof_blend_sha256"] != proof["files"]["home.blend"]
        ):
            raise ValueError(
                "Eye-view receipt disagrees with the scene or camera source."
            )
        if hd:
            camera_source = hd["camera_manifest_sha256"]
        for view, pair in frames.items():
            filename = f"bedroom-{view}.png"
            if hd:
                (shot,) = [
                    s
                    for s in hd["shots"]
                    if s.get("room", "bedroom") == "bedroom" and s["view"] == view
                ]
                if shot["file"] != filename:
                    raise ValueError("Unexpected camera filename.")
                camera, expected, path = shot["camera"], shot["sha256"], eye / filename
            else:
                (camera,) = [c for c in room["cameras"] if c["id"] == view]
                expected, path = proof["files"][filename], directory / filename
            if digest(path) != expected:
                raise ValueError("Camera image digest mismatch.")
            pair.append((camera, path, expected))
        if hd and any(
            len(pair) == 2 and pair[0][0] != pair[1][0] for pair in frames.values()
        ):
            raise ValueError("HD cameras moved between revisions.")
    return frames


def build(directories, eyes, dest):
    boards, receipts = zip(*(load_revision(p) for p in directories), strict=True)
    before, after = boards
    if (
        before["project"] != after["project"]
        or after["revision"] != before["revision"] + 1
    ):
        raise ValueError("Supply consecutive revisions of the same project.")
    rows = [measurements(board) for board in boards]
    frames = matched_frames(boards, receipts, directories, eyes)
    displacement = math.dist(rows[0]["chair_home_xy_m"], rows[1]["chair_home_xy_m"])
    pages = []
    for view, pair in frames.items():
        figures = []
        for board, row, (_, path, _) in zip(boards, rows, pair, strict=True):
            image = base64.b64encode(path.read_bytes()).decode("ascii")
            figures.append(
                f'<figure><img src="data:image/png;base64,{image}"><figcaption>Revision {board["revision"]} &nbsp;·&nbsp; Chair to desk {row["chair_desk_gap_m"]:.3f} m</figcaption></figure>'
            )
        same = pair[0][0] == pair[1][0]
        pages.append(f"""<section><header>ARCHIMIND &emsp; / &emsp; INTERIOR DESIGN DEVELOPMENT</header>
        <h1>{"The bedroom approach" if view == "doorway" else "At the writing desk"}</h1>
        <p>{"Fixed camera across both revisions." if same else "Independently framed cameras. Use the plan dimensions to compare positions."}
        &emsp; Blender Cycles · {"HD photography" if eyes[0] else "CPU proof"}</p>
        <main>{"".join(figures)}</main><article><div><h2>{displacement * 1000:.0f} mm</h2>Writing-chair displacement on the whole-home plan</div>
        <div><h2>{rows[1]["desk_center_to_window_midpoint_m"]:.3f} m</h2>Desk center to {escape(rows[1]["window_wall"])} window midpoint in the edited room</div></article>
        <p>Chair and desk clearances above use their floor footprints. Confirm passage between desk supports,
        floor-to-apron height and seated pullback before specifying the pair. Window distance alone does not establish glare performance.</p>
        <footer>{escape(after["project"])} · {escape(before["home_id"][:12])} → {escape(after["home_id"][:12])} · desk-chair / belaya / bedroom-window</footer></section>""")
    css = """@page{size:A3 landscape;margin:0}*{box-sizing:border-box}body{margin:0;color:#263c34;background:#f9f7f1;font:14pt/1.45 Arial,sans-serif}section{width:420mm;height:297mm;padding:14mm 17mm;break-after:page;position:relative}section:last-child{break-after:auto}header,footer{font-size:10pt;letter-spacing:.07em;border-bottom:1px solid #86958a;padding-bottom:3mm}h1,h2{font:normal 39pt/1 Georgia,serif;margin:6mm 0 2mm}h2{font-size:27pt}main,article{display:grid;grid-template-columns:1fr 1fr;gap:8mm}figure{margin:1mm 0}img{width:100%;aspect-ratio:16/9;object-fit:contain}figcaption{font-weight:bold}footer{position:absolute;bottom:9mm;left:17mm;right:17mm;border:0;border-top:1px solid #86958a;padding-top:3mm}"""
    dest.write_text(
        '<!DOCTYPE html><html lang="en"><meta charset="utf-8"><title>Bedroom revision study</title><style>'
        + css
        + "</style>"
        + "".join(pages)
        + "</html>"
    )
    report = {
        "project": after["project"],
        "displacement_m": displacement,
        "revisions": [
            {
                "revision": b["revision"],
                "home_id": b["home_id"],
                "manifest_sha256": r["manifest_sha256"],
                **m,
            }
            for b, r, m in zip(boards, receipts, rows, strict=True)
        ],
        "images": {
            v: {"fixed_camera": p[0][0] == p[1][0], "sha256": [f[2] for f in p]}
            for v, p in frames.items()
        },
        "html_sha256": digest(dest),
    }
    dest.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("output_html", type=Path)
    parser.add_argument("--eye-views", nargs=2, type=Path, metavar=("BEFORE", "AFTER"))
    args = parser.parse_args()
    build((args.before, args.after), args.eye_views or (None, None), args.output_html)

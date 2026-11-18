"""Publish a visually reviewed Blender candidate into the local source checkout.

The writing chair (category ``chair``, concept ``oak-sage-writing-chair``) keeps
its PR #21 path: authoring schema 1, ``chair.*`` files, the CI operator run and
the exact recipe hash. Every other piece uses authoring schema 2 with
``piece.*`` files, a declared ``category`` and ``dimensions_wdh_m`` that must
match ``--category``/``--wdh`` and the measured GLB bounds.
"""

import argparse
import json
import re
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image

from archimind.assets import inspection
from archimind.assets.designer_concepts import (
    CATEGORIES,
    WRITING_CHAIR_ID,
    inspect_chair,
    inspect_piece,
)

_CI_RUN = r"https://github\.com/ngstephen1/ArchiMind/actions/runs/[0-9]+"
_LOCAL_RUN = r"local-operator:[0-9]{4}-[0-9]{2}-[0-9]{2}"


def _json(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode()


def _immutable(path, content):
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"Existing artifact differs: {path.name}")
    else:
        with path.open("xb") as file:
            file.write(content)


def _check_previews(payload):
    for image in ("front.png", "three-quarter.png"):
        with Image.open(BytesIO(payload[image])) as preview:
            if preview.format != "PNG" or preview.size != (600, 640):
                raise ValueError("Unexpected preview size or format")
            preview.load()


def _writing_chair(candidate, root, source, meta):
    versions = {"gentle": "1.0.0", "deep": "1.1.0"}
    if (
        meta["schema_version"] != 1
        or meta["concept_id"] != WRITING_CHAIR_ID
        or meta["version"] != versions[meta["variant"]]
        or meta["dimensions_wdh_m"] != [0.48, 0.52, 0.83]
        or meta["seat_height_m"] != 0.455
        or not meta["name"]
        or not meta["attribution"]
        or not meta["blender_version"]
        or meta["inputs"]["author_script_sha256"]
        != sha256((root / "scripts/author_designer_chair.py").read_bytes()).hexdigest()
    ):
        raise ValueError("Unexpected authoring identity, dimensions or source")
    if not re.fullmatch(_CI_RUN, source):
        raise ValueError("Supply the successful authoring run URL")
    names = ("chair.glb", "chair.blend", "front.png", "three-quarter.png")
    payload = {name: inspection._read_local(candidate / name) for name in names}
    digests = {k: sha256(v).hexdigest() for k, v in payload.items()}
    if digests != meta["sha256"]:
        raise ValueError("Candidate digest mismatch")
    measured = inspect_chair(payload["chair.glb"])
    _check_previews(payload)
    operator = json.loads(inspection._read_local(candidate.parent / "operator.json"))
    if operator[meta["variant"]]["sha256"] != digests:
        raise ValueError("Candidate does not match operator receipt")
    return payload, digests, measured, (0.48, 0.52, 0.83), "chair"


def _piece(candidate, source, meta, category, wdh):
    if (
        meta["schema_version"] != 2
        or category not in CATEGORIES
        or meta["category"] != category
        or meta["concept_id"] == WRITING_CHAIR_ID
        or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", meta["concept_id"])
        or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", meta["version"])
        or [float(v) for v in meta["dimensions_wdh_m"]] != [float(v) for v in wdh]
        or not meta["name"]
        or not meta["attribution"]
        or not meta["blender_version"]
    ):
        raise ValueError("Unexpected authoring identity, category or dimensions")
    if not (re.fullmatch(_CI_RUN, source) or re.fullmatch(_LOCAL_RUN, source)):
        raise ValueError("Supply the authoring run URL or local-operator:<date>")
    names = ("piece.glb", "piece.blend", "front.png", "three-quarter.png")
    payload = {name: inspection._read_local(candidate / name) for name in names}
    digests = {k: sha256(v).hexdigest() for k, v in payload.items()}
    if digests != meta["sha256"]:
        raise ValueError("Candidate digest mismatch")
    measured = inspect_piece(payload["piece.glb"], wdh)
    _check_previews(payload)
    operator = json.loads(inspection._read_local(candidate.parent / "operator.json"))
    if operator[f"{meta['concept_id']}@{meta['version']}"]["sha256"] != digests:
        raise ValueError("Candidate does not match operator receipt")
    return payload, digests, measured, tuple(float(v) for v in wdh), category


def release(candidate, root, source, *, category="chair", wdh=None):
    meta = json.loads(inspection._read_local(candidate / "authoring.json"))
    if category == "chair" and meta.get("concept_id") == WRITING_CHAIR_ID:
        payload, digests, measured, size, category = _writing_chair(
            candidate, root, source, meta
        )
        model, blend = "chair.glb", "chair.blend"
    else:
        if wdh is None:
            raise ValueError("Supply --wdh for a designer piece")
        payload, digests, measured, size, category = _piece(
            candidate, source, meta, category, wdh
        )
        model, blend = "piece.glb", "piece.blend"
    record = {k: meta[k] for k in ("concept_id", "version", "name")}
    record.update(
        category=category,
        sha256=digests[model],
        front_sha256=digests["front.png"],
        three_quarter_sha256=digests["three-quarter.png"],
        width_m=size[0],
        depth_m=size[1],
        height_m=size[2],
        bytes=len(payload[model]),
    )
    directory = root / "src/archimind/_viewer_assets"
    path = directory / "designer_registry.json"
    lock = directory / ".designer-release.lock"
    # Close the lock file before unlinking it: Windows cannot delete open files.
    lock.open("x").close()
    try:
        registry = json.loads(path.read_bytes())
        if registry["schema_version"] == 1:
            registry = {
                "schema_version": 2,
                "pieces": [{**r, "category": "chair"} for r in registry["chairs"]],
            }
        if registry["schema_version"] != 2:
            raise ValueError("Unsupported designer registry")
        previous = [
            r
            for r in registry["pieces"]
            if (r["concept_id"], r["version"])
            == (record["concept_id"], record["version"])
        ]
        if previous and previous != [record]:
            raise ValueError("An immutable release already exists for this version")
        archive = root / "design" / record["concept_id"] / record["version"]
        archive.mkdir(parents=True, exist_ok=True)
        receipt = {
            "authoring": meta,
            "inspection": measured,
            "operator_run": source,
            "review": f"Front and three-quarter images reviewed; approved as a concept {category}.",
        }
        _immutable(archive / "release.json", _json(receipt))
        _immutable(archive / blend, payload[blend])
        for name in (model, "front.png", "three-quarter.png"):
            _immutable(
                directory / ("designer-" + digests[name] + Path(name).suffix),
                payload[name],
            )
        if not previous:
            registry["pieces"].append(record)
            with NamedTemporaryFile(dir=directory, delete=False) as tmp:
                tmp.write(_json(registry))
            Path(tmp.name).replace(path)
    finally:
        lock.unlink()
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--operator-run", required=True)
    parser.add_argument("--category", choices=sorted(CATEGORIES), default="chair")
    parser.add_argument(
        "--wdh",
        type=float,
        nargs=3,
        metavar=("WIDTH_M", "DEPTH_M", "HEIGHT_M"),
        help="Reservation the piece must fill exactly (required except for the writing chair)",
    )
    parser.add_argument(
        "--approve-reviewed-previews", action="store_true", required=True
    )
    args = parser.parse_args()
    print(
        release(
            args.candidate.resolve(),
            Path(__file__).resolve().parents[1],
            args.operator_run,
            category=args.category,
            wdh=tuple(args.wdh) if args.wdh else None,
        )
    )

"""Admit both visually reviewed bedroom assets after checking their Blender receipts."""

import argparse
import json
import os
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from PIL import Image

from archimind.assets.designer_concepts import BEDROOM_SIZES, inspect_concept
from release_designer_chair import _immutable, _json


def release(candidates, root, run):
    assets = root / "src/archimind/_viewer_assets"
    path = assets / "designer_registry.json"
    registry = json.loads(path.read_bytes())
    records = []
    for key, dims in sorted(BEDROOM_SIZES.items()):
        source = candidates / key
        meta = json.loads((source / "authoring.json").read_bytes())
        if (
            meta["concept_id"] != key
            or meta["version"] != "1.0.0"
            or tuple(meta["dimensions_wdh_m"]) != dims
            or meta["reopened"] is not True
            or meta["recipe_sha256"]
            != sha256(
                (root / "scripts/author_bedroom_collection.py").read_bytes()
            ).hexdigest()
        ):
            raise ValueError("Unexpected Blender authoring evidence")
        files = ["model.glb", "editable.blend", "front.png", "three-quarter.png"]
        data = {f: (source / f).read_bytes() for f in files}
        hashes = {f: sha256(data[f]).hexdigest() for f in files}
        if hashes != meta["sha256"]:
            raise ValueError("Artifact integrity check failed")
        checked = inspect_concept(data["model.glb"], dims)
        for f in files[2:]:
            with Image.open(BytesIO(data[f])) as image:
                if image.format != "PNG" or image.size != (600, 640):
                    raise ValueError("Unexpected preview")
                image.load()
        release = root / "design" / key / meta["version"]
        release.mkdir(parents=True, exist_ok=True)
        _immutable(release / "editable.blend", data["editable.blend"])
        _immutable(
            release / "release.json",
            _json(
                {
                    "authoring": meta,
                    "inspection": checked,
                    "authoring_run": f"https://github.com/ngstephen1/ArchiMind/actions/runs/{run}",
                    "attribution": "Original ArchiMind geometry and base materials.",
                }
            ),
        )
        for f in ["model.glb", *files[2:]]:
            _immutable(assets / f"designer-{hashes[f]}{Path(f).suffix}", data[f])
        records.append(
            dict(
                concept_id=key,
                version=meta["version"],
                name=meta["name"],
                sha256=hashes["model.glb"],
                front_sha256=hashes["front.png"],
                three_quarter_sha256=hashes["three-quarter.png"],
                width_m=dims[0],
                depth_m=dims[1],
                height_m=dims[2],
                bytes=len(data["model.glb"]),
            )
        )
    if "bedroom" in registry and registry["bedroom"] != records:
        raise ValueError("Release already exists with different content")
    registry["bedroom"] = records
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(_json(registry))
    os.replace(tmp, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("--authoring-run", type=int, required=True)
    parser.add_argument(
        "--approve-reviewed-previews", action="store_true", required=True
    )
    args = parser.parse_args()
    release(args.candidates, Path(__file__).resolve().parents[1], args.authoring_run)

"""Publish a visually reviewed Blender candidate into the local source checkout."""

import argparse
import json
import re
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image

from archimind.assets import inspection
from archimind.assets.designer_concepts import inspect_chair


def _json(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode()


def _immutable(path, content):
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"Existing artifact differs: {path.name}")
    else:
        with path.open("xb") as file:
            file.write(content)


def release(candidate, root, source):
    meta = json.loads(inspection._read_local(candidate / "authoring.json"))
    versions = {"gentle": "1.0.0", "deep": "1.1.0"}
    if (
        meta["schema_version"] != 1
        or meta["concept_id"] != "oak-sage-writing-chair"
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
    payload = {
        name: inspection._read_local(candidate / name)
        for name in ("chair.glb", "chair.blend", "front.png", "three-quarter.png")
    }
    digests = {k: sha256(v).hexdigest() for k, v in payload.items()}
    if digests != meta["sha256"]:
        raise ValueError("Candidate digest mismatch")
    measured = inspect_chair(payload["chair.glb"])
    for image in ("front.png", "three-quarter.png"):
        with Image.open(BytesIO(payload[image])) as preview:
            if preview.format != "PNG" or preview.size != (600, 640):
                raise ValueError("Unexpected preview size or format")
            preview.load()
    if not re.fullmatch(
        r"https://github\.com/ngstephen1/ArchiMind/actions/runs/[0-9]+", source
    ):
        raise ValueError("Supply the successful authoring run URL")
    operator = json.loads(inspection._read_local(candidate.parent / "operator.json"))
    if operator[meta["variant"]]["sha256"] != digests:
        raise ValueError("Candidate does not match operator receipt")
    record = {k: meta[k] for k in ("concept_id", "version", "name")}
    record.update(
        sha256=digests["chair.glb"],
        front_sha256=digests["front.png"],
        three_quarter_sha256=digests["three-quarter.png"],
        width_m=0.48,
        depth_m=0.52,
        height_m=0.83,
        bytes=len(payload["chair.glb"]),
    )
    directory = root / "src/archimind/_viewer_assets"
    path = directory / "designer_registry.json"
    lock = directory / ".designer-release.lock"
    with lock.open("x"):
        try:
            registry = json.loads(path.read_bytes())
            if registry["schema_version"] != 1:
                raise ValueError("Unsupported designer registry")
            previous = [
                r
                for r in registry["chairs"]
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
                "review": "Front and three-quarter images reviewed; approved as a concept chair.",
            }
            _immutable(archive / "release.json", _json(receipt))
            _immutable(archive / "chair.blend", payload["chair.blend"])
            for name in ("chair.glb", "front.png", "three-quarter.png"):
                _immutable(
                    directory / ("designer-" + digests[name] + Path(name).suffix),
                    payload[name],
                )
            if not previous:
                registry["chairs"].append(record)
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
    parser.add_argument(
        "--approve-reviewed-previews", action="store_true", required=True
    )
    args = parser.parse_args()
    print(
        release(
            args.candidate.resolve(),
            Path(__file__).resolve().parents[1],
            args.operator_run,
        )
    )

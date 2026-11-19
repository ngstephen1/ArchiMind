"""Fetch one CC0 asset from Poly Haven or ambientCG into the style-pack store.

    python -I scripts/fetch_cc0_asset.py --source polyhaven --id oak_veneer_01 \
        --kind material [--roles diffuse,normal,roughness] [--high-roles diffuse]

Downloads go to a new, empty temporary directory and are only ever read as
data. Poly Haven files are checked against the API's published MD5. Textures
are re-encoded as WebP (1k for every role, plus 2k for ``--high-roles``);
environments stay 1k Radiance .hdr; glTF models are packed into a single GLB.
Each output is written as ``packs/assets/<sha256>.<ext>``; the release record
in ``packs/releases.json`` and the line in ``packs/THIRD_PARTY_NOTICES.txt``
are added or replaced. The asset ID is ``<source>:<slug>``.
"""

import argparse
import copy
import hashlib
import io
import json
import re
import struct
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "src/archimind/_viewer_assets/packs"
USER_AGENT = "archimind-asset-fetch/1.0"
POLYHAVEN_KEYS = {
    "diffuse": "Diffuse",
    "normal": "nor_gl",
    "roughness": "Rough",
    "ao": "AO",
    "metalness": "Metal",
}
AMBIENTCG_SUFFIX = {
    "diffuse": "Color",
    "normal": "NormalGL",
    "roughness": "Roughness",
    "ao": "AmbientOcclusion",
    "metalness": "Metalness",
}
_PX = {"1k": 1024, "2k": 2048}


def polyhaven_material_plan(files, roles, high_roles):
    """Which Poly Haven texture files to fetch: role, tier, target px, url, md5."""
    plan = []
    for role in roles:
        key = POLYHAVEN_KEYS.get(role)
        if not key or key not in files:
            raise ValueError(f"Poly Haven asset has no {role} map")
        sizes = ("1k", "2k") if role in high_roles else ("1k",)
        for size in sizes:
            entry = files[key].get(size, {})
            fmt = entry.get("jpg") or entry.get("png")
            if not fmt:
                raise ValueError(f"Poly Haven asset has no {size} {role} map")
            tier = "both" if len(sizes) == 1 else ("low" if size == "1k" else "high")
            plan.append(
                {
                    "role": role,
                    "tier": tier,
                    "px": _PX[size],
                    "url": fmt["url"],
                    "md5": fmt.get("md5"),
                }
            )
    return plan


def to_webp(data, px):
    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        image = image.convert("RGB")
        if image.size != (px, px):
            image = image.resize((px, px), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        image.save(out, "WEBP", quality=86, method=6)
    return out.getvalue()


def _pad(blob, fill=b"\0"):
    while len(blob) % 4:
        blob += fill
    return blob


def _mime(uri, data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    raise ValueError(f"Unsupported model image: {uri}")


def pack_glb(doc, resources):
    """Pack a glTF document and its external buffers/images into one GLB."""
    doc = copy.deepcopy(doc)
    blob = bytearray()
    offsets = []
    for buffer in doc.get("buffers", []):
        data = resources[buffer["uri"]]
        _pad(blob)
        offsets.append(len(blob))
        blob += data
    views = doc.setdefault("bufferViews", [])
    for view in views:
        view["byteOffset"] = view.get("byteOffset", 0) + offsets[view["buffer"]]
        view["buffer"] = 0
    for image in doc.get("images", []):
        if "uri" not in image:
            continue
        uri = image.pop("uri")
        data = resources[uri]
        _pad(blob)
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)})
        image["bufferView"] = len(views) - 1
        image["mimeType"] = _mime(uri, data)
        blob += data
    _pad(blob)
    doc["buffers"] = [{"byteLength": len(blob)}]
    text = _pad(bytearray(json.dumps(doc, separators=(",", ":")).encode()), b" ")
    total = 12 + 8 + len(text) + 8 + len(blob)
    return (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<II", len(text), 0x4E4F534A)
        + bytes(text)
        + struct.pack("<II", len(blob), 0x004E4942)
        + bytes(blob)
    )


def notice_line(asset_id, name, authors, url):
    return f"{asset_id} — {name} by {', '.join(authors)}, CC0 1.0 (public domain dedication), {url}"


def _hdr_size(data):
    for line in data[:4096].split(b"\n")[1:]:
        if match := re.fullmatch(rb"-Y (\d+) \+X (\d+)", line.strip()):
            return int(match[2]), int(match[1])
    raise ValueError("No .hdr resolution line")


def _get(url, workdir, md5=None):
    if not url.startswith(
        (
            "https://dl.polyhaven.org/",
            "https://api.polyhaven.com/",
            "https://ambientcg.com/",
            "https://acg-download.struffelproductions.com/",
        )
    ):
        raise ValueError(f"Refusing unexpected download host: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(64 * 1024 * 1024 + 1)
    if len(data) > 64 * 1024 * 1024:
        raise ValueError(f"Download too large: {url}")
    if md5 and hashlib.md5(data).hexdigest() != md5:
        raise ValueError(f"Upstream checksum mismatch: {url}")
    (workdir / hashlib.sha256(url.encode()).hexdigest()[:16]).write_bytes(data)
    return data


def _store(data, ext):
    digest = hashlib.sha256(data).hexdigest()
    path = PACKS / "assets" / f"{digest}.{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)
    return digest


def _file(role, tier, data, ext, size=None):
    row = {
        "role": role,
        "tier": tier,
        "sha256": _store(data, ext),
        "ext": ext,
        "bytes": len(data),
    }
    if size:
        row["width_px"], row["height_px"] = size
    return row


def fetch_polyhaven(slug, kind, roles, high_roles, workdir):
    info = json.loads(_get(f"https://api.polyhaven.com/info/{slug}", workdir))
    files = json.loads(_get(f"https://api.polyhaven.com/files/{slug}", workdir))
    checksums, rows = [], []
    if kind == "material":
        for item in polyhaven_material_plan(files, roles, high_roles):
            raw = _get(item["url"], workdir, item["md5"])
            checksums.append(item["md5"])
            rows.append(
                _file(
                    item["role"],
                    item["tier"],
                    to_webp(raw, item["px"]),
                    "webp",
                    (item["px"], item["px"]),
                )
            )
    elif kind == "environment":
        entry = files["hdri"]["1k"]["hdr"]
        raw = _get(entry["url"], workdir, entry["md5"])
        checksums.append(entry["md5"])
        rows.append(_file("hdr", "both", raw, "hdr", _hdr_size(raw)))
    else:
        entry = files["gltf"]["1k"]["gltf"]
        doc = json.loads(_get(entry["url"], workdir, entry.get("md5")))
        resources = {
            uri: _get(meta["url"], workdir, meta.get("md5"))
            for uri, meta in entry.get("include", {}).items()
        }
        checksums.append(entry.get("md5"))
        rows.append(_file("model", "both", pack_glb(doc, resources), "glb"))
    authors = sorted(info.get("authors", {})) or ["Poly Haven"]
    return (
        info.get("name", slug),
        authors,
        f"https://polyhaven.com/a/{slug}",
        rows,
        checksums,
    )


def fetch_ambientcg(slug, kind, roles, high_roles, workdir):
    if kind != "material":
        raise ValueError("ambientCG support covers materials only")
    meta = json.loads(
        _get(
            f"https://ambientcg.com/api/v2/full_json?id={slug}&include=downloadData",
            workdir,
        )
    )["foundAssets"][0]
    downloads = meta["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"][
        "downloads"
    ]
    rows = []
    for size in ("1K", "2K"):
        wanted = [r for r in roles if size == "1K" or r in high_roles]
        if not wanted:
            continue
        link = next(
            d["downloadLink"] for d in downloads if d["attribute"] == f"{size}-JPG"
        )
        with zipfile.ZipFile(io.BytesIO(_get(link, workdir))) as archive:
            names = archive.namelist()
            for role in wanted:
                member = next(
                    (
                        n
                        for n in names
                        if n.endswith(f"_{AMBIENTCG_SUFFIX[role]}.jpg") and "/" not in n
                    ),
                    None,
                )
                if member is None:
                    raise ValueError(f"ambientCG asset has no {role} map")
                px = 1024 if size == "1K" else 2048
                tier = (
                    "both"
                    if role not in high_roles
                    else ("low" if size == "1K" else "high")
                )
                rows.append(
                    _file(
                        role, tier, to_webp(archive.read(member), px), "webp", (px, px)
                    )
                )
    return (
        meta.get("displayName", slug),
        ["ambientCG"],
        f"https://ambientcg.com/view?id={slug}",
        rows,
        [],
    )


def record(asset_id, kind, url, upstream, rows, name, authors):
    sys.path.insert(0, str(ROOT / "src"))
    from archimind.style_packs.models import AssetRelease
    from archimind.style_packs.release import verify_release

    release = AssetRelease.model_validate(
        {
            "asset_id": asset_id,
            "kind": kind,
            "license": "CC0-1.0",
            "source_url": url,
            "upstream_checksum": upstream,
            "files": rows,
        }
    )
    verify_release(release, PACKS / "assets")
    path = PACKS / "releases.json"
    releases = [
        r
        for r in json.loads(path.read_text(encoding="utf-8"))
        if r["asset_id"] != asset_id
    ]
    releases.append(release.model_dump(mode="json"))
    releases.sort(key=lambda r: r["asset_id"])
    path.write_text(
        json.dumps(releases, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    notices = PACKS / "THIRD_PARTY_NOTICES.txt"
    lines = notices.read_text(encoding="utf-8").splitlines() if notices.exists() else []
    lines = [line for line in lines if not line.startswith(asset_id + " ")]
    lines.append(notice_line(asset_id, name, authors, url))
    header = [line for line in lines if not re.match(r"^(polyhaven|ambientcg):", line)]
    body = sorted(line for line in lines if re.match(r"^(polyhaven|ambientcg):", line))
    notices.write_text("\n".join(header + body) + "\n", encoding="utf-8", newline="\n")
    return release


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--source", choices=("polyhaven", "ambientcg"), required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument(
        "--kind", choices=("material", "environment", "model"), required=True
    )
    parser.add_argument("--roles", default="diffuse,normal,roughness")
    parser.add_argument("--high-roles", default="diffuse")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.id):
        parser.error("asset slug must be letters, digits, '.', '_' or '-'")
    roles = [r for r in args.roles.split(",") if r]
    high = [r for r in args.high_roles.split(",") if r]
    fetch = fetch_polyhaven if args.source == "polyhaven" else fetch_ambientcg
    with tempfile.TemporaryDirectory(prefix="archimind-cc0-") as tmp:
        name, authors, url, rows, sums = fetch(
            args.id, args.kind, roles, high, Path(tmp)
        )
    upstream = ("md5:" + ",".join(s for s in sums if s))[:128] if any(sums) else None
    release = record(
        f"{args.source}:{args.id}", args.kind, url, upstream, rows, name, authors
    )
    print(
        json.dumps(
            {
                "asset_id": release.asset_id,
                "files": len(release.files),
                "bytes": sum(f.bytes for f in release.files),
            }
        )
    )


if __name__ == "__main__":
    main()

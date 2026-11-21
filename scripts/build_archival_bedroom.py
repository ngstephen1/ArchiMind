"""Build a verified Library of Congress bedroom source packet for designer intake."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

CATALOG = "https://www.loc.gov/item/wv0365/"
BASE = "https://tile.loc.gov/storage-services/"
PATH = "pnp/habshaer/wv/wv0300/wv0365/"
SOURCES = {
    "photo-key.pdf": (
        f"{BASE}master/{PATH}data/wv0365cap.pdf",
        "8405db98fbcfdc10305b98762208c72d470c4629ba2dfe80198d4d202529adfa",
    ),
    "history.pdf": (
        f"{BASE}master/{PATH}data/wv0365data.pdf",
        "170bcd65bcdc9e1a217d5e0f780fcc41644a94fdde1e1a422c4708837e1c1ed8",
    ),
    "north-front.jpg": (
        f"{BASE}service/{PATH}photos/372906pv.jpg",
        "73c9072501a5973e1e3fda8e0b25ef2459bbce55720bf89e4da4210af55a1f23",
    ),
    "north-bedroom.jpg": (
        f"{BASE}service/{PATH}photos/372911pv.jpg",
        "09918adb1b388350c0a565dd9e6984755594bd46dabd84aabfedaad6dc457736",
    ),
}
GUIDE = Path(__file__).resolve().parents[1] / "docs/handovers/zane-street"


def build(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as scratch:
        root = Path(scratch)
        for name, (url, digest) in SOURCES.items():
            target = root / name
            subprocess.run(
                [
                    "curl",
                    "--fail",
                    "--silent",
                    "--show-error",
                    "--max-time",
                    "45",
                    "--output",
                    str(target),
                    url,
                ],
                check=True,
            )
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError(f"Source changed: {name}. Review the archive record.")
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                "4",
                "-l",
                "4",
                "-singlefile",
                "-png",
                "-scale-to",
                "1600",
                str(root / "photo-key.pdf"),
                str(root / "plan"),
            ],
            check=True,
        )
        shutil.copyfile(GUIDE / "brief.html", root / "brief.html")
        shutil.copyfile(GUIDE / "README.md", root / "README.md")
        browser = (
            os.environ.get("CHROME_BIN")
            or shutil.which("chromium")
            or shutil.which("google-chrome")
            or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
        pdf = root / "Bedroom-source-brief.pdf"
        subprocess.run(
            [
                browser,
                "--headless",
                "--disable-gpu",
                "--disable-extensions",
                f"--user-data-dir={root / 'profile'}",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf}",
                (root / "brief.html").as_uri(),
            ],
            check=True,
            timeout=60,
            capture_output=True,
        )
        if not pdf.is_file() or pdf.stat().st_size == 0:
            raise RuntimeError("Browser did not produce a source brief")
        record = {
            "archive": "HABS WV-275",
            "archive_date": "1992-04",
            "property": "182 Zane Street, Wheeling, West Virginia",
            "room": "second floor, north bedroom",
            "catalog": CATALOG,
            "plan_reference": "photo-key.pdf, page 4, triangle 6",
            "photo_reference": "WV-275-6, Norse Angus",
            "nominal_dimensions_ft": [11, 14],
            "nominal_dimensions_m": [3.3528, 4.2672],
            "profile": "angled north bay",
            "field_verified": False,
            "surveyed_polygon_m": None,
            "height_m": None,
            "client_budget": None,
            "currency": None,
            "must_keep_items": None,
            "use": "archival design research",
            "current_building_status": "unverified",
            "sources": {k: {"url": v[0], "sha256": v[1]} for k, v in SOURCES.items()},
        }
        (root / "evidence.json").write_text(json.dumps(record, indent=2) + "\n")
        bundle = root / "Zane-Street-source-pack.zip"
        with ZipFile(bundle, "w", ZIP_DEFLATED) as archive:
            for name in [*SOURCES, pdf.name, "README.md", "evidence.json"]:
                archive.write(root / name, name)
        for file in [pdf, bundle, root / "evidence.json"]:
            file.replace(output / file.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    build(parser.parse_args().output.resolve())

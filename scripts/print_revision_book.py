"""Print a Town portfolio and its two-revision design study as one landscape A3 book."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from publish_revision_study import build, digest, load_revision
from publish_studio_board import book, portfolio_cover


def print_page(chrome, source, output, profile):
    subprocess.run(
        [
            chrome,
            "--headless",
            "--disable-gpu",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-dev-shm-usage",
            "--disk-cache-size=1048576",
            f"--user-data-dir={profile}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output}",
            source.resolve().as_uri(),
        ],
        capture_output=True,
        check=True,
        timeout=180,
    )


def print_book(before, after, eyes, destination, chrome):
    board, proof = load_revision(after)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as temporary:
        work = Path(temporary)
        stage = work / "scene"
        stage.mkdir()
        # Use only the proof inventory, leaving the supplied scene and render files untouched.
        for name in [*proof["files"], "receipt.json"]:
            if Path(name).name != name:
                raise ValueError("Unexpected file path in the render receipt")
            try:
                os.link(after / name, stage / name)
            except OSError:
                shutil.copyfile(after / name, stage / name)
        comparison = work / "comparison.html"
        build(
            (before, after), eyes, comparison, preceding_pages=len(board["rooms"]) + 4
        )
        book(stage, eyes[1], comparison_pages=2)
        portfolio = work / "portfolio.pdf"
        study = work / "comparison.pdf"
        print_page(chrome, stage / "index.html", portfolio, work / "chrome")
        print_page(chrome, comparison, study, work / "chrome")
        final = work / "final.pdf"
        subprocess.run(["pdfunite", str(portfolio), str(study), str(final)], check=True)
        text = subprocess.check_output(
            ["pdftotext", "-layout", str(final), "-"], text=True
        )
        pages = [page.strip() for page in text.split("\f") if page.strip()]
        if len(pages) != len(board["rooms"]) + 6 or any(
            board["project"] not in p for p in pages
        ):
            raise ValueError(
                "Unexpected pagination or project in the printed comparison."
            )
        if any(board["home_id"][:12] not in p for p in pages):
            raise ValueError("Printed page lacks the expected home identity.")
        if any(
            not page.endswith(f"{number} / {len(pages)}")
            for number, page in enumerate(pages, start=1)
        ):
            raise ValueError(
                "Printed book folios must run continuously through the comparison."
            )
        evidence = json.loads(comparison.with_suffix(".json").read_bytes())
        evidence.update(
            {
                "book_sha256": digest(final),
                "page_count": len(pages),
                "portfolio_sha256": digest(portfolio),
                "revision": board["revision"],
                "home_id": board["home_id"],
                "source_receipt_sha256": digest(after / "receipt.json"),
            }
        )
        hero = stage / f"presentation-{portfolio_cover(board)}.png"
        if hero.is_file():
            evidence["hero_sha256"] = digest(hero)
        receipt = work / "book.json"
        receipt.write_text(json.dumps(evidence, indent=2) + "\n")
        final.replace(destination)
        receipt.replace(destination.with_suffix(".json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("output_pdf", type=Path)
    parser.add_argument("--eye-views", nargs=2, type=Path)
    parser.add_argument(
        "--chrome",
        default=(
            shutil.which("google-chrome")
            or shutil.which("chromium")
            or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ),
    )
    args = parser.parse_args()
    print_book(
        args.before,
        args.after,
        args.eye_views or (None, None),
        args.output_pdf,
        args.chrome,
    )

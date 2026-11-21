"""Build a portable, printable client book next to a verified studio render receipt."""

import argparse
import hashlib
import html
import json
import re
from pathlib import Path


def esc(value):
    return html.escape(str(value), quote=True)


def drawing(home):
    w, d = home["width"], home["depth"]
    shapes = [
        f'<svg viewBox="-0.3 -0.3 {w + 0.6} {d + 0.6}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Dimensioned home plan">'
    ]

    def rect(x, y, w, h, color):
        shapes.append(
            f'<rect x="{x}" y="{d - y - h}" width="{w}" height="{h}" fill="{color}" stroke="#686558" stroke-width=".026"/>'
        )

    rect(0, 0, w, d, "#d7c09e")
    for part in home["rooms"]:
        x, y = part["origin"]
        room = part["room"]
        rw, rd = room["width_m"], room["depth_m"]
        rect(x, y, rw, rd, "#faf7ee")
        for f in part["furniture"]:
            rect(x + f["x_m"], y + f["y_m"], f["width_m"], f["depth_m"], "#c0c4ae")
        for o in room["doors"] + room["windows"]:
            off = o["offset_m"]
            length = o["width_m"]
            wall = o["wall"]
            color = "#cb8e3c" if "sill_height_m" not in o else "#568993"
            if wall in ("west", "east"):
                rect(
                    x + (rw if wall == "east" else 0) - 0.035,
                    y + off,
                    0.07,
                    length,
                    color,
                )
            else:
                rect(
                    x + off,
                    y + (rd if wall == "north" else 0) - 0.035,
                    length,
                    0.07,
                    color,
                )
        shapes.append(
            f'<text x="{x + 0.15}" y="{d - y - rd + 0.44}" font-size=".28">{esc(room["name"])} · {rw:.2f} × {rd:.2f} m</text>'
        )
    return "".join(shapes) + "</svg>"


def elevations(part):
    r = part["room"]
    result = []
    for wall in ("north", "east"):
        east = wall == "east"
        w = r["depth_m" if east else "width_m"]
        h = r["ceiling_height_m"]
        svg = [
            f'<svg viewBox="-.15 -.15 {w + 0.3} {h + 0.68}" role="img" aria-label="{wall} elevation">'
        ]

        def rect(x, z, width, height, color):
            svg.append(
                f'<rect x="{x}" y="{h - z - height}" width="{width}" height="{height}" fill="{color}" stroke="#53554d" stroke-width=".015"/>'
            )

        rect(0, 0, w, h, "#e6dfd3")
        for o in r["windows"] + r["doors"]:
            if o["wall"] == wall:
                rect(
                    w - o["offset_m"] - o["width_m"] if east else o["offset_m"],
                    o.get("sill_height_m", 0),
                    o["width_m"],
                    o["height_m"],
                    "#c3d7d3",
                )
        for f in sorted(
            part["furniture"], key=lambda f: f["x_m" if east else "y_m"], reverse=True
        ):
            rect(
                w - f["y_m"] - f["depth_m"] if east else f["x_m"],
                0,
                f["depth_m"] if east else f["width_m"],
                f["height_m"],
                "#b8aa94",
            )
        svg.append(
            f'<text x="0" y="{h + 0.32}" font-size=".20">{wall.title()} · {w:.2f} m × {h:.2f} m</text></svg>'
        )
        result.append("".join(svg))
    return "".join(result)


def book(directory, eye_views=None):
    receipt = json.loads((directory / "receipt.json").read_bytes())
    for name, expected in receipt["files"].items():
        if (
            Path(name).name != name
            or hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected
        ):
            raise ValueError(f"Render member failed integrity check: {name}")
    board = json.loads((directory / "manifest.json").read_bytes())
    if receipt["manifest_sha256"] != receipt["files"]["manifest.json"] or (
        board["home_id"],
        board["revision"],
    ) != (receipt["home_id"], receipt["revision"]):
        raise ValueError("Manifest identity mismatch")

    replacements = {}
    if eye_views:
        evidence = json.loads((eye_views / "eye-view-receipt.json").read_bytes())
        if (
            evidence["manifest_sha256"] != receipt["manifest_sha256"]
            or evidence["proof_blend_sha256"] != receipt["files"]["home.blend"]
        ):
            raise ValueError("Eye views identify a different source proof")
        for shot in evidence["shots"]:
            name = shot["file"]
            if (
                Path(name).name != name
                or name not in receipt["files"]
                or not name.endswith(".png")
            ):
                raise ValueError("Unexpected eye-view filename")
            data = (eye_views / name).read_bytes()
            if hashlib.sha256(data).hexdigest() != shot["sha256"]:
                raise ValueError(
                    "Eye-view PNG differs from its signed-off render receipt"
                )
            replacements[name] = "presentation-" + name
            (directory / replacements[name]).write_bytes(data)
    style = (
        json.loads((directory / "saved-style-receipt.json").read_bytes())
        if "saved-style-receipt.json" in receipt["files"]
        else None
    )

    def img(name):
        filename = name + ".png"
        if filename not in receipt["files"]:
            raise ValueError("Missing render: " + filename)
        return f'<img src="{esc(replacements.get(filename, filename))}" alt="{esc(name.replace("-", " "))}">'

    pages = []
    featured = next(
        (r for r in board["rooms"] if r["room"]["id"] == "salon"), board["rooms"][0]
    )
    hero = featured["room"]["id"] + "-" + featured["cameras"][0]["id"]
    palette = (
        (style["style_pack"]["id"] + " style pack")
        if style
        else (board["palette"] + " palette")
    )
    pages.append(
        "<h1>The Studio House</h1>"
        + img(hero)
        + f"<p>Whole-home interior study · {board['width']} × {board['depth']} m · {esc(palette.title())}</p>"
    )
    finish_rows = "".join(
        f'<p><i style="background:{esc(col)}"></i>{esc(label.title())}</p>'
        for label, col in board["finishes"].items()
    )
    if style:
        finish_rows = ""
        surfaces = (
            Path(__file__).resolve().parents[1]
            / "src/archimind/_viewer_assets/packs/assets"
        )
        for role, row in style["surfaces"].items():
            digest = row["files"]["diffuse"]
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("Invalid surface swatch digest")
            asset = next(
                (
                    f
                    for f in surfaces.glob(digest + ".*")
                    if f.suffix in {".webp", ".jpg", ".png"}
                ),
                None,
            )
            if not asset or hashlib.sha256(asset.read_bytes()).hexdigest() != digest:
                raise ValueError("Released surface swatch unavailable")
            filename = "swatch-" + asset.name
            (directory / filename).write_bytes(asset.read_bytes())
            label = row["asset_id"].split(":")[-1].replace("_", " ").title()
            finish_rows += f'<p><img class="swatch" src="{esc(filename)}" alt=""><b>{esc(role.title())}</b> · {esc(label)}</p>'
        finish_rows += "<p>Furniture and dressing follow the saved high-quality Town style. The furniture schedule gives reserved dimensions and floor positions.</p>"
    credits = '<p><small>Belaya model © Amazon.com. <a href="https://amazon-berkeley-objects.s3.amazonaws.com/index.html">Amazon Berkeley Objects</a> · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Scene assembly and rendering by ArchiMind. <a href="https://polyhaven.com/license">Poly Haven</a> surfaces and lighting · CC0. Full notices accompany the source book.</small></p>'
    pages.append(
        "<h2>Plan &amp; finishes</h2><div class='grid'><div>"
        + drawing(board)
        + "</div><div><p>North is up. Blue marks windows and ochre marks doors. Dimensions are in metres.</p>"
        + finish_rows
        + "</div></div>"
        + credits
    )
    pages.append(
        '<h2>From drawing to daylight</h2><div class="compare">'
        + img(hero)
        + '<div class="ink">'
        + img(hero + "-drawing")
        + "</div></div><label>Drawing coverage <input type=\"range\" value=\"50\" oninput=\"document.querySelector('.ink').style.clipPath='inset(0 '+(100-this.value)+'% 0 0)'\"></label>"
    )
    pages.append("<h2>Evening lighting study</h2>" + img(hero + "-evening"))
    for part in board["rooms"]:
        r = part["room"]
        views = part["cameras"]
        rows = "".join(
            f"<tr><td>{esc(f['name'])}</td><td>{f['width_m']:.2f} × {f['depth_m']:.2f} × {f['height_m']:.2f}</td><td>{f['x_m']:.2f}, {f['y_m']:.2f}</td></tr>"
            for f in part["furniture"]
        )
        pages.append(
            f'<h2>{esc(r["name"])}</h2><div class="grid">'
            + "".join(
                "<figure>"
                + img(r["id"] + "-" + v["id"])
                + "<figcaption>"
                + esc(v.get("reason") or v["label"])
                + (
                    " · 1080p, comparison camera"
                    if r["id"] == "bedroom" and f"bedroom-{v['id']}.png" in replacements
                    else ""
                )
                + "</figcaption></figure>"
                for v in views[:2]
            )
            + '</div><div class="grid">'
            + elevations(part)
            + "</div><table><tr><th>Furniture</th><th>Reserved W × D × H (m)</th><th>Room X, Y (m)</th></tr>"
            + rows
            + "</table>"
        )
    css = """*{box-sizing:border-box}body{margin:auto;max-width:1120px;color:#24382f;background:#eeeae1;font:16px/1.4 system-ui}section{padding:3.5%;background:#faf8f2;margin:15px 0}h1,h2{font:normal 2.8em/1.1 Georgia;margin:.25em 0 .5em}img,svg{width:100%;display:block}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}figcaption,footer{font-size:.85em}footer{margin-top:1em;border-top:1px solid #b8ac97;padding-top:.6em}table{border-collapse:collapse;width:100%;margin-top:1em}td,th{text-align:left;border-bottom:1px solid #ccc;padding:.2em}i{width:2em;height:1em;display:inline-block;margin-right:.6em}.compare{position:relative}.ink{position:absolute;inset:0;clip-path:inset(0 50% 0 0)}@media(max-width:650px){.grid{grid-template-columns:1fr}}@page{size:A3 landscape;margin:12mm}@media print{body{max-width:none;font-size:11pt;background:white}section{margin:0;padding:0;break-after:page}section:last-child{break-after:auto}section>img,.compare{width:82%}.grid{grid-template-columns:1fr 1fr}.grid svg{max-height:32vh}label{display:none}*{print-color-adjust:exact}}"""
    css += ".swatch{width:6.2em;height:2em;object-fit:cover;display:inline-block;vertical-align:middle;margin-right:.75em}"
    if "camera-studies.json" in receipt["files"]:
        studies = json.loads((directory / "camera-studies.json").read_text())
        panels = "".join(
            "<figure>"
            + img(s["view"])
            + f"<figcaption>{esc(s['view'])} · {esc(s['review'])}</figcaption></figure>"
            for s in studies
        )
        if "bedroom-bedside-before.png" in receipt["files"]:
            panels += (
                "<h2>Coverlet study</h2>"
                + img("bedroom-bedside-before")
                + img("bedroom-bedside")
            )
        (directory / "studies.html").write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Camera studies</title><style>'
            + css
            + '</style><section><h1>Camera studies</h1><p>Six candidates per benchmark room. Labels describe the contrast measured in each gray render.</p><div class="grid">'
            + panels
            + '</div><a href="index.html">Return to client book</a></section></html>'
        )
        pages[0] += (
            '<a href="studies.html" class="online">Open the camera and coverlet studies</a>'
        )
        css += "@media print{.online{display:none}}"
    footer = f"Revision {board['revision']} · {esc(board['home_id'][:12])} · Interior design presentation"
    (directory / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>The Studio House</title><style>'
        + css
        + "</style>"
        + "".join(
            "<section>"
            + p
            + "<footer>"
            + footer
            + f" · {i + 1} / {len(pages)}</footer></section>"
            for i, p in enumerate(pages)
        )
        + "</html>"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--eye-views", type=Path)
    args = parser.parse_args()
    book(args.directory, args.eye_views)

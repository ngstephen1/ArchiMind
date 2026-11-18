"""Concurrent specialist tasks. Each published event corresponds to executed work."""

import copy
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from archimind.assets import load_catalog
from archimind.datasets.search import (
    ReferenceQuery,
    load_reference_pack,
    search_references,
)

from . import design_review
from .design import PROGRAM, digest, generate, validate_home

ROLES = {
    "A": "Brief and constraints",
    "B": "Furniture and references",
    "C": "Layout planner",
    "D": "Spatial critic",
    "E": "Style and presentation",
}
SWATCH = {"oak": "#e5d6bc", "sage": "#bac6ad", "terracotta": "#d8ab91"}


def search(message):
    words = set(re.findall(r"[a-z0-9]+", message.lower()))
    products = []
    for r in load_catalog().records:
        terms = [r.category, *r.search.aliases, *r.search.usage_tags]
        matched = [t for t in terms if set(t.lower().split()) <= words]
        if matched:
            products.append(
                {
                    "product": r.search.reviewed_name,
                    "matched": matched,
                    "source": r.source.metadata_url,
                }
            )
    root = os.getenv("ARCHIMIND_DATASET_REFERENCE_ROOT")
    refs = {"status": "disabled"}
    if root and os.getenv("ARCHIMIND_ENABLE_DATASET_REFERENCES") == "1":
        audience = (
            os.getenv("ARCHIMIND_DATASET_REFERENCE_AUDIENCE", "public")
            if os.getenv("TOWN_MODE") == "local"
            else "public"
        )
        pack = load_reference_pack(Path(root), audience=audience)
        query = ReferenceQuery(
            keywords=tuple(
                sorted(
                    w
                    for w in words
                    if w in {"desk", "bed", "chair", "bedroom", "window", "wardrobe"}
                )
            ),
            max_scene_hits=3,
            max_asset_hits=0,
        )
        refs = search_references(query, pack=pack).model_dump(mode="json")
    return {"catalog_matches": products, "references": refs}


def coordinate(req, previous, interpret, emit):
    def task(agent, label, operation):
        emit(agent, "running", label, {})
        try:
            value = operation()
            artifact = (
                value.model_dump(mode="json") if hasattr(value, "model_dump") else value
            )
            state = (
                "failed"
                if label.startswith("Codex CLI") and artifact.get("status") != "success"
                else "completed"
            )
            emit(agent, state, label, artifact)
            return value
        except Exception:
            emit(agent, "failed", label, {})
            raise

    def baseline():
        if previous:
            validate_home(previous)
        return {
            "validated_revision": req.base if previous else None,
            "minimum_clearance_m": 0.6,
        }

    with ThreadPoolExecutor(max_workers=5, thread_name_prefix="town-agent") as pool:
        tasks = [
            (
                "A",
                "OpenAI · Interpret brief" if req.live else "Interpret requirements",
                lambda: interpret(req, previous),
            ),
            ("B", "Find eligible evidence", lambda: search(req.message)),
            (
                "C",
                "Inspect lot and partitions",
                lambda: {
                    "width_m": req.brief.width,
                    "depth_m": req.brief.depth,
                    "program": PROGRAM + (["salon"] if req.brief.formal_salon else []),
                    "existing_rooms": len(previous["rooms"]) if previous else 0,
                },
            ),
            ("D", "Check starting geometry", baseline),
            (
                "E",
                "OpenAI · Generate styling direction"
                if req.agent_team
                else "Inspect finish options",
                lambda: (
                    design_review.direction(req)
                    if req.agent_team
                    else {
                        "starting_palette": previous["palette"] if previous else None,
                        "options": SWATCH,
                    }
                ),
            ),
        ]
        futures = [pool.submit(task, *t) for t in tasks]
        brief = futures[0].result()
        for future in futures[1:]:
            future.result()
        emit(
            "E",
            "completed",
            "Resolved finish",
            {"palette": brief.palette, "swatch": SWATCH[brief.palette]},
        )
        checks = []

        def progress(kind, artifact):
            emit("C", "running", kind, artifact)
            if kind == "Furnished candidate":

                def critique():
                    validate_home(artifact)
                    return {"candidate": artifact["id"], **artifact["evidence"]}

                checks.append(
                    pool.submit(
                        task, "D", "Validate candidate " + artifact["id"][:8], critique
                    )
                )

        finish_only = (
            previous
            and re.fullmatch(
                r"(?:use )?(oak|sage|terracotta)(?: finishes)?[.!]?",
                req.message.strip().lower(),
            )
            and (brief.width, brief.depth) == (previous["width"], previous["depth"])
            and brief.priority == "balanced"
            and (
                not brief.formal_salon
                or any(p["design"]["room"]["id"] == "salon" for p in previous["rooms"])
            )
        )
        if finish_only:
            home = copy.deepcopy(previous)
            home["palette"] = brief.palette
            home.pop("id")
            home["id"] = digest(home)
            emit("C", "skipped", "Finish edit preserves geometry", {})
            homes = [home]
        else:
            homes = generate(brief, previous, on_progress=progress)
            emit("C", "completed", "Furnishing complete", {"candidates": len(homes)})
        for h in homes:
            rooms = {p["design"]["room"]["id"]: p["design"]["room"] for p in h["rooms"]}
            if "salon" not in rooms:
                continue
            window = rooms["salon"]["windows"][0]
            emit(
                "E",
                "completed",
                "Compose client views",
                {
                    "home_id": h["id"],
                    "palette": h["palette"],
                    "salon_subjects": ["salon-suite", "salon-dining"],
                    "daylight_opening": window["id"],
                    "daylight_wall": window["wall"],
                    "lighting_studies": ["daylight", "pendant evening"],
                    "camera_proofs": "Available after the applied revision is rendered in Cycles.",
                },
            )
        for check in checks:
            check.result()
        if req.agent_team and homes:
            style = futures[4].result()
            visual = pool.submit(
                task,
                "D",
                "OpenAI · Review plan images",
                lambda: design_review.review_candidates(req, homes, style),
            )
            if (
                os.getenv("TOWN_MODE") == "local"
                and os.getenv("ARCHIMIND_ENABLE_CODEX_ADVISOR") == "1"
            ):
                task(
                    "E",
                    "Codex CLI · Review bedroom placement",
                    lambda: design_review.codex_review(req, homes[0]),
                )
            else:
                emit("E", "skipped", "Codex CLI · Local advisor unavailable", {})
            visual.result()
        emit(
            "E",
            "completed",
            "Prepare presentation",
            {"candidates": [h["id"] for h in homes], "palette": brief.palette},
        )
        return homes

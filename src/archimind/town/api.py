"""Same-origin local demo or authenticated hosted API."""

import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import decision_review, designer_chair, render_queue
from . import service as db


def identity(request):
    origin = request.headers.get("origin")
    if os.getenv("TOWN_MODE") == "local":
        if request.url.hostname not in {"localhost", "127.0.0.1"} or (
            origin and origin != str(request.base_url).rstrip("/")
        ):
            raise db.Problem("Local access only.", 403)
        return "local-designer"
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise db.Problem("Sign in to design.", 401)
    req = urllib.request.Request(
        os.environ["SUPABASE_URL"].rstrip("/") + "/auth/v1/user",
        headers={"Authorization": auth, "apikey": os.environ["SUPABASE_ANON_KEY"]},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.load(response)["id"]
    except urllib.error.HTTPError:
        raise db.Problem("Sign in again.", 401) from None
    except OSError:
        raise db.Problem("Sign-in service unavailable.", 503) from None


def handle(request, data):
    owner = identity(request)
    path = request.path_params.get("path", "").split("/")
    if path == ["designer-chairs"] and request.method == "GET":
        return {"chairs": designer_chair.chair_options()}
    if path == ["bedroom-collection"] and request.method == "GET":
        return {"concepts": designer_chair.chair_options(collection=True)}
    if path == ["projects"] and request.method == "POST":
        return db.create(owner)
    if path == ["jobs"] and request.method == "POST":
        return db.enqueue(owner, db.Request.model_validate(data))
    if len(path) == 3 and path[0] == "projects" and path[2] == "decision-review":
        if request.method == "POST":
            return decision_review.check(
                owner, path[1], decision_review.ReviewRequest.model_validate(data)
            )
        with db.transaction() as q:
            db.project(q, owner, path[1])
        return {
            kind: decision_review.settings(kind)[0] for kind in decision_review.RUBRICS
        }
    if len(path) >= 3 and path[0] == "projects" and path[2] == "render":
        blender = render_queue.configuration()
        if blender is None:
            raise db.Problem("Configure a local Blender renderer.", 503)
        p = path[1]
        n = int(request.query_params.get("revision", "0"))
        if n <= 0:
            raise db.Problem("Select an applied revision.")
        with db.transaction() as q:
            db.project(q, owner, p)
            home = db.revision(q, p, n)
        snapshot = {"project": p, "revision": n, "home": home}
        if len(path) == 3 and request.method == "GET":
            return render_queue.describe(snapshot, blender)
        if len(path) == 3 and request.method == "POST":
            return render_queue.request(snapshot, blender, data.get("stage"))
        if len(path) == 5 and request.method == "GET":
            asset = render_queue.asset(snapshot, blender, path[3], path[4])
            return FileResponse(asset, filename=asset.name)
        raise db.Problem("Render action unavailable.", 404)
    with db.transaction() as q:
        if (
            len(path) == 4
            and path[0] == "projects"
            and path[2] in {"designer-chair", "bedroom-collection", "chair-pullout"}
            and path[3] in {"preview", "apply"}
            and request.method == "POST"
        ):
            if path[2] == "chair-pullout":
                return designer_chair.chair_pullout(
                    q, owner, path[1], data, apply=path[3] == "apply"
                )
            return designer_chair.chair_change(
                q,
                owner,
                path[1],
                data,
                apply=path[3] == "apply",
                collection=path[2] == "bedroom-collection",
            )
        if len(path) == 2 and path[0] == "projects" and request.method == "GET":
            p = path[1]
            head = db.project(q, owner, p)
            n = int(request.query_params.get("revision", head))
            return {
                "project": p,
                "revision": n,
                "head": head,
                "history": [
                    {
                        "base": base,
                        "status": status,
                        "message": json.loads(raw).get("message", ""),
                    }
                    for base, status, raw in q(
                        "SELECT base,status,request FROM jobs WHERE project=? AND owner=? AND base<=? ORDER BY created DESC,id DESC LIMIT 20",
                        (p, owner, n),
                    )
                ],
                "latest_job": next(
                    (
                        r[0]
                        for r in q(
                            "SELECT id FROM jobs WHERE project=? AND owner=? AND base=? ORDER BY created DESC,id DESC LIMIT 1",
                            (p, owner, n),
                        )
                    ),
                    None,
                ),
                "home": db.revision(q, p, n) if n else None,
            }
        if (
            len(path) == 3
            and path[0] == "projects"
            and path[2] == "undo"
            and request.method == "POST"
        ):
            p = path[1]
            base = data["base"]
            db.project(q, owner, p)
            if base < 2:
                raise db.Problem("No earlier applied home.")
            return db.apply(q, owner, p, base, db.revision(q, p, base - 1))
        if path[0] == "jobs" and len(path) in (2, 3):
            db.expire_jobs(q, int(time.time()))
            row = q(
                "SELECT project,base,status,result FROM jobs WHERE id=? AND owner=?",
                (path[1], owner),
            ).fetchone()
            if not row:
                raise db.Problem("Job unavailable.", 404)
            p, base, status, result = row
            result = json.loads(result) if result else None
            if path[-1] == "events" and request.method == "GET":
                after = int(request.query_params.get("after", "0"))
                events = [
                    json.loads(r[0])
                    for r in q(
                        "SELECT payload FROM job_events WHERE job=? AND seq>? ORDER BY seq",
                        (path[1], after),
                    )
                ]
                message = json.loads(
                    q("SELECT request FROM jobs WHERE id=?", (path[1],)).fetchone()[0]
                )["message"]
                return {
                    "events": events,
                    "status": status,
                    "message": message,
                    "base": base,
                }
            if len(path) == 2 and request.method == "GET":
                return {"status": status, "result": result}
            if request.method == "POST" and path[-1] == "cancel":
                q(
                    "UPDATE jobs SET status='cancelled',result=NULL WHERE id=? AND status IN ('queued','running','ready')",
                    (path[1],),
                )
                return {"cancelled": True}
            if request.method == "POST" and path[-1] == "apply" and status == "ready":
                index = data.get("index")
                if type(index) is not int or not 0 <= index < len(result):
                    raise db.Problem("Choose a valid layout index.")
                return db.apply(q, owner, p, base, result[index])
    raise db.Problem("Unavailable action.", 404)


async def api(request: Request):
    try:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 12000:
                raise db.Problem("Request too large.", 413)
        data = json.loads(body) if body else {}
        if not isinstance(data, dict):
            raise ValueError
        result = await asyncio.to_thread(handle, request, data)
        return result if isinstance(result, Response) else JSONResponse(result)
    except db.Problem as exc:
        return JSONResponse({"error": str(exc)}, status_code=exc.status)
    except (KeyError, ValueError, ValidationError, TypeError):
        return JSONResponse({"error": "Invalid design request."}, status_code=400)


async def health(request):
    return JSONResponse({"status": "ok"})


routes = [
    Route("/health", health),
    Route("/api/{path:path}", api, methods=["GET", "POST"]),
]
if os.getenv("TOWN_STATIC"):
    routes.append(
        Mount("/", StaticFiles(directory=Path(os.environ["TOWN_STATIC"]), html=True))
    )
app = Starlette(routes=routes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("TOWN_ORIGIN", "http://localhost:8790")],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

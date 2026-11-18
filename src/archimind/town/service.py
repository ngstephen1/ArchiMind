"""Private revision store and bounded design jobs. SQLite for loopback, Postgres for hosting."""

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from archimind.studio import provider
from archimind.town.agents import coordinate
from archimind.town.design import Brief, Kind, interpret_offline

SCHEMA = [
    "CREATE TABLE IF NOT EXISTS job_events (job TEXT NOT NULL, seq INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(job,seq))",
    "CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, owner TEXT NOT NULL, revision INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS revisions (project TEXT NOT NULL, revision INTEGER NOT NULL, home TEXT NOT NULL, PRIMARY KEY(project,revision))",
    "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, owner TEXT NOT NULL, project TEXT NOT NULL, base INTEGER NOT NULL, created BIGINT NOT NULL, started BIGINT, status TEXT NOT NULL, request TEXT NOT NULL, result TEXT, UNIQUE(owner,id))",
]


class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


@contextmanager
def transaction():
    url = os.getenv("DATABASE_URL")
    if url:
        import psycopg

        c = psycopg.connect(url, connect_timeout=6)
    else:
        if os.getenv("TOWN_MODE") != "local":
            raise RuntimeError("Hosted mode requires Postgres.")
        c = sqlite3.connect(os.environ["TOWN_DB"], timeout=8)
    try:
        if url:
            c.execute("SELECT pg_advisory_xact_lock(47388512)")
            c.execute("SET LOCAL search_path TO archimind_town")
        else:
            c.execute("BEGIN IMMEDIATE")

        def run(sql, args=()):
            return c.execute(sql.replace("?", "%s") if url else sql, args)

        yield run
        c.commit()
    except BaseException:
        c.rollback()
        raise
    finally:
        c.close()


def initialize():
    with transaction() as q:
        if os.getenv("DATABASE_URL"):
            q("CREATE SCHEMA IF NOT EXISTS archimind_town")
            q("REVOKE ALL ON SCHEMA archimind_town FROM PUBLIC, anon, authenticated")
        for statement in SCHEMA:
            q(statement)
        if os.getenv("DATABASE_URL"):
            # Only the server DB role accesses these tables. Public Supabase clients
            # have neither table grants nor row policies granting direct access.
            for table in ["projects", "revisions", "jobs", "job_events"]:
                q(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
                q(f"REVOKE ALL ON {table} FROM PUBLIC, anon, authenticated")


def project(q, owner, p):
    row = q(
        "SELECT revision FROM projects WHERE id=? AND owner=?", (p, owner)
    ).fetchone()
    if not row:
        raise Problem("Project unavailable.", 404)
    return row[0]


def revision(q, p, n):
    row = q(
        "SELECT home FROM revisions WHERE project=? AND revision=?", (p, n)
    ).fetchone()
    if not row:
        raise Problem("Revision unavailable.", 404)
    return json.loads(row[0])


def create(owner):
    p = str(uuid.uuid4())
    with transaction() as q:
        q("INSERT INTO projects VALUES(?,?,0)", (p, owner))
    return {"project": p, "revision": 0}


def apply(q, owner, p, base, home):
    if project(q, owner, p) != base:
        raise Problem("A newer revision exists. Reopen the current design.", 409)
    q("INSERT INTO revisions VALUES(?,?,?)", (p, base + 1, json.dumps(home)))
    q("UPDATE projects SET revision=? WHERE id=?", (base + 1, p))
    return {"project": p, "revision": base + 1, "home": home}


class Request(BaseModel):
    project: uuid.UUID
    base: int = Field(ge=0)
    id: uuid.UUID
    brief: Brief
    message: str = Field(max_length=1800, default="")
    live: bool = False


def enqueue(owner, req):
    p, j = str(req.project), str(req.id)
    with transaction() as q:
        head = project(q, owner, p)
        raw = req.model_dump_json()
        existing = q(
            "SELECT request FROM jobs WHERE id=? AND owner=?", (j, owner)
        ).fetchone()
        if existing:
            if existing[0] != raw:
                raise Problem("Request ID already used.", 409)
            return {"job": j}
        if head != req.base:
            raise Problem("Project changed. Reload this revision.", 409)
        now = int(time.time())
        expire_jobs(q, now)
        if req.live:
            if not req.message.strip():
                raise Problem("Enter a design request.")
            if os.getenv("ARCHIMIND_ENABLE_OPENAI_STUDIO") != "1":
                raise Problem("Live interpretation is disabled on this server.")
        if q(
            "SELECT 1 FROM jobs WHERE owner=? AND status IN ('queued','running')",
            (owner,),
        ).fetchone():
            raise Problem("One design is already in progress.", 409)
        day = now - now % 86400
        if (
            q(
                "SELECT count(*) FROM jobs WHERE owner=? AND created>=?", (owner, day)
            ).fetchone()[0]
            >= 3
        ):
            raise Problem("Daily limit of three design jobs reached.", 429)
        # Each live job makes at most one bounded model call. Reserve quota before queueing.
        if req.live:
            used = q(
                "SELECT count(*) FROM jobs WHERE created>=? AND request LIKE ?",
                (day, '%"live":true%'),
            ).fetchone()[0]
            cap = int(os.getenv("TOWN_DAILY_MODEL_CALLS", "0"))
            reserve = int(os.getenv("TOWN_CALL_RESERVE_MICROUSD", "0"))
            budget = int(os.getenv("TOWN_DAILY_MICROUSD", "0"))
            if used >= cap or reserve <= 0 or (used + 1) * reserve > budget:
                raise Problem("The operator's daily AI allowance is exhausted.", 429)
        q(
            "INSERT INTO jobs(id,owner,project,base,created,status,request) VALUES(?,?,?,?,?,'queued',?)",
            (j, owner, p, req.base, now, raw),
        )
    return {"job": j}


class Interpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    priority: Literal[
        "balanced", "quiet bedroom", "bright study", "quiet bedroom and bright study"
    ]
    palette: Literal["oak", "sage", "terracotta"]
    formal_salon: bool = False
    lock_rooms: list[Kind] = Field(max_length=6)
    clarification: str = Field(max_length=500)
    unsupported: list[str] = Field(max_length=8)
    shift_bedroom_chair: bool = False
    closer_study_desk: bool = False
    lock_furniture: list[str] = Field(max_length=12)


def expire_jobs(q, now):
    q(
        "UPDATE jobs SET status='failed',result=? WHERE (status='running' AND started<?) OR (status='queued' AND created<?)",
        (json.dumps("Job expired. Previous home preserved."), now - 240, now - 600),
    )


def interpret(req, previous):
    brief = req.brief
    if req.live:
        cfg = provider.configuration(True)
        facts = {
            "controls": brief.model_dump(),
            "previous_rooms": [
                {
                    "room": r["design"]["room"]["id"],
                    "furniture": [f["id"] for f in r["design"]["furniture"]],
                }
                for r in previous["rooms"]
            ]
            if previous
            else [],
            "request": req.message,
        }
        parsed = provider.request(
            Interpretation,
            "Interpret this whole-home revision. Measured lot dimensions and checked locks are authoritative. Start from the controls for palette and priority unless text explicitly requests a different supported option. Supported: single storey, five base rooms, optional additional formal salon with a dining group for entertaining, global palette, quiet bedroom and bright study priorities, repositioning the bedroom desk chair, moving the existing study desk closer to its window, locks, seed. List unsupported mandatory requests; ask for clarification if ambiguous. For furniture locks, return the IDs (the whole containing room will be preserved). Never silently drop requirements. "
            + json.dumps(facts),
            config=cfg,
            deadline=time.monotonic() + 30,
        )
        if parsed.unsupported or parsed.clarification:
            raise Problem(
                parsed.clarification
                or "Unsupported requirements: " + ", ".join(parsed.unsupported)
            )
        locks = set(brief.locks) | set(parsed.lock_rooms)
        for item in parsed.lock_furniture:
            match = [
                r["design"]["room"]["id"]
                for r in (previous or {}).get("rooms", [])
                if any(f["id"] == item for f in r["design"]["furniture"])
            ]
            if len(match) != 1:
                raise Problem("Clarify which room contains the furniture to lock.")
            locks.update(match)
        brief = brief.model_copy(
            update={
                "priority": parsed.priority,
                "formal_salon": parsed.formal_salon or brief.formal_salon,
                "palette": parsed.palette,
                "locks": sorted(locks),
                "shift_bedroom_chair": parsed.shift_bedroom_chair
                or brief.shift_bedroom_chair,
                "closer_study_desk": parsed.closer_study_desk
                or brief.closer_study_desk,
            }
        )
    else:
        brief = interpret_offline(brief, req.message)
    return brief


def work_once():
    with transaction() as q:
        expire_jobs(q, int(time.time()))
        row = q(
            "SELECT id,project,base,request FROM jobs WHERE status='queued' ORDER BY created LIMIT 1"
        ).fetchone()
        if not row:
            return False
        j, p, base, raw = row
        q(
            "UPDATE jobs SET status='running',started=? WHERE id=?",
            (int(time.time()), j),
        )
        previous = revision(q, p, base) if base else None
    try:
        req = Request.model_validate_json(raw)
        deadline = time.monotonic() + 180

        def emit(agent, state, task, artifact):
            if time.monotonic() > deadline:
                raise Problem("Design deadline exceeded.")
            with transaction() as q:
                if (
                    q("SELECT status FROM jobs WHERE id=?", (j,)).fetchone()[0]
                    != "running"
                ):
                    raise Problem("Run stopped.")
                seq = q(
                    "SELECT COALESCE(MAX(seq),0)+1 FROM job_events WHERE job=?", (j,)
                ).fetchone()[0]
                event = dict(
                    seq=seq,
                    run=j,
                    base=base,
                    time=time.time(),
                    agent=agent,
                    state=state,
                    task=task,
                    artifact=artifact,
                )
                q("INSERT INTO job_events VALUES(?,?,?)", (j, seq, json.dumps(event)))

        result = coordinate(req, previous, interpret, emit)
        status = "ready"
    except (ValueError, Problem, provider.StudioError) as exc:
        result = str(exc)[:600]
        status = "failed"
    except Exception:
        result = "Design service unavailable. Your applied home is preserved."
        status = "failed"
    with transaction() as q:
        q(
            "UPDATE jobs SET status=?,result=? WHERE id=? AND status='running'",
            (status, json.dumps(result), j),
        )
    return True

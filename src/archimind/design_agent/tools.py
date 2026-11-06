"""Deterministic tools for the agent. None of them accepts furniture coordinates."""

from dataclasses import dataclass, field

import openai
from pydantic import BaseModel, ConfigDict, Field

from archimind.agents.requirements_conversion import prepare_requirements
from archimind.agents.requirements_schemas import (
    RequirementsResult,
    RequirementsSchema,
)
from archimind.design_agent.gate import (
    GateResult,
    PlacementGoal,
    goal_met,
    release_gate,
    window_blockers,
)
from archimind.geometry import (
    AccessibilityConfig,
    LayoutCandidate,
    generate_layout_candidates,
)
from archimind.models import RoomDesign

SEEDS_PER_CALL = 3  # The generator returns at most two layouts per seed.
CANDIDATES_PER_SEED = 2
ATTEMPTS_PER_SEED = 500
MAX_POOL = 24
LAYOUTS_SHOWN = 5
MAX_SUMMARY_CHARS = 1000
WALL_TOUCH_M = 0.05
QUOTE_MARKS = "\"'“”‘’`"


class GenerateArgs(BaseModel):
    """Generate more validated layouts for the current requirements."""

    model_config = ConfigDict(extra="forbid")

    seed: int | None = Field(description="Search seed, or null for the next one.")


class GoalsArgs(BaseModel):
    """Replace the placement goals. required=true only for what the user insists on."""

    model_config = ConfigDict(extra="forbid")

    goals: list[PlacementGoal]


class ReleaseArgs(BaseModel):
    """Ask the code gate to release a layout. Only this can show a design as approved."""

    model_config = ConfigDict(extra="forbid")

    layout_id: str
    summary: str = Field(description="One or two sentences for the user.")


@dataclass
class ReleasedDesign:
    layout_id: str
    candidate: LayoutCandidate
    specification: RoomDesign
    gate: GateResult


@dataclass
class AgentSession:
    """One browser conversation. Lost on refresh; nothing is stored on disk."""

    messages: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    requirements: RequirementsResult | None = None
    specification: RoomDesign | None = None
    candidates: dict[str, LayoutCandidate] = field(default_factory=dict)
    goals: list[PlacementGoal] = field(default_factory=list)
    released: ReleasedDesign | None = None
    config: AccessibilityConfig = field(default_factory=AccessibilityConfig)
    next_seed: int = 42
    next_layout: int = 1


@dataclass
class ToolOutcome:
    ok: bool
    output: dict
    detail: str = ""
    released: bool = False
    summary: str = ""


def _walls_touching(design: RoomDesign, item) -> list[str]:
    """Code states where an item is, so the model need not work it out from x and y."""
    room = design.room
    walls = []
    if item.y_m + item.depth_m >= room.depth_m - WALL_TOUCH_M:
        walls.append("north")
    if item.y_m <= WALL_TOUCH_M:
        walls.append("south")
    if item.x_m + item.width_m >= room.width_m - WALL_TOUCH_M:
        walls.append("east")
    if item.x_m <= WALL_TOUCH_M:
        walls.append("west")
    return walls


def _describe(session: AgentSession, layout_id: str) -> dict:
    candidate = session.candidates[layout_id]
    design = candidate.design
    return {
        "id": layout_id,
        "score": round(candidate.score.total, 1),
        "blocks_window": window_blockers(design),
        "goals_met": [
            f"{goal.item} {goal.relation}"
            for goal in session.goals
            if goal_met(design, goal)
        ],
        "positions": [
            {
                "item": item.id,
                "x": round(item.x_m, 2),
                "y": round(item.y_m, 2),
                "walls": _walls_touching(design, item),
            }
            for item in design.furniture
        ],
    }


def _ranked(session: AgentSession) -> list[dict]:
    """Best first: required goals, then a clear window, then the heuristic score."""

    def order(layout_id: str) -> tuple:
        design = session.candidates[layout_id].design
        unmet = sum(
            goal.required and not goal_met(design, goal) for goal in session.goals
        )
        met = sum(goal_met(design, goal) for goal in session.goals)
        return (
            unmet,
            bool(window_blockers(design)),
            -met,
            -session.candidates[layout_id].score.total,
        )

    ranked = sorted(session.candidates, key=order)
    return [_describe(session, layout_id) for layout_id in ranked[:LAYOUTS_SHOWN]]


def _unquoted(value):
    """Models often wrap a quote in quotation marks; the words must still match."""
    if isinstance(value, dict):
        return {
            key: item.strip().strip(QUOTE_MARKS).strip()
            if key.endswith(("source_text", "_source")) and isinstance(item, str)
            else _unquoted(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_unquoted(item) for item in value]
    return value


def set_requirements(session: AgentSession, args: RequirementsSchema, model: str):
    cleaned = RequirementsSchema.model_validate(_unquoted(args.model_dump()))
    result = prepare_requirements(
        cleaned, "\n".join(session.messages), mode="api_response", model=model
    )
    session.requirements = result
    session.specification = result.specification
    session.candidates = {}
    output = {
        "ok": True,
        "status": result.status,
        "questions_for_user": result.clarifications,
        "assumptions": result.assumptions,
        "limitations": result.limitations,
    }
    if result.specification is not None:
        output["furniture"] = [item.id for item in result.specification.furniture]
    return ToolOutcome(True, output, detail=result.status)


def generate_layouts(session: AgentSession, args: GenerateArgs, _model: str):
    if session.specification is None:
        message = "No ready requirements yet; call set_requirements first."
        return ToolOutcome(False, {"ok": False, "error": message}, detail=message)
    seed = args.seed if args.seed is not None else session.next_seed
    session.next_seed = seed + SEEDS_PER_CALL
    results = [
        generate_layout_candidates(
            session.specification.room,
            session.specification.furniture,
            seed=current,
            max_candidates=CANDIDATES_PER_SEED,
            max_attempts=ATTEMPTS_PER_SEED,
            config=session.config,
        )
        for current in range(seed, seed + SEEDS_PER_CALL)
    ]
    known = {
        tuple((item.id, item.x_m, item.y_m) for item in candidate.design.furniture)
        for candidate in session.candidates.values()
    }
    found = 0
    for result in results:
        for candidate in result.candidates:
            found += 1
            key = tuple(
                (item.id, item.x_m, item.y_m) for item in candidate.design.furniture
            )
            if key not in known and len(session.candidates) < MAX_POOL:
                known.add(key)
                session.candidates[f"L{session.next_layout}"] = candidate
                session.next_layout += 1
    # With nothing found, the last generator status says why (infeasible, exhausted).
    last = results[-1]
    status = "complete" if found else last.status
    output = {
        "ok": True,
        "generator_status": status,
        "generator_message": "" if found else last.message,
        "seeds": [seed, seed + SEEDS_PER_CALL - 1],
        "found": found,
        "pool_size": len(session.candidates),
        "layouts": _ranked(session),
    }
    return ToolOutcome(True, output, detail=f"{status}: {found} found")


def set_placement_goals(session: AgentSession, args: GoalsArgs, _model: str):
    session.goals = list(args.goals)
    output = {"ok": True, "goals": len(session.goals), "layouts": _ranked(session)}
    return ToolOutcome(True, output, detail=f"{len(session.goals)} goal(s)")


def release_design(session: AgentSession, args: ReleaseArgs, _model: str):
    candidate = session.candidates.get(args.layout_id)
    if candidate is None or session.specification is None:
        message = f"Unknown layout id: {args.layout_id[:40]}"
        return ToolOutcome(False, {"ok": False, "error": message}, detail=message)
    gate = release_gate(
        session.specification,
        candidate,
        session.messages,
        session.goals,
        session.config,
    )
    if not gate.passed:
        detail = " ".join(gate.reasons)
        output = {
            "ok": False,
            "released": False,
            "reasons": gate.reasons,
            "layouts": _ranked(session),
        }
        return ToolOutcome(False, output, detail=detail)
    session.released = ReleasedDesign(
        layout_id=args.layout_id,
        candidate=candidate.model_copy(deep=True),
        specification=session.specification.model_copy(deep=True),
        gate=gate,
    )
    return ToolOutcome(
        True,
        {"ok": True, "released": True},
        detail="gate passed",
        released=True,
        summary=args.summary[:MAX_SUMMARY_CHARS],
    )


TOOLS = {
    "set_requirements": (
        set_requirements,
        RequirementsSchema,
        "Record the room and furniture the user asked for, quoting their exact "
        "words as evidence. Replaces earlier requirements and discards old layouts.",
    ),
    "generate_layouts": (generate_layouts, GenerateArgs, GenerateArgs.__doc__),
    "set_placement_goals": (set_placement_goals, GoalsArgs, GoalsArgs.__doc__),
    "release_design": (release_design, ReleaseArgs, ReleaseArgs.__doc__),
}


def tool_definitions() -> list[dict]:
    """Strict function schemas in the Responses API shape."""
    definitions = []
    for name, (_, schema, description) in TOOLS.items():
        function = openai.pydantic_function_tool(
            schema, name=name, description=description
        )["function"]
        definitions.append({"type": "function", **function})
    return definitions

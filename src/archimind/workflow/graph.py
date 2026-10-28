"""A bounded, sequential LangGraph workflow with conditional safe termination."""

from collections.abc import Callable
from functools import partial

from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context

from archimind.agents.interior_stylist_schemas import InteriorStylistResult
from archimind.agents.layout_schemas import LayoutAdviceResult
from archimind.agents.requirements_schemas import RequirementsResult
from archimind.agents.spatial_critic_schemas import SpatialCriticResult
from archimind.workflow import nodes
from archimind.workflow.interior_styling import interior_styling, stylist_policy
from archimind.workflow.layout_recommendation import layout_recommendation
from archimind.workflow.spatial_critique import spatial_critique
from archimind.workflow.state import (
    AIStylingState,
    DesignRequest,
    LayoutRecommendationState,
    NodeName,
    SpatialCritiqueState,
    WorkflowState,
)


def _guard(name: NodeName, operation: Callable[[WorkflowState], dict]) -> Callable:
    def execute(state: WorkflowState) -> dict:
        try:
            updates = operation(state.model_copy(deep=True))
            # LangGraph does not validate every output; validate complete handoffs.
            return dict(WorkflowState.model_validate({**dict(state), **updates}))
        except Exception:
            # Do not include exception text, credentials, paths or backend payloads.
            return nodes.stop(
                state,
                name,
                "node_error",
                f"Workflow node {name} failed; no design was approved.",
                iteration_count=1
                if name == "layout_designer"
                else state.iteration_count,
            )

    return execute


def _continue(state: WorkflowState) -> str:
    return "next" if state.status == "running" else "stop"


def _after_critic(state: WorkflowState) -> str:
    if state.status != "running":
        return "stop"
    if state.layout_recommendation.status == "pending":
        return "advisor"
    return _after_advisor(state)


def _after_advisor(state: WorkflowState) -> str:
    if state.status != "running":
        return "stop"
    return (
        "critique"
        if state.spatial_critique.status == "pending"
        else _before_styling(state)
    )


def _before_styling(state: WorkflowState) -> str:
    if state.status != "running":
        return "stop"
    return "ai_stylist" if state.ai_styling.status == "pending" else "stylist"


def _build_workflow(
    *,
    interpret_free_text: bool = False,
    allow_live_requirements: bool = False,
    interpreter: Callable[..., RequirementsResult] | None = None,
    allow_live_layout: bool = False,
    layout_advisor: Callable[..., LayoutAdviceResult] | None = None,
    allow_live_critic: bool = False,
    spatial_critic: Callable[..., SpatialCriticResult] | None = None,
    allow_live_stylist: bool = False,
    interior_stylist: Callable[..., InteriorStylistResult] | None = None,
):
    """Build fresh internal orchestration; there is no global graph/checkpointer."""
    graph = StateGraph(WorkflowState)
    requirements = (
        partial(
            nodes.requirements_interpreter,
            interpret_free_text=True,
            allow_live=allow_live_requirements,
            interpreter=interpreter,
        )
        if interpret_free_text
        else nodes.requirements_interpreter
    )
    roles = (
        ("requirements_interpreter", requirements),
        ("layout_designer", nodes.layout_designer),
        ("spatial_critic", nodes.spatial_critic),
        (
            "layout_advisor",
            partial(
                layout_recommendation,
                allow_live=allow_live_layout,
                advisor=layout_advisor,
            ),
        ),
        (
            "ai_spatial_critic",
            partial(
                spatial_critique, allow_live=allow_live_critic, critic=spatial_critic
            ),
        ),
        ("interior_stylist", nodes.interior_stylist),
        (
            "ai_interior_stylist",
            partial(
                interior_styling,
                allow_live=allow_live_stylist,
                stylist=interior_stylist,
            ),
        ),
    )
    for name, operation in roles:
        graph.add_node(name, _guard(name, operation))
    graph.add_edge(START, roles[0][0])
    graph.add_conditional_edges(
        "requirements_interpreter", _continue, {"next": "layout_designer", "stop": END}
    )
    graph.add_conditional_edges(
        "layout_designer", _continue, {"next": "spatial_critic", "stop": END}
    )
    graph.add_conditional_edges(
        "spatial_critic",
        _after_critic,
        {
            "advisor": "layout_advisor",
            "critique": "ai_spatial_critic",
            "stylist": "interior_stylist",
            "ai_stylist": "ai_interior_stylist",
            "stop": END,
        },
    )
    graph.add_conditional_edges(
        "layout_advisor",
        _after_advisor,
        {
            "critique": "ai_spatial_critic",
            "stylist": "interior_stylist",
            "ai_stylist": "ai_interior_stylist",
            "stop": END,
        },
    )
    graph.add_conditional_edges(
        "ai_spatial_critic",
        _before_styling,
        {
            "stylist": "interior_stylist",
            "ai_stylist": "ai_interior_stylist",
            "stop": END,
        },
    )
    graph.add_conditional_edges(
        "ai_interior_stylist", _continue, {"next": "interior_stylist", "stop": END}
    )
    graph.add_edge("interior_stylist", END)
    return graph.compile()


def run_workflow(
    request: DesignRequest,
    *,
    interpret_free_text: bool = False,
    allow_live_requirements: bool = False,
    interpreter: Callable[..., RequirementsResult] | None = None,
    use_ai_layout: bool = False,
    allow_live_layout: bool = False,
    layout_advisor: Callable[..., LayoutAdviceResult] | None = None,
    use_ai_critic: bool = False,
    allow_live_critic: bool = False,
    spatial_critic: Callable[..., SpatialCriticResult] | None = None,
    use_ai_stylist: bool = False,
    allow_live_stylist: bool = False,
    interior_stylist: Callable[..., InteriorStylistResult] | None = None,
) -> WorkflowState:
    """Run from a fresh request with separately gated interpretation and advice.

    Default execution remains offline. Live interpretation requires explicit
    mode, feature flag, API key and per-call authorization. Layout advice also
    requires use_ai_layout, its feature flag and allow_live_layout for API usage.
    An explicit trusted offline fixture may run without live authorization, but
    cannot bypass the workflow opt-in or environment feature flag.
    No retry loop, persistence, C01, callbacks or remote tracing.
    Critique additionally requires use_ai_critic, its environment flag and exact
    allow_live_critic authorization for API use. It cannot change selection.
    Styling requires use_ai_stylist, its feature flag and exact allow_live_stylist
    consent, including trusted offline injections (which never use a live client).
    Four default, at most seven with advisors and a fixture fallback; no retries.
    Caller objects and environment are unchanged. LangGraph's internal execution
    IDs are excluded from the deterministic result; placement uses its own seed.
    """
    if (
        type(interpret_free_text) is not bool
        or type(allow_live_requirements) is not bool
        or type(use_ai_layout) is not bool
        or type(allow_live_layout) is not bool
        or type(use_ai_critic) is not bool
        or type(allow_live_critic) is not bool
        or type(use_ai_stylist) is not bool
        or type(allow_live_stylist) is not bool
    ):
        raise ValueError("Workflow modes and authorization must be boolean")
    request = DesignRequest.model_validate(request).model_copy(deep=True)
    initial = WorkflowState(
        request=request,
        layout_recommendation=LayoutRecommendationState(
            requested=use_ai_layout,
            status="pending" if use_ai_layout else "not_requested",
        ),
        spatial_critique=SpatialCritiqueState(
            requested=use_ai_critic,
            status="pending" if use_ai_critic else "not_requested",
        ),
        ai_styling=AIStylingState(
            requested=use_ai_stylist,
            status="pending" if use_ai_stylist else "not_requested",
        ),
    )
    initial.ai_styling = stylist_policy(initial, allow_live=allow_live_stylist)
    # Override even an externally configured LangSmith tracing environment locally.
    with tracing_context(enabled=False):
        result = _build_workflow(
            interpret_free_text=interpret_free_text,
            allow_live_requirements=allow_live_requirements,
            interpreter=interpreter,
            allow_live_layout=allow_live_layout,
            layout_advisor=layout_advisor,
            allow_live_critic=allow_live_critic,
            spatial_critic=spatial_critic,
            allow_live_stylist=allow_live_stylist,
            interior_stylist=interior_stylist,
        ).invoke(
            dict(initial),
            {"recursion_limit": 9, "callbacks": []},
        )
    return WorkflowState.model_validate(result)

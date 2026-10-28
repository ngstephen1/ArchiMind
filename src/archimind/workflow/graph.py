"""A bounded, sequential LangGraph workflow with conditional safe termination."""

from collections.abc import Callable
from functools import partial

from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context

from archimind.agents.layout_schemas import LayoutAdviceResult
from archimind.agents.requirements_schemas import RequirementsResult
from archimind.workflow import nodes
from archimind.workflow.layout_recommendation import layout_recommendation
from archimind.workflow.state import (
    DesignRequest,
    LayoutRecommendationState,
    NodeName,
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
    return "advisor" if state.layout_recommendation.status == "pending" else "stylist"


def _build_workflow(
    *,
    interpret_free_text: bool = False,
    allow_live_requirements: bool = False,
    interpreter: Callable[..., RequirementsResult] | None = None,
    allow_live_layout: bool = False,
    layout_advisor: Callable[..., LayoutAdviceResult] | None = None,
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
        ("interior_stylist", nodes.interior_stylist),
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
        {"advisor": "layout_advisor", "stylist": "interior_stylist", "stop": END},
    )
    graph.add_conditional_edges(
        "layout_advisor", _continue, {"next": "interior_stylist", "stop": END}
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
) -> WorkflowState:
    """Run from a fresh request with separately gated interpretation and advice.

    Default execution remains offline. Live interpretation requires explicit
    mode, feature flag, API key and per-call authorization. Layout advice also
    requires use_ai_layout, its feature flag and allow_live_layout for API usage.
    An explicit trusted offline fixture may run without live authorization, but
    cannot bypass the workflow opt-in or environment feature flag.
    No retry loop, persistence, C01, callbacks or remote tracing.
    Four default/five optional nodes execute at most once; recursion is bounded.
    Caller objects and environment are unchanged. LangGraph's internal execution
    IDs are excluded from the deterministic result; placement uses its own seed.
    """
    if (
        type(interpret_free_text) is not bool
        or type(allow_live_requirements) is not bool
        or type(use_ai_layout) is not bool
        or type(allow_live_layout) is not bool
    ):
        raise ValueError("Workflow modes and authorization must be boolean")
    request = DesignRequest.model_validate(request).model_copy(deep=True)
    initial = WorkflowState(
        request=request,
        layout_recommendation=LayoutRecommendationState(
            requested=use_ai_layout,
            status="pending" if use_ai_layout else "not_requested",
        ),
    )
    # Override even an externally configured LangSmith tracing environment locally.
    with tracing_context(enabled=False):
        result = _build_workflow(
            interpret_free_text=interpret_free_text,
            allow_live_requirements=allow_live_requirements,
            interpreter=interpreter,
            allow_live_layout=allow_live_layout,
            layout_advisor=layout_advisor,
        ).invoke(
            dict(initial),
            {"recursion_limit": 7, "callbacks": []},
        )
    return WorkflowState.model_validate(result)

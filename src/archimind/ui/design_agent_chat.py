"""Chat with the design agent. A design appears here only after the code gate passes."""

import logging
import os

import streamlit as st

from archimind.design_agent.loop import AgentSession, TurnResult, run_turn
from archimind.render import render_design_3d, render_floorplan

CONSENT_KEY = "design_agent_consent"
SESSION_KEY = "design_agent_session"
CHAT_KEY = "design_agent_chat"
LAST_KEY = "design_agent_last"
RESET_KEY = "design_agent_reset"

_logger = logging.getLogger("archimind.design_agent")


def _configure_logging() -> None:
    """Show agent traces in the server console without touching other loggers."""
    if _logger.level == logging.NOTSET:
        _logger.setLevel(logging.INFO)
    if not _logger.handlers and not logging.getLogger().handlers:
        _logger.addHandler(logging.StreamHandler())


def _setup_problem() -> str | None:
    if os.environ.get("ARCHIMIND_ENABLE_OPENAI_AGENT", "0") != "1":
        return (
            "The design agent is turned off. Start the app with "
            "`python scripts/run_with_agent.py` to use it. Everything else on "
            "this page works without it."
        )
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        return "The design agent needs OPENAI_API_KEY in the environment."
    return None


def _show_design(last: TurnResult | None, session: AgentSession) -> None:
    released = session.released
    if released is None:
        return
    if last is not None and last.status != "released":
        st.warning(
            "This is the earlier approved design. Your latest request is not "
            "reflected in it."
        )
    else:
        st.success(
            "Approved by code checks: spatial rules, requested furniture and a "
            "clear window. The model cannot override these checks."
        )
    design = released.candidate.design
    st.plotly_chart(
        render_floorplan(design),
        width="stretch",
        theme=None,
        key="design-agent-floorplan",
        config={"scrollZoom": True, "displaylogo": False},
        alt="Floor plan of the design approved for this conversation.",
    )
    st.plotly_chart(
        render_design_3d(design),
        width="stretch",
        theme=None,
        key="design-agent-3d",
        config={"scrollZoom": True, "displaylogo": False},
        alt="3D view of the design approved for this conversation.",
    )
    if session.requirements is not None and session.requirements.assumptions:
        with st.expander("Assumptions in this design"):
            for assumption in session.requirements.assumptions:
                st.write(f"- {assumption}")


def _show_trace(last: TurnResult) -> None:
    st.caption(
        f"Last request: {last.steps} model call(s), {last.tokens:,} tokens, "
        f"{last.seconds:g} s · Trace {last.trace_id}"
    )
    if last.events:
        with st.expander("What the agent did"):
            st.dataframe(
                [
                    {
                        "Tool": event.tool,
                        "Worked": event.ok,
                        "Result": event.detail,
                    }
                    for event in last.events
                ],
                hide_index=True,
                width="stretch",
                key="design_agent_events",
            )


def render_design_agent() -> None:
    """Conversation state lives in this browser session only."""
    _configure_logging()
    st.subheader("Describe Your Room")
    st.write(
        "Describe a rectangular bedroom or studio with its size, door and window, "
        "and choose from a queen bed, desk and wardrobe. You can then ask for "
        "changes, such as moving the desk near the window."
    )
    problem = _setup_problem()
    if problem:
        st.info(problem)
        return
    consent = st.checkbox(
        "Send my messages to OpenAI for this conversation (uses your API key)",
        key=CONSENT_KEY,
    )
    if st.button("Start over", key=RESET_KEY):
        for key in (SESSION_KEY, CHAT_KEY, LAST_KEY):
            st.session_state.pop(key, None)

    session = st.session_state.setdefault(SESSION_KEY, AgentSession())
    chat = st.session_state.setdefault(CHAT_KEY, [])
    for role, text in chat:
        st.chat_message(role).markdown(text)

    prompt = st.chat_input(
        "For example: a 5 m by 4 m bedroom with a 2.7 m ceiling, a queen bed and a desk…",
        disabled=not consent,
        key="design_agent_input",
    )
    if prompt and consent:
        chat.append(("user", prompt))
        st.chat_message("user").markdown(prompt)
        with st.spinner("Working on your design…"):
            result = run_turn(session, prompt, allow_live=True)
        chat.append(("assistant", result.reply))
        st.chat_message("assistant").markdown(result.reply)
        st.session_state[LAST_KEY] = result

    last = st.session_state.get(LAST_KEY)
    _show_design(last, session)
    if last is not None:
        _show_trace(last)

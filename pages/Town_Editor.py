"""Streamlit client for the same Town projects, revisions and checked design jobs."""

import json
import os
import urllib.error
import urllib.request
import uuid
from urllib.parse import urlencode

import streamlit as st

from archimind.town.agents import ROLES
from archimind.town.photo_form import photo_form

api = os.getenv("TOWN_API_URL", "http://127.0.0.1:8790/api").rstrip("/")
town = os.getenv("TOWN_SITE_URL", "http://127.0.0.1:8790")
hosted = bool(os.getenv("SUPABASE_URL"))


def call(path, body=None):
    headers = {"Content-Type": "application/json"}
    if token := st.session_state.get("town_auth"):
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        api + path,
        headers=headers,
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        st.error(json.loads(exc.read()).get("error", "Request failed."))
        st.stop()
    except OSError:
        st.error("The town service is unavailable.")
        st.stop()


st.title("Town editor")
if hosted and not st.session_state.get("town_auth"):
    with st.form("town_login"):
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Sign in"):
            req = urllib.request.Request(
                os.environ["SUPABASE_URL"].rstrip("/")
                + "/auth/v1/token?grant_type=password",
                data=json.dumps({"email": email, "password": pw}).encode(),
                headers={
                    "Content-Type": "application/json",
                    "apikey": os.environ["SUPABASE_ANON_KEY"],
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=8) as r:
                    st.session_state["town_auth"] = json.load(r)["access_token"]
            except OSError:
                st.error("Could not sign in.")
                st.stop()
            st.rerun()
    st.stop()
project = st.query_params.get("project")
if not project:
    st.link_button("Explore Market Square", town)
    if st.button("Create private project"):
        st.query_params["project"] = call("/projects", {})["project"]
        st.rerun()
    st.stop()
try:
    p = str(uuid.UUID(project))
    requested = int(st.query_params.get("revision", "0"))
except ValueError:
    st.error("Invalid project link.")
    st.stop()
snapshot = call(
    "/projects/"
    + p
    + ("?revision=" + str(requested) if "revision" in st.query_params else "")
)
rev = snapshot["revision"]
home = snapshot["home"]
st.link_button(
    "Open this revision in Town",
    town + "?" + urlencode({"project": p, "revision": rev}),
)
st.caption(f"Revision {rev} · Current head {snapshot['head']}")
if rev != snapshot["head"] and st.button("Open latest"):
    st.query_params["revision"] = str(snapshot["head"])
    st.rerun()
with st.expander(
    "Room photos and field survey", expanded=st.query_params.get("mode") == "photos"
):
    photo_form(p, rev, home, allow_analysis=not hosted)
if home:
    st.table(
        [
            {
                "Room": r["design"]["room"]["name"],
                "Width (m)": r["design"]["room"]["width_m"],
                "Depth (m)": r["design"]["room"]["depth_m"],
                "Furniture": ", ".join(f["name"] for f in r["design"]["furniture"]),
            }
            for r in home["rooms"]
        ]
    )
if snapshot.get("history"):
    with st.expander("Recent design briefs"):
        for past in snapshot["history"]:
            st.write(
                f"From revision {past['base']} · {past['status']} · {past['message'] or 'Measured design brief'}"
            )

with st.form("town_edit"):
    w = st.number_input(
        "Lot width (m)", 9.0, 15.0, float(home["width"]) if home else 13.0
    )
    d = st.number_input(
        "Lot depth (m)", 9.0, 16.0, float(home["depth"]) if home else 13.0
    )
    salon = st.checkbox("Include a formal salon and dining group")
    priority = st.selectbox("Priority", ["balanced", "quiet bedroom", "bright study"])
    finishes = ["oak", "sage", "terracotta"]
    palette = st.selectbox(
        "Finishes", finishes, index=finishes.index(home["palette"]) if home else 0
    )
    locks = st.multiselect(
        "Preserve rooms",
        [r["design"]["room"]["id"] for r in home["rooms"]] if home else [],
    )
    brief = st.text_area("Design brief (optional)")
    st.caption(
        "Generate sends the brief and floor plans to OpenAI for interpretation, styling and visual review (up to three calls). A configured local Codex CLI also reviews the bedroom."
    )
    if st.form_submit_button("Generate alternatives", disabled=rev != snapshot["head"]):
        st.session_state["town_job:" + p] = call(
            "/jobs",
            {
                "id": str(uuid.uuid4()),
                "project": p,
                "base": rev,
                "message": brief,
                "live": True,
                "agent_team": True,
                "brief": {
                    "width": w,
                    "depth": d,
                    "priority": priority,
                    "formal_salon": salon,
                    "palette": palette,
                    "locks": locks,
                    "seed": 42 + rev,
                },
            },
        )["job"]
        st.rerun()
j = snapshot.get("latest_job") if rev == snapshot["head"] else None
if j:
    initial = call("/jobs/" + j + "/events")

    @st.fragment(run_every="1s" if initial["status"] in ("running", "queued") else None)
    def monitor():
        feed = call("/jobs/" + j + "/events")
        st.subheader("Design team")
        st.caption(feed["message"] or "Measured design brief")
        for agent, role in ROLES.items():
            events = [e for e in feed["events"] if e["agent"] == agent]
            last = events[-1] if events else None
            state = last["state"] if last else "waiting"
            if feed["status"] in ("cancelled", "failed") and state in (
                "waiting",
                "running",
            ):
                state = "stopped"
            with st.expander(f"Agent {agent} · {role} · {state}"):
                for event in events:
                    st.write(event["task"], event["state"])
                    if event["artifact"]:
                        st.json(event["artifact"], expanded=False)
            if state == "running":
                st.status(last["task"], state="running")
        if feed["status"] == "ready" and any(
            e["state"] == "failed" and e["task"] == "OpenAI · Review plan images"
            for e in feed["events"]
        ):
            st.warning("Spatial checks passed. AI visual review unavailable.")
        plans = [
            e
            for e in feed["events"]
            if e["task"] in ("Proposed partitions", "Furnished candidate")
        ]
        if plans:
            import plotly.graph_objects as go

            latest = plans[-1]
            home = latest["artifact"]
            fig = go.Figure()
            for part in home["rooms"]:
                if "design" in part:
                    x, y = part["origin"]
                    room = part["design"]["room"]
                    w, d = room["width_m"], room["depth_m"]
                    name = room["name"]
                    for f in part["design"]["furniture"]:
                        fx, fy = x + f["x_m"], y + f["y_m"]
                        fig.add_shape(
                            type="rect",
                            x0=fx,
                            y0=fy,
                            x1=fx + f["width_m"],
                            y1=fy + f["depth_m"],
                            fillcolor="#9bb19d",
                        )
                else:
                    x, y, w, d, name = (part[k] for k in ("x", "y", "w", "d", "name"))
                fig.add_shape(type="rect", x0=x, y0=y, x1=x + w, y1=y + d)
                fig.add_annotation(x=x + w / 2, y=y + d / 2, text=name, showarrow=False)
            fig.update_xaxes(range=[0, home["width"]])
            fig.update_yaxes(range=[0, home["depth"]], scaleanchor="x")
            st.plotly_chart(fig, key="working-plan-" + j)
        if initial["status"] in ("running", "queued") and feed["status"] not in (
            "running",
            "queued",
        ):
            st.rerun()

    monitor()
    result = call("/jobs/" + j)
    st.write("Design job", result["status"])
    if result["status"] == "ready":
        for i, alternative in enumerate(result["result"]):
            st.write("Layout " + chr(65 + i), alternative["evidence"])
            if st.button("Apply layout " + chr(65 + i)):
                applied = call("/jobs/" + j + "/apply", {"index": i})
                st.query_params["revision"] = str(applied["revision"])
                st.session_state.pop("town_job:" + p, None)
                st.rerun()
    elif result["status"] == "failed":
        st.warning(result["result"])
    else:
        if result["status"] in ("queued", "running") and st.button("Cancel design job"):
            call("/jobs/" + j + "/cancel", {})
            st.rerun()

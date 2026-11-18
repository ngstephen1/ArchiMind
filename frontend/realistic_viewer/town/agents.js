const roles = [
  "Brief & constraints",
  "Furniture & references",
  "Layout planner",
  "Spatial critic",
  "Style & presentation",
];
export function timeline(container, events, status) {
  const expanded = new Set(
    [...container.querySelectorAll("details[open]")].map(
      (e) => e.dataset.agent,
    ),
  );
  const nodes = roles.map((role, index) => {
    const agent = String.fromCharCode(65 + index),
      log = events.filter((e) => e.agent === agent),
      latest = log.at(-1);
    const terminal = ["ready", "failed", "cancelled"].includes(status);
    const state =
      latest?.state === "running" && terminal
        ? "stopped"
        : latest?.state || (terminal ? "skipped" : "waiting");
    const card = document.createElement("details");
    card.dataset.agent = agent;
    card.open = expanded.has(agent);
    card.dataset.state = state;
    const title = document.createElement("summary"),
      badge = document.createElement("b"),
      name = document.createElement("strong"),
      detail = document.createElement("small");
    badge.textContent = agent;
    name.textContent = role;
    const duration = log.length
      ? Math.max(
          0,
          (state === "running"
            ? status === "replaying"
              ? events.at(-1).time
              : Date.now() / 1000
            : latest.time) - log[0].time,
        )
      : 0;
    detail.textContent =
      state +
      " · " +
      (latest?.task || "Awaiting worker") +
      (log.length ? " · " + duration.toFixed(2) + " s" : "");
    const engine = document.createElement("img");
    const ai = /^(OpenAI|Codex CLI) ·/.test(latest?.task || "");
    engine.src = "assets/" + (ai ? "openai" : "python") + ".svg";
    engine.alt = ai ? "OpenAI" : "Python";
    engine.className = "agent-engine";
    if (latest && latest.state !== "skipped" && !latest.task.startsWith("Codex CLI")) title.append(engine);
    title.append(badge, name, detail);
    card.append(title);
    for (const e of log) {
      const line = document.createElement("p");
      line.textContent = e.state + " · " + e.task;
      card.append(line);
      if (e.artifact.advice) {
        const advice = e.artifact.advice;
        const analysis = document.createElement("p");
        analysis.textContent = "Layout A · " + e.artifact.room + " · " + e.artifact.candidate.slice(0, 8) + " — " + advice.design_analysis;
        card.append(analysis);
        const items = document.createElement("ul");
        for (const suggestion of advice.suggestions) {
          const item = document.createElement("li");
          item.textContent = suggestion.furniture_id + " at (" + suggestion.x_m + ", " +
            suggestion.y_m + ") m — " + suggestion.explanation;
          items.append(item);
        }
        if (advice.suggestions.length) {
          const heading = document.createElement("strong");
          heading.textContent = "Suggested placements · require spatial validation";
          card.append(heading, items);
        }
        for (const limitation of advice.limitations) {
          const note = document.createElement("p");
          note.textContent = "Limitation: " + limitation;
          card.append(note);
        }
      } else if (e.artifact.material_direction || e.artifact.observation) {
        const summary = document.createElement("p");
        summary.textContent = [
          e.artifact.material_direction, e.artifact.lighting_direction, e.artifact.tradeoff,
          e.artifact.observation, e.artifact.recommendation, e.artifact.uncertainty,
        ].filter(Boolean).join(" ");
        card.append(summary);
      } else if (Object.keys(e.artifact).length) {
        const pre = document.createElement("pre");
        pre.textContent = JSON.stringify(e.artifact, null, 2);
        card.append(pre);
      }
    }
    return card;
  });
  container.replaceChildren(...nodes);
}

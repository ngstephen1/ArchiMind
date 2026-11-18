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
    title.append(badge, name, detail);
    card.append(title);
    for (const e of log) {
      const line = document.createElement("p");
      line.textContent = e.state + " · " + e.task;
      card.append(line);
      if (Object.keys(e.artifact).length) {
        const pre = document.createElement("pre");
        pre.textContent = JSON.stringify(e.artifact, null, 2);
        card.append(pre);
      }
    }
    return card;
  });
  container.replaceChildren(...nodes);
}

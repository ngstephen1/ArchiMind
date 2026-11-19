// Each entry keeps the original candidate index used by preview and Apply.
export function competingGoals(homes) {
  if (homes.length !== 2) return [];
  const rows = homes.map(home => home.evidence?.room_preferences ?? []);
  if (rows[0].length !== rows[1].length) return [];
  const choices = [];
  for (const goal of rows[0]) {
    const peer = rows[1].find(other =>
      other.room === goal.room && other.target === goal.target && other.relation === goal.relation);
    if (!peer || !["near", "far"].includes(goal.relation)) return [];
    const distances = [goal.center_distance_m, peer.center_distance_m];
    if (!distances.every(Number.isFinite)) return [];
    if (distances[0] === distances[1]) continue;
    const shorter = distances[0] < distances[1] ? 0 : 1;
    choices.push({room: goal.room, target: goal.target, relation: goal.relation,
      distances, winner: goal.relation === "near" ? shorter : 1 - shorter});
  }
  return new Set(choices.map(choice => choice.winner)).size === 2 ? choices : [];
}

import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import {
  bedroomManifest,
  manifestDigest,
  manifestText,
  publicationFor,
} from "../town/bedroom_manifest.js";

const sample = JSON.parse(
  await readFile(new URL("../town/showcase.json", import.meta.url), "utf8"),
);
const saved = () => ({
  project: "test-project",
  revision: 1,
  home: structuredClone(sample),
});
const bedroom = (d) => d.home.rooms.find((p) => p.design.room.id === "bedroom");

test("an applied design controls native sources, openings, furniture and camera targets", async () => {
  const d = saved(),
    p = bedroom(d),
    m = bedroomManifest(d);
  assert.deepEqual(m.room.windows, p.design.room.windows);
  const desk = (rows) => rows.find((f) => f.id === "belaya");
  assert.match(desk(m.furniture).source.sha256, /^[0-9a-f]{64}$/);
  assert.equal(m.furniture.find((f) => f.id === "desk-chair").source, null);
  assert.equal(m.cameras.length, 3);
  const before = await manifestDigest(m);
  p.design.room.windows[0].offset_m += 0.12;
  desk(p.design.furniture).x_m -= 0.25;
  const moved = bedroomManifest(d);
  assert.notEqual(await manifestDigest(moved), before);
  assert.notEqual(moved.room.windows[0].offset_m, m.room.windows[0].offset_m);
  assert.notDeepEqual(
    desk(moved.furniture).center_floor_xyz_m,
    desk(m.furniture).center_floor_xyz_m,
  );
  assert.notDeepEqual(moved.cameras[1].target_xyz_m, m.cameras[1].target_xyz_m);
});

test("only the exact published revision and canonical bytes produce a download", async () => {
  const d = saved(),
    m = bedroomManifest(d),
    hash = await manifestDigest(m);
  const entry = {
    project: d.project,
    revision: 1,
    home_id: d.home.id,
    manifest_sha256: hash,
    url: "demo.zip",
  };
  assert.equal(publicationFor(m, hash, [entry]), entry);
  for (const changes of [
    { project: "different" },
    { home_id: "different" },
    { revision: 2 },
    { manifest_sha256: "different" },
  ])
    assert.equal(
      publicationFor(m, hash, [{ ...entry, ...changes }]),
      undefined,
    );
  assert.equal(
    manifestText({ b: 1, a: { y: 2, x: 3 } }),
    manifestText({ a: { x: 3, y: 2 }, b: 1 }),
  );
  for (const revision of [0, -1, 0.3, null])
    assert.throws(() => bedroomManifest({ ...d, revision }));
});

test("chair version, unavailable desk evidence and unsupported orientation", () => {
  const d = saved(),
    part = bedroom(d);
  const binding = {
    concept_id: "oak-sage-writing-chair",
    version: "1.1.0",
    sha256: "a".repeat(64),
  };
  part.designer_chair = { name: "chair", binding };
  let m = bedroomManifest(d);
  assert.equal(
    m.furniture.find((f) => f.id === "desk-chair").source.version,
    "1.1.0",
  );
  part.asset_bindings.find((b) => b.furniture_id === "belaya").envelope_sha256 =
    "stale";
  m = bedroomManifest(d);
  assert.equal(m.furniture.find((f) => f.id === "belaya").source, null);
  part.design.furniture[0].rotation_deg = 90;
  assert.throws(() => bedroomManifest(d));
});

test("the handoff ZIP matches only the archived revision 2 whole-home export", async () => {
  const { homeBoard } = await import("../town/home_board.js");
  const read = async (file) => JSON.parse(await readFile(new URL(file, import.meta.url), "utf8"));
  const entries = await read("../town/conference_publications.json");
  const snapshot = await read("../../../docs/data/nov24-fresh-live/snapshot-r2.json");
  const manifest = homeBoard(snapshot);
  const digest = await manifestDigest(manifest);
  const candidate = publicationFor(manifest, digest, entries);
  assert.equal(candidate?.kind, "rehearsal-package");
  assert.equal(candidate.url, "https://github.com/ngstephen1/ArchiMind/actions/runs/45207279553/artifacts/14834053043");
  assert.equal(candidate.pdf, undefined);
  const before = homeBoard(await read("../../../docs/data/nov24-fresh-live/snapshot-r1.json"));
  assert.equal(publicationFor(before, await manifestDigest(before), entries), undefined);
  for (const change of [{ project: "other" }, { revision: 1 }, { home_id: "other" }]) {
    assert.equal(publicationFor({ ...manifest, ...change }, digest, entries), undefined);
  }
  const revised = { ...manifest, palette: "new finish" };
  assert.equal(publicationFor(revised, await manifestDigest(revised), entries), undefined);
});

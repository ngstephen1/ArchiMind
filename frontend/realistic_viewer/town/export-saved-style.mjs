// Export the same high-quality pack transforms that Town applies to an exact saved home.
import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { buildTownDressing } from "./dressing_detail.js";
import { dressFurniture } from "../src/pack_furniture.js";
import { loadStylePack } from "../src/style_pack.js";
import { manifestText } from "./bedroom_manifest.js";
import { homeBoard } from "./home_board.js";
import { dressingOrigin } from "./floor.js";

const assets = fileURLToPath(
  new URL("../../../src/archimind/_viewer_assets/", import.meta.url),
);
const sha = (bytes) => createHash("sha256").update(bytes).digest("hex");

// Town computes placement from the full Three scene's hierarchy and bounds.
// Decode its unmodified meshes locally, skipping image decode just for this Node pass.
// Blender imports the complete original file, including its original materials.
async function modelForPlacement(bytes) {
  const original = Buffer.from(bytes);
  const length = original.readUInt32LE(12);
  const gltf = JSON.parse(original.toString("utf8", 20, 20 + length));
  for (const mesh of gltf.meshes)
    for (const p of mesh.primitives) delete p.material;
  delete gltf.materials;
  delete gltf.textures;
  delete gltf.images;
  const json = Buffer.from(JSON.stringify(gltf));
  const aligned = (json.length + 3) & ~3;
  const encoded = Buffer.alloc(
    20 + aligned + original.length - 20 - length,
    32,
  );
  original.copy(encoded, 0, 0, 20);
  encoded.writeUInt32LE(encoded.length, 8);
  encoded.writeUInt32LE(aligned, 12);
  json.copy(encoded, 20);
  original.copy(encoded, 20 + aligned, 20 + length);
  const scene = (
    await new GLTFLoader().parseAsync(
      encoded.buffer.slice(
        encoded.byteOffset,
        encoded.byteOffset + encoded.length,
      ),
      "",
    )
  ).scene;
  scene.userData.releaseSha256 = sha(original);
  return scene;
}

const [snapshotFile, manifestFile, outputFile] = process.argv.slice(2);
const raw = await readFile(snapshotFile),
  manifest = await readFile(manifestFile);
const snapshot = JSON.parse(raw);
if (!manifest.equals(Buffer.from(manifestText(homeBoard(snapshot)))))
  throw Error("Snapshot does not reproduce the exact approved Town manifest.");
const bytes = async (path) => {
  if (!/^[a-zA-Z0-9_./-]+$/.test(path) || path.includes(".."))
    throw Error("Unsafe asset path");
  return new Uint8Array(await readFile(resolve(assets, path)));
};
const pack = await loadStylePack({
  baseUrl: "",
  ref: snapshot.home.style_pack,
  tier: "high",
  fetchBytes: bytes,
  decodeTexture: async () => new THREE.Texture(),
  parseEnvironment: async () => new THREE.Texture(),
  parseModel: modelForPlacement,
});
if (!pack || pack.failures.length || pack.unreleased.length)
  throw Error("Incomplete saved style pack.");
const rooms = [];
for (const part of snapshot.home.rooms) {
  if (
    !part.style ||
    part.style.style_pack.id !== pack.id ||
    part.style.style_pack.version !== pack.version
  )
    throw Error("Room pack differs from the saved home.");
  const holder = new THREE.Group();
  holder.position.set(...dressingOrigin(part));
  const dressing = buildTownDressing(holder, part.style.dressing, pack, "high");
  if ((await dressing.ready).length)
    throw Error("Saved dressing failed to resolve.");
  const tagged = new Map();
  const bindings = part.style.bindings.filter(
    (b) => b.furniture_id !== "belaya",
  );
  const furniture = dressFurniture({
    bindings,
    furniture: part.design.furniture,
    pack,
    objects: tagged,
    parent: holder,
  });
  const { placed, failed } = await furniture.ready;
  if (failed.length || pack.failures.length)
    throw Error("Saved model release failed: " + failed.join(","));
  holder.updateMatrixWorld(true);
  const models = [],
    shapes = [];
  function visit(node, group) {
    if (node.userData.releaseSha256) {
      const bounds = new THREE.Box3().setFromObject(node);
      models.push({
        group,
        sha256: node.userData.releaseSha256,
        matrix: node.matrixWorld.toArray(),
        bounds: [bounds.min.toArray(), bounds.max.toArray()],
      });
      return;
    }
    if (node.isMesh) {
      const g = node.geometry,
        a = g.attributes.position,
        v = new THREE.Vector3(),
        vertices = [];
      for (let i = 0; i < a.count; i++) {
        v.fromBufferAttribute(a, i).applyMatrix4(node.matrixWorld);
        vertices.push([v.x, -v.z, v.y]);
      }
      const m = node.material;
      shapes.push({
        group,
        type: g.type,
        vertices,
        triangles: g.index
          ? [...g.index.array]
          : Array.from({ length: a.count }, (_, i) => i),
        color: m.color.getHexString(),
        roughness: m.roughness,
        metalness: m.metalness,
        emission: m.emissive?.getHexString() || "000000",
        strength: m.emissiveIntensity || 0,
      });
    }
    for (const child of node.children) visit(child, group);
  }
  for (const object of dressing.root.children)
    visit(object, "decor/" + object.name);
  for (const object of holder.children)
    if (object.userData.packFurniture)
      visit(object, "furniture/" + object.userData.packFurniture);
  rooms.push({
    id: part.design.room.id,
    placed,
    models,
    shapes,
    dressing: part.style.dressing,
    bindings: part.style.bindings,
  });
}
await writeFile(
  outputFile,
  JSON.stringify({
    home_id: snapshot.home.id,
    project: snapshot.project,
    revision: snapshot.revision,
    snapshot_sha256: sha(raw),
    manifest_sha256: sha(manifest),
    style_pack: snapshot.home.style_pack,
    rooms,
  }),
);

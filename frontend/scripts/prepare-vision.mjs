import { mkdir, cp, writeFile, readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { build } from "esbuild";
await mkdir("public/models", { recursive: true });
await cp("node_modules/@mediapipe/tasks-vision/wasm", "public/wasm", {
  recursive: true,
});
const url =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";
let data;
try {
  data = await readFile("public/models/pose_landmarker_lite.task");
} catch {
  const response = await fetch(url);
  if (!response.ok)
    throw new Error("Falha no download do modelo: " + response.status);
  data = Buffer.from(await response.arrayBuffer());
}
const hash = createHash("sha256").update(data).digest("hex");
let manifest;
try {
  manifest = JSON.parse(await readFile("vision/model-manifest.json", "utf8"));
} catch {}
if (manifest?.sha256 && manifest.sha256 !== hash)
  throw new Error("Hash do modelo diferente do manifesto. Não executar.");
await writeFile("public/models/pose_landmarker_lite.task", data);
await writeFile(
  "vision/model-manifest.json",
  JSON.stringify(
    {
      provider: "MediaPipePoseProvider",
      package: "0.10.32",
      model: "pose_landmarker_lite/float16/1",
      url,
      sha256: hash,
    },
    null,
    2,
  ),
);
await build({
  entryPoints: ["vision/pose.worker.ts"],
  bundle: true,
  format: "iife",
  platform: "browser",
  target: "es2022",
  outfile: "public/pose-worker.js",
  minify: true,
});
console.log("Modelo local verificado e worker preparado. SHA256: " + hash);

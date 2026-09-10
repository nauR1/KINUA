import { FilesetResolver, PoseLandmarker } from "@mediapipe/tasks-vision";
import { names } from "./types";
import manifest from "./model-manifest.json";
let landmarker: PoseLandmarker | undefined;
let initialization: Promise<PoseLandmarker> | undefined;
let lastTime = 0;
self.onmessage = async (event: MessageEvent) => {
  const { id, bitmap } = event.data as { id: number; bitmap: ImageBitmap };
  try {
    if (!landmarker) {
      if (!initialization)
        initialization = FilesetResolver.forVisionTasks("/wasm").then((files) =>
          PoseLandmarker.createFromOptions(files, {
            baseOptions: {
              modelAssetPath: "/models/pose_landmarker_lite.task",
              delegate: "CPU",
            },
            runningMode: "VIDEO",
            numPoses: 2,
            minPoseDetectionConfidence: 0.5,
            minPosePresenceConfidence: 0.5,
            minTrackingConfidence: 0.5,
          }),
        );
      landmarker = await initialization;
    }
    lastTime = Math.max(lastTime + 1, performance.now());
    const result = landmarker.detectForVideo(bitmap, lastTime);
    if (result.landmarks.length > 1)
      throw new Error(
        "Mais de uma pessoa detectada. Mantenha somente o paciente no enquadramento.",
      );
    const landmarks = (result.landmarks[0] || []).map((p, index) => ({
      name: names[index],
      x: p.x,
      y: p.y,
      z: p.z,
      visibility: p.visibility ?? 0,
    }));
    self.postMessage({
      id,
      result: {
        landmarks,
        provider: "MediaPipePoseProvider",
        provider_version:
          "tasks-vision/0.10.32;pose_landmarker_lite/float16/1;sha256=" +
          manifest.sha256,
      },
    });
  } catch (error) {
    self.postMessage({
      id,
      error:
        error instanceof Error ? error.message : "Falha na detecção corporal",
    });
  } finally {
    bitmap.close();
  }
};

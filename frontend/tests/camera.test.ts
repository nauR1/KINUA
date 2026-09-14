import { describe, it, expect } from "vitest";
import { cameraError } from "../lib/camera";
describe("camera failures", () => {
  for (const name of [
    "NotAllowedError",
    "NotFoundError",
    "NotReadableError",
    "OverconstrainedError",
  ]) {
    it(name, () => {
      const e = new Error("native diagnostic");
      e.name = name;
      expect(cameraError(e)).not.toContain("native diagnostic");
      expect(cameraError(e)).toContain("câmera");
    });
  }
});

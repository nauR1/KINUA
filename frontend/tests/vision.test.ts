import { describe, it, expect } from "vitest";
import { names, connections } from "../vision/types";
describe("canonical pose contract", () => {
  it("maps all 33 MediaPipe landmarks without duplicate identifiers", () => {
    expect(names).toHaveLength(33);
    expect(new Set(names).size).toBe(33);
    expect(names[23]).toBe("left_hip");
    expect(names[28]).toBe("right_ankle");
  });
  it("connects only defined anatomical endpoints", () => {
    for (const [a, b] of connections) {
      expect(names).toContain(a);
      expect(names).toContain(b);
      expect(a).not.toBe(b);
    }
  });
});

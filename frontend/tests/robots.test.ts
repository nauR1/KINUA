import { describe, expect, it } from "vitest";
import robots from "../app/robots";

describe("robots", () => {
  it("blocks all crawlers from authenticated production routes", () => {
    expect(robots()).toEqual({
      rules: [{ userAgent: "*", disallow: "/" }],
    });
  });
});

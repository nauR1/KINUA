import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { toDatetimeLocal, toUtcIso } from "../lib/access-datetime";

const originalTimezone = process.env.TZ;

beforeAll(() => {
  process.env.TZ = "America/Bahia";
});

afterAll(() => {
  process.env.TZ = originalTimezone;
});

describe("access datetime serialization", () => {
  it("keeps empty access start as inheritance", () => {
    expect(toUtcIso("")).toBeNull();
    expect(toUtcIso(null)).toBeNull();
  });

  it("round-trips a local datetime without applying the offset twice", () => {
    const local = "2026-09-16T09:45";
    expect(toDatetimeLocal(toUtcIso(local))).toBe(local);
  });

  it("keeps the local calendar day near midnight in Bahia", () => {
    expect(toUtcIso("2026-09-16T00:30")).toBe("2026-09-16T03:30:00.000Z");
    expect(toDatetimeLocal("2026-09-16T03:30:00.000Z")).toBe(
      "2026-09-16T00:30",
    );
  });
});

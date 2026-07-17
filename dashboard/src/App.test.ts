import { describe, it, expect } from "vitest";

// Mirrors the pass/fail classification a reviewer glances at in the UI —
// kept as a small pure function so it's independently testable.
function classifySimResult(verified: boolean, expectedVerified: boolean): "pass" | "fail" {
  return verified === expectedVerified ? "pass" : "fail";
}

describe("classifySimResult", () => {
  it("passes when a clean dataset verifies successfully", () => {
    expect(classifySimResult(true, true)).toBe("pass");
  });

  it("passes when a poisoned dataset is correctly blocked", () => {
    expect(classifySimResult(false, false)).toBe("pass");
  });

  it("fails when a poisoned dataset incorrectly verifies", () => {
    expect(classifySimResult(true, false)).toBe("fail");
  });
});

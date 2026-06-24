import { describe, expect, it } from "vitest";

import { hoursMinutes, keur, num, pct, share } from "../src/lib/format";

describe("formats français", () => {
  it("sépare les milliers par une espace fine insécable", () => {
    expect(num(13087)).toBe("13\u202f087");
  });
  it("utilise la virgule décimale et l'espace insécable avant %", () => {
    expect(pct(0.1716, 1)).toBe("17,2\u00a0%");
  });
  it("signe les montants en k€", () => {
    expect(keur(47918, 0, true)).toBe("+48\u00a0k€");
    expect(keur(-88631)).toBe("−89\u00a0k€");
  });
  it("exprime les durées en heures et minutes", () => {
    expect(hoursMinutes(1.434)).toBe("1\u00a0h\u00a026");
  });
  it("n'arrondit pas à 0 % une part rare mais observée", () => {
    expect(share(0.8774)).toBe("88\u00a0%");
    expect(share(0.0036)).toBe("moins de 1\u00a0%");
    expect(share(0.0036, true)).toBe("<\u00a01\u00a0%");
    expect(share(0)).toBe("0\u00a0%");
  });
});

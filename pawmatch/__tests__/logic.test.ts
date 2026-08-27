import {
  BIO_MAX_LENGTH,
  isProfileComplete,
  isWithinLength,
  sanitizeSearchText,
  wouldFormMatch,
} from "@/lib/logic";

describe("isProfileComplete", () => {
  it("requires both a human and a pet photo", () => {
    expect(isProfileComplete([])).toBe(false);
    expect(isProfileComplete(["human"])).toBe(false);
    expect(isProfileComplete(["pet"])).toBe(false);
    expect(isProfileComplete(["human", "pet"])).toBe(true);
    expect(isProfileComplete(["pet", "human", "pet"])).toBe(true);
  });
});

describe("wouldFormMatch", () => {
  it("forms a match only when the like is mutual", () => {
    const existingLikes = [{ swiper_id: "b", swiped_id: "a" }];
    expect(wouldFormMatch(existingLikes, { swiper_id: "a", swiped_id: "b" })).toBe(true);
  });

  it("does not form a match from a one-sided like", () => {
    const existingLikes = [{ swiper_id: "c", swiped_id: "a" }];
    expect(wouldFormMatch(existingLikes, { swiper_id: "a", swiped_id: "b" })).toBe(false);
  });
});

describe("sanitizeSearchText", () => {
  it("strips HTML/script-like content and keeps plain text", () => {
    expect(sanitizeSearchText("<script>alert(1)</script>")).toBe("scriptalert1script");
  });

  it("strips SQL-injection-style punctuation", () => {
    expect(sanitizeSearchText("dog'; DROP TABLE profiles; --")).toBe("dog' DROP TABLE profiles --");
  });

  it("keeps Hebrew and Latin letters, digits and spaces", () => {
    expect(sanitizeSearchText("כלב 2")).toBe("כלב 2");
  });

  it("truncates to the max search length", () => {
    const longInput = "a".repeat(200);
    expect(sanitizeSearchText(longInput).length).toBeLessThanOrEqual(60);
  });
});

describe("isWithinLength", () => {
  it("rejects empty or overly long input", () => {
    expect(isWithinLength("", BIO_MAX_LENGTH)).toBe(false);
    expect(isWithinLength("   ", BIO_MAX_LENGTH)).toBe(false);
    expect(isWithinLength("a".repeat(BIO_MAX_LENGTH + 1), BIO_MAX_LENGTH)).toBe(false);
    expect(isWithinLength("hello", BIO_MAX_LENGTH)).toBe(true);
  });
});

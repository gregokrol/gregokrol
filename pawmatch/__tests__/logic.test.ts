import {
  BIO_MAX_LENGTH,
  isPlausibleRealName,
  sanitizePersonNameInput,
  base64DecodedByteLength,
  isAtLeastAge,
  isProfileComplete,
  isValidIsoDate,
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

describe("birthdate validation", () => {
  const now = new Date(Date.UTC(2026, 7, 27));

  it("accepts real ISO dates only", () => {
    expect(isValidIsoDate("2000-02-29")).toBe(true);
    expect(isValidIsoDate("2001-02-29")).toBe(false);
    expect(isValidIsoDate("27/08/2000")).toBe(false);
  });

  it("enforces the 18+ boundary", () => {
    expect(isAtLeastAge("2008-08-27", 18, now)).toBe(true);
    expect(isAtLeastAge("2008-08-28", 18, now)).toBe(false);
  });
});


describe("base64DecodedByteLength", () => {
  it("calculates decoded byte length including padding", () => {
    expect(base64DecodedByteLength("YQ==")).toBe(1);
    expect(base64DecodedByteLength("YWI=")).toBe(2);
    expect(base64DecodedByteLength("YWJj")).toBe(3);
  });
});


describe("real-name validation", () => {
  it("accepts plausible Hebrew and English names", () => {
    expect(isPlausibleRealName("דניאל כהן")).toBe(true);
    expect(isPlausibleRealName("Daniel Cohen")).toBe(true);
    expect(isPlausibleRealName("נועה")).toBe(true);
  });

  it("rejects punctuation, numbers, emoji and junk", () => {
    expect(isPlausibleRealName("דניאל123")).toBe(false);
    expect(isPlausibleRealName("דניאל!!!")).toBe(false);
    expect(isPlausibleRealName("Daniel🙂")).toBe(false);
    expect(isPlausibleRealName("qwerty")).toBe(false);
    expect(isPlausibleRealName("test")).toBe(false);
    expect(isPlausibleRealName("aaa")).toBe(false);
  });

  it("rejects too many words and one-letter words", () => {
    expect(isPlausibleRealName("A")).toBe(false);
    expect(isPlausibleRealName("John A Smith")).toBe(false);
    expect(isPlausibleRealName("One Two Three Four")).toBe(false);
  });

  it("sanitizes disallowed characters while typing", () => {
    expect(sanitizePersonNameInput("דניאל123!!! כהן🙂")).toBe("דניאל כהן");
    expect(sanitizePersonNameInput("Daniel   Cohen")).toBe("Daniel Cohen");
  });
});

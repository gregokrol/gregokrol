import type { PhotoKind } from "./types";

export const BIO_MAX_LENGTH = 500;
export const NAME_MAX_LENGTH = 40;
export const NAME_MIN_LENGTH = 2;
export const MESSAGE_MAX_LENGTH = 1000;
export const SEARCH_MAX_LENGTH = 60;
export const MINIMUM_AGE = 18;
export const MAX_PHOTOS_PER_KIND = 1;
export const MAX_IMAGE_BYTES = 8 * 1024 * 1024;

/** A profile only enters the swipe deck once it has at least one human photo and one pet photo. */
export function isProfileComplete(photoKinds: PhotoKind[]): boolean {
  return photoKinds.includes("human") && photoKinds.includes("pet");
}

/** Mirrors the DB trigger: a match forms only when both sides have liked each other. */
export function wouldFormMatch(
  existingLikes: Array<{ swiper_id: string; swiped_id: string }>,
  newLike: { swiper_id: string; swiped_id: string }
): boolean {
  return existingLikes.some(
    (like) => like.swiper_id === newLike.swiped_id && like.swiped_id === newLike.swiper_id
  );
}


const BLOCKED_NAME_WORDS = new Set([
  "test", "testing", "admin", "administrator", "user", "qwerty", "asdf", "zxcv", "xxx", "abc",
  "unknown", "fake", "none", "noname", "anonymous", "anon",
  "טסט", "בדיקה", "משתמש", "אדמין", "פלוני", "אלמוני", "שם"
]);

/**
 * Heuristic real-name validation. It cannot verify legal identity, but it rejects
 * punctuation, digits, emoji and common junk/gibberish patterns.
 */
export function isPlausibleRealName(input: string): boolean {
  const name = input.trim();
  if (name.length < NAME_MIN_LENGTH || name.length > NAME_MAX_LENGTH) return false;
  const scriptPatterns = [
    /^[A-Za-z]{2,}(?: [A-Za-z]{2,}){0,2}$/,
    /^[א-ת]{2,}(?: [א-ת]{2,}){0,2}$/,
    /^[А-Яа-яЁё]{2,}(?: [А-Яа-яЁё]{2,}){0,2}$/,
    /^[ء-ي]{2,}(?: [ء-ي]{2,}){0,2}$/,
  ];
  if (!scriptPatterns.some((pattern) => pattern.test(name))) return false;

  const words = name.toLocaleLowerCase().split(" ");
  if (words.some((word) => BLOCKED_NAME_WORDS.has(word))) return false;
  if (/(.)\1\1/iu.test(name.replace(/ /g, ""))) return false;
  if (words.some((word) => /^(.{1,2})\1{2,}$/iu.test(word))) return false;

  return true;
}

export function sanitizePersonNameInput(input: string): string {
  return input
    .replace(/[^A-Za-zא-תА-Яа-яЁёء-ي ]/g, "")
    .replace(/\s{2,}/g, " ")
    .slice(0, NAME_MAX_LENGTH);
}

export function sanitizeSearchText(input: string): string {
  return input
    .replace(/[^\p{L}\p{N}\s'".,-]/gu, "")
    .trim()
    .slice(0, SEARCH_MAX_LENGTH);
}


export function base64DecodedByteLength(base64: string): number {
  const clean = base64.replace(/\s/g, "");
  if (!clean) return 0;
  const padding = clean.endsWith("==") ? 2 : clean.endsWith("=") ? 1 : 0;
  return Math.floor((clean.length * 3) / 4) - padding;
}

export function isWithinLength(input: string, maxLength: number): boolean {
  return input.trim().length > 0 && input.length <= maxLength;
}

export function isValidIsoDate(input: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(input);
  if (!match) return false;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));

  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

export function isAtLeastAge(input: string, age: number, now = new Date()): boolean {
  if (!isValidIsoDate(input)) return false;

  const [year, month, day] = input.split("-").map(Number);
  let currentAge = now.getUTCFullYear() - year;
  const currentMonth = now.getUTCMonth() + 1;
  const currentDay = now.getUTCDate();

  if (currentMonth < month || (currentMonth === month && currentDay < day)) {
    currentAge -= 1;
  }

  return currentAge >= age;
}

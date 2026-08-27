import type { PhotoKind } from "./types";

export const BIO_MAX_LENGTH = 500;
export const NAME_MAX_LENGTH = 60;
export const MESSAGE_MAX_LENGTH = 1000;
export const SEARCH_MAX_LENGTH = 60;

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

/**
 * Search input only ever needs letters (any script), digits, spaces and a small set of
 * punctuation. Anything else is stripped before the value reaches a query, closing off
 * markup/script injection attempts riding in through a search or filter box.
 */
export function sanitizeSearchText(input: string): string {
  return input
    .replace(/[^\p{L}\p{N}\s'".,-]/gu, "")
    .trim()
    .slice(0, SEARCH_MAX_LENGTH);
}

export function isWithinLength(input: string, maxLength: number): boolean {
  return input.trim().length > 0 && input.length <= maxLength;
}

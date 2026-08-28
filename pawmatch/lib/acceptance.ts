import { MINIMUM_AGE, isAtLeastAge } from './logic';
import type { PhotoKind, SwipeDirection } from './types';

export interface AcceptanceUser {
  id: string;
  name: string;
  birthdate: string | null;
  petName: string;
  petType: string;
  photos: PhotoKind[];
}

export interface AcceptanceSwipe {
  swiperId: string;
  swipedId: string;
  direction: SwipeDirection;
}

export function isEligiblePetOwner(user: AcceptanceUser, now: Date): boolean {
  return Boolean(
    user.name.trim() &&
      user.birthdate &&
      isAtLeastAge(user.birthdate, MINIMUM_AGE, now) &&
      user.petName.trim() &&
      user.petType.trim() &&
      user.photos.includes('human') &&
      user.photos.includes('pet')
  );
}

export function canSwipe(swiper: AcceptanceUser, target: AcceptanceUser, now: Date): boolean {
  return swiper.id !== target.id && isEligiblePetOwner(swiper, now) && isEligiblePetOwner(target, now);
}

export function createsMatch(existing: AcceptanceSwipe[], incoming: AcceptanceSwipe): boolean {
  if (incoming.direction !== 'like') return false;
  return existing.some(
    (swipe) =>
      swipe.direction === 'like' &&
      swipe.swiperId === incoming.swipedId &&
      swipe.swipedId === incoming.swiperId
  );
}

export function canSendMessage(userId: string, matchUsers: [string, string], content: string): boolean {
  return matchUsers.includes(userId) && content.trim().length > 0 && content.length <= 1000;
}

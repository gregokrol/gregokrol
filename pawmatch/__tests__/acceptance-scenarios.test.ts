import { canSendMessage, canSwipe, createsMatch, isEligiblePetOwner, type AcceptanceUser } from '@/lib/acceptance';

const now = new Date(Date.UTC(2026, 7, 27));

function user(overrides: Partial<AcceptanceUser> = {}): AcceptanceUser {
  return {
    id: 'adult-dog-owner',
    name: 'מאיה',
    birthdate: '1995-04-12',
    petName: 'לואי',
    petType: 'כלב',
    photos: ['human', 'pet'],
    ...overrides,
  };
}

describe('PawMatch acceptance personas', () => {
  test.each([
    ['adult dog owner', user()],
    ['adult cat owner', user({ id: 'cat-owner', petName: 'מיקה', petType: 'חתול' })],
    ['adult other-pet owner', user({ id: 'rabbit-owner', petName: 'באני', petType: 'ארנב' })],
    ['exactly 18 today', user({ id: 'just-18', birthdate: '2008-08-27' })],
  ])('%s is eligible for discovery', (_label, persona) => {
    expect(isEligiblePetOwner(persona, now)).toBe(true);
  });

  test.each([
    ['under 18', user({ id: 'minor', birthdate: '2008-08-28' })],
    ['no birthdate', user({ id: 'no-birthdate', birthdate: null })],
    ['no name', user({ id: 'no-name', name: '   ' })],
    ['no pet name', user({ id: 'no-pet-name', petName: '' })],
    ['no pet type', user({ id: 'no-pet-type', petType: '' })],
    ['no human photo', user({ id: 'no-human', photos: ['pet'] })],
    ['no pet photo / person without pet evidence', user({ id: 'no-pet-photo', photos: ['human'] })],
    ['no photos at all', user({ id: 'no-photos', photos: [] })],
  ])('%s is rejected from discovery', (_label, persona) => {
    expect(isEligiblePetOwner(persona, now)).toBe(false);
  });
});

describe('swipe and matching acceptance', () => {
  const a = user({ id: 'a' });
  const b = user({ id: 'b', name: 'יואב', petName: 'הארי' });
  const incomplete = user({ id: 'incomplete', petName: '', photos: ['human'] });

  it('allows eligible pet owners to swipe each other', () => {
    expect(canSwipe(a, b, now)).toBe(true);
  });

  it('rejects self swipe', () => {
    expect(canSwipe(a, a, now)).toBe(false);
  });

  it('rejects a swipe from or toward an incomplete/non-pet profile', () => {
    expect(canSwipe(incomplete, b, now)).toBe(false);
    expect(canSwipe(a, incomplete, now)).toBe(false);
  });

  it('does not create a match from one like', () => {
    expect(createsMatch([], { swiperId: 'a', swipedId: 'b', direction: 'like' })).toBe(false);
  });

  it('does not create a match from a pass', () => {
    expect(
      createsMatch([{ swiperId: 'b', swipedId: 'a', direction: 'like' }], {
        swiperId: 'a', swipedId: 'b', direction: 'pass',
      })
    ).toBe(false);
  });

  it('creates a match only after reciprocal likes', () => {
    expect(
      createsMatch([{ swiperId: 'b', swipedId: 'a', direction: 'like' }], {
        swiperId: 'a', swipedId: 'b', direction: 'like',
      })
    ).toBe(true);
  });
});

describe('chat acceptance', () => {
  const participants: [string, string] = ['a', 'b'];

  it('lets both match participants send a normal message', () => {
    expect(canSendMessage('a', participants, 'היי!')).toBe(true);
    expect(canSendMessage('b', participants, 'שלום :)')).toBe(true);
  });

  it('rejects outsiders', () => {
    expect(canSendMessage('outsider', participants, 'היי')).toBe(false);
  });

  it('rejects empty and whitespace-only messages', () => {
    expect(canSendMessage('a', participants, '')).toBe(false);
    expect(canSendMessage('a', participants, '   ')).toBe(false);
  });

  it('rejects messages above the 1000 character limit', () => {
    expect(canSendMessage('a', participants, 'a'.repeat(1001))).toBe(false);
  });
});

# PawMatch QA Results — 2026-08-27

## Executed in this build

- 30/30 executable acceptance-logic scenarios passed.
- 14/14 Pressable UI controls have an action handler.
- 23/23 UI/DB/storage contract checks passed.
- TypeScript/TSX syntax transpilation check passed.

## Positive personas covered

- Adult dog owner.
- Adult cat owner.
- Adult rabbit/other-pet owner.
- User who turns 18 exactly today.

## Negative personas / actions covered

- Under 18.
- Missing birthdate.
- Missing display name.
- Missing pet name.
- Missing pet type.
- Missing human photo.
- Missing pet photo / no pet evidence.
- No photos.
- Self swipe.
- Incomplete profile tries to swipe.
- Swipe toward incomplete profile.
- One-sided Like does not create a match.
- Pass does not create a match.
- Reciprocal Likes create a match.
- Non-participant tries to send a chat message.
- Blank/whitespace chat message.
- Message above 1000 characters.
- Oversized image above 8MB.
- Duplicate photo kind is rejected by the DB in the current MVP.
- Duplicate swipe pair is rejected by the DB.

## Bugs found and fixed during this QA pass

1. Profile-photo upload path did not match the Storage RLS / DB path contract. Fixed to `<kind>/<user-id>/<filename>`.
2. Chat list used `inverted` with ascending data, which could reverse message order. Restored chronological display with newest messages at the bottom.
3. The declared 8MB image limit was not enforced. It is now checked before upload.
4. Discovery completeness now requires pet name and pet type in addition to adult age + human photo + pet photo.
5. The DB now blocks incomplete users from swiping or being targeted by a swipe.
6. The DB now rejects whitespace-only messages.

## Important live-environment limitation

This environment does not contain real `EXPO_PUBLIC_SUPABASE_URL` / `EXPO_PUBLIC_SUPABASE_ANON_KEY` credentials, and dependency installation timed out. Therefore a physical-device / emulator test against a real Supabase project was not executed here.

Before production release, run the included migrations through `0004_acceptance_hardening.sql`, install dependencies, then execute `npm test`, `npm run typecheck`, `npm run lint`, and a two-device live flow: sign-up -> profile -> photos -> swipe -> reciprocal match -> realtime chat.

## Real-name validation update

- 25/25 dedicated name-validation cases passed.
- Accepts plausible names written consistently in Hebrew, Latin, Cyrillic or Arabic letters.
- Rejects digits, punctuation, emoji, one-letter tokens, more than three name words, mixed writing systems, repeated-character junk, and common placeholder/gibberish values such as test/admin/qwerty/בדיקה/פלוני.
- The profile UI filters unsupported characters while typing and validates again before save.
- Migration `0005_real_name_validation.sql` adds the same protection at the database boundary and prevents an invalid-name profile from becoming complete.
- This is format/plausibility validation; legal identity cannot be guaranteed without a separate identity-verification process.

# PawMatch Acceptance Test Matrix

## Profiles / discovery

| Scenario | Expected |
|---|---|
| Adult dog owner, all required fields/photos | Appears in discovery |
| Adult cat owner, all required fields/photos | Appears in discovery |
| Adult other-pet owner, all required fields/photos | Appears in discovery |
| Turns 18 today | Appears in discovery |
| Under 18 | Blocked |
| Missing birthdate | Blocked |
| Missing name | Blocked |
| Missing pet name | Blocked |
| Missing pet type | Blocked |
| Missing human photo | Blocked |
| Missing pet photo / no pet evidence | Blocked |
| No photos | Blocked |

## Swipe / match

| Scenario | Expected |
|---|---|
| Two eligible users | Swipe allowed |
| Self swipe | Blocked |
| Incomplete user tries to swipe | Blocked by DB policy |
| Swipe toward incomplete user | Blocked by DB policy |
| One-sided Like | No match |
| Pass | No match |
| Reciprocal Like | One match |
| Second swipe for same pair from same user | Rejected by unique constraint |

## Chat

| Scenario | Expected |
|---|---|
| Participant A sends message | Allowed |
| Participant B sends message | Allowed |
| Non-participant sends message | Blocked by RLS |
| Empty/whitespace message | Blocked |
| >1000 characters | Blocked |
| Message ordering | Oldest at top, newest at bottom |

## Storage

| Scenario | Expected |
|---|---|
| Upload path | `<kind>/<user-id>/<filename>` |
| Upload into another user's folder | Blocked by Storage RLS |
| Profile photos | Private bucket |
| Duplicate photo of same kind in MVP | Blocked |
| Delete own photo | Allowed |

## Name-integrity cases

| Case | Expected |
|---|---|
| דניאל כהן / Daniel Cohen | Accepted |
| Cyrillic or Arabic real-looking name | Accepted |
| Name with digits | Rejected |
| Name with punctuation or emoji | Rejected |
| qwerty / test / admin / בדיקה / פלוני | Rejected |
| Triple repeated letters such as aaa / xxx | Rejected |
| Mixed scripts such as דניאל Cohen | Rejected |
| More than 3 name words | Rejected |
| One-letter word/token | Rejected |

# PawMatch

אפליקציית היכרויות בין **בני אדם בעלי חיית מחמד**. כדי להופיע בגילוי המשתמש חייב להיות בן 18+, למלא שם, ולהעלות לפחות תמונה אחת שלו ותמונה אחת של חיית המחמד. מעבר לכך זו חוויית Match/Chat בסיסית ל-MVP.

> השם PawMatch נמנע משימוש בשם המסחרי "Tinder".


## iPhone demo (Expo Go)

This project now targets **Expo SDK 54** so it can run in the current App Store version of Expo Go on a physical iPhone without an Apple Developer membership. See `DEMO_IOS_FREE.md` for the exact steps.

## סטאק

- **Frontend**: Expo + Expo Router + TypeScript — קודבייס אחד ל-iOS, Android ו-Web.
- **Backend**: Supabase — Postgres + Auth + Storage + Realtime.

## הרצה מקומית

1. התקנת תלויות:
   ```bash
   npm install
   ```
2. הגדרת Supabase:
   - ליצור פרויקט Supabase.
   - להריץ את כל הקבצים שב-`supabase/migrations/` **לפי הסדר**, כולל `0003_hardening.sql`.
   - להעתיק `.env.example` ל-`.env` ולמלא:
     - `EXPO_PUBLIC_SUPABASE_URL`
     - `EXPO_PUBLIC_SUPABASE_ANON_KEY`
3. בדיקות:
   ```bash
   npm run lint
   npm run typecheck
   npm test
   ```
4. הרצה:
   ```bash
   npm run web
   npm run ios
   npm run android
   ```

## תיקוני יציבות ואבטחה שנכללים בגרסה הזו

- פרופיל draft נוצר אוטומטית עם הרשמה, כך שאפשר להעלות תמונות בלי שגיאת foreign-key.
- `is_complete` מחושב בצד השרת ואי אפשר לסמן פרופיל כמלא ידנית מהלקוח.
- גיל מינימום 18 נבדק גם ב-UI וגם בחישוב השלמת הפרופיל ב-DB.
- תמונות הפרופיל נשמרות ב-bucket פרטי ומוצגות דרך signed URLs זמניים.
- מחיקת תמונה מנקה גם את רשומת ה-DB וגם את קובץ ה-Storage.
- העלאה שנכשלת אחרי יצירת הקובץ מבצעת cleanup כדי למנוע קבצים יתומים.
- ה-MVP שומר תמונה אחת לאדם ותמונה אחת לחיית המחמד, עד 8MB לכל תמונה.
- החיפוש לפי סוג חיה משתמש עכשיו בערך העדכני שהמשתמש הזין.
- הצ'אט ממזג הודעות לפי ID כדי למנוע כפילויות/אובדן הודעה במרוץ בין SELECT ל-Realtime, וטוען את 100 ההודעות האחרונות במקום היסטוריה בלתי מוגבלת.
- Realtime לטבלת `messages` מופעל במיגרציה אם publication קיים.
- RLS לא חושף יותר פרופילי draft, ותאריך הלידה המדויק נשאר זמין רק לבעל הפרופיל.
- נוספו indexes למסלולי השאילתות העיקריים.

## מודל אימות חיית מחמד

כרגע עצם העלאת תמונה מסוג `pet` היא תנאי הסף. **אין עדיין אימות AI** שהתמונה באמת מכילה חיית מחמד או שהיא שייכת למשתמש. לפני השקה מסחרית צריך להוסיף moderation/verification אמיתי.

## תשלום עתידי

הטבלאות `plans`, `user_subscriptions` ו-`coupons` הן scaffolding בלבד. אין עדיין שער סליקה או UI לרכישה.

## בדיקות ידניות מומלצות לפני הפצה

- [ ] הרשמה → אימות מייל (אם מופעל) → התחברות.
- [ ] משתמש חדש יכול להעלות תמונה לפני/אחרי שמירת הפרטים בלי שגיאת FK.
- [ ] משתמש מתחת לגיל 18 לא הופך ל-`is_complete`.
- [ ] משתמש 18+ עם שם + תמונת אדם + תמונת חיה כן הופך ל-`is_complete`.
- [ ] תמונה לא נפתחת דרך ה-public URL הישן, אבל מוצגת באפליקציה דרך signed URL.
- [ ] מחיקת תמונה מסירה אותה גם מה-DB וגם מ-Storage.
- [ ] סינון לפי סוג חיה באמת משנה את התוצאות.
- [ ] Like הדדי יוצר match אחד בלבד.
- [ ] צ'אט Realtime עובד בין שני משתמשים בלי הודעות כפולות.
- [ ] לא ניתן לשלוח הודעה ל-match שהמשתמש אינו משתתף בו.
- [ ] `npm run lint`, `npm run typecheck`, `npm test` עוברים בסביבה עם `node_modules` מותקן.

## הערת בדיקה בסביבה שבה הקוד תוקן

בוצעו בדיקות syntax לכל קבצי TypeScript/TSX ובדיקות smoke ללוגיקה הטהורה. התקנת `node_modules` דרך npm לא הושלמה בסביבת העבודה, ולכן לא בוצע כאן build מלא של Expo או חיבור אמיתי לפרויקט Supabase. לפני Production חובה לבצע את שלושת פקודות הבדיקה לעיל ובדיקת end-to-end עם שני משתמשים.

## Acceptance QA / latest hardening

Apply all Supabase migrations in order, including:

- `0003_hardening.sql`
- `0004_acceptance_hardening.sql`

The latest acceptance matrix and executed QA results are in `qa/`.
The current eligibility rule is: 18+, name, pet name, pet type, one human photo, and one pet photo.


## Latest migration
Run all migrations through `0005_real_name_validation.sql`. This adds plausible real-name enforcement in the database.

## תיקון נוסף שבוצע לפני המעבר לרפו הזה

`0005_real_name_validation.sql` הוסיפה CHECK constraint שדורש שם "אמיתי" בכל שורה בטבלת `profiles` — אבל `0003_hardening.sql` יוצרת פרופיל draft עם `name = ''` בכל הרשמה חדשה (כדי לאפשר להעלות תמונות לפני מילוי הטופס). שילוב שתי המיגרציות כלשונן היה שובר **כל** הרשמה חדשה: ה-trigger שיוצר את הפרופיל היה נכשל על ה-constraint, וה-INSERT ל-`auth.users` היה מתבטל כולו.

התיקון: ה-constraint עודכן ל-`check (btrim(name) = '' or public.is_plausible_person_name(name))` — כך שמצב ה-draft הריק עדיין מותר, אבל `enforce_profile_completeness()` ממשיכה לדרוש שם אמיתי לפני שהפרופיל יכול להיחשב `is_complete`. שום התנהגות אחרת לא השתנתה.

זה נמצא בסקירת קוד ידנית (קריאת כל קובצי המיגרציה וה-`app/`/`lib/`/`components/`), לא בהרצה בפועל — עדיין לא בוצע `npm install` מול registry אמיתי בסביבה הזו, אז חובה להריץ את `npm run lint` / `npm run typecheck` / `npm test` ולבדוק הרשמה אמיתית מקצה לקצה מול פרויקט Supabase אמיתי לפני כל דמו או שחרור.

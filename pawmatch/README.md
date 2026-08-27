# PawMatch

אפליקציית היכרויות בין **בני אדם** — תנאי הסף לכניסה הוא שיש למשתמש חיית מחמד, ולכן בנוסף לתמונת הפרופיל יש להעלות גם תמונה מאומתת של החיה. מעבר לכך זו חוויית Swipe/Match/Chat רגילה.

> למה "PawMatch" ולא "PetTinder"? כי "Tinder" הוא סימן מסחר רשום, ושימוש בו בשם אפליקציה חושף לסיכון משפטי אם הפרויקט יתפרסם.

## סטאק

- **Frontend**: [Expo](https://expo.dev) + Expo Router + TypeScript — קודבייס אחד שרץ על iOS, Android ו-Web.
- **Backend**: [Supabase](https://supabase.com) — Postgres + Auth + Storage + Realtime. אין שרת custom נפרד; ה-app מדבר ישירות מול Supabase.

## הרצה מקומית

> ⚠️ **הערה חשובה**: הקוד נכתב ונבדק ידנית (סקירת קוד + סימולציית לוגיקה טהורה) בסביבה שבה אין גישת רשת החוצה ל-npm registry, ולכן `npm install` וההרצה בפועל (`expo start`) לא בוצעו בסביבה שבה נכתב הקוד. יש להריץ את כל השלבים הבאים לפני שסומכים על כך שהאפליקציה עולה כמו שצריך.

1. **התקנת תלויות**:
   ```bash
   npm install
   ```
2. **הגדרת Supabase**:
   - ליצור פרויקט חדש ב-[supabase.com](https://supabase.com).
   - להריץ את קבצי ה-SQL שב-`supabase/migrations/` לפי הסדר (דרך ה-SQL editor בדשבורד, או `supabase db push` אם עובדים עם ה-CLI).
   - להעתיק `.env.example` ל-`.env` ולמלא את `EXPO_PUBLIC_SUPABASE_URL` ו-`EXPO_PUBLIC_SUPABASE_ANON_KEY` מתוך Project Settings → API.
   - לוודא ב-Authentication settings שאימות מייל (Confirm email) מופעל או מבוטל לפי הצורך לבדיקות.
3. **בדיקות איכות (יש להריץ ולוודא שעוברות לפני כל push):**
   ```bash
   npm run lint
   npm run typecheck
   npm test
   ```
4. **הרצה**:
   ```bash
   npm run web      # דפדפן
   npm run ios      # סימולטור iOS
   npm run android  # אמולטור Android
   ```

## מבנה הפרויקט

```
app/            מסכי Expo Router
  (auth)/       הרשמה / התחברות
  (tabs)/       גילוי (swipe), התאמות, פרופיל
  chat/         צ'אט per-match
components/     SwipeCard, PhotoUploader, MessageBubble
lib/            supabase client, auth context, טיפוסים, לוגיקה טהורה (logic.ts)
supabase/migrations/   סכימת ה-DB, RLS, וה-trigger שיוצר match בלייק הדדי
__tests__/      טסטים יחידה ללוגיקה הטהורה
```

## מודל האימות (verification)

פרופיל מסומן `is_complete` (ומופיע במסך הגילוי) רק לאחר שהועלו **גם** תמונה אנושית **וגם** תמונת חיית מחמד. זהו trigger ב-Postgres (`recompute_profile_completeness`) שרץ בכל שינוי בתמונות — אין כרגע בדיקת AI שמאמתת שהתמונה אכן מציגה חיה; זו החלטת scope מכוונת ל-MVP.

## תשלום עתידי

האפליקציה חינמית כרגע. הוכנו מראש טבלאות `plans`, `user_subscriptions` ו-`coupons` כדי שאפשר יהיה להפעיל מודל תשלום ולתת הנחות (קופון) בעתיד בלי שינוי סכימה — אין עדיין שער סליקה מחובר ואין UI לרכישה עצמית.

## אבטחת קלט

- כל שאילתה מול Supabase עוברת דרך ה-query builder הפרמטרי של `supabase-js` — אין SQL גולמי הבנוי מקלט משתמש.
- שדה החיפוש/הסינון (סינון לפי סוג חיה במסך הגילוי) עובר `sanitizeSearchText` (ב-`lib/logic.ts`) שמשאיר רק אותיות, ספרות, רווחים ופיסוק בסיסי, ומגביל אורך — כך שלא ניתן להזריק תגי HTML/JS או תחביר שאילתה דרכו.
- שדות טקסט חופשי (שם, ביו, הודעות צ'אט) מוגבלים גם ב-UI (`maxLength`) וגם ב-DB (`check` constraints).

## רשימת בדיקות ידניות (בנוסף לטסטים האוטומטיים)

- [ ] הרשמה + התחברות + התנתקות עובדות.
- [ ] לא ניתן לשמור/להיכנס למסך הגילוי בלי להעלות גם תמונה אנושית וגם תמונת חיה.
- [ ] סוויפ כפול על אותו פרופיל לא יוצר שגיאה (unique constraint על `swipes`).
- [ ] סוויפ הדדי (like/like) יוצר שורה ב-`matches` ומאפשר גישה לצ'אט.
- [ ] לא ניתן לשלוח הודעה לפני שיש match (RLS על `messages`).
- [ ] הזנת `<script>...</script>` או `'; DROP TABLE...` בשדה הסינון/ביו לא גורמת לשגיאה או להתנהגות לא צפויה.
- [ ] בדיקת שני משתמשים אמיתיים מקצה לקצה: הרשמה → פרופיל מלא → סוויפ הדדי → צ'אט.

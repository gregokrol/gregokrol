import { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/lib/AuthProvider';
import { supabase } from '@/lib/supabase';
import {
  BIO_MAX_LENGTH,
  MINIMUM_AGE,
  NAME_MAX_LENGTH,
  isPlausibleRealName,
  sanitizePersonNameInput,
  isAtLeastAge,
  isValidIsoDate,
  isWithinLength,
} from '@/lib/logic';
import { withSignedPhotoUrls } from '@/lib/photos';
import type { ProfilePhoto } from '@/lib/types';
import { PhotoUploader } from '@/components/PhotoUploader';
import { Pill } from '@/components/Pill';
import { colors, radii, shadows, spacing } from '@/lib/theme';

export default function ProfileScreen() {
  const { session, profile, refreshProfile } = useAuth();
  const userId = session?.user.id;

  const [name, setName] = useState(profile?.name ?? '');
  const [birthdate, setBirthdate] = useState(profile?.birthdate ?? '');
  const [bio, setBio] = useState(profile?.bio ?? '');
  const [petName, setPetName] = useState(profile?.pet_name ?? '');
  const [petType, setPetType] = useState(profile?.pet_type ?? '');
  const [photos, setPhotos] = useState<ProfilePhoto[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setName(profile?.name ?? '');
    setBirthdate(profile?.birthdate ?? '');
    setBio(profile?.bio ?? '');
    setPetName(profile?.pet_name ?? '');
    setPetType(profile?.pet_type ?? '');
  }, [profile]);

  useEffect(() => {
    if (userId) void loadPhotos(userId);
  }, [userId]);

  async function loadPhotos(id: string) {
    const { data, error } = await supabase
      .from('profile_photos')
      .select('*')
      .eq('profile_id', id)
      .order('position', { ascending: true });

    if (error) {
      Alert.alert('שגיאה בטעינת התמונות', error.message);
      return;
    }

    setPhotos(await withSignedPhotoUrls(data ?? []));
  }

  async function handlePhotosChanged() {
    if (!userId) return;
    await Promise.all([loadPhotos(userId), refreshProfile()]);
  }

  async function handleSave() {
    if (!userId) return;
    const cleanName = name.trim();
    const cleanBirthdate = birthdate.trim();

    if (!isPlausibleRealName(cleanName)) {
      Alert.alert('שם לא תקין', 'יש להזין שם אמיתי באותיות בלבד, ללא מספרים, סימני פיסוק, אימוג׳י או טקסט אקראי.');
      return;
    }
    if (!isValidIsoDate(cleanBirthdate)) {
      Alert.alert('תאריך לידה לא תקין', 'יש להזין תאריך בפורמט YYYY-MM-DD.');
      return;
    }
    if (!isAtLeastAge(cleanBirthdate, MINIMUM_AGE)) {
      Alert.alert('הגבלת גיל', `PawMatch מיועדת לבני ${MINIMUM_AGE} ומעלה בלבד.`);
      return;
    }
    if (bio.length > BIO_MAX_LENGTH) {
      Alert.alert('ביו ארוך מדי', `עד ${BIO_MAX_LENGTH} תווים.`);
      return;
    }
    if (!isWithinLength(petName.trim(), NAME_MAX_LENGTH)) {
      Alert.alert('חסרים פרטי חיית המחמד', 'יש להזין את שם חיית המחמד.');
      return;
    }
    if (!isWithinLength(petType.trim(), NAME_MAX_LENGTH)) {
      Alert.alert('חסר סוג חיית המחמד', 'יש להזין סוג חיית מחמד, למשל כלב או חתול.');
      return;
    }

    setSaving(true);
    const { error } = await supabase.from('profiles').upsert({
      id: userId,
      name: cleanName,
      birthdate: cleanBirthdate,
      bio: bio.trim(),
      pet_name: petName.trim(),
      pet_type: petType.trim(),
    });
    setSaving(false);

    if (error) {
      Alert.alert('השמירה נכשלה', error.message);
      return;
    }
    await refreshProfile();
    Alert.alert('נשמר בהצלחה');
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
  }

  if (!userId) return null;

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <View style={styles.hero}>
        <Pill text={profile?.is_complete ? 'הפרופיל שלך מוכן לגילוי' : 'יש להשלים פרופיל כדי להופיע בגילוי'} tone={profile?.is_complete ? 'secondary' : 'primary'} />
        <Text style={styles.title}>הפרופיל שלך</Text>
        <Text style={styles.subtitle}>המטרה כאן פשוטה: לגרום לאחרים להבין מהר מי אתה, מה סוג החיה שלך, ולמה שווה לעשות לך Match.</Text>
      </View>

      {!profile?.is_complete && (
        <View style={styles.banner}>
          <Text style={styles.bannerTitle}>לפני שמופיעים בגילוי</Text>
          <Text style={styles.bannerText}>צריך שם, גיל 18+, תמונה שלך ותמונה של חיית המחמד שלך.</Text>
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>פרטים אישיים</Text>
        <TextInput
          style={styles.input}
          placeholder="שם אמיתי בלבד"
          placeholderTextColor={colors.textMuted}
          value={name}
          onChangeText={(value) => setName(sanitizePersonNameInput(value))}
          autoCapitalize="words"
          autoCorrect={false}
          maxLength={NAME_MAX_LENGTH}
        />
        <Text style={styles.fieldHint}>אותיות בלבד · בלי מספרים, סימנים, אימוג׳י או שמות אקראיים</Text>
        <TextInput
          style={styles.input}
          placeholder="תאריך לידה YYYY-MM-DD"
          placeholderTextColor={colors.textMuted}
          value={birthdate}
          onChangeText={setBirthdate}
          keyboardType="numbers-and-punctuation"
          maxLength={10}
        />
        <TextInput
          style={[styles.input, styles.multiline]}
          placeholder="כמה מילים עליך ועל מה שאתה מחפש"
          placeholderTextColor={colors.textMuted}
          value={bio}
          onChangeText={setBio}
          multiline
          maxLength={BIO_MAX_LENGTH}
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>חיית המחמד</Text>
        <TextInput style={styles.input} placeholder="שם חיית המחמד" placeholderTextColor={colors.textMuted} value={petName} onChangeText={setPetName} maxLength={NAME_MAX_LENGTH} />
        <TextInput
          style={styles.input}
          placeholder="סוג חיית המחמד (כלב, חתול...)"
          placeholderTextColor={colors.textMuted}
          value={petType}
          onChangeText={setPetType}
          maxLength={NAME_MAX_LENGTH}
        />
      </View>

      <Pressable style={styles.button} onPress={handleSave} disabled={saving}>
        <Text style={styles.buttonText}>{saving ? 'שומר...' : 'שמירת פרטים'}</Text>
      </Pressable>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>תמונות</Text>
        <PhotoUploader kind="human" label="התמונה שלי" profileId={userId} photos={photos} onChanged={handlePhotosChanged} />
        <PhotoUploader kind="pet" label="תמונת חיית המחמד שלי" profileId={userId} photos={photos} onChanged={handlePhotosChanged} />
      </View>

      <Pressable style={styles.signOutButton} onPress={handleSignOut}>
        <Text style={styles.signOutText}>התנתקות</Text>
      </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  container: { padding: spacing.md, gap: spacing.md, backgroundColor: colors.background },
  hero: { gap: 8 },
  title: { fontSize: 28, lineHeight: 34, fontWeight: '800', color: colors.text },
  subtitle: { fontSize: 15, lineHeight: 22, color: colors.textMuted },
  banner: { backgroundColor: colors.primarySoft, padding: spacing.md, borderRadius: radii.lg, borderWidth: 1, borderColor: '#FFD1C9' },
  bannerTitle: { color: colors.text, fontWeight: '800', marginBottom: 4 },
  bannerText: { color: colors.textMuted, lineHeight: 20 },
  section: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.md, gap: spacing.sm, borderWidth: 1, borderColor: colors.border, ...shadows.soft },
  sectionTitle: { fontSize: 18, fontWeight: '800', color: colors.text, marginBottom: 4 },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, padding: 12, fontSize: 16, backgroundColor: '#FFFDFC', color: colors.text },
  fieldHint: { fontSize: 12, color: colors.textMuted, marginTop: -4 },
  multiline: { minHeight: 96, textAlignVertical: 'top' },
  button: { backgroundColor: colors.primary, borderRadius: radii.md, padding: 15, alignItems: 'center', marginTop: 2 },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  signOutButton: { padding: 14, alignItems: 'center', marginBottom: 12 },
  signOutText: { color: colors.textMuted, fontWeight: '700' },
});

import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/lib/AuthProvider';
import { supabase } from '@/lib/supabase';
import { SEARCH_MAX_LENGTH, sanitizeSearchText } from '@/lib/logic';
import { withSignedPhotoUrls } from '@/lib/photos';
import type { ProfilePhoto, PublicProfile } from '@/lib/types';
import { SwipeCard } from '@/components/SwipeCard';
import { Pill } from '@/components/Pill';
import { colors, radii, shadows, spacing } from '@/lib/theme';

interface Candidate {
  profile: PublicProfile;
  photos: ProfilePhoto[];
}

export default function SwipeScreen() {
  const { session } = useAuth();
  const userId = session?.user.id;

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [petTypeQuery, setPetTypeQuery] = useState('');

  const loadCandidates = useCallback(
    async (rawPetType = '') => {
      if (!userId) return;
      setLoading(true);

      const safePetType = sanitizeSearchText(rawPetType);
      const { data, error } = await supabase.rpc('get_swipe_candidates', {
        p_pet_type: safePetType,
        p_limit: 20,
      });

      if (error) {
        Alert.alert('שגיאה בטעינת פרופילים', error.message);
        setLoading(false);
        return;
      }

      const profiles = (data ?? []) as PublicProfile[];
      if (profiles.length === 0) {
        setCandidates([]);
        setLoading(false);
        return;
      }

      const profileIds = profiles.map((profile) => profile.id);
      const { data: photoRows, error: photoError } = await supabase
        .from('profile_photos')
        .select('*')
        .in('profile_id', profileIds)
        .order('position', { ascending: true });

      if (photoError) {
        Alert.alert('שגיאה בטעינת תמונות', photoError.message);
        setLoading(false);
        return;
      }

      const signedPhotos = await withSignedPhotoUrls((photoRows ?? []) as ProfilePhoto[]);
      const photosByProfile = new Map<string, ProfilePhoto[]>();
      signedPhotos.forEach((photo) => {
        const current = photosByProfile.get(photo.profile_id) ?? [];
        current.push(photo);
        photosByProfile.set(photo.profile_id, current);
      });

      setCandidates(
        profiles.map((profile) => ({
          profile,
          photos: photosByProfile.get(profile.id) ?? [],
        }))
      );
      setLoading(false);
    },
    [userId]
  );

  useEffect(() => {
    void loadCandidates();
  }, [loadCandidates]);

  async function handleSwipe(direction: 'like' | 'pass') {
    if (!userId || candidates.length === 0 || acting) return;
    const current = candidates[0];
    setActing(true);

    const { error } = await supabase.from('swipes').insert({
      swiper_id: userId,
      swiped_id: current.profile.id,
      direction,
    });

    setActing(false);
    if (error) {
      Alert.alert('הפעולה נכשלה', error.message);
      return;
    }

    setCandidates((existing) => existing.filter((candidate) => candidate.profile.id !== current.profile.id));
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  const current = candidates[0];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.headerBlock}>
        <Pill text="גילוי לפי חיית המחמד ותחומי העניין" tone="secondary" />
        <Text style={styles.title}>גלה אנשים דרך החיה שמלווה אותם</Text>
        <Text style={styles.subtitle}>עושים סווייפ, יוצרים Match, ואז מתחילים שיחה.</Text>
      </View>

      <View style={styles.searchWrap}>
        <TextInput
          style={styles.search}
          placeholder="סינון לפי סוג חיה: כלב, חתול..."
          placeholderTextColor={colors.textMuted}
          value={petTypeQuery}
          onChangeText={setPetTypeQuery}
          onSubmitEditing={() => void loadCandidates(petTypeQuery)}
          returnKeyType="search"
          maxLength={SEARCH_MAX_LENGTH}
        />
        <Pressable style={styles.filterButton} onPress={() => void loadCandidates(petTypeQuery)}>
          <Text style={styles.filterButtonText}>סינון</Text>
        </Pressable>
      </View>

      {current ? (
        <>
          <SwipeCard profile={current.profile} photos={current.photos} />
          <View style={styles.actions}>
            <View style={styles.actionWrap}>
              <Pressable style={[styles.actionButton, styles.pass]} onPress={() => handleSwipe('pass')} disabled={acting}>
                <Text style={styles.actionIcon}>✕</Text>
              </Pressable>
              <Text style={styles.actionLabel}>לא בשבילי</Text>
            </View>
            <View style={styles.actionWrap}>
              <Pressable style={[styles.actionButton, styles.like]} onPress={() => handleSwipe('like')} disabled={acting}>
                <Text style={styles.actionIcon}>❤️</Text>
              </Pressable>
              <Text style={styles.actionLabel}>כן, מעניין</Text>
            </View>
          </View>
        </>
      ) : (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyTitle}>אין כרגע פרופילים חדשים</Text>
          <Text style={styles.emptyText}>או שאין התאמות במסנן הזה, או שכבר עברת על כולן.</Text>
          <Pressable style={styles.refreshButton} onPress={() => void loadCandidates(petTypeQuery)}>
            <Text style={styles.refreshText}>רענון</Text>
          </Pressable>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.md, gap: spacing.md, backgroundColor: colors.background },
  headerBlock: { gap: 8 },
  title: { fontSize: 28, lineHeight: 34, fontWeight: '800', color: colors.text, textAlign: 'right' },
  subtitle: { fontSize: 15, lineHeight: 22, color: colors.textMuted },
  searchWrap: { flexDirection: 'row-reverse', gap: 8 },
  search: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.pill,
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: colors.surface,
    color: colors.text,
  },
  filterButton: {
    backgroundColor: colors.secondary,
    borderRadius: radii.pill,
    paddingHorizontal: 18,
    alignItems: 'center',
    justifyContent: 'center',
    ...shadows.soft,
  },
  filterButtonText: { color: '#fff', fontWeight: '800' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12, backgroundColor: colors.background },
  actions: { flexDirection: 'row-reverse', justifyContent: 'space-evenly', paddingBottom: 4 },
  actionWrap: { alignItems: 'center', gap: 6 },
  actionButton: {
    width: 74,
    height: 74,
    borderRadius: 37,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    ...shadows.card,
  },
  pass: { backgroundColor: '#fff' },
  like: { backgroundColor: '#fff' },
  actionIcon: { fontSize: 28 },
  actionLabel: { fontSize: 13, color: colors.textMuted, fontWeight: '700' },
  emptyCard: {
    marginTop: spacing.lg,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.lg,
    padding: spacing.xl,
    alignItems: 'center',
    gap: spacing.sm,
    ...shadows.card,
  },
  emptyTitle: { fontSize: 22, fontWeight: '800', color: colors.text, textAlign: 'center' },
  emptyText: { fontSize: 15, lineHeight: 22, color: colors.textMuted, textAlign: 'center' },
  refreshButton: { marginTop: 6, backgroundColor: colors.primary, borderRadius: radii.md, paddingHorizontal: 24, paddingVertical: 12 },
  refreshText: { color: '#fff', fontWeight: '800' },
});

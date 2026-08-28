import { useCallback, useState } from 'react';
import { useFocusEffect, useRouter } from 'expo-router';
import { ActivityIndicator, Alert, FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/lib/AuthProvider';
import { supabase } from '@/lib/supabase';
import type { Match, PublicProfile } from '@/lib/types';
import { Pill } from '@/components/Pill';
import { colors, radii, shadows, spacing } from '@/lib/theme';

interface MatchRow {
  match: Match;
  otherProfile: PublicProfile;
}

export default function MatchesScreen() {
  const { session } = useAuth();
  const router = useRouter();
  const userId = session?.user.id;

  const [rows, setRows] = useState<MatchRow[]>([]);
  const [loading, setLoading] = useState(true);

  const loadMatches = useCallback(async () => {
    if (!userId) return;
    setLoading(true);

    const { data: matches, error } = await supabase
      .from('matches')
      .select('*')
      .or(`user_a.eq.${userId},user_b.eq.${userId}`)
      .order('created_at', { ascending: false });

    if (error) {
      Alert.alert('שגיאה בטעינת התאמות', error.message);
      setLoading(false);
      return;
    }

    if (!matches?.length) {
      setRows([]);
      setLoading(false);
      return;
    }

    const otherIds = matches.map((match) => (match.user_a === userId ? match.user_b : match.user_a));
    const { data: profiles, error: profilesError } = await supabase.from('visible_profiles').select('*').in('id', otherIds);

    if (profilesError) {
      Alert.alert('שגיאה בטעינת פרופילים', profilesError.message);
      setLoading(false);
      return;
    }

    const profileById = new Map((profiles ?? []).map((profile) => [profile.id, profile]));

    setRows(
      matches
        .map((match) => {
          const otherId = match.user_a === userId ? match.user_b : match.user_a;
          const otherProfile = profileById.get(otherId);
          return otherProfile ? { match, otherProfile } : null;
        })
        .filter((row): row is MatchRow => row !== null)
    );
    setLoading(false);
  }, [userId]);

  useFocusEffect(
    useCallback(() => {
      void loadMatches();
    }, [loadMatches])
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <FlatList
      contentContainerStyle={styles.list}
      data={rows}
      keyExtractor={(row) => row.match.id}
      ListHeaderComponent={
        <View style={styles.hero}>
          <Pill text="אחרי Match מתחילים לדבר" tone="primary" />
          <Text style={styles.title}>ההתאמות שלך</Text>
          <Text style={styles.subtitle}>כאן רואים מי התאים לך, ובלחיצה עוברים ישר לצ׳אט.</Text>
        </View>
      }
      ListEmptyComponent={
        <View style={styles.emptyCard}>
          <Text style={styles.emptyTitle}>אין עדיין התאמות</Text>
          <Text style={styles.emptyText}>זה אומר שצריך לחזור לגילוי ולעשות עוד כמה סווייפים טובים.</Text>
        </View>
      }
      renderItem={({ item, index }) => (
        <Pressable style={styles.row} onPress={() => router.push(`/chat/${item.match.id}`)}>
          <View style={[styles.avatar, index % 3 === 0 && styles.avatarPrimary, index % 3 === 1 && styles.avatarSecondary]}>
            <Text style={styles.avatarText}>{item.otherProfile.name.slice(0, 1)}</Text>
          </View>
          <View style={styles.rowBody}>
            <Text style={styles.name}>{item.otherProfile.name}</Text>
            <Text style={styles.pet}>🐾 {item.otherProfile.pet_name || 'חיית מחמד אהובה'}{item.otherProfile.pet_type ? ` · ${item.otherProfile.pet_type}` : ''}</Text>
          </View>
          <Text style={styles.chevron}>‹</Text>
        </Pressable>
      )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.background },
  list: { padding: spacing.md, gap: 10, flexGrow: 1, backgroundColor: colors.background },
  hero: { gap: 8, marginBottom: 8 },
  title: { fontSize: 28, lineHeight: 34, fontWeight: '800', color: colors.text },
  subtitle: { fontSize: 15, lineHeight: 22, color: colors.textMuted },
  row: {
    flexDirection: 'row-reverse',
    alignItems: 'center',
    gap: 14,
    padding: spacing.md,
    borderRadius: radii.lg,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    ...shadows.soft,
  },
  avatar: { width: 56, height: 56, borderRadius: 28, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  avatarPrimary: { backgroundColor: colors.primarySoft },
  avatarSecondary: { backgroundColor: colors.secondarySoft },
  avatarText: { fontSize: 22, fontWeight: '800', color: colors.text },
  rowBody: { flex: 1, gap: 4 },
  name: { fontSize: 18, fontWeight: '800', color: colors.text },
  pet: { fontSize: 14, color: colors.textMuted },
  chevron: { fontSize: 28, color: colors.textMuted },
  emptyCard: { marginTop: 32, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radii.lg, padding: spacing.xl, alignItems: 'center', gap: spacing.sm },
  emptyTitle: { fontSize: 22, fontWeight: '800', color: colors.text },
  emptyText: { textAlign: 'center', color: colors.textMuted, lineHeight: 22 },
});

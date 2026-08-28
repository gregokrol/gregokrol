import { Image, StyleSheet, Text, View } from 'react-native';
import type { ProfilePhoto, PublicProfile } from '@/lib/types';
import { colors, radii, shadows, spacing } from '@/lib/theme';

interface SwipeCardProps {
  profile: PublicProfile;
  photos: ProfilePhoto[];
}

export function SwipeCard({ profile, photos }: SwipeCardProps) {
  const humanPhoto = photos.find((photo) => photo.kind === 'human');
  const petPhoto = photos.find((photo) => photo.kind === 'pet');
  const chips = [profile.pet_type ? `🐾 ${profile.pet_type}` : null, profile.pet_name ? `❤️ ${profile.pet_name}` : null]
    .filter(Boolean)
    .slice(0, 2) as string[];

  return (
    <View style={styles.card}>
      {humanPhoto ? (
        <Image source={{ uri: humanPhoto.display_url ?? humanPhoto.url }} style={styles.mainPhoto} />
      ) : (
        <View style={[styles.mainPhoto, styles.placeholder]}>
          <Text style={styles.placeholderEmoji}>📷</Text>
          <Text style={styles.placeholderText}>עדיין אין תמונה</Text>
        </View>
      )}

      {petPhoto ? <Image source={{ uri: petPhoto.display_url ?? petPhoto.url }} style={styles.petBadge} /> : null}

      <View style={styles.overlay}>
        <View style={styles.infoBox}>
          <Text style={styles.name}>{profile.name}</Text>
          {!!chips.length && (
            <View style={styles.chipsRow}>
              {chips.map((chip) => (
                <View key={chip} style={styles.chip}>
                  <Text style={styles.chipText}>{chip}</Text>
                </View>
              ))}
            </View>
          )}
          {profile.bio ? <Text style={styles.bio}>{profile.bio}</Text> : <Text style={styles.bio}>מחפש/ת התאמה דרך אהבה אמיתית לחיות מחמד.</Text>}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minHeight: 460,
    borderRadius: radii.xl,
    overflow: 'hidden',
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    ...shadows.card,
  },
  mainPhoto: { width: '100%', height: '100%', backgroundColor: '#eee' },
  placeholder: { alignItems: 'center', justifyContent: 'center', gap: 10 },
  placeholderEmoji: { fontSize: 42 },
  placeholderText: { fontSize: 16, color: colors.textMuted, fontWeight: '600' },
  overlay: { position: 'absolute', left: 0, right: 0, bottom: 0, padding: spacing.md },
  infoBox: { backgroundColor: 'rgba(25,34,55,0.74)', borderRadius: radii.lg, padding: spacing.md, gap: 8 },
  petBadge: {
    position: 'absolute',
    top: 14,
    right: 14,
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 3,
    borderColor: '#fff',
  },
  name: { fontSize: 28, fontWeight: '800', color: '#fff' },
  chipsRow: { flexDirection: 'row-reverse', flexWrap: 'wrap', gap: 8 },
  chip: { backgroundColor: 'rgba(255,255,255,0.18)', borderRadius: radii.pill, paddingHorizontal: 10, paddingVertical: 7 },
  chipText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  bio: { fontSize: 14, lineHeight: 20, color: 'rgba(255,255,255,0.92)' },
});

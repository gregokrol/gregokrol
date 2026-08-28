import { Redirect, useRouter } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/lib/AuthProvider';
import { AppLogo } from '@/components/AppLogo';
import { Pill } from '@/components/Pill';
import { colors, radii, shadows, spacing } from '@/lib/theme';

function StepCard({ emoji, title, text }: { emoji: string; title: string; text: string }) {
  return (
    <View style={styles.stepCard}>
      <Text style={styles.stepEmoji}>{emoji}</Text>
      <Text style={styles.stepTitle}>{title}</Text>
      <Text style={styles.stepText}>{text}</Text>
    </View>
  );
}

export default function WelcomeScreen() {
  const router = useRouter();
  const { session } = useAuth();

  if (session) {
    return <Redirect href="/" />;
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
      <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.heroCard}>
        <Pill text="מכירים אנשים דרך חיות המחמד" tone="secondary" />
        <AppLogo large />
        <Text style={styles.heroTitle}>היכרויות לאנשים שאוהבים חיות באמת</Text>
        <Text style={styles.heroSubtitle}>
          PawMatch מחברת בין אנשים דרך הכלב, החתול ושאר החברים על ארבע. יוצרים פרופיל, עושים סווייפ, ואם יש התאמה — מתחילים לדבר.
        </Text>

        <View style={styles.previewRow}>
          <View style={[styles.previewChip, styles.previewChipPrimary]}><Text style={styles.previewChipText}>🐾 פרופיל לך ולחיה</Text></View>
          <View style={[styles.previewChip, styles.previewChipSecondary]}><Text style={styles.previewChipText}>❤️ התאמות חכמות</Text></View>
          <View style={[styles.previewChip, styles.previewChipNeutral]}><Text style={styles.previewChipText}>💬 צ׳אט אחרי Match</Text></View>
        </View>

        <Pressable style={styles.primaryButton} onPress={() => router.push('/(auth)/sign-up')}>
          <Text style={styles.primaryButtonText}>התחל/י עכשיו</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => router.push('/(auth)/sign-in')}>
          <Text style={styles.secondaryButtonText}>כבר יש חשבון? להתחברות</Text>
        </Pressable>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>איך זה עובד</Text>
        <View style={styles.stepsGrid}>
          <StepCard emoji="📸" title="יוצרים פרופיל" text="מעלים תמונה שלך ותמונה של חיית המחמד, כדי שיהיה ברור מי אתם." />
          <StepCard emoji="🔎" title="מגלים אנשים" text="עוברים על פרופילים לפי אהבה לחיות, סוג חיה ותחומי עניין." />
          <StepCard emoji="🎉" title="יש Match" text="כששני הצדדים בעניין, נוצרת התאמה אמיתית ולא סתם לייק חד צדדי." />
          <StepCard emoji="💬" title="מתחילים לדבר" text="אחרי Match נפתח צ׳אט, ומשם אפשר להכיר ולצאת לטיול עם החברים על ארבע." />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>למה זה ברור יותר טוב מאפליקציית דייטים רגילה</Text>
        <View style={styles.bulletCard}>
          <Text style={styles.bullet}>• כבר מהמסך הראשון ברור שזו מערכת היכרויות סביב חיות מחמד.</Text>
          <Text style={styles.bullet}>• החיה היא לא “תוספת”, אלא חלק מרכזי מההתאמה.</Text>
          <Text style={styles.bullet}>• הזרימה פשוטה: פרופיל → גילוי → Match → שיחה.</Text>
        </View>
      </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  container: { padding: spacing.md, gap: spacing.md, backgroundColor: colors.background },
  heroCard: {
    backgroundColor: colors.surface,
    borderRadius: radii.xl,
    padding: spacing.xl,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.md,
    ...shadows.card,
  },
  heroTitle: { fontSize: 34, lineHeight: 40, fontWeight: '800', color: colors.text, textAlign: 'center' },
  heroSubtitle: { fontSize: 16, lineHeight: 24, color: colors.textMuted, textAlign: 'center' },
  previewRow: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 8 },
  previewChip: { borderRadius: radii.pill, paddingHorizontal: 12, paddingVertical: 9 },
  previewChipPrimary: { backgroundColor: colors.primarySoft },
  previewChipSecondary: { backgroundColor: colors.secondarySoft },
  previewChipNeutral: { backgroundColor: '#F4F6FA' },
  previewChipText: { color: colors.text, fontWeight: '700', fontSize: 13 },
  primaryButton: { backgroundColor: colors.primary, borderRadius: radii.md, paddingVertical: 15, alignItems: 'center' },
  primaryButtonText: { color: '#fff', fontSize: 17, fontWeight: '800' },
  secondaryButton: { backgroundColor: colors.surface, borderRadius: radii.md, paddingVertical: 14, alignItems: 'center', borderWidth: 1.5, borderColor: colors.secondary },
  secondaryButtonText: { color: colors.secondary, fontSize: 16, fontWeight: '800' },
  section: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.md,
    ...shadows.soft,
  },
  sectionTitle: { fontSize: 24, fontWeight: '800', color: colors.text, textAlign: 'center' },
  stepsGrid: { gap: 10 },
  stepCard: { backgroundColor: '#FFFDFC', borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, padding: spacing.md, gap: 6 },
  stepEmoji: { fontSize: 26, textAlign: 'center' },
  stepTitle: { fontSize: 18, fontWeight: '800', color: colors.text, textAlign: 'center' },
  stepText: { fontSize: 14, lineHeight: 21, color: colors.textMuted, textAlign: 'center' },
  bulletCard: { gap: 10, backgroundColor: '#FFFDFC', borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, padding: spacing.md },
  bullet: { fontSize: 15, lineHeight: 22, color: colors.text },
});

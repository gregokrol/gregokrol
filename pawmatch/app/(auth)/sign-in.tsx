import { useState } from 'react';
import { Link } from 'expo-router';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { supabase } from '@/lib/supabase';
import { AppLogo } from '@/components/AppLogo';
import { Pill } from '@/components/Pill';
import { colors, radii, shadows, spacing } from '@/lib/theme';

export default function SignIn() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSignIn() {
    setError(null);
    setSubmitting(true);
    const { error: signInError } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
    setSubmitting(false);
    if (signInError) {
      setError(signInError.message);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
      <KeyboardAvoidingView style={styles.screen} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.hero}>
          <Pill text="היכרויות דרך חיות המחמד" tone="secondary" />
          <AppLogo large />
          <Text style={styles.title}>מכירים אנשים דרך הכלב, החתול ושאר החברים על ארבע</Text>
          <Text style={styles.subtitle}>
            יוצרים פרופיל, עושים סווייפ להתאמות, ומתחילים שיחה רק עם אנשים שגם אוהבים חיות.
          </Text>
          <View style={styles.benefitsRow}>
            <View style={styles.benefitChip}><Text style={styles.benefitText}>🐾 פרופילי חיות</Text></View>
            <View style={styles.benefitChip}><Text style={styles.benefitText}>💬 צ׳אט אחרי Match</Text></View>
            <View style={styles.benefitChip}><Text style={styles.benefitText}>❤️ תחומי עניין משותפים</Text></View>
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>התחברות</Text>
          <Text style={styles.cardSubtitle}>נכנסים וממשיכים לגלות אנשים שמתאימים לך ולחיית המחמד שלך.</Text>

          <TextInput
            style={styles.input}
            placeholder="אימייל"
            placeholderTextColor={colors.textMuted}
            autoCapitalize="none"
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
          />
          <TextInput
            style={styles.input}
            placeholder="סיסמה"
            placeholderTextColor={colors.textMuted}
            secureTextEntry
            value={password}
            onChangeText={setPassword}
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Pressable style={styles.button} onPress={handleSignIn} disabled={submitting}>
            <Text style={styles.buttonText}>{submitting ? 'מתחבר...' : 'התחבר/י'}</Text>
          </Pressable>

          <Link href="/(auth)/sign-up" style={styles.link}>
            אין לך חשבון? להרשמה
          </Link>
        </View>
      </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  screen: { flex: 1, backgroundColor: colors.background },
  container: { flexGrow: 1, padding: spacing.xl, justifyContent: 'center', gap: spacing.lg },
  hero: { gap: spacing.md, marginTop: spacing.lg },
  title: { fontSize: 32, lineHeight: 40, fontWeight: '800', color: colors.text, textAlign: 'center' },
  subtitle: { fontSize: 16, lineHeight: 24, color: colors.textMuted, textAlign: 'center' },
  benefitsRow: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 8 },
  benefitChip: { backgroundColor: colors.surface, borderRadius: radii.pill, paddingHorizontal: 12, paddingVertical: 8, borderWidth: 1, borderColor: colors.border },
  benefitText: { color: colors.text, fontWeight: '600', fontSize: 13 },
  card: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.xl, gap: spacing.md, borderWidth: 1, borderColor: colors.border, ...shadows.card },
  cardTitle: { fontSize: 24, fontWeight: '800', color: colors.text, textAlign: 'center' },
  cardSubtitle: { fontSize: 14, color: colors.textMuted, textAlign: 'center', lineHeight: 21 },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, padding: 14, fontSize: 16, color: colors.text, backgroundColor: '#FFFDFC' },
  button: { backgroundColor: colors.primary, borderRadius: radii.md, paddingVertical: 15, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  error: { color: colors.danger, textAlign: 'center', lineHeight: 20 },
  link: { textAlign: 'center', color: colors.secondary, fontWeight: '700', marginTop: 4 },
});

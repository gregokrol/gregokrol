import { useState } from 'react';
import { Link } from 'expo-router';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { supabase } from '@/lib/supabase';
import { AppLogo } from '@/components/AppLogo';
import { Pill } from '@/components/Pill';
import { colors, radii, shadows, spacing } from '@/lib/theme';

export default function SignUp() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [confirmationSent, setConfirmationSent] = useState(false);

  async function handleSignUp() {
    setError(null);
    setSubmitting(true);
    const { error: signUpError } = await supabase.auth.signUp({ email: email.trim(), password });
    setSubmitting(false);
    if (signUpError) {
      setError(signUpError.message);
      return;
    }
    setConfirmationSent(true);
  }

  if (confirmationSent) {
    return (
      <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
        <View style={styles.doneScreen}>
        <View style={styles.doneCard}>
          <AppLogo />
          <Text style={styles.doneTitle}>כמעט סיימת</Text>
          <Text style={styles.doneText}>שלחנו מייל לאימות החשבון. אחרי האימות אפשר להתחבר, להשלים פרופיל ולהתחיל לעשות Match.</Text>
          <Link href="/(auth)/sign-in" style={styles.link}>
            חזרה להתחברות
          </Link>
        </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
      <KeyboardAvoidingView style={styles.screen} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.hero}>
          <Pill text="מתחילים עם פרופיל אמיתי לך ולחיית המחמד" tone="primary" />
          <AppLogo large />
          <Text style={styles.title}>הרשמה מהירה, ואז משלימים פרופיל ומתחילים להכיר</Text>
          <Text style={styles.subtitle}>תמונה שלך, תמונה של חיית המחמד, כמה פרטים בסיסיים — וזהו. משם האפליקציה כבר ברורה ועובדת כמו שצריך.</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>פתיחת חשבון</Text>
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
            placeholder="סיסמה (לפחות 6 תווים)"
            placeholderTextColor={colors.textMuted}
            secureTextEntry
            value={password}
            onChangeText={setPassword}
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Pressable style={styles.button} onPress={handleSignUp} disabled={submitting}>
            <Text style={styles.buttonText}>{submitting ? 'נרשם...' : 'הרשמה'}</Text>
          </Pressable>

          <Link href="/(auth)/sign-in" style={styles.link}>
            כבר יש לך חשבון? להתחברות
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
  title: { fontSize: 30, lineHeight: 38, fontWeight: '800', color: colors.text, textAlign: 'center' },
  subtitle: { fontSize: 16, lineHeight: 24, color: colors.textMuted, textAlign: 'center' },
  card: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.xl, gap: spacing.md, borderWidth: 1, borderColor: colors.border, ...shadows.card },
  cardTitle: { fontSize: 24, fontWeight: '800', color: colors.text, textAlign: 'center' },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, padding: 14, fontSize: 16, color: colors.text, backgroundColor: '#FFFDFC' },
  button: { backgroundColor: colors.primary, borderRadius: radii.md, paddingVertical: 15, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  error: { color: colors.danger, textAlign: 'center', lineHeight: 20 },
  link: { textAlign: 'center', color: colors.secondary, fontWeight: '700' },
  doneScreen: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl, backgroundColor: colors.background },
  doneCard: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.xl, gap: spacing.md, borderWidth: 1, borderColor: colors.border, ...shadows.card },
  doneTitle: { fontSize: 26, fontWeight: '800', color: colors.text, textAlign: 'center' },
  doneText: { fontSize: 16, lineHeight: 24, textAlign: 'center', color: colors.textMuted },
});

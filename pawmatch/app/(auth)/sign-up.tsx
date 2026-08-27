import { useState } from "react";
import { Link } from "expo-router";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { supabase } from "@/lib/supabase";

export default function SignUp() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [confirmationSent, setConfirmationSent] = useState(false);

  async function handleSignUp() {
    setError(null);
    setSubmitting(true);
    const { error: signUpError } = await supabase.auth.signUp({ email, password });
    setSubmitting(false);
    if (signUpError) {
      setError(signUpError.message);
      return;
    }
    setConfirmationSent(true);
  }

  if (confirmationSent) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>כמעט שם!</Text>
        <Text style={styles.subtitle}>שלחנו לך מייל לאימות החשבון. לאחר האימות תוכל/י להתחבר.</Text>
        <Link href="/(auth)/sign-in" style={styles.link}>
          חזרה להתחברות
        </Link>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>PawMatch</Text>
      <Text style={styles.subtitle}>הרשמה</Text>

      <TextInput
        style={styles.input}
        placeholder="אימייל"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="סיסמה (לפחות 6 תווים)"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Pressable style={styles.button} onPress={handleSignUp} disabled={submitting}>
        <Text style={styles.buttonText}>{submitting ? "נרשם..." : "הרשמה"}</Text>
      </Pressable>

      <Link href="/(auth)/sign-in" style={styles.link}>
        כבר יש לך חשבון? התחברות
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24, gap: 12 },
  title: { fontSize: 32, fontWeight: "700", textAlign: "center" },
  subtitle: { fontSize: 18, textAlign: "center", marginBottom: 12, color: "#666" },
  input: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 12, fontSize: 16 },
  button: { backgroundColor: "#ff5864", borderRadius: 8, padding: 14, alignItems: "center" },
  buttonText: { color: "#fff", fontWeight: "600", fontSize: 16 },
  error: { color: "red", textAlign: "center" },
  link: { textAlign: "center", color: "#ff5864", marginTop: 8 },
});

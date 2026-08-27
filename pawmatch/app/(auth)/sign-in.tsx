import { useState } from "react";
import { Link } from "expo-router";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { supabase } from "@/lib/supabase";

export default function SignIn() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSignIn() {
    setError(null);
    setSubmitting(true);
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
    setSubmitting(false);
    if (signInError) {
      setError(signInError.message);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>PawMatch</Text>
      <Text style={styles.subtitle}>התחברות</Text>

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
        placeholder="סיסמה"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Pressable style={styles.button} onPress={handleSignIn} disabled={submitting}>
        <Text style={styles.buttonText}>{submitting ? "מתחבר..." : "התחבר"}</Text>
      </Pressable>

      <Link href="/(auth)/sign-up" style={styles.link}>
        אין לך חשבון? הרשמה
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

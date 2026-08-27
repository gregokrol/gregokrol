import { useEffect, useState } from "react";
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { useAuth } from "@/lib/AuthProvider";
import { supabase } from "@/lib/supabase";
import { BIO_MAX_LENGTH, NAME_MAX_LENGTH, isWithinLength } from "@/lib/logic";
import type { ProfilePhoto } from "@/lib/types";
import { PhotoUploader } from "@/components/PhotoUploader";

export default function ProfileScreen() {
  const { session, profile, refreshProfile } = useAuth();
  const userId = session?.user.id;

  const [name, setName] = useState(profile?.name ?? "");
  const [bio, setBio] = useState(profile?.bio ?? "");
  const [petName, setPetName] = useState(profile?.pet_name ?? "");
  const [petType, setPetType] = useState(profile?.pet_type ?? "");
  const [photos, setPhotos] = useState<ProfilePhoto[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setName(profile?.name ?? "");
    setBio(profile?.bio ?? "");
    setPetName(profile?.pet_name ?? "");
    setPetType(profile?.pet_type ?? "");
  }, [profile]);

  useEffect(() => {
    if (userId) loadPhotos(userId);
  }, [userId]);

  async function loadPhotos(id: string) {
    const { data } = await supabase
      .from("profile_photos")
      .select("*")
      .eq("profile_id", id)
      .order("position", { ascending: true });
    setPhotos(data ?? []);
  }

  async function handleSave() {
    if (!userId) return;
    if (!isWithinLength(name, NAME_MAX_LENGTH)) {
      Alert.alert("שם לא תקין", `השם חייב להיות בין 1 ל-${NAME_MAX_LENGTH} תווים.`);
      return;
    }
    if (bio.length > BIO_MAX_LENGTH) {
      Alert.alert("ביו ארוך מדי", `עד ${BIO_MAX_LENGTH} תווים.`);
      return;
    }

    setSaving(true);
    const { error } = await supabase.from("profiles").upsert({
      id: userId,
      name,
      bio,
      pet_name: petName,
      pet_type: petType,
    });
    setSaving(false);

    if (error) {
      Alert.alert("השמירה נכשלה", error.message);
      return;
    }
    await refreshProfile();
    Alert.alert("נשמר בהצלחה");
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
  }

  if (!userId) return null;

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {!profile?.is_complete && (
        <View style={styles.banner}>
          <Text style={styles.bannerText}>
            כדי להופיע במסך ההיכרויות צריך להעלות לפחות תמונה אחת שלך ותמונה אחת של חיית המחמד שלך.
          </Text>
        </View>
      )}

      <PhotoUploader
        kind="human"
        label="התמונה שלי"
        profileId={userId}
        photos={photos}
        onChanged={() => loadPhotos(userId)}
      />
      <PhotoUploader
        kind="pet"
        label="תמונת חיית המחמד שלי"
        profileId={userId}
        photos={photos}
        onChanged={() => loadPhotos(userId)}
      />

      <TextInput style={styles.input} placeholder="שם" value={name} onChangeText={setName} maxLength={NAME_MAX_LENGTH} />
      <TextInput
        style={[styles.input, styles.multiline]}
        placeholder="קצת עליי..."
        value={bio}
        onChangeText={setBio}
        multiline
        maxLength={BIO_MAX_LENGTH}
      />
      <TextInput style={styles.input} placeholder="שם חיית המחמד" value={petName} onChangeText={setPetName} maxLength={NAME_MAX_LENGTH} />
      <TextInput style={styles.input} placeholder="סוג חיית המחמד (כלב, חתול...)" value={petType} onChangeText={setPetType} maxLength={NAME_MAX_LENGTH} />

      <Pressable style={styles.button} onPress={handleSave} disabled={saving}>
        <Text style={styles.buttonText}>{saving ? "שומר..." : "שמירה"}</Text>
      </Pressable>

      <Pressable style={styles.signOutButton} onPress={handleSignOut}>
        <Text style={styles.signOutText}>התנתקות</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  banner: { backgroundColor: "#fff3cd", padding: 12, borderRadius: 8, marginBottom: 8 },
  bannerText: { color: "#856404" },
  input: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 12, fontSize: 16 },
  multiline: { minHeight: 80, textAlignVertical: "top" },
  button: { backgroundColor: "#ff5864", borderRadius: 8, padding: 14, alignItems: "center", marginTop: 8 },
  buttonText: { color: "#fff", fontWeight: "600", fontSize: 16 },
  signOutButton: { padding: 14, alignItems: "center" },
  signOutText: { color: "#999" },
});

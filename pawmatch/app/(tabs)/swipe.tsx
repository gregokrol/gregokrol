import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { useAuth } from "@/lib/AuthProvider";
import { supabase } from "@/lib/supabase";
import { SEARCH_MAX_LENGTH, sanitizeSearchText } from "@/lib/logic";
import type { Profile, ProfilePhoto } from "@/lib/types";
import { SwipeCard } from "@/components/SwipeCard";

interface Candidate {
  profile: Profile;
  photos: ProfilePhoto[];
}

export default function SwipeScreen() {
  const { session } = useAuth();
  const userId = session?.user.id;

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [petTypeQuery, setPetTypeQuery] = useState("");

  const loadCandidates = useCallback(async () => {
    if (!userId) return;
    setLoading(true);

    const { data: swiped } = await supabase.from("swipes").select("swiped_id").eq("swiper_id", userId);
    const swipedIds = (swiped ?? []).map((row) => row.swiped_id);
    const excludedIds = [userId, ...swipedIds];

    // Sanitized before it ever reaches the query: strips anything but letters/digits/
    // spaces/basic punctuation, so a search box can't be used to smuggle markup or
    // query syntax into the system (defense in depth on top of supabase-js's
    // already-parameterized query builder).
    const safePetType = sanitizeSearchText(petTypeQuery);

    let query = supabase
      .from("profiles")
      .select("*, profile_photos(*)")
      .eq("is_complete", true)
      .not("id", "in", `(${excludedIds.join(",")})`)
      .limit(20);

    if (safePetType) {
      query = query.ilike("pet_type", `%${safePetType}%`);
    }

    const { data, error } = await query;

    if (error) {
      Alert.alert("שגיאה בטעינת פרופילים", error.message);
      setLoading(false);
      return;
    }

    const nextCandidates: Candidate[] = (data ?? []).map((row) => {
      const { profile_photos, ...profile } = row as Profile & { profile_photos: ProfilePhoto[] };
      return { profile, photos: profile_photos };
    });

    setCandidates(nextCandidates);
    setLoading(false);
  }, [userId]);

  useEffect(() => {
    loadCandidates();
  }, [loadCandidates]);

  async function handleSwipe(direction: "like" | "pass") {
    if (!userId || candidates.length === 0 || acting) return;
    const [current, ...rest] = candidates;
    setActing(true);

    const { error } = await supabase.from("swipes").insert({
      swiper_id: userId,
      swiped_id: current.profile.id,
      direction,
    });

    setActing(false);
    if (error) {
      Alert.alert("הפעולה נכשלה", error.message);
      return;
    }

    setCandidates(rest);
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
      </View>
    );
  }

  const current = candidates[0];

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.search}
        placeholder="סינון לפי סוג חיה (כלב, חתול...)"
        value={petTypeQuery}
        onChangeText={(text) => setPetTypeQuery(text)}
        onSubmitEditing={loadCandidates}
        maxLength={SEARCH_MAX_LENGTH}
      />
      {current ? (
        <>
          <SwipeCard profile={current.profile} photos={current.photos} />
          <View style={styles.actions}>
            <Pressable style={[styles.actionButton, styles.pass]} onPress={() => handleSwipe("pass")} disabled={acting}>
              <Text style={styles.actionText}>✖</Text>
            </Pressable>
            <Pressable style={[styles.actionButton, styles.like]} onPress={() => handleSwipe("like")} disabled={acting}>
              <Text style={styles.actionText}>❤</Text>
            </Pressable>
          </View>
        </>
      ) : (
        <View style={styles.center}>
          <Text style={styles.emptyText}>אין כרגע פרופילים חדשים. נסה שוב מאוחר יותר!</Text>
          <Pressable style={styles.refreshButton} onPress={loadCandidates}>
            <Text style={styles.refreshText}>רענון</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, gap: 16 },
  search: { borderWidth: 1, borderColor: "#ccc", borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12 },
  actions: { flexDirection: "row", justifyContent: "center", gap: 24 },
  actionButton: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 3,
  },
  pass: { backgroundColor: "#fff" },
  like: { backgroundColor: "#fff" },
  actionText: { fontSize: 28 },
  emptyText: { fontSize: 16, color: "#666", textAlign: "center" },
  refreshButton: { padding: 12 },
  refreshText: { color: "#ff5864", fontWeight: "600" },
});

import { useCallback, useEffect, useState } from "react";
import { useFocusEffect, useRouter } from "expo-router";
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import { useAuth } from "@/lib/AuthProvider";
import { supabase } from "@/lib/supabase";
import type { Match, Profile } from "@/lib/types";

interface MatchRow {
  match: Match;
  otherProfile: Profile;
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
      .from("matches")
      .select("*")
      .or(`user_a.eq.${userId},user_b.eq.${userId}`)
      .order("created_at", { ascending: false });

    if (error || !matches) {
      setLoading(false);
      return;
    }

    const otherIds = matches.map((match) => (match.user_a === userId ? match.user_b : match.user_a));
    const { data: profiles } = await supabase.from("profiles").select("*").in("id", otherIds);
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
      loadMatches();
    }, [loadMatches])
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <FlatList
      contentContainerStyle={styles.list}
      data={rows}
      keyExtractor={(row) => row.match.id}
      ListEmptyComponent={<Text style={styles.emptyText}>אין עדיין התאמות. המשיכו לגלות!</Text>}
      renderItem={({ item }) => (
        <Pressable style={styles.row} onPress={() => router.push(`/chat/${item.match.id}`)}>
          <Text style={styles.name}>{item.otherProfile.name}</Text>
          <Text style={styles.pet}>🐾 {item.otherProfile.pet_name}</Text>
        </Pressable>
      )}
    />
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  list: { padding: 16, gap: 8 },
  row: { padding: 16, borderRadius: 12, backgroundColor: "#f5f5f5" },
  name: { fontSize: 18, fontWeight: "600" },
  pet: { fontSize: 14, color: "#666", marginTop: 2 },
  emptyText: { textAlign: "center", color: "#666", marginTop: 40 },
});

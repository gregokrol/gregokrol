import { useEffect, useRef, useState } from "react";
import { useLocalSearchParams } from "expo-router";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useAuth } from "@/lib/AuthProvider";
import { supabase } from "@/lib/supabase";
import { MESSAGE_MAX_LENGTH, isWithinLength } from "@/lib/logic";
import type { Message } from "@/lib/types";
import { MessageBubble } from "@/components/MessageBubble";

export default function ChatScreen() {
  const { matchId } = useLocalSearchParams<{ matchId: string }>();
  const { session } = useAuth();
  const userId = session?.user.id;

  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const listRef = useRef<FlatList>(null);

  useEffect(() => {
    if (!matchId) return;

    supabase
      .from("messages")
      .select("*")
      .eq("match_id", matchId)
      .order("created_at", { ascending: true })
      .then(({ data }) => {
        setMessages(data ?? []);
        setLoading(false);
      });

    const channel = supabase
      .channel(`messages:${matchId}`)
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "messages", filter: `match_id=eq.${matchId}` },
        (payload) => {
          setMessages((current) => [...current, payload.new as Message]);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [matchId]);

  async function handleSend() {
    if (!userId || !matchId || sending) return;
    const content = draft.trim();
    if (!isWithinLength(content, MESSAGE_MAX_LENGTH)) return;

    setSending(true);
    const { error } = await supabase.from("messages").insert({
      match_id: matchId,
      sender_id: userId,
      content,
    });
    setSending(false);

    if (!error) {
      setDraft("");
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(message) => message.id}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => <MessageBubble message={item} isOwn={item.sender_id === userId} />}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
      />
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={draft}
          onChangeText={setDraft}
          placeholder="הודעה..."
          maxLength={MESSAGE_MAX_LENGTH}
          multiline
        />
        <Pressable style={styles.sendButton} onPress={handleSend} disabled={sending || draft.trim().length === 0}>
          <Text style={styles.sendText}>שליחה</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  list: { padding: 16 },
  inputRow: { flexDirection: "row", padding: 12, gap: 8, borderTopWidth: 1, borderTopColor: "#eee" },
  input: { flex: 1, borderWidth: 1, borderColor: "#ccc", borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, maxHeight: 100 },
  sendButton: { justifyContent: "center", paddingHorizontal: 16 },
  sendText: { color: "#ff5864", fontWeight: "600" },
});

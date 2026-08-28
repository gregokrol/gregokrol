import { useEffect, useRef, useState } from 'react';
import { useLocalSearchParams } from 'expo-router';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/lib/AuthProvider';
import { supabase } from '@/lib/supabase';
import { MESSAGE_MAX_LENGTH, isWithinLength } from '@/lib/logic';
import type { Message } from '@/lib/types';
import { MessageBubble } from '@/components/MessageBubble';
import { colors, radii, spacing } from '@/lib/theme';

function mergeMessages(...groups: Message[][]): Message[] {
  const byId = new Map<string, Message>();
  groups.flat().forEach((message) => byId.set(message.id, message));
  return Array.from(byId.values()).sort((a, b) => {
    const timeDiff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    return timeDiff !== 0 ? timeDiff : a.id.localeCompare(b.id);
  });
}

export default function ChatScreen() {
  const { matchId } = useLocalSearchParams<{ matchId: string }>();
  const { session } = useAuth();
  const userId = session?.user.id;

  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const listRef = useRef<FlatList<Message>>(null);

  useEffect(() => {
    if (!matchId) return;
    let active = true;
    setLoading(true);
    setMessages([]);

    const channel = supabase
      .channel(`messages:${matchId}`)
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'messages', filter: `match_id=eq.${matchId}` },
        (payload) => {
          if (!active) return;
          setMessages((current) => mergeMessages(current, [payload.new as Message]));
        }
      )
      .subscribe();

    void supabase
      .from('messages')
      .select('*')
      .eq('match_id', matchId)
      .order('created_at', { ascending: false })
      .limit(100)
      .then(({ data, error }) => {
        if (!active) return;
        if (error) {
          Alert.alert('שגיאה בטעינת הצ׳אט', error.message);
        } else {
          setMessages((current) => mergeMessages(data ?? [], current));
        }
        setLoading(false);
      });

    return () => {
      active = false;
      void supabase.removeChannel(channel);
    };
  }, [matchId]);

  async function handleSend() {
    if (!userId || !matchId || sending) return;
    const content = draft.trim();
    if (!isWithinLength(content, MESSAGE_MAX_LENGTH)) return;

    setSending(true);
    const { error } = await supabase.from('messages').insert({
      match_id: matchId,
      sender_id: userId,
      content,
    });
    setSending(false);

    if (error) {
      Alert.alert('שליחת ההודעה נכשלה', error.message);
      return;
    }

    setDraft('');
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['bottom']}>
      <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 80 : 0}
    >
      <View style={styles.topHint}>
        <Text style={styles.topHintText}>אחרי Match מתחילים שיחה פשוטה, בלי בלגן.</Text>
      </View>
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(message) => message.id}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => <MessageBubble message={item} isOwn={item.sender_id === userId} />}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
        keyboardShouldPersistTaps="handled"
      />
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={draft}
          onChangeText={setDraft}
          placeholder="הודעה..."
          placeholderTextColor={colors.textMuted}
          maxLength={MESSAGE_MAX_LENGTH}
          multiline
        />
        <Pressable style={[styles.sendButton, (sending || draft.trim().length === 0) && styles.sendButtonDisabled]} onPress={handleSend} disabled={sending || draft.trim().length === 0}>
          <Text style={styles.sendText}>{sending ? '...' : 'שליחה'}</Text>
        </Pressable>
      </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  container: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.background },
  topHint: { paddingHorizontal: spacing.md, paddingTop: spacing.sm },
  topHintText: { color: colors.textMuted, fontSize: 13, textAlign: 'center' },
  list: { padding: spacing.md, flexGrow: 1, justifyContent: 'flex-end' },
  inputRow: {
    flexDirection: 'row-reverse',
    padding: spacing.md,
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.surface,
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.pill,
    paddingHorizontal: 16,
    paddingVertical: 12,
    maxHeight: 110,
    backgroundColor: '#FFFDFC',
    color: colors.text,
  },
  sendButton: { justifyContent: 'center', paddingHorizontal: 18, backgroundColor: colors.primary, borderRadius: radii.pill },
  sendButtonDisabled: { opacity: 0.55 },
  sendText: { color: '#fff', fontWeight: '800' },
});

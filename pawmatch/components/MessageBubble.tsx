import { StyleSheet, Text, View } from 'react-native';
import type { Message } from '@/lib/types';
import { colors, radii } from '@/lib/theme';

interface MessageBubbleProps {
  message: Message;
  isOwn: boolean;
}

export function MessageBubble({ message, isOwn }: MessageBubbleProps) {
  return (
    <View style={[styles.row, isOwn ? styles.ownRow : styles.otherRow]}>
      <View style={[styles.bubble, isOwn ? styles.ownBubble : styles.otherBubble]}>
        <Text style={isOwn ? styles.ownText : styles.otherText}>{message.content}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', marginVertical: 5 },
  ownRow: { justifyContent: 'flex-end' },
  otherRow: { justifyContent: 'flex-start' },
  bubble: { maxWidth: '78%', paddingVertical: 10, paddingHorizontal: 14, borderRadius: 18 },
  ownBubble: { backgroundColor: colors.primary },
  otherBubble: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  ownText: { color: '#fff', lineHeight: 20 },
  otherText: { color: colors.text, lineHeight: 20 },
});

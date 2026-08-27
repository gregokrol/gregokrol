import { StyleSheet, Text, View } from "react-native";
import type { Message } from "@/lib/types";

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
  row: { flexDirection: "row", marginVertical: 4 },
  ownRow: { justifyContent: "flex-end" },
  otherRow: { justifyContent: "flex-start" },
  bubble: { maxWidth: "75%", paddingVertical: 8, paddingHorizontal: 12, borderRadius: 16 },
  ownBubble: { backgroundColor: "#ff5864" },
  otherBubble: { backgroundColor: "#f0f0f0" },
  ownText: { color: "#fff" },
  otherText: { color: "#000" },
});

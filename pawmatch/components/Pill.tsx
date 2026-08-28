import { StyleSheet, Text, View } from 'react-native';
import { colors, radii } from '@/lib/theme';

export function Pill({ text, tone = 'secondary' }: { text: string; tone?: 'secondary' | 'primary' | 'neutral' }) {
  return (
    <View
      style={[
        styles.pill,
        tone === 'secondary' && styles.secondary,
        tone === 'primary' && styles.primary,
        tone === 'neutral' && styles.neutral,
      ]}
    >
      <Text
        style={[
          styles.text,
          tone === 'secondary' && styles.secondaryText,
          tone === 'primary' && styles.primaryText,
          tone === 'neutral' && styles.neutralText,
        ]}
      >
        {text}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: radii.pill, alignSelf: 'flex-start' },
  text: { fontSize: 13, fontWeight: '600' },
  secondary: { backgroundColor: colors.secondarySoft },
  primary: { backgroundColor: colors.primarySoft },
  neutral: { backgroundColor: '#F3F5F8' },
  secondaryText: { color: colors.secondary },
  primaryText: { color: colors.primary },
  neutralText: { color: colors.textMuted },
});

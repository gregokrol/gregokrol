import { Image, StyleSheet, Text, View } from 'react-native';
import { colors, radii } from '@/lib/theme';

const pawMatchMark = require('../assets/pawmatch-mark.png');

export function AppLogo({ large = false }: { large?: boolean }) {
  return (
    <View style={styles.row}>
      <View style={[styles.iconWrap, large && styles.iconWrapLarge]}>
        <Image source={pawMatchMark} style={[styles.icon, large && styles.iconLarge]} resizeMode="contain" />
      </View>
      <Text style={[styles.logo, large && styles.logoLarge]}>
        <Text style={styles.paw}>Paw</Text>
        <Text style={styles.match}>Match</Text>
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row-reverse', alignItems: 'center', gap: 10, alignSelf: 'center' },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: radii.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#F4D7E0',
    overflow: 'hidden',
  },
  iconWrapLarge: { width: 62, height: 62, borderRadius: radii.lg },
  icon: { width: 40, height: 40 },
  iconLarge: { width: 58, height: 58 },
  logo: { fontSize: 28, fontWeight: '800', color: colors.text },
  logoLarge: { fontSize: 34 },
  paw: { color: colors.secondary },
  match: { color: colors.primary },
});

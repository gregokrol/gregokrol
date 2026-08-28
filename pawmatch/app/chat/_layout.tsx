import { Stack } from 'expo-router';
import { colors } from '@/lib/theme';

export default function ChatLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: true,
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.text,
        headerShadowVisible: false,
        contentStyle: { backgroundColor: colors.background },
        title: 'שיחה',
      }}
    />
  );
}

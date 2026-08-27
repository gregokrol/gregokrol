import { Redirect, Tabs } from "expo-router";
import { useAuth } from "@/lib/AuthProvider";

export default function TabsLayout() {
  const { session, loading } = useAuth();

  if (!loading && !session) {
    return <Redirect href="/(auth)/sign-in" />;
  }

  return (
    <Tabs screenOptions={{ headerShown: true }}>
      <Tabs.Screen name="swipe" options={{ title: "גילוי" }} />
      <Tabs.Screen name="matches" options={{ title: "התאמות" }} />
      <Tabs.Screen name="profile" options={{ title: "הפרופיל שלי" }} />
    </Tabs>
  );
}

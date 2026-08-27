import { Slot } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { AuthProvider } from "@/lib/AuthProvider";

export default function RootLayout() {
  return (
    <AuthProvider>
      <StatusBar style="auto" />
      <Slot />
    </AuthProvider>
  );
}

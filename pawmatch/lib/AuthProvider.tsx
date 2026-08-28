import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";
import type { Profile } from "./types";

interface AuthContextValue {
  session: Session | null;
  profile: Profile | null;
  loading: boolean;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const syncVersion = useRef(0);

  async function loadProfile(userId: string): Promise<Profile | null> {
    const { data, error } = await supabase.from("profiles").select("*").eq("id", userId).maybeSingle();
    if (error) throw error;
    return data ?? null;
  }

  async function syncSession(nextSession: Session | null) {
    const version = ++syncVersion.current;
    setLoading(true);
    setSession(nextSession);

    try {
      const nextProfile = nextSession?.user.id ? await loadProfile(nextSession.user.id) : null;
      if (version === syncVersion.current) {
        setProfile(nextProfile);
      }
    } catch {
      if (version === syncVersion.current) {
        setProfile(null);
      }
    } finally {
      if (version === syncVersion.current) {
        setLoading(false);
      }
    }
  }

  async function refreshProfile() {
    const userId = session?.user.id;
    if (!userId) {
      setProfile(null);
      return;
    }

    try {
      setProfile(await loadProfile(userId));
    } catch {
      // Keep the last known profile on a transient network error.
    }
  }

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (mounted) void syncSession(data.session);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (mounted) void syncSession(nextSession);
    });

    return () => {
      mounted = false;
      subscription.subscription.unsubscribe();
    };
  }, []);

  return (
    <AuthContext.Provider value={{ session, profile, loading, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { me as fetchMe, refreshTokens, type MeResponse, type TokenResponse } from "../lib/authApi";
import { getJwtExpiryMs } from "../lib/jwt";

type Session = {
  accessToken: string;
  refreshToken: string;
  user: MeResponse;
};

type AuthContextValue = {
  session: Session | null;
  /** Stores tokens in memory, fetches the profile, and schedules a silent
   * refresh before the access token expires. Nothing is persisted to disk —
   * a page reload requires logging in again (see manual-tests.http / README
   * for the tradeoff this implements). */
  startSession: (tokens: TokenResponse) => Promise<MeResponse>;
  clearSession: () => void;
  refreshUser: () => Promise<MeResponse | undefined>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const REFRESH_SAFETY_MARGIN_MS = 60_000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimer.current) {
      clearTimeout(refreshTimer.current);
      refreshTimer.current = null;
    }
  }, []);

  const clearSession = useCallback(() => {
    clearRefreshTimer();
    setSession(null);
  }, [clearRefreshTimer]);

  const scheduleSilentRefresh = useCallback(
    (tokens: TokenResponse) => {
      clearRefreshTimer();
      const expiryMs = getJwtExpiryMs(tokens.access_token);
      if (expiryMs === null) return;

      const delay = Math.max(expiryMs - Date.now() - REFRESH_SAFETY_MARGIN_MS, 5_000);
      refreshTimer.current = setTimeout(async () => {
        try {
          const nextTokens = await refreshTokens(tokens.refresh_token);
          setSession((prev) => (prev ? { ...prev, accessToken: nextTokens.access_token, refreshToken: nextTokens.refresh_token } : prev));
          scheduleSilentRefresh(nextTokens);
        } catch {
          clearSession();
        }
      }, delay);
    },
    [clearRefreshTimer, clearSession],
  );

  const startSession = useCallback(
    async (tokens: TokenResponse) => {
      const user = await fetchMe(tokens.access_token);
      setSession({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token, user });
      scheduleSilentRefresh(tokens);
      return user;
    },
    [scheduleSilentRefresh],
  );

  const refreshUser = useCallback(async () => {
    if (!session) return undefined;
    const user = await fetchMe(session.accessToken);
    setSession((prev) => (prev ? { ...prev, user } : prev));
    return user;
  }, [session]);

  const value = useMemo(
    () => ({ session, startSession, clearSession, refreshUser }),
    [session, startSession, clearSession, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth doit être utilisé à l'intérieur d'un AuthProvider");
  }
  return ctx;
}

export function roleHomePath(role: MeResponse["role"]): string {
  switch (role) {
    case "membre_pme":
      return "/app/pme";
    case "validateur_1":
    case "validateur_2":
      return "/app/acheteur";
    case "agent_financier":
      return "/app/partenaire";
    case "admin":
      return "/app/admin";
    default:
      return "/login";
  }
}

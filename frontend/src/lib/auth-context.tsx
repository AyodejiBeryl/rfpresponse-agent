"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api } from "./api";

interface User {
  id: string;
  email: string;
  full_name: string;
  org_id: string;
  role: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    orgName: string,
    fullName: string,
    email: string,
    password: string
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        setLoading(false);
        return;
      }
      const userData = await api.get<User>("/api/v1/auth/me");
      setUser(userData);
    } catch {
      localStorage.removeItem("access_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = async (email: string, password: string) => {
    const res = await api.post<{
      access_token: string;
      user_id: string;
      org_id: string;
      role: string;
    }>("/api/v1/auth/login", { email, password });
    localStorage.setItem("access_token", res.access_token);
    await fetchUser();
  };

  const register = async (
    orgName: string,
    fullName: string,
    email: string,
    password: string
  ) => {
    const res = await api.post<{
      access_token: string;
      user_id: string;
      org_id: string;
      role: string;
    }>("/api/v1/auth/register", {
      org_name: orgName,
      full_name: fullName,
      email,
      password,
    });
    localStorage.setItem("access_token", res.access_token);
    await fetchUser();
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

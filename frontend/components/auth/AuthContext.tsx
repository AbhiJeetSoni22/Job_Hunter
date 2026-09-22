"use client";

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { User, UserLoginRequest, UserRegisterRequest } from "@/lib/types";
import { getMe, login as apiLogin, register as apiRegister } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (credentials: UserLoginRequest) => Promise<void>;
  register: (data: UserRegisterRequest) => Promise<void>;
  loginWithToken: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadUser() {
      const token = localStorage.getItem("token");
      if (token) {
        try {
          const userData = await getMe();
          setUser(userData);
        } catch {
          localStorage.removeItem("token");
          setUser(null);
        }
      }
      setLoading(false);
    }
    loadUser();
  }, []);

  const loginWithToken = useCallback(async (token: string) => {
    localStorage.setItem("token", token);
    const userData = await getMe();
    setUser(userData);
  }, []);

  const login = useCallback(async (credentials: UserLoginRequest) => {
    const res = await apiLogin(credentials);
    await loginWithToken(res.access_token);
  }, [loginWithToken]);

  const register = useCallback(async (data: UserRegisterRequest) => {
    await apiRegister(data);
    await login({ email: data.email, password: data.password });
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, loginWithToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

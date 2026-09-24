"use client";

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { User, OtpResponse } from "@/lib/types";
import { getMe, requestOtp as apiRequestOtp, verifyOtp as apiVerifyOtp } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  requestOtp: (email: string) => Promise<OtpResponse>;
  verifyOtp: (email: string, otp: string) => Promise<void>;
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

  const requestOtp = useCallback(async (email: string): Promise<OtpResponse> => {
    return await apiRequestOtp(email);
  }, []);

  const verifyOtp = useCallback(async (email: string, otp: string): Promise<void> => {
    const res = await apiVerifyOtp(email, otp);
    await loginWithToken(res.access_token);
  }, [loginWithToken]);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, requestOtp, verifyOtp, loginWithToken, logout }}>
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

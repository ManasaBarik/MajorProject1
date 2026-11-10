import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import * as authApi from "@/services/api/auth";

const CivicAuthContext = createContext(null);

export function CivicAuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const access = sessionStorage.getItem("civic_access_token");
    if (!access) { setLoading(false); return; }
    try {
      const me = await authApi.getMe();
      setUser(me);
    } catch {
      sessionStorage.removeItem("civic_access_token");
      localStorage.removeItem("civic_refresh_token");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadUser(); }, [loadUser]);

  const login = useCallback(async (email, password) => {
    const data = await authApi.login(email, password);
    sessionStorage.setItem("civic_access_token", data.access);
    localStorage.setItem("civic_refresh_token", data.refresh);
    sessionStorage.setItem("civic_email", email);
    setUser(data.user);
    return data.user;
  }, []);

  const register = useCallback(async (form) => {
    const data = await authApi.register(form);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try { await authApi.logout(); } catch {}
    sessionStorage.removeItem("civic_access_token");
    localStorage.removeItem("civic_refresh_token");
    setUser(null);
  }, []);

  const updateMe = useCallback(async (form) => {
    const updated = await authApi.updateMe(form);
    setUser(prev => ({ ...prev, ...updated }));
    return updated;
  }, []);

  const value = { user, loading, login, register, logout, updateMe };
  return <CivicAuthContext.Provider value={value}>{children}</CivicAuthContext.Provider>;
}

export function useCivicAuth() {
  const ctx = useContext(CivicAuthContext);
  if (!ctx) throw new Error("useCivicAuth must be used within CivicAuthProvider");
  return ctx;
}
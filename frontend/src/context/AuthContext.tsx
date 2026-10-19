import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from '../types';
import { api, getStoredAuthToken, setStoredAuthToken } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (data: { email: string; password: string; remember_me?: boolean }) => Promise<void>;
  signup: (data: { full_name: string; email: string; password: string; confirm_password: string }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(getStoredAuthToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    const activeToken = getStoredAuthToken();
    if (!activeToken) {
      setUser(null);
      setToken(null);
      setIsLoading(false);
      return;
    }

    try {
      const currentUser = await api.getMe();
      setUser(currentUser);
      setToken(activeToken);
    } catch (err) {
      console.warn('Session expired or invalid, clearing local session.');
      setStoredAuthToken(null);
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (data: { email: string; password: string; remember_me?: boolean }) => {
    setIsLoading(true);
    try {
      const authRes = await api.login(data);
      setUser(authRes.user);
      setToken(authRes.access_token);
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (data: {
    full_name: string;
    email: string;
    password: string;
    confirm_password: string;
  }) => {
    setIsLoading(true);
    try {
      const authRes = await api.signup(data);
      setUser(authRes.user);
      setToken(authRes.access_token);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await api.logout();
    } finally {
      setUser(null);
      setToken(null);
      setStoredAuthToken(null);
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        signup,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

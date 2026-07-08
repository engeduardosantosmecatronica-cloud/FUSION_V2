import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { clearLocalAuthSession, getLocalAuthSession, localAuthConfig } from '@/lib/utils';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const [isLoadingPublicSettings, setIsLoadingPublicSettings] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [appPublicSettings] = useState({ id: 'fusion-local', public_settings: { auth: 'local' } });

  const loadLocalAuthState = useCallback(() => {
    const session = getLocalAuthSession();
    if (session?.user) {
      setUser(session.user);
      setIsAuthenticated(true);
    } else {
      setUser(null);
      setIsAuthenticated(false);
    }
    setIsLoadingPublicSettings(false);
    setIsLoadingAuth(false);
    setAuthChecked(true);
    setAuthError(null);
  }, []);

  useEffect(() => {
    loadLocalAuthState();
  }, [loadLocalAuthState]);

  const checkUserAuth = useCallback(async () => {
    loadLocalAuthState();
  }, [loadLocalAuthState]);

  const checkAppState = useCallback(async () => {
    loadLocalAuthState();
  }, [loadLocalAuthState]);

  const logout = (shouldRedirect = true) => {
    clearLocalAuthSession();
    setUser(null);
    setIsAuthenticated(false);
    if (shouldRedirect) window.location.href = '/login';
  };

  const navigateToLogin = () => {
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated,
      isLoadingAuth,
      isLoadingPublicSettings,
      authError,
      appPublicSettings,
      authChecked,
      logout,
      navigateToLogin,
      checkUserAuth,
      checkAppState,
      localAuthConfig,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};

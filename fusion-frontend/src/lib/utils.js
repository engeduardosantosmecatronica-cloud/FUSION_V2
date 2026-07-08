import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export const isIframe = window.self !== window.top;

const LOCAL_AUTH_SESSION_KEY = 'fusion_local_auth_session';

const envFlag = (value) => String(value ?? '').toLowerCase() === 'true' || String(value ?? '') === '1';

export const localAuthConfig = {
  enabled: envFlag(import.meta.env.VITE_LOCAL_AUTH_ENABLED),
  email: import.meta.env.VITE_LOCAL_ADMIN_EMAIL || 'admin@fusion.local',
  password: import.meta.env.VITE_LOCAL_ADMIN_PASSWORD || 'Fusion@123',
  name: import.meta.env.VITE_LOCAL_ADMIN_NAME || 'Admin',
};

export const isLocalAuthEnabled = () => localAuthConfig.enabled;

export const getLocalAuthSession = () => {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(LOCAL_AUTH_SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
};

export const setLocalAuthSession = (user) => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(LOCAL_AUTH_SESSION_KEY, JSON.stringify({
    user,
    authenticatedAt: new Date().toISOString(),
  }));
};

export const clearLocalAuthSession = () => {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(LOCAL_AUTH_SESSION_KEY);
};

export const loginWithLocalAuth = (email, password) => {
  if (!localAuthConfig.enabled) {
    throw new Error('Modo local de autenticação está desativado.');
  }

  if (email.trim().toLowerCase() !== localAuthConfig.email.toLowerCase() || password !== localAuthConfig.password) {
    throw new Error('Email ou senha inválidos.');
  }

  const user = {
    id: 'local-admin',
    name: localAuthConfig.name,
    email: localAuthConfig.email,
    role: 'admin',
    provider: 'local',
  };

  setLocalAuthSession(user);
  return user;
};

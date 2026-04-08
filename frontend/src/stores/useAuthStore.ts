import { create } from 'zustand';
import { saveTokens, clearTokens, isAuthenticated } from '@/utils/auth';
import { login as loginApi, logout as logoutApi, getCurrentUser } from '@/services/auth';

interface AuthState {
  currentUser: CurrentUser | null;
  isLoggedIn: boolean;
  permissions: string[];
  loading: boolean;
  login: (params: LoginParams) => Promise<void>;
  logout: () => Promise<void>;
  fetchCurrentUser: () => Promise<CurrentUser | null>;
  reset: () => void;
}

const useAuthStore = create<AuthState>((set) => ({
  currentUser: null,
  isLoggedIn: isAuthenticated(),
  permissions: [],
  loading: false,

  login: async (params: LoginParams) => {
    set({ loading: true });
    try {
      const res = await loginApi(params);
      const { access_token, refresh_token } = res.data;
      saveTokens(access_token, refresh_token);
      set({ isLoggedIn: true });

      const userRes = await getCurrentUser();
      set({
        currentUser: userRes.data,
        permissions: userRes.data.permissions || [],
      });
    } finally {
      set({ loading: false });
    }
  },

  logout: async () => {
    try {
      await logoutApi();
    } finally {
      clearTokens();
      set({ currentUser: null, isLoggedIn: false, permissions: [] });
    }
  },

  fetchCurrentUser: async () => {
    if (!isAuthenticated()) return null;
    set({ loading: true });
    try {
      const res = await getCurrentUser();
      set({
        currentUser: res.data,
        permissions: res.data.permissions || [],
        isLoggedIn: true,
      });
      return res.data;
    } catch {
      clearTokens();
      set({ currentUser: null, isLoggedIn: false, permissions: [] });
      return null;
    } finally {
      set({ loading: false });
    }
  },

  reset: () => {
    clearTokens();
    set({ currentUser: null, isLoggedIn: false, permissions: [], loading: false });
  },
}));

export default useAuthStore;

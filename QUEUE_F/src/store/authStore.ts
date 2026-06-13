import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Role = 'ADMIN' | 'OPERATOR' | null;

interface AuthState {
  token: string | null;
  sessionId: string | null;
  role: Role;
  loginAdmin: (token: string) => void;
  loginOperator: (token: string, sessionId: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      sessionId: null,
      role: null,
      loginAdmin: (token) => set({ token, role: 'ADMIN', sessionId: null }),
      loginOperator: (token, sessionId) => set({ token, sessionId, role: 'OPERATOR' }),
      logout: () => set({ token: null, sessionId: null, role: null }),
    }),
    {
      name: 'queuemind-auth',
    }
  )
);

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Role = 'ADMIN' | 'OPERATOR' | null;

interface AuthState {
  token: string | null;
  sessionId: string | null;
  role: Role;
  counterId: number | null;
  loginAdmin: (token: string) => void;
  loginOperator: (token: string, sessionId: string, counterId?: number) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      sessionId: null,
      role: null,
      counterId: null,
      loginAdmin: (token) => set({ token, role: 'ADMIN', sessionId: null, counterId: null }),
      loginOperator: (token, sessionId, counterId) => set({ token, sessionId, role: 'OPERATOR', counterId: counterId || null }),
      logout: () => set({ token: null, sessionId: null, role: null, counterId: null }),
    }),
    {
      name: 'queuemind-auth',
    }
  )
);

import { create } from 'zustand';
import type { TokenOut } from '@/types/api';

interface QueueState {
  currentQueue: TokenOut[];
  currentServing: TokenOut | null;
  setQueue: (queue: TokenOut[]) => void;
  setCurrentServing: (token: TokenOut | null) => void;
  updateTokenInQueue: (token: TokenOut) => void;
  removeTokenFromQueue: (tokenId: number) => void;
}

export const useQueueStore = create<QueueState>((set) => ({
  currentQueue: [],
  currentServing: null,
  setQueue: (queue) => set({ currentQueue: queue }),
  setCurrentServing: (token) => set({ currentServing: token }),
  updateTokenInQueue: (updatedToken) => set((state) => ({
    currentQueue: state.currentQueue.map(t => t.id === updatedToken.id ? updatedToken : t).sort((a, b) => b.priority_score - a.priority_score)
  })),
  removeTokenFromQueue: (tokenId) => set((state) => ({
    currentQueue: state.currentQueue.filter(t => t.id !== tokenId)
  })),
}));

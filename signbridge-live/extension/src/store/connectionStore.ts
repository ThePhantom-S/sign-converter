import { create } from 'zustand';
import { ConnectionState } from '../types';

interface ConnectionStoreState extends ConnectionState {
  setConnection: (status: Partial<ConnectionState>) => void;
  updateLatency: (latency: number) => void;
}

export const useConnectionStore = create<ConnectionStoreState>((set) => {
  return {
    isConnected: false,
    latencyMs: 0,
    error: null,
    isRetrying: false,
    
    setConnection: (status) => set((state) => ({ ...state, ...status })),
    updateLatency: (latency) => set({ latencyMs: latency }),
  };
});

if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener((message) => {
    if (message.action === 'BACKEND_STATUS_CHANGE') {
      useConnectionStore.setState(message.payload);
    }
  });
}

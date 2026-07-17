import { create } from 'zustand';
import { AppSettings } from '../types';

interface SettingsState extends AppSettings {
  isLoaded: boolean;
  setSetting: <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => void;
  updateSettings: (settings: Partial<AppSettings>) => void;
  loadSettings: () => Promise<void>;
}

const DEFAULT_SETTINGS: AppSettings = {
  language: 'en-US',
  theme: 'dark',
  captionSize: 'medium',
  captionPosition: 'bottom',
  voice: 'default',
  avatar: 'default-3d-signbot',
  speechSpeed: 1.0,
  transparency: 85,
  backendUrl: 'http://localhost:8000',
  apiKey: '',
  recognitionMode: 'speech-api',
  micEnabled: false,
  camEnabled: false,
  gestureEnabled: true,
  gestureConfidenceThreshold: 0.6,
};

export const useSettingsStore = create<SettingsState>((set, get) => {
  // Synchronize changes to chrome.storage.local if available
  const persist = (updated: Partial<AppSettings>) => {
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      chrome.storage.local.set(updated);
      
      // Send message to sync other extension contexts
      chrome.runtime.sendMessage({
        action: 'UPDATE_SETTINGS',
        payload: updated
      }).catch(() => {
        // Suppress errors if nobody is listening
      });
    }
  };

  return {
    ...DEFAULT_SETTINGS,
    isLoaded: false,
    
    setSetting: (key, value) => {
      set({ [key]: value } as unknown as Partial<SettingsState>);
      persist({ [key]: value });
    },
    
    updateSettings: (settings) => {
      set(settings as Partial<SettingsState>);
      persist(settings);
    },
    
    loadSettings: async () => {
      if (get().isLoaded) return;
      
      if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        return new Promise<void>((resolve) => {
          chrome.storage.local.get(null, (result) => {
            const loadedSettings = {
              ...DEFAULT_SETTINGS,
              ...result
            };
            set({ ...loadedSettings, isLoaded: true });
            resolve();
          });
        });
      } else {
        set({ isLoaded: true });
      }
    }
  };
});

// Setup runtime message listener to sync settings changes across frames
if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener((message) => {
    if (message.action === 'UPDATE_SETTINGS') {
      useSettingsStore.setState(message.payload);
    }
  });
}

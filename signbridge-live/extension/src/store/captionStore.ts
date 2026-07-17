import { create } from 'zustand';
import { CaptionEntry } from '../types';

interface CaptionState {
  captions: CaptionEntry[];
  currentCaption: CaptionEntry | null;
  addCaption: (caption: CaptionEntry) => void;
  clearCaptions: () => void;
}

export const useCaptionStore = create<CaptionState>((set) => {
  return {
    captions: [],
    currentCaption: null,
    
    addCaption: (entry) => {
      set((state) => {
        // If it's a non-final update to an existing caption, replace it. Otherwise append.
        const existingIndex = state.captions.findIndex((c) => c.id === entry.id);
        
        let newCaptions = [...state.captions];
        if (existingIndex > -1) {
          newCaptions[existingIndex] = entry;
        } else {
          newCaptions.push(entry);
        }
        
        // Cap the cached transcript at 200 items for performance
        if (newCaptions.length > 200) {
          newCaptions.shift();
        }
        
        return {
          captions: newCaptions,
          currentCaption: entry.isFinal ? null : entry,
        };
      });
    },
    
    clearCaptions: () => set({ captions: [], currentCaption: null }),
  };
});

// Sync captions across contexts via runtime messages
if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener((message) => {
    if (message.action === 'NEW_CAPTION') {
      useCaptionStore.getState().addCaption(message.payload);
    }
  });
}

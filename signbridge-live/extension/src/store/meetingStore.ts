import { create } from 'zustand';
import { MeetingStatus, MeetingSession } from '../types';

interface MeetingState {
  currentMeeting: MeetingSession | null;
  setMeeting: (meeting: MeetingSession | null) => void;
  updateMeetingStatus: (status: MeetingStatus) => void;
  updateParticipantCount: (count: number) => void;
  loadMeetingState: () => Promise<void>;
}

export const useMeetingStore = create<MeetingState>((set, get) => {
  const syncMeetingState = (meeting: MeetingSession | null) => {
    if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage) {
      chrome.runtime.sendMessage({
        action: 'MEETING_STARTED',
        payload: meeting
      }).catch(() => {});
    }
  };

  return {
    currentMeeting: null,
    
    setMeeting: (meeting) => {
      set({ currentMeeting: meeting });
      syncMeetingState(meeting);
    },
    
    updateMeetingStatus: (status) => {
      const current = get().currentMeeting;
      if (!current) return;
      
      const updated = { ...current, status };
      if (status === 'ACTIVE' && !current.startTime) {
        updated.startTime = Date.now();
      } else if (status === 'ENDED') {
        updated.endTime = Date.now();
      }
      
      set({ currentMeeting: updated });
      syncMeetingState(updated);
    },

    updateParticipantCount: (count) => {
      const current = get().currentMeeting;
      if (!current) return;
      set({ currentMeeting: { ...current, participantCount: count } });
    },

    loadMeetingState: async () => {
      if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.session) {
        // Use session storage for meeting state so it persists during the active browser session
        const result = await chrome.storage.session.get('currentMeeting');
        if (result.currentMeeting) {
          set({ currentMeeting: result.currentMeeting });
        }
      }
    }
  };
});

if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener((message) => {
    if (message.action === 'MEETING_STARTED') {
      useMeetingStore.setState({ currentMeeting: message.payload });
    } else if (message.action === 'MEETING_ENDED') {
      useMeetingStore.setState({ currentMeeting: null });
    }
  });
}

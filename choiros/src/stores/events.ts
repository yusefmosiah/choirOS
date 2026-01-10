// Event Stream Store - centralized event/notification management
import { create } from 'zustand';

export interface StreamEvent {
    id: string;
    message: string;
    type: 'info' | 'success' | 'error' | 'thinking';
    timestamp: number;
    artifactId?: string;
}

interface EventStore {
    events: StreamEvent[];
    addEvent: (message: string, type: StreamEvent['type'], artifactId?: string) => string;
    removeEvent: (id: string) => void;
    clearAll: () => void;
}

let eventCounter = 0;

export const useEventStore = create<EventStore>((set) => ({
    events: [],
    
    addEvent: (message, type, artifactId) => {
        const id = `event-${Date.now()}-${eventCounter++}`;
        const event: StreamEvent = {
            id,
            message,
            type,
            timestamp: Date.now(),
            artifactId,
        };
        
        set((state) => ({
            events: [...state.events, event],
        }));
        
        return id;
    },
    
    removeEvent: (id) => {
        set((state) => ({
            events: state.events.filter((e) => e.id !== id),
        }));
    },
    
    clearAll: () => {
        set({ events: [] });
    },
}));

// Helper hook for components to emit events easily
export function emitEvent(message: string, type: StreamEvent['type'] = 'info', artifactId?: string) {
    return useEventStore.getState().addEvent(message, type, artifactId);
}

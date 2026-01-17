// Event Stream Store - centralized event/notification management
import { create } from 'zustand';

export interface StreamEvent {
    id: string;
    message: string;
    type: 'info' | 'success' | 'error' | 'thinking';
    timestamp: number;
    artifactId?: string;
}

type NatsStatus = 'connecting' | 'online' | 'offline';

interface EventStore {
    events: StreamEvent[];
    addEvent: (message: string, type: StreamEvent['type'], artifactId?: string) => string;
    removeEvent: (id: string) => void;
    clearAll: () => void;
    natsStatus: NatsStatus;
    setNatsStatus: (status: NatsStatus) => void;
}

let eventCounter = 0;
const MAX_EVENTS = 200;

export const useEventStore = create<EventStore>((set) => ({
    events: [],
    natsStatus: 'connecting',
    
    addEvent: (message, type, artifactId) => {
        const id = `event-${Date.now()}-${eventCounter++}`;
        const event: StreamEvent = {
            id,
            message,
            type,
            timestamp: Date.now(),
            artifactId,
        };
        
        set((state) => {
            const next = [...state.events, event];
            return {
                events: next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next,
            };
        });
        
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

    setNatsStatus: (status) => {
        set({ natsStatus: status });
    },
}));

// Helper hook for components to emit events easily
export function emitEvent(message: string, type: StreamEvent['type'] = 'info', artifactId?: string) {
    return useEventStore.getState().addEvent(message, type, artifactId);
}

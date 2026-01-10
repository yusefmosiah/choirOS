// EventStream - ascending stack of events with perspective
import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { useEventStore, type StreamEvent } from '../../stores/events';
import { useWindowStore } from '../../stores/windows';
import './EventStream.css';

export function EventStream() {
    const events = useEventStore((s) => s.events);
    const removeEvent = useEventStore((s) => s.removeEvent);
    const openWindow = useWindowStore((s) => s.openWindow);
    const containerRef = useRef<HTMLDivElement>(null);

    // Auto-remove old events
    useEffect(() => {
        const interval = setInterval(() => {
            const now = Date.now();
            events.forEach((event) => {
                // Events older than 8 seconds start fading, removed at 12s
                if (now - event.timestamp > 12000) {
                    removeEvent(event.id);
                }
            });
        }, 1000);
        return () => clearInterval(interval);
    }, [events, removeEvent]);

    const handleEventClick = (event: StreamEvent) => {
        if (event.artifactId) {
            openWindow('writer', { artifactId: event.artifactId });
            removeEvent(event.id);
        }
    };

    // Only show last 8 events
    const visibleEvents = events.slice(-8);

    return (
        <div className="event-stream" ref={containerRef}>
            <div className="event-stream-inner">
                {visibleEvents.map((event, index) => {
                    const age = Date.now() - event.timestamp;
                    const position = visibleEvents.length - 1 - index; // 0 = newest (bottom)
                    
                    // Calculate perspective transform based on position in stack
                    const translateY = position * -52; // Stack upward
                    const translateZ = position * -30; // Push back into z-space
                    const scale = 1 - (position * 0.04); // Shrink slightly
                    const opacity = Math.max(0.2, 1 - (position * 0.12) - (age > 8000 ? (age - 8000) / 4000 : 0));
                    
                    return (
                        <div
                            key={event.id}
                            className={`event-item ${event.type} ${event.artifactId ? 'clickable' : ''}`}
                            style={{
                                transform: `translateY(${translateY}px) translateZ(${translateZ}px) scale(${scale})`,
                                opacity,
                                zIndex: 100 - position,
                            }}
                            onClick={() => handleEventClick(event)}
                        >
                            <span className="event-message">{event.message}</span>
                            {event.artifactId && <span className="event-hint">↵ open</span>}
                            <button 
                                className="event-close"
                                onClick={(e) => { e.stopPropagation(); removeEvent(event.id); }}
                            >
                                <X size={12} />
                            </button>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

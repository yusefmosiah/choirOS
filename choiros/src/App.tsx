import { useEffect } from 'react';
import { Desktop } from './components/desktop/Desktop';
import { connectNats, disconnectNats, onNatsStatusChange, subscribeUserEvents, type ChoirEvent } from './lib/nats';
import { authFetch, onSessionChange } from './lib/auth';
import { useEventStore } from './stores/events';

const SUPERVISOR_BASE = import.meta.env.VITE_SUPERVISOR_URL || 'http://localhost:8001';

function App() {
    const addEvent = useEventStore((s) => s.addEvent);
    const setNatsStatus = useEventStore((s) => s.setNatsStatus);

    useEffect(() => {
        let unsubscribe: (() => void) | undefined;
        let cancelled = false;
        const stopStatus = onNatsStatusChange((status) => setNatsStatus(status));
        setNatsStatus('connecting');

        const handleEvent = (event: ChoirEvent) => {
            const payload = event.payload as Record<string, unknown>;
            if (event.event_type === 'file.write' && typeof payload.path === 'string') {
                addEvent(`file.write ${payload.path}`, 'info');
                return;
            }
            addEvent(event.event_type, 'info');
        };

        const start = async (forceReconnect = false) => {
            try {
                if (forceReconnect) {
                    if (unsubscribe) {
                        unsubscribe();
                        unsubscribe = undefined;
                    }
                    await disconnectNats();
                }
                await connectNats();
                if (cancelled) return;
                if (!unsubscribe) {
                    unsubscribe = await subscribeUserEvents(handleEvent);
                }
            } catch (error) {
                setNatsStatus('offline');
                addEvent('NATS offline', 'error');
            }
        };

        start();
        const stopSession = onSessionChange(() => {
            if (!cancelled) {
                start(true);
            }
        });

        return () => {
            cancelled = true;
            if (unsubscribe) unsubscribe();
            disconnectNats();
            stopStatus();
            stopSession();
        };
    }, [addEvent, setNatsStatus]);

    useEffect(() => {
        if (import.meta.env.VITE_FRONTEND_SANDBOX !== '1') {
            return;
        }
        let cancelled = false;
        const ensureProxy = async () => {
            try {
                const res = await authFetch(`${SUPERVISOR_BASE}/frontend/url`);
                if (!res.ok || cancelled) return;
                const data = await res.json();
                if (!data.url) return;
                const target = new URL(data.url, window.location.href);
                if (target.origin !== window.location.origin) {
                    window.location.replace(target.toString());
                }
            } catch {
                // Ignore proxy errors; keep local URL.
            }
        };
        ensureProxy();
        return () => {
            cancelled = true;
        };
    }, []);

    return <Desktop />;
}

export default App

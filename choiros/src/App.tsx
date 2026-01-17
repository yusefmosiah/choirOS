import { useEffect } from 'react';
import { Desktop } from './components/desktop/Desktop';
import { connectNats, disconnectNats, onNatsStatusChange, subscribeUserEvents, type ChoirEvent } from './lib/nats';
import { useEventStore } from './stores/events';

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

        const start = async () => {
            try {
                await connectNats();
                if (cancelled) return;
                unsubscribe = await subscribeUserEvents(handleEvent);
            } catch (error) {
                setNatsStatus('offline');
                addEvent('NATS offline', 'error');
            }
        };

        start();

        return () => {
            cancelled = true;
            if (unsubscribe) unsubscribe();
            disconnectNats();
            stopStatus();
        };
    }, [addEvent, setNatsStatus]);

    return <Desktop />;
}

export default App

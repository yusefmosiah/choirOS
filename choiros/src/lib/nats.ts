/**
 * NATS WebSocket client for browser.
 *
 * Enables real-time event streaming between browser and server.
 * Uses nats.ws for WebSocket connection to NATS JetStream.
 */

import { connect, StringCodec } from 'nats.ws';
import type { NatsConnection, JetStreamClient } from 'nats.ws';
import { buildSubject, normalizeEventType, CHOIR_SUBJECT_ROOT } from './event_contract';

// Configuration
const NATS_WS_URL = import.meta.env.VITE_NATS_WS_URL || 'ws://localhost:8080';
const USER_ID = import.meta.env.VITE_USER_ID || 'local';

const sc = StringCodec();

export type NatsConnectionStatus = 'online' | 'offline';

// Singleton connection
let nc: NatsConnection | null = null;
let _js: JetStreamClient | null = null;  // Prefixed with _ to indicate intentionally unused for now

type StatusListener = (status: NatsConnectionStatus) => void;
const statusListeners = new Set<StatusListener>();

function notifyStatus(status: NatsConnectionStatus) {
    statusListeners.forEach((listener) => listener(status));
}

export function onNatsStatusChange(listener: StatusListener): () => void {
    statusListeners.add(listener);
    return () => statusListeners.delete(listener);
}

export interface ChoirEvent {
    id: string;
    timestamp: number;
    user_id: string;
    source: 'user' | 'agent' | 'system';
    event_type: string;
    payload: Record<string, unknown>;
}

/**
 * Connect to NATS via WebSocket.
 */
export async function connectNats(): Promise<NatsConnection> {
    if (nc) {
        notifyStatus('online');
        return nc;
    }

    try {
        nc = await connect({
            servers: NATS_WS_URL,
            // Add auth token here when implementing multi-user
        });

        _js = nc.jetstream();
        console.log('✓ NATS WebSocket connected');
        notifyStatus('online');

        // Handle disconnection
        nc.closed().then(() => {
            console.log('NATS connection closed');
            nc = null;
            _js = null;
            notifyStatus('offline');
        });

        return nc;
    } catch (error) {
        console.error('NATS connection failed:', error);
        notifyStatus('offline');
        throw error;
    }
}

/**
 * Disconnect from NATS.
 */
export async function disconnectNats(): Promise<void> {
    if (nc) {
        await nc.drain();
        nc = null;
        _js = null;
        notifyStatus('offline');
    }
}

/**
 * Publish an event to NATS.
 */
export async function publishEvent(
    eventType: string,
    payload: Record<string, unknown>,
    source: 'user' | 'agent' | 'system' = 'user'
): Promise<void> {
    if (!nc) {
        console.warn('NATS not connected, skipping publish');
        return;
    }

    const normalizedType = normalizeEventType(eventType);
    const event: ChoirEvent = {
        id: crypto.randomUUID(),
        timestamp: Date.now(),
        user_id: USER_ID,
        source,
        event_type: normalizedType,
        payload,
    };

    const subject = eventToSubject(event);
    nc.publish(subject, sc.encode(JSON.stringify(event)));
}

/**
 * Subscribe to events with a callback.
 */
export async function subscribeEvents(
    pattern: string,
    callback: (event: ChoirEvent) => void
): Promise<() => void> {
    if (!nc) {
        throw new Error('NATS not connected');
    }

    const sub = nc.subscribe(pattern);

    // Process messages in background
    (async () => {
        for await (const msg of sub) {
            try {
                const event = JSON.parse(sc.decode(msg.data)) as ChoirEvent;
                callback(event);
            } catch (error) {
                console.error('Failed to parse NATS message:', error);
            }
        }
    })();

    // Return unsubscribe function
    return () => sub.unsubscribe();
}

/**
 * Subscribe to user's event stream.
 */
export async function subscribeUserEvents(
    callback: (event: ChoirEvent) => void
): Promise<() => void> {
    return subscribeEvents(`${CHOIR_SUBJECT_ROOT}.${USER_ID}.>`, callback);
}

/**
 * Get connection status.
 */
export function isConnected(): boolean {
    return nc !== null && !nc.isClosed();
}

/**
 * Map event to NATS subject hierarchy.
 */
function eventToSubject(event: ChoirEvent): string {
    const normalizedType = normalizeEventType(event.event_type);
    return buildSubject(event.user_id, event.source, normalizedType);
}

// Re-export types
export type { NatsConnection, JetStreamClient };

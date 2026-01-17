// Canonical event contract for ChoirOS.
// Keep in sync with docs/specs/CHOIR_EVENT_CONTRACT_SPEC.md.

export const CHOIR_STREAM = 'CHOIR';
export const CHOIR_SUBJECT_ROOT = 'choiros';
export const CHOIR_SUBJECT_PATTERN = 'choiros.>';
export const CHOIR_SUBJECT_FORMAT = 'choiros.{user_id}.{source}.{event_type}';

export type EventSource = 'user' | 'agent' | 'system';

export const CHOIR_EVENT_TYPES_V0 = [
    'file.write',
    'file.delete',
    'file.move',
    'message',
    'tool.call',
    'tool.result',
    'window.open',
    'window.close',
    'checkpoint',
    'undo',
] as const;

export type ChoirEventType = (typeof CHOIR_EVENT_TYPES_V0)[number];

const LEGACY_EVENT_TYPE_MAP: Record<string, string> = {
    FILE_WRITE: 'file.write',
    FILE_DELETE: 'file.delete',
    FILE_MOVE: 'file.move',
    CONVERSATION_MESSAGE: 'message',
    TOOL_CALL: 'tool.call',
    TOOL_RESULT: 'tool.result',
    WINDOW_OPEN: 'window.open',
    WINDOW_CLOSE: 'window.close',
    CHECKPOINT: 'checkpoint',
    UNDO: 'undo',
};

export function buildSubject(userId: string, source: EventSource, eventType: string): string {
    return `${CHOIR_SUBJECT_ROOT}.${userId}.${source}.${eventType}`;
}

export function normalizeEventType(eventType: string): string {
    const raw = eventType?.trim();
    if (!raw) return eventType;
    const upper = raw.toUpperCase();
    if (LEGACY_EVENT_TYPE_MAP[upper]) {
        return LEGACY_EVENT_TYPE_MAP[upper];
    }
    return raw.toLowerCase().replace(/_/g, '.');
}

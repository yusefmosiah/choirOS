// Canonical event contract for ChoirOS.
// Keep in sync with docs/specs/CHOIR_EVENT_CONTRACT_SPEC.md.

export const CHOIR_STREAM = 'CHOIR';
export const CHOIR_SUBJECT_ROOT = 'choiros';
export const CHOIR_SUBJECT_PATTERN = 'choiros.>';
export const CHOIR_SUBJECT_FORMAT = 'choiros.{user_id}.{source}.{event_type}';

export type EventSource = 'user' | 'agent' | 'system';

export const CHOIR_EVENT_TYPES_V0 = [
    // Core events
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
    // Notes (AHDB-typed telemetry)
    'note.observation',
    'note.hypothesis',
    'note.hyperthesis',
    'note.conjecture',
    'note.status',
    'note.request.help',
    'note.request.verify',
    // Receipts (capabilities + verification)
    'receipt.read',
    'receipt.patch',
    'receipt.verifier',
    'receipt.net',
    'receipt.db',
    'receipt.export',
    'receipt.publish',
    'receipt.context.footprint',
    'receipt.verifier.results',
    'receipt.verifier.attestations',
    'receipt.discrepancy.report',
    'receipt.commit',
    'receipt.ahdb.delta',
    'receipt.evidence.set.hash',
    'receipt.retrieval',
    'receipt.conjecture.set',
    'receipt.policy.decision.tokens',
    'receipt.security.attestations',
    'receipt.hyperthesis.delta',
    'receipt.expansion.plan',
    'receipt.projection.rebuild',
    'receipt.attack.report',
    'receipt.disclosure.objects',
    'receipt.mitigation.proposals',
    'receipt.preference.decision',
    'receipt.timeout',
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

function normalizeSegments(value: string): string {
    return value.trim().toLowerCase().replace(/\//g, '.').replace(/_/g, '.');
}

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
    if (upper.startsWith('RECEIPT/')) {
        const suffix = raw.split('/', 2)[1];
        return `receipt.${normalizeSegments(suffix)}`;
    }
    if (upper.endsWith('_RECEIPT') && upper !== 'RECEIPT') {
        const suffix = raw.slice(0, -'_RECEIPT'.length);
        return `receipt.${normalizeSegments(suffix)}`;
    }
    return normalizeSegments(raw);
}

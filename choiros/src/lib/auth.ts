/**
 * Auth helpers for passkeys + sessions.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const AUTH_BASE = `${API_BASE}/api/auth`;
const SESSION_TOKEN_KEY = 'choiros.session.token';
const SESSION_USER_KEY = 'choiros.session.user';
const SESSION_EVENT = 'choiros:session-changed';

let cachedNatsCredentials: NatsCredentials | null = null;
let cachedSessionToken: string | null = null;

export interface AuthSession {
    session_id: string;
    user_id: string;
    created_at: string;
    last_seen_at: string;
    client_label?: string | null;
}

export interface PasskeyOptionsResponse {
    challenge_id: string;
    publicKey: Record<string, unknown>;
}

export interface NatsCredentials {
    servers: string;
    user: string;
    password: string;
    subject_prefix: string;
    user_id: string;
}

export function getSessionToken(): string | null {
    if (typeof window === 'undefined' || !window.localStorage) {
        return null;
    }
    return localStorage.getItem(SESSION_TOKEN_KEY);
}

export function getSessionUserId(): string | null {
    if (typeof window === 'undefined' || !window.localStorage) {
        return null;
    }
    return localStorage.getItem(SESSION_USER_KEY);
}

export function setSession(token: string, userId: string): void {
    cachedNatsCredentials = null;
    cachedSessionToken = null;
    if (typeof window === 'undefined' || !window.localStorage) {
        return;
    }
    localStorage.setItem(SESSION_TOKEN_KEY, token);
    localStorage.setItem(SESSION_USER_KEY, userId);
    window.dispatchEvent(new Event(SESSION_EVENT));
}

export function clearSession(): void {
    cachedNatsCredentials = null;
    cachedSessionToken = null;
    if (typeof window === 'undefined' || !window.localStorage) {
        return;
    }
    localStorage.removeItem(SESSION_TOKEN_KEY);
    localStorage.removeItem(SESSION_USER_KEY);
    window.dispatchEvent(new Event(SESSION_EVENT));
}

export async function authFetch(input: RequestInfo, init: RequestInit = {}): Promise<Response> {
    const token = getSessionToken();
    const headers = new Headers(init.headers || {});
    if (token) {
        headers.set('X-Choir-Session', token);
    }
    return fetch(input, { ...init, headers });
}

export function onSessionChange(listener: () => void): () => void {
    if (typeof window === 'undefined') {
        return () => undefined;
    }
    window.addEventListener(SESSION_EVENT, listener);
    return () => window.removeEventListener(SESSION_EVENT, listener);
}

export function buildAgentWsUrl(baseUrl: string): string {
    const token = getSessionToken();
    if (!token) return baseUrl;
    try {
        const url = new URL(baseUrl);
        url.searchParams.set('session', token);
        return url.toString();
    } catch {
        return `${baseUrl}?session=${encodeURIComponent(token)}`;
    }
}

function bufferToBase64Url(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (const byte of bytes) {
        binary += String.fromCharCode(byte);
    }
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function base64UrlToBuffer(value: string): ArrayBuffer {
    const base64 = value.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64 + '==='.slice((base64.length + 3) % 4);
    const binary = atob(padded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}

function normalizeCreationOptions(options: PasskeyOptionsResponse['publicKey']): PublicKeyCredentialCreationOptions {
    const publicKey = { ...options } as Record<string, unknown>;
    publicKey.challenge = base64UrlToBuffer(String(publicKey.challenge));
    if (publicKey.user && typeof publicKey.user === 'object') {
        const user = { ...(publicKey.user as Record<string, unknown>) };
        user.id = base64UrlToBuffer(String(user.id));
        publicKey.user = user;
    }
    if (Array.isArray(publicKey.excludeCredentials)) {
        publicKey.excludeCredentials = publicKey.excludeCredentials.map((cred) => ({
            ...cred,
            id: base64UrlToBuffer(String((cred as Record<string, unknown>).id)),
        }));
    }
    return publicKey as PublicKeyCredentialCreationOptions;
}

function normalizeRequestOptions(options: PasskeyOptionsResponse['publicKey']): PublicKeyCredentialRequestOptions {
    const publicKey = { ...options } as Record<string, unknown>;
    publicKey.challenge = base64UrlToBuffer(String(publicKey.challenge));
    if (Array.isArray(publicKey.allowCredentials)) {
        publicKey.allowCredentials = publicKey.allowCredentials.map((cred) => ({
            ...cred,
            id: base64UrlToBuffer(String((cred as Record<string, unknown>).id)),
        }));
    }
    return publicKey as PublicKeyCredentialRequestOptions;
}

function credentialToJson(credential: PublicKeyCredential) {
    const response = credential.response as AuthenticatorResponse;
    const clientExtensionResults = credential.getClientExtensionResults?.() || {};

    const payload: Record<string, unknown> = {
        id: credential.id,
        rawId: bufferToBase64Url(credential.rawId),
        type: credential.type,
        response: {
            clientDataJSON: bufferToBase64Url(response.clientDataJSON),
        },
        clientExtensionResults,
    };

    if ('attestationObject' in response) {
        payload.response = {
            ...payload.response,
            attestationObject: bufferToBase64Url((response as AuthenticatorAttestationResponse).attestationObject),
        };
    }

    if ('authenticatorData' in response) {
        payload.response = {
            ...payload.response,
            authenticatorData: bufferToBase64Url((response as AuthenticatorAssertionResponse).authenticatorData),
            signature: bufferToBase64Url((response as AuthenticatorAssertionResponse).signature),
            userHandle: (response as AuthenticatorAssertionResponse).userHandle
                ? bufferToBase64Url((response as AuthenticatorAssertionResponse).userHandle as ArrayBuffer)
                : null,
        };
    }

    return payload;
}

export async function startPasskeyRegistration(userId: string, username?: string, displayName?: string) {
    const response = await fetch(`${AUTH_BASE}/passkeys/register/options`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, username, display_name: displayName }),
    });

    if (!response.ok) {
        throw new Error('Failed to start passkey registration');
    }

    return response.json() as Promise<PasskeyOptionsResponse>;
}

export async function finishPasskeyRegistration(userId: string, challengeId: string, credential: Record<string, unknown>, clientLabel?: string) {
    const response = await fetch(`${AUTH_BASE}/passkeys/register/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            challenge_id: challengeId,
            credential,
            client_label: clientLabel,
        }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Failed to verify passkey registration');
    }

    return response.json() as Promise<{ session: AuthSession; token: string }>;
}

export async function registerPasskey(userId: string, username?: string, displayName?: string, clientLabel?: string) {
    const options = await startPasskeyRegistration(userId, username, displayName);
    const publicKey = normalizeCreationOptions(options.publicKey);

    const credential = (await navigator.credentials.create({
        publicKey,
    })) as PublicKeyCredential | null;

    if (!credential) {
        throw new Error('Passkey creation was cancelled');
    }

    const result = await finishPasskeyRegistration(
        userId,
        options.challenge_id,
        credentialToJson(credential),
        clientLabel,
    );

    setSession(result.token, result.session.user_id);
    return result.session;
}

export async function startPasskeyAuthentication(userId: string) {
    const response = await fetch(`${AUTH_BASE}/passkeys/authenticate/options`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Failed to start passkey authentication');
    }

    return response.json() as Promise<PasskeyOptionsResponse>;
}

export async function finishPasskeyAuthentication(userId: string, challengeId: string, credential: Record<string, unknown>, clientLabel?: string) {
    const response = await fetch(`${AUTH_BASE}/passkeys/authenticate/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            challenge_id: challengeId,
            credential,
            client_label: clientLabel,
        }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Failed to verify passkey authentication');
    }

    return response.json() as Promise<{ session: AuthSession; token: string }>;
}

export async function authenticatePasskey(userId: string, clientLabel?: string) {
    const options = await startPasskeyAuthentication(userId);
    const publicKey = normalizeRequestOptions(options.publicKey);

    const credential = (await navigator.credentials.get({
        publicKey,
    })) as PublicKeyCredential | null;

    if (!credential) {
        throw new Error('Passkey authentication was cancelled');
    }

    const result = await finishPasskeyAuthentication(
        userId,
        options.challenge_id,
        credentialToJson(credential),
        clientLabel,
    );

    setSession(result.token, result.session.user_id);
    return result.session;
}

export async function fetchNatsCredentials(): Promise<NatsCredentials | null> {
    const token = getSessionToken();
    if (!token) {
        return null;
    }
    if (cachedNatsCredentials && cachedSessionToken === token) {
        return cachedNatsCredentials;
    }
    const response = await authFetch(`${AUTH_BASE}/nats/credentials`);
    if (!response.ok) {
        return null;
    }
    const creds = (await response.json()) as NatsCredentials;
    cachedNatsCredentials = creds;
    cachedSessionToken = token;
    return creds;
}

export async function listSessions(): Promise<AuthSession[]> {
    const response = await authFetch(`${AUTH_BASE}/sessions`);
    if (!response.ok) {
        throw new Error('Failed to fetch sessions');
    }
    const data = await response.json();
    return data.sessions as AuthSession[];
}

export async function revokeSession(sessionId: string): Promise<void> {
    const response = await authFetch(`${AUTH_BASE}/sessions/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
    });
    if (!response.ok) {
        throw new Error('Failed to revoke session');
    }
}

export function isWebAuthnSupported(): boolean {
    return typeof window !== 'undefined' && typeof window.PublicKeyCredential !== 'undefined';
}

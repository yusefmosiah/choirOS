// Auth App - Passkey registration + session management
import { useEffect, useState } from 'react';
import {
    authenticatePasskey,
    registerPasskey,
    isWebAuthnSupported,
    listSessions,
    revokeSession,
    getSessionToken,
    getSessionUserId,
    clearSession,
} from '../../lib/auth';
import { KeyRound, ShieldCheck, ShieldOff, RefreshCw, XCircle } from 'lucide-react';
import './Auth.css';

interface SessionView {
    session_id: string;
    user_id: string;
    created_at: string;
    last_seen_at: string;
    client_label?: string | null;
}

export function AuthApp() {
    const [userId, setUserId] = useState(getSessionUserId() || 'local');
    const [displayName, setDisplayName] = useState('');
    const [clientLabel, setClientLabel] = useState('');
    const [status, setStatus] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [sessions, setSessions] = useState<SessionView[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [sessionMarker, setSessionMarker] = useState(0);

    const token = getSessionToken();
    const supported = isWebAuthnSupported();

    const refreshSessions = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const list = await listSessions();
            setSessions(list);
        } catch (err) {
            setSessions([]);
            setError(err instanceof Error ? err.message : 'Failed to load sessions');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (token) {
            refreshSessions();
        } else {
            setSessions([]);
        }
    }, [token, sessionMarker]);

    const handleRegister = async () => {
        if (!supported) {
            setError('Passkeys are not supported in this browser');
            return;
        }
        setError(null);
        setStatus('Creating passkey...');
        try {
            const session = await registerPasskey(userId, userId, displayName || undefined, clientLabel || undefined);
            setStatus(`Registered passkey for ${session.user_id}`);
            setSessionMarker((v) => v + 1);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Passkey registration failed');
            setStatus(null);
        }
    };

    const handleLogin = async () => {
        if (!supported) {
            setError('Passkeys are not supported in this browser');
            return;
        }
        setError(null);
        setStatus('Signing in with passkey...');
        try {
            const session = await authenticatePasskey(userId, clientLabel || undefined);
            setStatus(`Signed in as ${session.user_id}`);
            setSessionMarker((v) => v + 1);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Passkey sign-in failed');
            setStatus(null);
        }
    };

    const handleLogout = () => {
        clearSession();
        setStatus('Session cleared');
        setSessionMarker((v) => v + 1);
    };

    const handleRevoke = async (sessionId: string) => {
        setError(null);
        try {
            await revokeSession(sessionId);
            setStatus('Session revoked');
            refreshSessions();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to revoke session');
        }
    };

    return (
        <div className="auth-app">
            <header className="auth-header">
                <div className="auth-title">
                    <KeyRound size={18} />
                    <span>Passkeys</span>
                </div>
                <div className={`auth-status-pill ${token ? 'online' : 'offline'}`}>
                    {token ? <ShieldCheck size={14} /> : <ShieldOff size={14} />}
                    <span>{token ? 'Session active' : 'No session'}</span>
                </div>
            </header>

            <section className="auth-section">
                <h3>Identity</h3>
                <label>
                    User ID
                    <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="local" />
                </label>
                <label>
                    Display name
                    <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Optional" />
                </label>
                <label>
                    Client label
                    <input value={clientLabel} onChange={(e) => setClientLabel(e.target.value)} placeholder="e.g. MacBook, iPhone" />
                </label>
                <div className="auth-actions">
                    <button type="button" onClick={handleRegister} disabled={!supported}>
                        Register passkey
                    </button>
                    <button type="button" onClick={handleLogin} disabled={!supported}>
                        Sign in
                    </button>
                    <button type="button" onClick={handleLogout} disabled={!token}>
                        Sign out (local)
                    </button>
                </div>
                <div className="auth-hint">
                    {supported ? 'Passkeys supported in this browser.' : 'Passkeys not supported in this browser.'}
                </div>
            </section>

            <section className="auth-section">
                <div className="auth-section-header">
                    <h3>Sessions</h3>
                    <button type="button" onClick={refreshSessions} disabled={!token || isLoading}>
                        <RefreshCw size={14} className={isLoading ? 'spin' : ''} />
                        Refresh
                    </button>
                </div>
                {!token && <p className="auth-muted">Sign in to view active sessions.</p>}
                {token && sessions.length === 0 && !isLoading && <p className="auth-muted">No active sessions.</p>}
                <div className="auth-sessions">
                    {sessions.map((session) => (
                        <div className="auth-session" key={session.session_id}>
                            <div>
                                <div className="auth-session-title">{session.client_label || 'Unnamed client'}</div>
                                <div className="auth-session-meta">{session.session_id}</div>
                                <div className="auth-session-meta">Last seen: {new Date(session.last_seen_at).toLocaleString()}</div>
                            </div>
                            <button type="button" onClick={() => handleRevoke(session.session_id)}>
                                <XCircle size={14} />
                                Revoke
                            </button>
                        </div>
                    ))}
                </div>
            </section>

            {status && <div className="auth-status">{status}</div>}
            {error && <div className="auth-error">{error}</div>}
        </div>
    );
}

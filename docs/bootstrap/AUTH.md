# ChoirOS Authentication

> Passkey-based WebAuthn authentication for secure, passwordless access.
> NATS-specific sections are deferred; v0 focuses on Ralph-in-Ralph sandboxing.

## Overview

ChoirOS uses **passkey authentication** (WebAuthn/FIDO2) for biometric login without passwords or seed phrases. This document describes how to implement it using the proven tuxedo passkey system as a reference.

## Why Passkeys?

**User Experience:**
- No passwords to remember
- Biometric authentication (Face ID, Touch ID, Windows Hello)
- Multi-device support (sync via iCloud Keychain, Google Password Manager)
- Works on all modern browsers

**Security:**
- Public-key cryptography (private keys never leave device)
- Phishing-resistant (domain-bound credentials)
- No credential database to breach
- Hardware-backed security (TPM, Secure Enclave)

**Perfect for ChoirOS:**
- Distributed system needs strong user identity
- No centralized password database
- Works with per-user S3 buckets (NATS ACLs later)
- Complements sovereign data architecture

---

## Reference Implementation

The tuxedo repository has a production-proven passkey auth system:

```
tuxedo/
├── backend/
│   ├── database_passkeys.py           # SQLite schema & operations
│   ├── services/passkey_service.py    # WebAuthn challenge/verify logic
│   ├── api/
│   │   ├── routes/passkey_auth_refactored.py  # FastAPI routes
│   │   ├── schemas/passkey_schemas.py         # Pydantic models
│   │   └── utils/passkey_helpers.py           # Helper functions
│   └── services/email.py              # SendGrid email service
└── src/
    ├── services/passkeyAuth.ts        # Frontend WebAuthn client
    └── contexts/AuthContext.tsx       # React auth context
```

**Key metrics:**
- 562 lines backend routes
- 427 lines service layer
- 833 lines database layer
- 825 lines frontend client
- ~2,600 lines total (well-tested, production-ready)

---

## Architecture

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    REGISTRATION FLOW                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. User enters email                                        │
│     └─► POST /auth/passkey/register/start                  │
│         ├─► Server generates challenge                      │
│         └─► Returns PublicKeyCredentialCreationOptions      │
│                                                              │
│  2. Browser prompts for biometric                           │
│     └─► navigator.credentials.create()                      │
│         ├─► User authenticates (Face ID, Touch ID, etc)     │
│         └─► Creates credential (private key stays on device)│
│                                                              │
│  3. Send credential to server                               │
│     └─► POST /auth/passkey/register/verify                 │
│         ├─► Server verifies challenge                       │
│         ├─► Creates user account                            │
│         ├─► Generates 8 recovery codes                      │
│         ├─► Returns session token                           │
│         └─► Shows recovery codes in UI (NOT email)          │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     LOGIN FLOW                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. User enters email                                        │
│     └─► POST /auth/passkey/login/start                     │
│         ├─► Server looks up user's passkeys                 │
│         └─► Returns PublicKeyCredentialRequestOptions       │
│                                                              │
│  2. Browser prompts for biometric                           │
│     └─► navigator.credentials.get()                         │
│         ├─► User authenticates                              │
│         └─► Signs challenge with private key                │
│                                                              │
│  3. Send signed credential to server                        │
│     └─► POST /auth/passkey/login/verify                    │
│         ├─► Server verifies signature                       │
│         ├─► Creates session                                 │
│         └─► Returns session token                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Session Management

```
Session Lifecycle:
  ├── Absolute timeout: 7 days (hard limit)
  ├── Idle timeout: 24 hours (sliding window)
  └── Refresh: on every API call (last_active_at updated)

Storage:
  ├── Browser: localStorage.setItem('session_token', token)
  ├── Database: passkey_sessions table
  └── NATS: Optional session events for distributed state
```

### Recovery Mechanisms

**Recovery Codes** (primary):
- 8 codes generated on registration
- SHA-256 hashed in database
- One-time use (marked as used after verification)
- Rate limited: 5 attempts per hour
- **CRITICAL: Show in UI only, never email**

**Email Recovery** (nuclear option):
- 1-hour expiration token
- Invalidates all passkeys and sessions
- Requires re-registration with new passkey
- Use only for completely lost access

---

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id TEXT PRIMARY KEY,              -- user_{random}
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Passkey credentials (multiple per user)
CREATE TABLE passkey_credentials (
    id TEXT PRIMARY KEY,              -- cred_{random}
    user_id TEXT NOT NULL,
    credential_id TEXT UNIQUE NOT NULL,  -- base64url from WebAuthn
    public_key TEXT NOT NULL,            -- base64url encoded
    sign_count INTEGER DEFAULT 0,        -- replay attack prevention
    backup_eligible BOOLEAN DEFAULT FALSE,
    transports TEXT,                     -- JSON array
    friendly_name TEXT,                  -- "MacBook Pro", "iPhone 15"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Challenges (short-lived, 15 min expiration)
CREATE TABLE passkey_challenges (
    id TEXT PRIMARY KEY,              -- challenge_{random}
    challenge TEXT UNIQUE NOT NULL,   -- random bytes
    user_id TEXT,                     -- NULL for registration
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sessions (sliding expiration)
CREATE TABLE passkey_sessions (
    id TEXT PRIMARY KEY,              -- session_{random}
    user_id TEXT NOT NULL,
    session_token TEXT UNIQUE NOT NULL,  -- Bearer token
    expires_at TIMESTAMP NOT NULL,    -- 7 days absolute
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 24hr sliding
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Recovery codes (8 per user)
CREATE TABLE recovery_codes (
    id TEXT PRIMARY KEY,              -- recovery_{random}
    user_id TEXT NOT NULL,
    code_hash TEXT NOT NULL,          -- SHA-256 hash
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Email recovery tokens (1 hour expiration)
CREATE TABLE email_recovery_tokens (
    id TEXT PRIMARY KEY,              -- email_recovery_{random}
    user_id TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Recovery attempts (rate limiting)
CREATE TABLE recovery_attempts (
    id TEXT PRIMARY KEY,              -- attempt_{random}
    user_id TEXT NOT NULL,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT FALSE,
    ip_address TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
```

**Indexes** (critical for performance):
```sql
CREATE INDEX idx_passkey_credentials_user_id ON passkey_credentials(user_id);
CREATE INDEX idx_passkey_credentials_credential_id ON passkey_credentials(credential_id);
CREATE INDEX idx_passkey_sessions_user_id ON passkey_sessions(user_id);
CREATE INDEX idx_passkey_sessions_token ON passkey_sessions(session_token);
CREATE INDEX idx_recovery_codes_user_id ON recovery_codes(user_id);
CREATE INDEX idx_recovery_attempts_user_id ON recovery_attempts(user_id);
CREATE INDEX idx_recovery_attempts_attempted_at ON recovery_attempts(attempted_at);
```

---

## Backend Implementation

### Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "webauthn>=2.0.0",           # WebAuthn server library
    "python-multipart>=0.0.12",
]

[project.optional-dependencies]
email = [
    "sendgrid>=6.11.0",          # Optional: email recovery
]
```

### Service Layer

```python
# services/passkey_service.py
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    AuthenticatorAttachment,
)

class PasskeyService:
    def __init__(self, database):
        self.db = database

    def generate_registration_challenge(
        self, email: str, rp_id: str, origin: str
    ) -> tuple[str, dict]:
        """Generate WebAuthn registration challenge."""

        # Check if user exists
        existing_user = self.db.get_user_by_email(email)
        if existing_user:
            raise ValueError("User already exists")

        # Create challenge
        challenge_id, challenge = self.db.create_challenge()

        # Generate registration options
        options = generate_registration_options(
            rp_id=rp_id,
            rp_name="ChoirOS",
            user_id=challenge_id.encode(),
            user_name=email,
            user_display_name=email,
            challenge=challenge.encode(),
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            timeout=60000,  # 60 seconds
        )

        return challenge_id, json.loads(options_to_json(options))

    def verify_and_complete_registration(
        self, email: str, challenge_id: str,
        credential: dict, rp_id: str, origin: str
    ) -> tuple[dict, str, list[str]]:
        """Verify registration and create user."""

        # Get challenge
        challenge_data = self.db.get_challenge(challenge_id)
        if not challenge_data:
            raise ValueError("Challenge expired or invalid")

        # Verify registration response
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=challenge_data['challenge'].encode(),
            expected_origin=origin,
            expected_rp_id=rp_id,
            require_user_verification=True,
        )

        # Mark challenge as used
        self.db.mark_challenge_used(challenge_id)

        # Create user
        user = self.db.create_user(email)

        # Store passkey credential
        credential_id = base64.urlsafe_b64encode(
            verification.credential_id
        ).decode('utf-8').rstrip('=')

        public_key = base64.urlsafe_b64encode(
            verification.credential_public_key
        ).decode('utf-8').rstrip('=')

        self.db.store_passkey_credential(
            user_id=user['id'],
            credential_id=credential_id,
            public_key=public_key,
            sign_count=verification.sign_count,
            backup_eligible=verification.credential_backed_up,
        )

        # Generate recovery codes
        recovery_codes = self.db.generate_recovery_codes(user['id'])

        # Create session
        session_token = self.db.create_session(user['id'])

        return user, session_token, recovery_codes
```

### API Routes

```python
# api/routes/passkey_auth.py
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/auth/passkey")

@router.post("/register/start")
async def register_start(request: Request, email: str):
    """Start passkey registration."""

    # Get dynamic RP_ID and origin
    rp_id = request.url.hostname
    origin = f"{request.url.scheme}://{request.url.netloc}"

    try:
        challenge_id, options = passkey_service.generate_registration_challenge(
            email=email, rp_id=rp_id, origin=origin
        )
        return {"challenge_id": challenge_id, "options": options}

    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/register/verify")
async def register_verify(
    request: Request,
    email: str,
    challenge_id: str,
    credential: dict
):
    """Verify passkey registration and create user."""

    rp_id = request.url.hostname
    origin = f"{request.url.scheme}://{request.url.netloc}"

    try:
        user, session_token, recovery_codes = \
            passkey_service.verify_and_complete_registration(
                email=email,
                challenge_id=challenge_id,
                credential=credential,
                rp_id=rp_id,
                origin=origin,
            )

        # CRITICAL: Return codes to UI, don't email them
        return {
            "user": {"id": user['id'], "email": user['email']},
            "session_token": session_token,
            "recovery_codes": recovery_codes,
            "must_acknowledge": True,
            "warning": "Save these codes now - they won't be shown again"
        }

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
```

---

## Frontend Implementation

### WebAuthn Client

```typescript
// src/services/passkeyAuth.ts
export class PasskeyAuthService {

  async register(email: string): Promise<RegistrationResult> {
    // Step 1: Get challenge from server
    const startResponse = await fetch('/auth/passkey/register/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    if (!startResponse.ok) {
      const error = await startResponse.json();
      throw new Error(error.detail || 'Registration failed');
    }

    const { challenge_id, options } = await startResponse.json();

    // Step 2: Create credential using WebAuthn
    const credential = await navigator.credentials.create({
      publicKey: {
        challenge: this.base64urlToBuffer(options.challenge),
        rp: options.rp,
        user: {
          id: this.base64urlToBuffer(options.user.id),
          name: options.user.name,
          displayName: options.user.displayName,
        },
        pubKeyCredParams: options.pubKeyCredParams,
        timeout: options.timeout,
        authenticatorSelection: options.authenticatorSelection,
      }
    });

    if (!credential) {
      throw new Error('Failed to create passkey');
    }

    // Step 3: Verify with server
    const credentialData = this.credentialToJSON(credential);

    const verifyResponse = await fetch('/auth/passkey/register/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        challenge_id,
        credential: credentialData,
      }),
    });

    if (!verifyResponse.ok) {
      const error = await verifyResponse.json();
      throw new Error(error.detail || 'Verification failed');
    }

    const result = await verifyResponse.json();

    // Store session
    localStorage.setItem('session_token', result.session_token);
    localStorage.setItem('user_data', JSON.stringify(result.user));

    return result;
  }

  private base64urlToBuffer(base64url: string): ArrayBuffer {
    const padding = '='.repeat((4 - base64url.length % 4) % 4);
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/') + padding;
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  private bufferToBase64url(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary)
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  }
}
```

### Recovery Code UI Component

```tsx
// src/components/RecoveryCodesModal.tsx
export function RecoveryCodesModal({
  codes,
  onAcknowledge
}: {
  codes: string[],
  onAcknowledge: () => void
}) {
  const [downloaded, setDownloaded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleDownload = () => {
    const blob = new Blob([codes.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'choiros-recovery-codes.txt';
    a.click();
    setDownloaded(true);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(codes.join('\n'));
    setCopied(true);
  };

  return (
    <Modal>
      <h2>⚠️ Save Your Recovery Codes</h2>
      <p>
        These codes allow you to recover your account if you lose access to
        your passkey. Save them in a secure location like a password manager.
      </p>

      <div className="recovery-codes">
        {codes.map((code, i) => (
          <div key={i} className="code">{code}</div>
        ))}
      </div>

      <div className="actions">
        <button onClick={handleDownload}>
          📥 Download Codes
        </button>
        <button onClick={handleCopy}>
          📋 Copy to Clipboard
        </button>
      </div>

      <p className="warning">
        ⚠️ These codes will never be shown again. Make sure you've saved them
        before continuing.
      </p>

      <button
        onClick={onAcknowledge}
        disabled={!downloaded && !copied}
      >
        I've Saved My Recovery Codes
      </button>
    </Modal>
  );
}
```

---

## ChoirOS-Specific Adaptations

### 1. NATS Integration

Publish auth events to NATS for distributed state:

```python
# When user logs in
nats_client.publish(
    subject=f"user.{user_id}.session.created",
    payload={
        "user_id": user_id,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }
)

# When user logs out
nats_client.publish(
    subject=f"user.{user_id}.session.terminated",
    payload={
        "user_id": user_id,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }
)
```

### 2. S3 User Bucket Creation

Create per-user S3 bucket on registration:

```python
# After user creation
user = self.db.create_user(email)

# Create S3 bucket
s3_client.create_bucket(
    Bucket=f"choiros-user-{user['id']}",
    ACL='private'
)

# Initialize SQLite in S3
initial_db = sqlite3.connect(':memory:')
# ... initialize schema ...
s3_client.put_object(
    Bucket=f"choiros-user-{user['id']}",
    Key='workspace.sqlite',
    Body=initial_db_bytes
)
```

### 3. NATS Subject ACLs

When creating session, grant NATS permissions:

```python
# Session creation grants NATS permissions
nats_client.grant_user_permissions(
    user_id=user['id'],
    subjects=[
        f"user.{user['id']}.*",      # All user events
        f"agent.{user['id']}.*",     # Agent events
        "system.health",             # Global health checks
    ]
)
```

### 4. API Gateway Integration

Add session validation middleware:

```python
# middleware/auth.py
async def validate_session(request: Request):
    """Validate session token from Bearer header."""

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="No session token")

    token = auth_header.split(' ')[1]
    session = db.validate_session(token)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Attach user to request
    request.state.user_id = session['user_id']
    request.state.session = session
```

---

## Security Considerations

### DO ✅

- **Use HTTPS in production** (WebAuthn requires secure context)
- **Dynamic RP_ID** based on request hostname (localhost vs production)
- **Rate limit recovery attempts** (5/hour prevents brute force)
- **Hash recovery codes** (SHA-256, never store plaintext)
- **Show recovery codes in UI only** (never email them)
- **Require user acknowledgment** before hiding recovery codes
- **Validate challenge uniqueness** (prevent replay attacks)
- **Check sign count** (detect cloned authenticators)
- **Use sliding session expiration** (24hr idle timeout)
- **Clean up expired challenges** (periodic cleanup job)

### DON'T ❌

- **Don't email recovery codes** (insecure channel)
- **Don't skip user verification** (require biometric/PIN)
- **Don't allow challenge reuse** (mark as used after verification)
- **Don't store credentials in localStorage** (session token only)
- **Don't skip origin validation** (prevents credential reuse)
- **Don't use HTTP in production** (WebAuthn will fail)
- **Don't allow unlimited recovery attempts** (enable rate limiting)
- **Don't regenerate recovery codes automatically** (user must initiate)

---

## Implementation Checklist

### Phase 1: Backend Core
- [ ] Copy `database_passkeys.py` schema
- [ ] Adapt for ChoirOS database (SQLite/PostgreSQL)
- [ ] Add NATS event publishing
- [ ] Add S3 bucket creation on user registration
- [ ] Copy `passkey_service.py`
- [ ] Copy API routes
- [ ] Add session validation middleware
- [ ] Install `webauthn` package
- [ ] Test registration flow
- [ ] Test login flow

### Phase 2: Frontend Core
- [ ] Copy `passkeyAuth.ts` client
- [ ] Create auth context/store
- [ ] Build login page
- [ ] Build registration page
- [ ] Build recovery code modal
- [ ] Test WebAuthn flows in browser
- [ ] Add error handling
- [ ] Add loading states

### Phase 3: Recovery & Security
- [ ] Build recovery code entry UI
- [ ] Build email recovery flow
- [ ] Add rate limiting
- [ ] Add session management UI (list devices)
- [ ] Add passkey management UI (add/remove)
- [ ] Test recovery scenarios
- [ ] Add security logging

### Phase 4: ChoirOS Integration
- [ ] NATS subject ACLs on session creation
- [ ] S3 bucket initialization
- [ ] Desktop shell auth state
- [ ] Window manager session handling
- [ ] Logout cleanup (sessions, NATS permissions)
- [ ] Multi-device testing

### Phase 5: Production Hardening
- [ ] HTTPS enforcement
- [ ] Dynamic RP_ID configuration
- [ ] Session cleanup cron job
- [ ] Challenge cleanup cron job
- [ ] Security monitoring
- [ ] Incident response plan

---

## Testing

### Unit Tests

```python
# tests/test_passkey_service.py
def test_registration_flow():
    """Test complete registration flow."""

    # Generate challenge
    challenge_id, options = service.generate_registration_challenge(
        email="test@example.com",
        rp_id="localhost",
        origin="http://localhost:3000"
    )

    assert challenge_id.startswith("challenge_")
    assert "challenge" in options
    assert options["rp"]["id"] == "localhost"

    # Verify registration (mock credential)
    user, token, codes = service.verify_and_complete_registration(
        email="test@example.com",
        challenge_id=challenge_id,
        credential=mock_credential,
        rp_id="localhost",
        origin="http://localhost:3000"
    )

    assert user["email"] == "test@example.com"
    assert len(codes) == 8
    assert len(token) > 32
```

### Integration Tests

```typescript
// tests/passkey.test.ts
describe('Passkey Authentication', () => {
  it('should register new user', async () => {
    const service = new PasskeyAuthService();

    // Mock navigator.credentials.create
    global.navigator.credentials.create = jest.fn().mockResolvedValue(
      mockCredential
    );

    const result = await service.register('test@example.com');

    expect(result.user.email).toBe('test@example.com');
    expect(result.recovery_codes).toHaveLength(8);
    expect(result.session_token).toBeTruthy();
  });

  it('should login existing user', async () => {
    const service = new PasskeyAuthService();

    // Mock navigator.credentials.get
    global.navigator.credentials.get = jest.fn().mockResolvedValue(
      mockCredential
    );

    const result = await service.login('test@example.com');

    expect(result.user.email).toBe('test@example.com');
    expect(result.session_token).toBeTruthy();
  });
});
```

### Browser Testing

Test on multiple devices:
- ✅ Chrome/Edge (Windows Hello)
- ✅ Safari (Touch ID, Face ID)
- ✅ Firefox (security keys)
- ✅ Mobile Safari (iOS)
- ✅ Chrome Android

---

## Migration from Tuxedo

### What to Keep

**Core logic:**
- `PasskeyService` class (challenge generation/verification)
- Database schema (all tables)
- API route structure
- Frontend WebAuthn client
- Session management logic

**Security patterns:**
- Rate limiting
- Challenge expiration
- Session sliding window
- Recovery code hashing

### What to Change

**Tuxedo → ChoirOS adaptations:**

```python
# ❌ Tuxedo: Email recovery codes
await email_service.send_welcome_email(user['email'], recovery_codes)

# ✅ ChoirOS: Show in UI only
return {
    "recovery_codes": recovery_codes,
    "must_acknowledge": True,
    "warning": "Save these codes now - they won't be shown again"
}
```

```python
# ❌ Tuxedo: Simple session creation
session_token = db.create_session(user_id)

# ✅ ChoirOS: Session + NATS + S3
session_token = db.create_session(user_id)
nats_client.publish(f"user.{user_id}.session.created", {...})
nats_client.grant_permissions(user_id, subjects=[...])
s3_client.create_bucket(f"choiros-user-{user_id}")
```

### What to Remove

**Tuxedo-specific features (not needed for ChoirOS):**
- Stellar wallet integration
- DeFi vault management
- Chat thread storage
- Message history

**Keep only:**
- User accounts
- Passkey credentials
- Sessions
- Recovery codes
- Challenges

---

## Common Issues & Solutions

### Issue: "NotAllowedError: The operation either timed out or was not allowed"

**Cause:** User cancelled biometric prompt or took too long

**Solution:**
- Increase timeout to 60 seconds
- Show clear "waiting for biometric" UI
- Add retry button

### Issue: "SecurityError: The operation is insecure"

**Cause:** Not using HTTPS (except localhost)

**Solution:**
- Use HTTPS in production
- Localhost exemption works for development
- Use self-signed cert for staging

### Issue: Recovery codes emailed to user

**Cause:** Tuxedo sends codes via email

**Solution:**
- Remove email sending code
- Show codes in UI modal
- Require download/copy before dismissing
- Add acknowledgment checkbox

### Issue: Session expires too quickly

**Cause:** Short absolute timeout

**Solution:**
- Adjust absolute timeout (7 days)
- Adjust idle timeout (24 hours)
- Implement "remember me" (30 days)

### Issue: Multi-device passkeys not working

**Cause:** Cross-device authentication disabled

**Solution:**
- Set `authenticatorAttachment` to `undefined` (not `PLATFORM`)
- Enable security key support
- Test with iCloud Keychain sync

---

## Resources

**Tuxedo Reference:**
- `/Users/wiz/tuxedo/backend/database_passkeys.py` (schema)
- `/Users/wiz/tuxedo/backend/services/passkey_service.py` (service)
- `/Users/wiz/tuxedo/backend/api/routes/passkey_auth_refactored.py` (routes)
- `/Users/wiz/tuxedo/src/services/passkeyAuth.ts` (frontend)

**WebAuthn Specs:**
- [W3C WebAuthn Spec](https://www.w3.org/TR/webauthn-2/)
- [FIDO2 Overview](https://fidoalliance.org/fido2/)
- [py_webauthn Docs](https://github.com/duo-labs/py_webauthn)

**Testing:**
- [WebAuthn.io](https://webauthn.io/) - Test authenticators
- [WebAuthn Debugger](https://github.com/MasterKale/SimpleWebAuthn)

---

## Next Steps

1. **Read companion docs:**
   - [ARCHITECTURE.md](./ARCHITECTURE.md) - ChoirOS architecture
   - [DESKTOP.md](./DESKTOP.md) - Window manager integration
   - [NATS.md](./NATS.md) - Event bus for auth events

2. **Copy tuxedo code:**
   - Start with `database_passkeys.py` schema
   - Adapt service layer for ChoirOS
   - Port frontend client

3. **Add ChoirOS integrations:**
   - NATS event publishing
   - S3 bucket creation
   - Subject-level ACLs

4. **Test thoroughly:**
   - Multi-device flows
   - Recovery scenarios
   - Session management

5. **Production hardening:**
   - HTTPS enforcement
   - Security monitoring
   - Incident response

---

**The goal:** Passwordless, secure, biometric authentication for ChoirOS that integrates with the distributed architecture (S3, Firecracker; NATS later).

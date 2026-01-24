# Agent Brief: ChoirOS Implementation Recovery
**Mission:** Transform ChoirOS from demo-ware to production-ready system by executing the merged critical review plan.

## 🎯 Primary Objective
Close the gap between ChoirOS's architectural vision ("Automatic Computer") and its current unsafe demo state by systematically addressing security vulnerabilities, architectural flaws, and contract mismatches.

---

## 📋 Mission Parameters

### Success Criteria
- [ ] **Zero critical security vulnerabilities** (CORS, auth, git safety)
- [ ] **Deterministic event sourcing** (NATS as actual source of truth)
- [ ] **Contract alignment** (docs ↔ code event taxonomy consistency)
- [ ] **User safety guarantees** (no data loss, reversible operations)
- [ ] **Transparent UI** (clearly labeled mocks vs real functionality)

### Non-Goals
- ❌ No new features (Mail backend, Terminal, economic model)
- ❌ No scalability work (TEEs, microVMs, multi-user)
- ❌ No aesthetic improvements (theming, animations)
- ❌ No performance optimization (caching, indexing)

### Constraints
- **Timebox:** 2 weeks maximum
- **Risk tolerance:** Zero - this is recovery, not innovation
- **User impact:** Minimal breaking changes to existing workflows
- **Testing:** Every change must include validation

---

## 🚨 Phase 1: Emergency Security Fixes (Days 1-2)

### 1.1 Git Safety Implementation
**File:** `supervisor/git_ops.py`
```python
# BEFORE: Dangerous
def git_revert(sha: str):
    result = git_run("reset", "--hard", sha)  # NO SAFETY CHECKS

# AFTER: Safe
def git_revert(sha: str, dry_run: bool = True):
    # Validate SHA is reachable
    if not is_reachable_commit(sha):
        raise ValueError(f"Commit {sha} is not reachable")
    
    # Create backup branch
    backup_branch = f"backup-before-revert-{int(time.time())}"
    git_run("branch", backup_branch)
    
    # Preview changes
    if dry_run:
        return {
            "dry_run": True,
            "backup_branch": backup_branch,
            "changes": get_diff_preview(sha)
        }
    
    # Execute with backup
    result = git_run("reset", "--hard", sha)
    return {"success": True, "backup_branch": backup_branch}
```

**Tasks:**
- [ ] Add commit reachability validation
- [ ] Implement automatic backup branches before destructive operations
- [ ] Add dry-run mode for git operations
- [ ] Create `.choirignore` file for generated content
- [ ] Test revert operations with various edge cases

### 1.2 Authentication Foundation
**File:** `supervisor/main.py`
```python
# Add to FastAPI app
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Validate JWT token
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Protect all endpoints
@app.post("/git/checkpoint")
async def git_checkpoint(message: str = None, user_id: str = Depends(get_current_user)):
    # Now user-aware
```

**Tasks:**
- [ ] Implement JWT-based authentication
- [ ] Add user isolation to all endpoints
- [ ] Create user registration/login endpoints
- [ ] Update frontend to send auth tokens

### 1.3 CORS Security
**File:** `supervisor/main.py`
```python
# BEFORE: Insecure
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ANY ORIGIN ALLOWED
)

# AFTER: Secure
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Explicit origins only
    allow_credentials=True,  # Required for auth
    allow_methods=["GET", "POST"],  # Restrict methods
    allow_headers=["Authorization", "Content-Type"],  # Restrict headers
)
```

**Tasks:**
- [ ] Restrict CORS to explicit origins
- [ ] Remove wildcard allowances
- [ ] Add environment-based CORS config
- [ ] Test cross-origin requests

---

## 🔧 Phase 2: Event Contract Alignment (Days 3-4)

### 2.1 Event Taxonomy Standardization
**Decision Matrix:**
| Aspect | Current Docs | Current Code | **Target** |
|--------|--------------|--------------|------------|
| Subject format | `choiros.{user_id}.{source}.{type}` | `choiros.{source}.{user_id}.{type}` | **Docs version** |
| Event types | `file.write` | `FILE_WRITE` | **Dot notation** |
| Streams | `CHOIR` | `USER_EVENTS`, etc. | **Single `CHOIR` stream** |

**Implementation:**
```python
# File: supervisor/nats_client.py
class EventPublisher:
    def publish_event(self, user_id: str, source: str, event_type: str, payload: dict):
        # Standardized subject format
        subject = f"choiros.{user_id}.{source}.{event_type}"
        
        # Standardized event structure
        event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "source": source,
            "type": event_type,  # Dot notation
            "payload": payload
        }
        
        self.js.publish(subject, json.dumps(event).encode())
```

**Tasks:**
- [ ] Update all event publishing to use standardized format
- [ ] Create event type constants file
- [ ] Migrate existing SQLite events to new format
- [ ] Update frontend event handling

### 2.2 NATS WebSocket Configuration
**File:** `docker-compose.yml`
```yaml
services:
  nats:
    ports:
      - "4222:4222"   # Client connections
      - "8222:8222"   # Monitoring UI
      - "8080:8080"   # WebSocket port - ADD THIS
    command: --jetstream --store_dir /data --websocket_port 8080
```

**File:** `choiros/src/lib/nats.ts`
```typescript
// Update connection config
const NATS_WS_URL = import.meta.env.VITE_NATS_WS_URL || 'ws://localhost:8080';
```

**Tasks:**
- [ ] Expose NATS WebSocket port in docker-compose
- [ ] Update frontend NATS client configuration
- [ ] Test WebSocket connection from browser
- [ ] Document NATS WS setup requirements

---

## 🔗 Phase 3: Close the Event Loop (Days 5-6)

### 3.1 Frontend NATS Integration
**File:** `choiros/src/stores/events.ts`
```typescript
// Replace local Zustand store with NATS subscription
import { connectNats, subscribeUserEvents } from '../lib/nats';

export const useEventStore = create<EventStore>((set, get) => ({
    events: [],
    
    // Initialize NATS connection and subscribe to events
    initializeNats: async () => {
        await connectNats();
        
        // Subscribe to real events
        await subscribeUserEvents((event) => {
            set((state) => ({
                events: [...state.events, event],
            }));
        });
    },
    
    // Remove old local event methods
}));
```

**Tasks:**
- [ ] Initialize NATS connection on app startup
- [ ] Replace local event store with NATS subscription
- [ ] Update EventStream component to handle real events
- [ ] Remove auto-clearing logic (events should persist)

### 3.2 Unified State Management
**File:** `supervisor/db.py`
```python
class UnifiedStore:
    def __init__(self):
        self.sqlite = SQLiteStore()
        self.nats = NATSStore()
    
    def write_event(self, event: Event):
        # Always write to both stores
        self.sqlite.write_event(event)
        self.nats.write_event(event)
    
    def rebuild_state(self):
        # Rebuild from authoritative source (NATS)
        events = self.nats.get_all_events()
        self.sqlite.rebuild_from_events(events)
```

**Tasks:**
- [ ] Create unified store that writes to both SQLite and NATS
- [ ] Implement state rebuilding from NATS authoritative source
- [ ] Add consistency checks between stores
- [ ] Handle NATS unavailability gracefully

---

## 🛡️ Phase 4: Safety & Reliability (Days 7-8)

### 4.1 Artifact Persistence
**File:** `api/services/artifact_store.py`
```python
# Replace in-memory dict with SQLite
class ArtifactStore:
    def __init__(self, db_path: str = "artifacts.sqlite"):
        self.conn = sqlite3.connect(db_path)
        self._init_schema()
    
    def store_artifact(self, artifact_id: str, content: str, metadata: dict):
        self.conn.execute(
            "INSERT OR REPLACE INTO artifacts (id, content, metadata, created_at) VALUES (?, ?, ?, ?)",
            (artifact_id, content, json.dumps(metadata), datetime.utcnow())
        )
        self.conn.commit()
```

**Tasks:**
- [ ] Replace in-memory artifact storage with SQLite
- [ ] Add artifact persistence across API restarts
- [ ] Implement artifact cleanup/garbage collection
- [ ] Test artifact storage/retrieval

### 4.2 Git Safety Enhancements
**File:** `supervisor/git_ops.py`
```python
# Add comprehensive ignore patterns
CHOIR_IGNORE_PATTERNS = [
    "*.log",
    "*.tmp",
    "node_modules/",
    "dist/",
    "build/",
    ".env*",
    "*.sqlite-journal",
    "__pycache__/",
    ".choir/"  # Internal state
]

def create_checkpoint(message: str):
    # Filter out ignored files
    status = get_status()
    filtered_status = filter_ignored_files(status)
    
    if not filtered_status.has_changes:
        return {"success": True, "message": "No changes to commit"}
    
    # Create checkpoint with safety checks
    return create_safe_checkpoint(filtered_status, message)
```

**Tasks:**
- [ ] Create comprehensive .gitignore for generated files
- [ ] Add file filtering before git operations
- [ ] Implement checkpoint preview/dry-run mode
- [ ] Add rollback capability for checkpoints

---

## 📋 Phase 5: UI Transparency (Days 9-10)

### 5.1 Mock Labeling
**File:** `choiros/src/components/apps/Mail.tsx`
```typescript
export function Mail() {
    return (
        <div className="mail-app">
            <div className="demo-banner">
                <IconInfoCircle size={16} />
                <span>Demo data - Mail backend not yet implemented</span>
            </div>
            {/* Existing mail UI */}
        </div>
    );
}
```

**File:** `choiros/src/components/desktop/EventStream.tsx`
```typescript
export function EventStream() {
    const isConnected = useNatsStore(state => state.isConnected);
    
    if (!isConnected) {
        return (
            <div className="event-stream-offline">
                <IconWifiOff size={16} />
                <span>Event stream offline - showing local notifications only</span>
            </div>
        );
    }
    
    // Real event stream
}
```

**Tasks:**
- [ ] Add demo banners to all mock UI components
- [ ] Show connection status for event stream
- [ ] Create consistent labeling for incomplete features
- [ ] Update documentation to reflect current state

### 5.2 Terminal Decision
**Decision:** Remove Terminal from UI until implementation is ready

**File:** `choiros/src/components/desktop/Desktop.tsx`
```typescript
// Remove terminal icon until implemented
const defaultIcons = [
    { id: 'files', label: 'Files', icon: 'folder', x: 20, y: 20 },
    { id: 'writer', label: 'Writer', icon: 'file-text', x: 20, y: 100 },
    { id: 'git', label: 'Git', icon: 'git-branch', x: 20, y: 180 },
    // { id: 'terminal', label: 'Terminal', icon: 'terminal', x: 20, y: 260 }, // REMOVED
];
```

**Tasks:**
- [ ] Remove terminal icon from desktop
- [ ] Update documentation to mark terminal as not implemented
- [ ] Create placeholder or remove from roadmap

---

## 🧪 Phase 6: Testing & Validation (Days 11-12)

### 6.1 Security Testing
```bash
# Test authentication
curl -X POST http://localhost:8001/git/checkpoint \
  -H "Content-Type: application/json" \
  # Should fail with 401

# Test CORS restrictions
curl -H "Origin: http://malicious-site.com" \
  http://localhost:8001/health \
  # Should be blocked

# Test git safety
curl -X POST http://localhost:8001/git/revert \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"sha": "invalid-sha"}' \
  # Should fail gracefully
```

### 6.2 Event System Testing
```python
# Test event consistency
def test_event_contract():
    event = publish_event("test_user", "user", "file.write", {"path": "test.txt"})
    
    # Verify subject format
    assert event.subject == "choiros.test_user.user.file.write"
    
    # Verify event structure
    assert event.type == "file.write"  # Dot notation
    assert "timestamp" in event.payload
    assert "id" in event.payload
```

### 6.3 End-to-End Testing
```typescript
// Test full event loop
describe('Event System', () => {
    it('should display real events from NATS', async () => {
        // Publish event via API
        await fetch('/api/event', {
            method: 'POST',
            body: JSON.stringify({
                type: 'file.write',
                path: 'test.txt',
                content: 'test'
            })
        });
        
        // Verify event appears in UI
        await waitFor(() => {
            const events = screen.getByTestId('event-stream');
            expect(events).toHaveTextContent('file.write');
        });
    });
});
```

---

## 📊 Success Metrics Checklist

### Security ✅
- [ ] All endpoints require authentication
- [ ] CORS restricted to explicit origins
- [ ] Git operations have safety checks
- [ ] No wildcard permissions

### Event System ✅
- [ ] NATS WebSocket connection working
- [ ] Frontend displays real events
- [ ] Event format matches documentation
- [ ] State rebuilding from NATS works

### Reliability ✅
- [ ] Artifacts persist across restarts
- [ ] Git operations are reversible
- [ ] Generated files are ignored
- [ ] Mock UI clearly labeled

### Contract Alignment ✅
- [ ] Subject format: `choiros.{user_id}.{source}.{type}`
- [ ] Event types use dot notation
- [ ] Single `CHOIR` stream documented
- [ ] Per-user layout planned (future)

---

## 🚨 Abort Conditions

**Stop immediately if:**
- Any security fix introduces new vulnerabilities
- Event system changes break existing functionality
- Git operations cause data loss during testing
- Authentication breaks legitimate user workflows

**Escalate if:**
- NATS integration requires major architectural changes
- User isolation reveals fundamental design flaws
- Contract alignment conflicts with existing client code

---

## 📦 Delivery Checklist

Before marking complete:
- [ ] All tests pass
- [ ] Security scan clean
- [ ] Documentation updated
- [ ] Breaking changes documented
- [ ] Rollback plan tested
- [ ] Performance impact measured

**Final verification:**
```bash
# Run full test suite
npm test && pytest && ./security-scan.sh

# Verify no data loss scenarios
./test-git-safety.sh

# Check event system integrity
./test-event-contract.sh
```

---

*Agent: Execute with precision. This is recovery, not feature development. Every change must make the system more secure, reliable, and aligned with its documented contracts.*
# ChoirOS Next Steps Checklist

## 🎯 CONTRACT ALIGNMENT (Docs ↔ Code) - High Priority

### Event Stream Contract
- [ ] **Decide and document canonical NATS subject format** - Resolve `choiros.{user_id}.{source}.{type}` (docs) vs `choiros.{source}.{user_id}.{type}` (code)
- [ ] **Standardize event type naming** - Align dot-delimited (`file.write`) vs underscore (`file_write`) vs uppercase (`FILE_WRITE`) across NATS, SQLite, and UI
- [ ] **Align stream naming** - Docs reference single `CHOIR` stream, code uses `USER_EVENTS`/`AGENT_EVENTS`/`SYSTEM_EVENTS`
- [ ] **Document NATS WebSocket requirement** - Expose WS port in docker-compose and provide setup instructions

### Operational Contracts
- [ ] **Clarify per-user filesystem layout** - Docs show `/users/{user_id}/.choir` but code uses single repo root
- [ ] **Decide on NATS optional vs mandatory** - Determine if system should fail when NATS disconnected
- [ ] **Label UI stubs clearly** - Add "Mock data"/"Demo only" indicators to Mail and other sample-data apps

## 🚨 CRITICAL SECURITY & SAFETY FIXES

### Immediate Actions (Do Not Deploy Without These)
- [ ] **Disable dangerous git operations** - Remove or severely restrict `git reset --hard` functionality
- [ ] **Add authentication system** - Implement basic user auth before any public access
- [ ] **Fix CORS configuration** - Replace `allow_origins=["*"]` with proper origin restrictions
- [ ] **Implement input validation** - Sanitize all user inputs and API parameters
- [ ] **Add file operation safeguards** - Prevent agent from modifying critical system files
- [ ] **Fix hardcoded configuration** - Move URLs and user IDs to environment variables

## 🔧 CORE ARCHITECTURE FIXES

## 🔧 CORE ARCHITECTURE FIXES

### Phase 1: Closing the Loop (Highest Priority)
- [ ] **Wire NATS to Frontend**
    - [ ] Initialize `connectNats()` in `choiros/src/App.tsx` (or a high-level provider)
    - [ ] Subscribe to `choiros.user.local.>` in `choiros/src/stores/events.ts`
    - [ ] Update `EventStream` to display real events from NATS instead of just local notifications
- [ ] **Fix NATS integration** - Remove `NATS_ENABLED=0` from dev.sh and make event sourcing work
- [ ] **Unify State**
    - [ ] Make `api` service use `state.sqlite` (or a shared DB service) instead of in-memory dictionaries for artifacts
    - [ ] Ensure `api` and `supervisor` share the same volume/storage path for persistence
- [ ] **Implement proper event serialization** - Fix type errors in event system
- [ ] **Add event persistence** - Ensure events survive system restarts
- [ ] **Build deterministic replay** - Implement actual time-travel functionality
- [ ] **Create event schema validation** - Validate all events before processing

### State Management
- [ ] **Consolidate state systems** - Choose single source of truth (NATS vs SQLite vs Git)
- [ ] **Implement state consistency checks** - Add validation between state layers
- [ ] **Add state backup/restore** - Create reliable backup mechanisms
- [ ] **Fix type safety issues** - Resolve TypeScript errors in agent harness

### Phase 2: Event Sourcing Completeness
- [ ] **Make `rebuild_from_nats` comprehensive** - Re-materialize messages, tool calls, and conversations, not just file events
- [ ] **Add deterministic replay tests** - SQLite after replay should match pre-replay state
- [ ] **Decide on NATS enforcement** - Fail writes when NATS disconnected if making it mandatory
- [ ] **Fix event type normalization** - SQLite stores `file.write` while NATS replays store `file_write`

## 🛡️ USER SAFETY & RELIABILITY

### Git Operations
- [ ] **Add git safety mechanisms** - Implement backup before destructive operations
- [ ] **Create .gitignore patterns** - Exclude build artifacts, logs, sensitive files
- [ ] **Add commit validation** - Validate commits before pushing
- [ ] **Implement gradual undo** - Support multi-level undo instead of hard resets
- [ ] **Add git status warnings** - Warn users about destructive operations

### Phase 2: Persistence & Reliability
- [ ] **Implement Artifact Persistence**
    - [ ] Replace `api/services/artifact_store.py` in-memory dict with SQLite (or filesystem) backing
- [ ] **Implement File Watchers**
    - [ ] Ensure the frontend `Files` app updates automatically when the Agent writes a file (via NATS event `file.write`)
- [ ] **Create backup strategy** - Automated backup of user data and state
- [ ] **Build migration system** - Handle schema changes and updates

### Phase 3: De-Stubbing with Transparency
- [ ] **Implement Mail Backend**
    - [ ] Create a `MailService` in `api` or `supervisor`
    - [ ] Connect `Mail.tsx` to fetch real emails (or at least persisted fake ones)
- [ ] **Implement/Remove Terminal**
    - [ ] Either implement the `Terminal` app or remove it from docs
- [ ] **Wire EventStream UI to NATS** - Or rename component to indicate it's local-only notifications

### Agent System
- [ ] **Implement tool sandboxing** - Restrict agent to safe operations only
- [ ] **Add operation rollback** - Allow undoing agent actions
- [ ] **Create operation limits** - Prevent runaway or excessive operations
- [ ] **Add agent operation logging** - Comprehensive audit trail for agent actions
- [ ] **Implement permission system** - Control what agents can and cannot do

## 📋 IMPLEMENTATION GAPS

### Missing Core Features
- [ ] **Implement real terminal** - Replace stub with actual terminal functionality
- [ ] **Build file system abstraction** - Create proper virtual file system
- [ ] **Add user isolation** - Implement per-user workspaces and data separation
- [ ] **Create workspace management** - Support multiple user workspaces
- [ ] **Implement proper error handling** - Add comprehensive error boundaries and recovery
- [ ] **Configuration Management** - Move hardcoded URLs (NATS, API) to `config.ts` / environment variables
- [ ] **Soften CORS restrictions** - Make them configurable instead of hardcoded localhost

### Deployment & Operations
- [ ] **Build CI/CD pipeline** - Implement automated deployment from git push
- [ ] **Create production Dockerfile** - Optimize for production deployment
- [ ] **Add monitoring and observability** - Implement logging, metrics, health checks
- [ ] **Create backup strategy** - Automated backup of user data and state
- [ ] **Build migration system** - Handle schema changes and updates

## 🎯 PRODUCT VALIDATION

### User Experience
- [ ] **Simplify "pansynchronous" concept** - Create clear mental model for users
- [ ] **Add progress indicators** - Show what background tasks are doing
- [ ] **Implement notification system** - Inform users of completed operations
- [ ] **Create onboarding flow** - Help users understand the system
- [ ] **Add help documentation** - In-app guidance and tutorials

### Testing & Validation
- [ ] **Write comprehensive tests** - Unit, integration, and end-to-end tests
- [ ] **Create staging environment** - Safe testing before production deployment
- [ ] **Implement feature flags** - Gradual rollout of new features
- [ ] **Add user feedback system** - Collect and act on user input
- [ ] **Create performance benchmarks** - Ensure system scales appropriately

## 🚫 DEFERRED (Post-MVP)

### Advanced Features (Do Not Build Yet)
- [ ] **Economic model (USDC/CHIP)** - Wait until core system is stable
- [ ] **Firecracker microVMs** - Focus on container-based solution first
- [ ] **TEE/SGX integration** - Advanced security for later phase
- [ ] **Multi-user collaboration** - Start with single-user focus
- [ ] **Custom domains** - Identity features after core product works
- [ ] **Citation graph** - Network effects after individual value proven

### Nice-to-Haves
- [ ] **Mobile responsive design** - Desktop-first approach
- [ ] **Advanced theming** - Basic theming sufficient for MVP
- [ ] **Plugin system** - Extensibility after core stable
- [ ] **Advanced search** - Basic search sufficient initially
- [ ] **Integration APIs** - External integrations later

## 📊 SUCCESS METRICS

### Technical Health
- [ ] **Zero data loss incidents** - Reliable state management
- [ ] **Sub-second response times** - Performance targets met
- [ ] **99.9% uptime** - System reliability
- [ ] **No security vulnerabilities** - Regular security audits
- [ ] **Automated deployment success** - CI/CD pipeline working

### User Satisfaction
- [ ] **Users can complete basic workflows** - Core functionality usable
- [ ] **Positive user feedback** - Net Promoter Score > 30
- [ ] **Low support burden** - Users can self-serve issues
- [ ] **Retention rate > 50%** - Users continue using system
- [ ] **Referral rate > 10%** - Users recommend to others

## 🏃‍♂️ IMMEDIATE NEXT ACTIONS (This Week)

1. **Monday**: Fix critical security issues (auth, CORS, git safety)
2. **Tuesday**: Resolve NATS integration and event sourcing
3. **Wednesday**: Fix TypeScript errors and type safety
4. **Thursday**: Implement basic user isolation
5. **Friday**: Create comprehensive error handling
6. **Weekend**: Write tests for critical paths

## 📝 DAILY STANDUP QUESTIONS

- What critical safety issues did we fix today?
- Are users' data and work protected from loss?
- Can we safely deploy this to production?
- What security vulnerabilities remain?
- Are all state changes reversible and auditable?
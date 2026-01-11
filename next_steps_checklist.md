# Next Steps Checklist

## Phase 1: Closing the Loop (High Priority)
- [ ] **Wire NATS to Frontend**
    - [ ] Initialize `connectNats()` in `choiros/src/App.tsx` (or a high-level provider).
    - [ ] Subscribe to `choiros.user.local.>` in `choiros/src/stores/events.ts`.
    - [ ] Update `EventStream` to display real events from NATS instead of just local notifications.
- [ ] **Unify State**
    - [ ] Make `api` service use `state.sqlite` (or a shared DB service) instead of in-memory dictionaries for artifacts.
    - [ ] Ensure `api` and `supervisor` share the same volume/storage path for persistence.

## Phase 2: Persistence & Reliability
- [ ] **Implement Artifact Persistence**
    - [ ] Replace `api/services/artifact_store.py` in-memory dict with SQLite (or filesystem) backing.
- [ ] **Implement File Watchers**
    - [ ] Ensure the frontend `Files` app updates automatically when the Agent writes a file (via NATS event `file.write`).

## Phase 3: De-Stubbing
- [ ] **Implement Mail Backend**
    - [ ] Create a `MailService` in `api` or `supervisor`.
    - [ ] Connect `Mail.tsx` to fetch real emails (or at least persisted fake ones).
- [ ] **Implement/Remove Terminal**
    - [ ] Either implement the `Terminal` app or remove the icon from `Desktop.tsx`.

## Phase 4: Hardening
- [ ] **Configuration**
    - [ ] Move hardcoded URLs (NATS, API) to `config.ts` / environment variables injected at runtime.
    - [ ] Soften `CORS` restrictions or make them configurable.
- [ ] **Agent Safety**
    - [ ] Verify `AgentHarness` respects sandbox boundaries (currently it has broad file access).

## Phase 5: Deployment
- [ ] **CI/CD**
    - [ ] Implement the "Git-based self-hosted deployment loop" mentioned in docs.

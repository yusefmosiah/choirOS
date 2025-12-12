# Storage & State Architecture

> Per-user SQLite, S3 sync, and Qdrant vectors.

---

## Core Principle

**Every user owns their state as a single SQLite file.**

- No shared database, no connection pools
- Export = download your `.sqlite` file
- Import = upload a `.sqlite` file
- Sync = push/pull to S3

---

## SQLite Schema

```sql
-- User's local database schema
-- File: workspace.sqlite

-- Artifacts (files, documents, notes)
CREATE TABLE artifacts (
  id TEXT PRIMARY KEY,
  path TEXT NOT NULL,                    -- Virtual path: /docs/notes.md
  name TEXT NOT NULL,
  mime_type TEXT,
  content BLOB,                          -- For small files < 1MB
  s3_key TEXT,                           -- For large files, pointer to S3
  size_bytes INTEGER,
  hash TEXT,                             -- SHA-256 for change detection
  created_at INTEGER NOT NULL,           -- Unix timestamp ms
  updated_at INTEGER NOT NULL,
  metadata JSON                          -- Extensible metadata
);

CREATE INDEX idx_artifacts_path ON artifacts(path);
CREATE INDEX idx_artifacts_updated ON artifacts(updated_at);

-- Action log (what happened, when)
CREATE TABLE action_log (
  id TEXT PRIMARY KEY,
  timestamp INTEGER NOT NULL,
  action_type TEXT NOT NULL,             -- ARTIFACT_CREATE, COMMAND, etc.
  payload JSON NOT NULL,
  synced INTEGER DEFAULT 0               -- Has this been pushed to NATS?
);

CREATE INDEX idx_action_log_timestamp ON action_log(timestamp);
CREATE INDEX idx_action_log_synced ON action_log(synced);

-- Agent tasks (pending, running, completed)
CREATE TABLE agent_tasks (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,                  -- PENDING, RUNNING, COMPLETED, FAILED
  task_type TEXT NOT NULL,
  input JSON NOT NULL,
  output JSON,
  created_at INTEGER NOT NULL,
  started_at INTEGER,
  completed_at INTEGER,
  error TEXT
);

CREATE INDEX idx_agent_tasks_status ON agent_tasks(status);

-- Citations (the economic record)
CREATE TABLE citations (
  id TEXT PRIMARY KEY,
  source_artifact_id TEXT NOT NULL,      -- What artifact was cited
  citing_run_id TEXT NOT NULL,           -- Which agent run cited it
  weight REAL NOT NULL,                  -- 0.0 - 1.0
  reason TEXT,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (source_artifact_id) REFERENCES artifacts(id)
);

CREATE INDEX idx_citations_source ON citations(source_artifact_id);

-- Sync state
CREATE TABLE sync_state (
  key TEXT PRIMARY KEY,
  value TEXT
);

-- Track database version for migrations
PRAGMA user_version = 1;
```

---

## Browser-Side SQLite (sql.js)

### Initialization

```typescript
// lib/db.ts
import initSqlJs, { Database } from 'sql.js';

let db: Database | null = null;

export async function initDatabase(): Promise<Database> {
  const SQL = await initSqlJs({
    locateFile: (file) => `/sql-wasm.wasm`,
  });

  // Try to load from IndexedDB cache first
  const cached = await loadFromCache();

  if (cached) {
    db = new SQL.Database(cached);
  } else {
    db = new SQL.Database();
    await runMigrations(db);
  }

  return db;
}

export function getDb(): Database {
  if (!db) throw new Error('Database not initialized');
  return db;
}
```

### CRUD Operations

```typescript
// lib/artifacts.ts
import { getDb } from './db';
import { v4 as uuid } from 'uuid';

export interface Artifact {
  id: string;
  path: string;
  name: string;
  mimeType: string | null;
  content: Uint8Array | null;
  s3Key: string | null;
  sizeBytes: number;
  hash: string | null;
  createdAt: number;
  updatedAt: number;
  metadata: Record<string, any>;
}

export function createArtifact(
  path: string,
  content: Uint8Array,
  mimeType: string
): Artifact {
  const db = getDb();
  const id = uuid();
  const now = Date.now();
  const name = path.split('/').pop() || 'untitled';

  db.run(`
    INSERT INTO artifacts (id, path, name, mime_type, content, size_bytes, created_at, updated_at, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `, [id, path, name, mimeType, content, content.length, now, now, '{}']);

  // Log action
  logAction('ARTIFACT_CREATE', { artifact_id: id, path });

  return {
    id,
    path,
    name,
    mimeType,
    content,
    s3Key: null,
    sizeBytes: content.length,
    hash: null,
    createdAt: now,
    updatedAt: now,
    metadata: {},
  };
}

export function getArtifact(id: string): Artifact | null {
  const db = getDb();
  const result = db.exec(`SELECT * FROM artifacts WHERE id = ?`, [id]);

  if (result.length === 0 || result[0].values.length === 0) {
    return null;
  }

  return rowToArtifact(result[0].columns, result[0].values[0]);
}

export function listDirectory(path: string): Artifact[] {
  const db = getDb();
  const prefix = path.endsWith('/') ? path : path + '/';

  const result = db.exec(`
    SELECT * FROM artifacts
    WHERE path LIKE ?
    AND path NOT LIKE ?
    ORDER BY name
  `, [prefix + '%', prefix + '%/%']);

  if (result.length === 0) return [];

  return result[0].values.map(row =>
    rowToArtifact(result[0].columns, row)
  );
}

export function updateArtifact(id: string, content: Uint8Array): void {
  const db = getDb();
  const now = Date.now();

  db.run(`
    UPDATE artifacts
    SET content = ?, size_bytes = ?, updated_at = ?
    WHERE id = ?
  `, [content, content.length, now, id]);

  logAction('ARTIFACT_UPDATE', { artifact_id: id });
}
```

---

## S3 Sync

### Structure

```
s3://choiros-data/
└── users/
    └── {user_id}/
        ├── workspace.sqlite     # The database
        └── artifacts/           # Large files (> 1MB)
            ├── {artifact_id_1}
            └── {artifact_id_2}
```

### Sync Logic

```typescript
// lib/sync.ts
import { getDb } from './db';

interface SyncState {
  lastSyncTimestamp: number;
  lastLocalVersion: number;
  lastRemoteVersion: number;
}

export async function syncToS3(): Promise<void> {
  const db = getDb();
  const userId = getUserId();

  // Export database to binary
  const data = db.export();
  const blob = new Blob([data], { type: 'application/x-sqlite3' });

  // Get presigned upload URL from API
  const { uploadUrl } = await api.getUploadUrl(userId, 'workspace.sqlite');

  // Upload
  await fetch(uploadUrl, {
    method: 'PUT',
    body: blob,
    headers: {
      'Content-Type': 'application/x-sqlite3',
    },
  });

  // Update sync state
  setSyncState('lastSyncTimestamp', Date.now().toString());

  // Emit sync complete event to NATS
  await publishEvent(`choiros.user.${userId}.sync.complete`, {
    direction: 'PUSH',
    timestamp: Date.now(),
  });
}

export async function syncFromS3(): Promise<void> {
  const userId = getUserId();

  // Get presigned download URL
  const { downloadUrl } = await api.getDownloadUrl(userId, 'workspace.sqlite');

  // Download
  const response = await fetch(downloadUrl);
  const arrayBuffer = await response.arrayBuffer();

  // Replace local database
  const SQL = await initSqlJs();
  db = new SQL.Database(new Uint8Array(arrayBuffer));

  // Save to IndexedDB cache
  await saveToCache(db.export());

  setSyncState('lastSyncTimestamp', Date.now().toString());
}

// Debounced auto-sync on changes
let syncTimeout: number | null = null;

export function scheduleSyncToS3(delayMs = 5000): void {
  if (syncTimeout) {
    clearTimeout(syncTimeout);
  }
  syncTimeout = setTimeout(() => {
    syncToS3();
    syncTimeout = null;
  }, delayMs);
}
```

### Large File Handling

```typescript
// Files > 1MB go directly to S3, not in SQLite

export async function uploadLargeArtifact(
  path: string,
  file: File
): Promise<Artifact> {
  const userId = getUserId();
  const id = uuid();

  // Upload to S3
  const s3Key = `users/${userId}/artifacts/${id}`;
  const { uploadUrl } = await api.getUploadUrl(userId, s3Key);

  await fetch(uploadUrl, {
    method: 'PUT',
    body: file,
    headers: {
      'Content-Type': file.type,
    },
  });

  // Store metadata in SQLite (content = null, s3_key = set)
  const db = getDb();
  const now = Date.now();

  db.run(`
    INSERT INTO artifacts (id, path, name, mime_type, content, s3_key, size_bytes, created_at, updated_at, metadata)
    VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
  `, [id, path, file.name, file.type, s3Key, file.size, now, now, '{}']);

  return getArtifact(id)!;
}
```

---

## Qdrant Vector DB

Hosted on EC2, shared across all users (but queries are always scoped to user).

### Collection Schema

```json
{
  "name": "artifacts",
  "vectors": {
    "size": 384,
    "distance": "Cosine"
  },
  "payload_schema": {
    "user_id": "keyword",
    "artifact_id": "keyword",
    "path": "keyword",
    "content_preview": "text"
  }
}
```

### Indexing Flow

```
User saves artifact
    │
    ▼
NATS: choiros.user.{id}.file.UPDATED
    │
    ▼
Embedding worker (subscribes to file events):
    1. Fetch artifact content
    2. Generate embedding (all-MiniLM-L6-v2)
    3. Upsert to Qdrant with user_id filter
```

### Search

```typescript
// lib/search.ts

export async function semanticSearch(
  query: string,
  limit = 10
): Promise<SearchResult[]> {
  const userId = getUserId();

  // Generate query embedding (can happen in-browser with Transformers.js)
  const embedding = await generateEmbedding(query);

  // Search Qdrant (via API)
  const results = await api.search({
    collection: 'artifacts',
    vector: embedding,
    filter: {
      must: [{ key: 'user_id', match: { value: userId } }],
    },
    limit,
  });

  return results.map(r => ({
    artifactId: r.payload.artifact_id,
    path: r.payload.path,
    score: r.score,
    preview: r.payload.content_preview,
  }));
}
```

---

## Zustand Stores

### Artifact Store

```typescript
// stores/artifacts.ts
import { create } from 'zustand';
import { Artifact, createArtifact, getArtifact, listDirectory, updateArtifact } from '../lib/artifacts';
import { scheduleSyncToS3 } from '../lib/sync';

interface ArtifactStore {
  cache: Map<string, Artifact>;

  load: (id: string) => Promise<Artifact | null>;
  list: (path: string) => Artifact[];
  create: (path: string, content: Uint8Array, mimeType: string) => Artifact;
  update: (id: string, content: Uint8Array) => void;
  delete: (id: string) => void;
}

export const useArtifactStore = create<ArtifactStore>((set, get) => ({
  cache: new Map(),

  load: async (id) => {
    const cached = get().cache.get(id);
    if (cached) return cached;

    const artifact = getArtifact(id);
    if (artifact) {
      set(s => ({ cache: new Map(s.cache).set(id, artifact) }));
    }
    return artifact;
  },

  list: (path) => {
    return listDirectory(path);
  },

  create: (path, content, mimeType) => {
    const artifact = createArtifact(path, content, mimeType);
    set(s => ({ cache: new Map(s.cache).set(artifact.id, artifact) }));
    scheduleSyncToS3();
    return artifact;
  },

  update: (id, content) => {
    updateArtifact(id, content);
    const artifact = getArtifact(id);
    if (artifact) {
      set(s => ({ cache: new Map(s.cache).set(id, artifact) }));
    }
    scheduleSyncToS3();
  },

  delete: (id) => {
    // Implementation
    scheduleSyncToS3();
  },
}));
```

---

## AWS Infrastructure

### S3 Bucket Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "UserIsolation",
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::choiros-data/users/${aws:PrincipalTag/user_id}/*",
      "Condition": {
        "StringEquals": {
          "aws:PrincipalTag/user_id": "${aws:PrincipalTag/user_id}"
        }
      }
    }
  ]
}
```

### Qdrant on EC2

```bash
# Instance: r6i.large (2 vCPU, 16GB RAM)
# Storage: 100GB gp3

docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v /data/qdrant:/qdrant/storage \
  qdrant/qdrant:latest
```

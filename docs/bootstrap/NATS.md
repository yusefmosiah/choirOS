# NATS JetStream Configuration

> The event bus / kernel of ChoirOS.

---

## Why NATS JetStream

- **Browser-native**: `nats.ws` client works directly in browser via WebSocket
- **Persistent streams**: JetStream provides durable, replayable event logs
- **Subject hierarchy**: Natural for multi-tenant `user.*`, `agent.*` patterns
- **Lightweight**: Single binary, runs on t3.medium

---

## Subject Hierarchy

```
choiros.
├── user.{user_id}.
│   ├── action.*          # User-initiated actions
│   ├── file.*            # File system events
│   └── sync.*            # State sync events
├── agent.{run_id}.
│   ├── started           # Agent run began
│   ├── progress          # Incremental updates
│   ├── result            # Final output
│   └── error             # Failure
├── system.
│   ├── health            # Heartbeats
│   └── announce          # System-wide announcements
├── citation.
│   ├── created           # Citation graph events
│   └── notify.{agent_id} # "You were cited" → agent inbox
└── orchestrator.
    ├── priority          # Task priority updates
    └── context           # Context manager broadcasts
```

### Agent Inbox Pattern

Agents are **continuous NATS subscribers**. While blocked on LLM calls, their inbox accumulates events:

```
choiros.agent.{agent_id}.
├── inbox              # Incoming: citations, priority, context updates
├── outbox             # Agent publishes results here
├── status             # running | blocked | complete
├── spawn              # Spawn child agent requests
└── tasks              # New tasks assigned to this agent
```

Events flow to inbox while agent is processing:
```
Agent A cites Agent B
    │
    ▼
choiros.citation.created → economics service
    │
    ├─── choiros.citation.notify.{agent_b_id} → Agent B's inbox
    │
    └─── Agent B (mid-LLM-call) accumulates event
         │
         └─── On next turn, adapts: "Your work was just cited"
```

---

## Event Schemas

### User Actions

```typescript
// Subject: choiros.user.{user_id}.action.{action_type}

interface UserAction {
  id: string;                    // UUID
  user_id: string;
  timestamp: number;             // Unix ms
  action_type:
    | "COMMAND"                  // ? bar command
    | "ARTIFACT_CREATE"
    | "ARTIFACT_UPDATE"
    | "ARTIFACT_DELETE"
    | "WINDOW_OPEN"
    | "WINDOW_CLOSE";
  payload: Record<string, any>;  // Action-specific data
}

// Example: User issues command from ? bar
{
  "id": "a1b2c3d4",
  "user_id": "user_abc",
  "timestamp": 1702345678000,
  "action_type": "COMMAND",
  "payload": {
    "command": "summarize",
    "target_artifact_id": "doc_xyz",
    "natural_language": "Summarize this and tighten the intro"
  }
}
```

### File Events

```typescript
// Subject: choiros.user.{user_id}.file.{event_type}

interface FileEvent {
  id: string;
  user_id: string;
  timestamp: number;
  event_type: "CREATED" | "UPDATED" | "DELETED" | "MOVED";
  artifact_id: string;
  path: string;
  metadata: {
    size_bytes?: number;
    mime_type?: string;
    hash?: string;                // SHA-256 of content
  };
}
```

### Agent Events

```typescript
// Subject: choiros.agent.{run_id}.started
interface AgentStarted {
  run_id: string;
  user_id: string;
  timestamp: number;
  task_type: string;
  input_artifacts: string[];     // IDs
}

// Subject: choiros.agent.{run_id}.progress
interface AgentProgress {
  run_id: string;
  timestamp: number;
  message: string;
  percent_complete?: number;
}

// Subject: choiros.agent.{run_id}.result
interface AgentResult {
  run_id: string;
  timestamp: number;
  status: "SUCCESS" | "FAILURE";
  output: any;
  citations: Citation[];         // Priors used
  artifacts_created: string[];   // New artifact IDs
  artifacts_modified: string[];
}

interface Citation {
  artifact_id: string;
  weight: number;                // 0.0 - 1.0
  reason: string;
}
```

### Sync Events

```typescript
// Subject: choiros.user.{user_id}.sync.request
interface SyncRequest {
  user_id: string;
  timestamp: number;
  direction: "PUSH" | "PULL";
  last_known_version: number;    // SQLite user_version pragma
}

// Subject: choiros.user.{user_id}.sync.complete
interface SyncComplete {
  user_id: string;
  timestamp: number;
  new_version: number;
  changes_applied: number;
}
```

---

## JetStream Streams

```bash
# Create user events stream (durable, 30 day retention)
nats stream add USER_EVENTS \
  --subjects "choiros.user.>" \
  --retention limits \
  --max-age 720h \
  --storage file \
  --replicas 3

# Create agent events stream (durable, 7 day retention)
nats stream add AGENT_EVENTS \
  --subjects "choiros.agent.>" \
  --retention limits \
  --max-age 168h \
  --storage file \
  --replicas 3

# Create citation stream (permanent, the economic record)
nats stream add CITATIONS \
  --subjects "choiros.citation.>" \
  --retention limits \
  --max-age 0 \
  --storage file \
  --replicas 3

# Create agent inbox stream (workqueue, ephemeral)
# Agents consume and ack, messages deleted after processing
nats stream add AGENT_INBOX \
  --subjects "choiros.agent.*.inbox" \
  --retention workqueue \
  --max-msgs-per-subject 1000 \
  --storage memory \
  --replicas 1

# Create orchestrator stream (short retention)
nats stream add ORCHESTRATOR \
  --subjects "choiros.orchestrator.>" \
  --retention limits \
  --max-age 24h \
  --storage memory \
  --replicas 1
```

---

## Consumers

```bash
# Browser consumer (ephemeral, per-session)
# Created dynamically when user connects via nats.ws

# Agent pool consumer (durable, shared)
nats consumer add USER_EVENTS AGENT_POOL \
  --filter "choiros.user.*.action.COMMAND" \
  --deliver all \
  --ack explicit \
  --max-deliver 3

# Sync worker consumer (durable)
nats consumer add USER_EVENTS SYNC_WORKER \
  --filter "choiros.user.*.file.*" \
  --deliver all \
  --ack explicit
```

---

## AWS Deployment

### EC2 Setup (3-node cluster)

```bash
# Instance type: t3.medium or m6i.large
# AMI: Amazon Linux 2023

# Install NATS
curl -L https://github.com/nats-io/nats-server/releases/download/v2.10.14/nats-server-v2.10.14-linux-amd64.tar.gz | tar xz
sudo mv nats-server-v2.10.14-linux-amd64/nats-server /usr/local/bin/
```

### Cluster Config (`/etc/nats/nats.conf`)

```hcl
server_name: nats-1
listen: 0.0.0.0:4222

jetstream {
  store_dir: /data/jetstream
  max_memory_store: 1G
  max_file_store: 50G
}

cluster {
  name: choiros-nats
  listen: 0.0.0.0:6222
  routes: [
    nats://nats-1.internal:6222
    nats://nats-2.internal:6222
    nats://nats-3.internal:6222
  ]
}

# WebSocket for browser clients
websocket {
  port: 8080
  no_tls: false
  tls {
    cert_file: /etc/nats/cert.pem
    key_file: /etc/nats/key.pem
  }
}

# Authorization (browser clients get JWT, agents get NKey)
authorization {
  timeout: 5s

  # Browser clients (via API gateway)
  users: [
    { user: "browser", password: "$BROWSER_PASSWORD" }
  ]

  # Agent workers (NKey auth)
  # NKey accounts configured separately
}
```

### Security Groups

```
Inbound:
- 4222 from VPC (client connections)
- 6222 from VPC (cluster gossip)
- 8080 from ALB (WebSocket)

Outbound:
- All to VPC
```

---

## Browser Client Usage

```typescript
// lib/nats.ts
import { connect, StringCodec, NatsConnection } from 'nats.ws';

const sc = StringCodec();
let nc: NatsConnection | null = null;

export async function connectNats(token: string): Promise<NatsConnection> {
  nc = await connect({
    servers: 'wss://nats.choiros.com:8080',
    token,
  });
  return nc;
}

export async function publish(subject: string, data: object): Promise<void> {
  if (!nc) throw new Error('NATS not connected');
  nc.publish(subject, sc.encode(JSON.stringify(data)));
}

export async function subscribe(
  subject: string,
  callback: (data: object) => void
): Promise<void> {
  if (!nc) throw new Error('NATS not connected');
  const sub = nc.subscribe(subject);
  for await (const msg of sub) {
    callback(JSON.parse(sc.decode(msg.data)));
  }
}
```

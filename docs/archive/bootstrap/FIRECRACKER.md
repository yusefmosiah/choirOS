# Firecracker MicroVM Setup

> Isolated agent execution on AWS.
> Deferred in v0; Sprites is the bootstrap sandbox backend.

---

## Why Firecracker

- **Hard isolation**: Real VM with separate kernel, not just namespace separation
- **Fast boot**: ~125ms cold start, ~5MB memory overhead
- **AWS native**: What Lambda uses, battle-tested
- **Minimal attack surface**: Stripped-down VMM, no PCI, no USB

---

## AWS Requirements

### EC2 Instance Types

Firecracker requires **bare metal** instances or instances with **nested virtualization**:

| Instance | vCPUs | Memory | Notes |
|----------|-------|--------|-------|
| `c6i.metal` | 128 | 256 GB | Best for production |
| `m6i.metal` | 128 | 512 GB | More memory |
| `c6i.8xlarge` | 32 | 64 GB | Cheaper, check nested virt support |

**Cost optimization**: Start with 1 `.metal` instance, auto-scale based on agent queue depth.

---

## Host Setup

### 1. Install Firecracker

```bash
# Download Firecracker
ARCH="$(uname -m)"
VERSION="v1.5.0"
curl -L "https://github.com/firecracker-microvm/firecracker/releases/download/${VERSION}/firecracker-${VERSION}-${ARCH}.tgz" | tar xz

sudo mv release-${VERSION}-${ARCH}/firecracker-${VERSION}-${ARCH} /usr/local/bin/firecracker
sudo mv release-${VERSION}-${ARCH}/jailer-${VERSION}-${ARCH} /usr/local/bin/jailer

# Verify
firecracker --version
```

### 2. Prepare Root Filesystem

```bash
# Use Alpine Linux for minimal footprint
# Pre-bake with Python runtime for agents

# Download base rootfs
curl -O https://s3.amazonaws.com/spec.ccfc.min/img/hello/fsfiles/hello-rootfs.ext4

# Or build custom:
# - Alpine base
# - Python 3.12
# - Agent runtime deps (requests, etc.)
# - Read-only /artifacts mount point
```

### 3. Kernel

```bash
# Use the recommended guest kernel
curl -O https://s3.amazonaws.com/spec.ccfc.min/img/hello/kernel/hello-vmlinux.bin

# Or compile custom with minimal config
```

---

## VM Configuration

### Firecracker Config (`vm-config.json`)

```json
{
  "boot-source": {
    "kernel_image_path": "/var/lib/firecracker/vmlinux",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "/var/lib/firecracker/rootfs.ext4",
      "is_root_device": true,
      "is_read_only": false
    },
    {
      "drive_id": "artifacts",
      "path_on_host": "/mnt/user_artifacts/user_abc",
      "is_root_device": false,
      "is_read_only": true
    }
  ],
  "machine-config": {
    "vcpu_count": 2,
    "mem_size_mib": 512
  },
  "network-interfaces": [
    {
      "iface_id": "eth0",
      "guest_mac": "AA:FC:00:00:00:01",
      "host_dev_name": "tap0"
    }
  ]
}
```

---

## Orchestration Design

### Agent Execution Flow

```
1. NATS receives: choiros.user.{user_id}.action.COMMAND
                         │
                         ▼
2. Agent Scheduler (Go/Rust service) picks up task
   - Validates user quota
   - Prepares artifact mount
                         │
                         ▼
3. Spawn Firecracker VM via Jailer
   - Isolated network namespace
   - Read-only artifact mount from S3 (pre-synced)
   - NATS connection only (no other network)
                         │
                         ▼
4. Agent runs inside VM
   - Reads task from stdin or env
   - Executes (e.g., summarize document)
   - Writes results to stdout
   - Emits NATS events (progress, result)
                         │
                         ▼
5. VM terminates
   - Results captured
   - VM destroyed (ephemeral)
   - Resources freed
```

### Jailer for Production

Jailer provides additional containment:

```bash
jailer --id agent-run-abc123 \
  --exec-file /usr/local/bin/firecracker \
  --uid 1000 \
  --gid 1000 \
  --chroot-base-dir /srv/jailer \
  --daemonize \
  -- \
  --config-file /srv/jailer/agent-run-abc123/root/vm-config.json
```

---

## Network Isolation

### Option A: No Network (Simplest)

Agent VMs have **no network access** at all:
- Input passed via drive or stdin
- Output written to drive or stdout
- NATS events streamed via host-side proxy

```
┌─────────────────────┐
│   Firecracker VM    │
│   (no eth0)         │
│                     │
│  stdin ─────────────┼─── Task JSON
│  stdout ────────────┼─── Result JSON
│  /artifacts (ro) ───┼─── User files
└─────────────────────┘
```

### Option B: NATS-Only Network (More Flexible)

Agent VMs can only reach NATS:

```bash
# On host, create isolated network
ip link add natsbr0 type bridge
ip addr add 192.168.100.1/24 dev natsbr0
ip link set natsbr0 up

# Create tap device for VM
ip tuntap add tap0 mode tap
ip link set tap0 master natsbr0
ip link set tap0 up

# iptables: only allow traffic to NATS
iptables -A FORWARD -i natsbr0 -d $NATS_IP -p tcp --dport 4222 -j ACCEPT
iptables -A FORWARD -i natsbr0 -j DROP
```

---

## Agent Scheduler Service

### Rust Pseudocode

```rust
// Simple scheduler that listens to NATS and spawns VMs

async fn main() {
    let nats = nats::connect("nats://localhost:4222").await?;
    let sub = nats.subscribe("choiros.user.*.action.COMMAND").await?;

    while let Some(msg) = sub.next().await {
        let task: UserAction = serde_json::from_slice(&msg.data)?;

        // Spawn VM in background
        tokio::spawn(async move {
            execute_agent(task).await;
        });
    }
}

async fn execute_agent(task: UserAction) {
    let run_id = Uuid::new_v4();

    // Emit started event
    nats.publish(
        format!("choiros.agent.{}.started", run_id),
        AgentStarted { run_id, user_id: task.user_id, ... }
    ).await;

    // Prepare VM
    let vm = FirecrackerVm::new()
        .rootfs("/var/lib/firecracker/agent-rootfs.ext4")
        .kernel("/var/lib/firecracker/vmlinux")
        .vcpus(2)
        .memory_mb(512)
        .artifact_mount(&task.user_id)
        .build()?;

    // Run and capture output
    let result = vm.run_with_stdin(&task.payload).await?;

    // Emit result
    nats.publish(
        format!("choiros.agent.{}.result", run_id),
        AgentResult { run_id, output: result, ... }
    ).await;

    // VM is automatically destroyed
}
```

---

## Pre-built VM Images

### Agent Base Image Contents

```dockerfile
# Build script for agent rootfs
FROM alpine:3.19

RUN apk add --no-cache \
    python3 \
    py3-pip \
    ca-certificates

# Agent runtime
COPY agent-runtime /opt/agent
RUN pip install -r /opt/agent/requirements.txt

# Entrypoint reads task from stdin, writes result to stdout
ENTRYPOINT ["python3", "/opt/agent/main.py"]
```

Convert to ext4:

```bash
# Create ext4 image from container
container_id=$(docker create agent-runtime)
docker export $container_id | docker2ext4 > agent-rootfs.ext4
docker rm $container_id
```

---

## Scaling

### Auto-Scaling Group

```yaml
# CloudFormation / CDK
Resources:
  AgentHostASG:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      InstanceType: c6i.metal
      MinSize: 1
      MaxSize: 10
      DesiredCapacity: 1
      HealthCheckType: EC2
      LaunchTemplate: !Ref AgentHostLaunchTemplate

  # Scale based on NATS queue depth
  ScaleUpPolicy:
    Type: AWS::AutoScaling::ScalingPolicy
    Properties:
      AutoScalingGroupName: !Ref AgentHostASG
      PolicyType: TargetTrackingScaling
      TargetTrackingConfiguration:
        CustomizedMetricSpecification:
          MetricName: AgentQueueDepth
          Namespace: ChoirOS
          Statistic: Average
        TargetValue: 10  # Target 10 pending tasks per host
```

---

## Alternatives Considered

| Option | Verdict |
|--------|---------|
| **Docker** | Not enough isolation for multi-tenant |
| **gVisor** | Good, but syscall filtering is leaky |
| **Kata Containers** | Heavier, more complex orchestration |
| **AWS Lambda** | Data leaves your control, expensive at scale |
| **Modal/E2B** | Sandbox-as-a-service, data sovereignty issues |

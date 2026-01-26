# Claude-in-Claude: Multi-Agent Tmux Orchestration

## Vision

Multiple Claude agents running in parallel tmux panes, each with specialized context, coordinated by an orchestrator.

## Architecture

```
┌─ tmux session: "claude-agents" ────────────────────────────┐
│                                                                │
│  Pane 0: Agent A         Pane 1: Agent B    Pane 2: You      │
│  (coding specialist)  (testing specialist)  (orchestrator)   │
│                                                                │
│  Context:              Context:              Context:          │
│  - Feature X code      - Test suite Y       - All agents     │
│  - API routes         - E2E tests          - Coordination   │
│  - Database schema     - Performance         - Strategy       │
│                                                                │
│  Task:                Task:                Task:             │
│  - Implement auth     - Run tests          - Assign work    │
│  - Fix bugs            - Analyze results    - Monitor agents │
│  - Write tests         - Report findings    - Integrate work │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Skills to Create

### Agent Orchestration

**skill: spawn-agent**
```yaml
name: spawn-agent
description: Start a new Claude agent in a tmux pane
parameters:
  - pane: tmux pane target
  - context: file(s) or context to give agent
  - task: what the agent should work on
example: "Spawn Agent A in pane 0 with supervisor/ context"
```

**skill: agent-status**
```yaml
name: agent-status
description: Show status of all running agents
parameters: none
output: Table of agents, their tasks, current status
```

**skill: coordinate-agents**
```yaml
name: coordinate-agents
description: Orchestrate multiple agents working on related tasks
parameters:
  - tasks: list of tasks for each agent
  - dependencies: which tasks depend on others
```

### Workflow Awareness

**skill: nvim.telescope**
```yaml
name: nvim.telescope
description: Navigate code using Telescope fuzzy finder
capabilities:
  - list_changed_files: git status
  - find_file: fuzzy search
  - show_diff: review changes
```

**skill: docker.env**
```yaml
name: docker.env
description: Manage dockerized development environments
capabilities:
  - start_worktree: spin up container
  - stop_worktree: shut down container
  - show_status: list all containers
  - view_logs: tail container logs
```

**skill: tmux.worktree**
```yaml
name: tmux.worktree
description: Create and switch between git worktrees
capabilities:
  - create_worktree: new branch + window
  - switch_worktree: change context
  - list_worktrees: show all branches
```

## Implementation Plan

1. **spawn-agent skill**
   - Creates new tmux window/pane
   - Starts claude CLI with specific context
   - Records agent ID and task

2. **agent-status skill**
   - Queries tmux for all Claude processes
   - Shows current task/context per agent
   - Displays agent output

3. **coordinate-agents skill**
   - Assigns tasks to multiple agents
   - Manages dependencies
   - Collects and integrates results

4. **Workflow skills**
   - Wrap existing scripts (choiros-worktree, etc.)
   - Make them accessible to Claude
   - Enable Claude to understand and use the workflow

## Benefits

1. **Parallelization**: 3-10x faster on complex tasks
2. **Specialization**: Each agent focuses on one area
3. **Observability**: See all agent activity
4. **Fault Tolerance**: Failed agents don't crash others
5. **Metacognition**: You become orchestrator, not implementer

## Example Workflow

```bash
# You (orchestrator) say:
"Spawn 3 agents to work on feature X"

# System creates:
Agent A (pane 0): Implement backend API
Agent B (pane 1): Implement frontend UI
Agent C (pane 2): Write tests

# You monitor all agents
agent-status

# Agent A finishes first
# You redirect Agent B to help Agent C

# All done, you integrate the work
coordinate-agents --integrate
```

This is the future of AI-augmented development.

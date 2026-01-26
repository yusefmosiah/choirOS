# ChoirOS Terminal-Based Development Workflow

## Complete Stack - All Steps Implemented

### ✅ Step 1: nvim + Telescope (File Navigation)
- nvim 0.11.5 configured with Telescope
- `Space g s` - Git status (changed files)
- `Space f f` - Find files
- `Space d v` - Diffview (review changes)

### ✅ Step 2: tmux + 3-Pane Layout
- Pane 0 (60%): nvim editor
- Pane 1 (25%): tests/logs
- Pane 2 (15%): commands/Claude
- Mouse navigation enabled

### ✅ Step 3: Git Worktrees (Parallel Development)
- Work on multiple branches simultaneously
- Each worktree = separate tmux window
- `~/.local/bin/choiros-worktree` - Create worktree + window

### ✅ Step 4: Container Orchestration (Isolated Environments)
- Per-worktree Docker containers
- **Non-overlapping port allocation**
- `~/.local/bin/choiros-containerize` - Manage containers
- `~/.local/bin/choiros-env` - Environment status

## Port Allocation (No Overlaps!)

```
Worktree      Frontend  Backend  Supervisor  Port Range
─────────────  ────────  ───────  ──────────  ───────────
main             5173      5174       5175      5173-5175
spokane          5176      5177       5178      5176-5178
auckland         5179      5180       5181      5179-5181
albuquerque     5182      5183       5184      5182-5184
curitiba        5185      5186       5187      5185-5187
monterrey       5188      5189       5190      5188-5190
osaka           5191      5192       5193      5191-5193
taipei          5194      5195       5196      5194-5196
new-*           5200+     5201+      5202+      5200-5250
```

## Architecture

```
┌─ tmux session "choiros" ──────────────────────────────────┐
│                                                             │
│  Window 0: main      Window 1: spokane   Window 2:       │
│  ├─ nvim             ├─ nvim          auckland           │
│  ├─ tests            ├─ tests         ├─ nvim            │
│  └─ commands         └─ commands      ├─ tests           │
│       │                   │             └─ commands        │
│       ▼                   ▼                 │              │
│  Container:         Container:         ▼              │
│  choiros-main       choiros-spokane  Container:        │
│  Ports:             Ports:            choiros-auckland  │
│  5173 (fe)          5176 (fe)         Ports:            │
│  5174 (be)          5177 (be)         5179 (fe)         │
│  5175 (sup)         5178 (sup)        5180 (be)         │
│                                       5181 (sup)        │
└─────────────────────────────────────────────────────────────┘
```

## Daily Workflow

```bash
# Morning: Start work
~/.local/bin/choiros-env              # Check what's running
tmux attach-session -t choiros          # Attach to session

# Create new feature
~/.local/bin/choiros-worktree feature/new origin/main --container
# → Creates worktree, tmux window, AND container
# → Ports: 5203 (fe), 5204 (be), 5205 (sup)

# Work in nvim
Space g s                              # See changed files
# (Navigate, open, edit)

# Review changes
Space d v                              # Diffview
# (Navigate diffs, review)

# Switch between branches
Ctrl+b w                               # Choose window (branch)

# Ask Claude for help
"Open the supervisor module"
"Run pytest in pane 1"
"Show git status in pane 2"

# Evening: Stop work
~/.local/bin/choiros-containerize feature/new stop
```

## Keybindings

### nvim (leader = Space)
- `Space g s` - Git status
- `Space f f` - Find files
- `Space d v` - Diffview
- `Space d c` - Close diffview
- `Space w s` - Switch worktree

### tmux
- `Ctrl+b w` - Switch windows
- `Ctrl+b o` - Rotate panes (or use mouse)
- `Ctrl+b 0/1/2` - Switch to window 0/1/2

## Resources

- Full tutorial: `docs/CHOIR_WORKFLOW_TUTORIAL.md`
- Port allocation: `docs/PORT_ALLOCATION.md`
- Quick reference: `~/.local/bin/choiros-help`
- Demo session: `~/.local/bin/choiros-demo`

## Done!

You now have a complete, production-ready terminal development environment
with parallel branches, isolated containers (no port conflicts!), and AI assistance.

# ChoirOS Terminal-Based Development Workflow

**Tutorial: Mastering nvim + tmux + Claude + Git Worktrees**

---

## Table of Contents
1. [Overview](#overview)
2. [The Architecture](#the-architecture)
3. [Getting Started](#getting-started)
4. [Core Workflows](#core-workflows)
5. [Keybindings Reference](#keybindings-reference)
6. [The Bidirectional Control Flow](#the-bidirectional-control-flow)
7. [Worktree Workflow](#worktree-workflow)
8. [Daily Development Patterns](#daily-development-patterns)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This workflow combines four powerful tools into a cohesive, terminal-based development environment:

- **nvim 0.11.5+**: Fast, modal text editor with Telescope fuzzy finder
- **tmux**: Terminal multiplexer managing multiple panes/windows
- **Claude Code**: AI assistant that can see and control your editor
- **Git Worktrees**: Work on multiple branches simultaneously without context switching

**Key Benefit**: Parallel development - test one branch while coding another, with Claude assisting across all contexts.

---

## The Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ tmux session "choiros"                                          │
├──────────────────┬──────────────────┬──────────────────────────┤
│ Window 0: main   │ Window 1: feature │ Window 2: bugfix         │
│ [main branch]    │ [feature branch]  │ [bugfix branch]          │
├──────┬──────┬────┼──────┬──────┬────┼──────┬──────┬──────────┤
│ p0   │ p1   │ p2  │ p0   │ p1   │ p2  │ p0   │ p1   │ p2        │
│ nvim │test │cmd │ nvim │test │cmd │ nvim │test │cmd        │
│      │     │    │      │     │    │      │     │           │
│ edit │log  │Claude│ edit│log  │Claude│ edit│log  │Claude     │
└──────┴──────┴────┴──────┴──────┴────┴──────┴──────┴──────────┘

Per-Window 3-Pane Layout:
┌─────────────────────┬─────────────────┬─────────────────┐
│ Pane 0: nvim (60%)  │ Pane 1: tests   │ Pane 2: cmd     │
│ • Telescope         │ (25%)           │ (15%)           │
│ • git-worktree      │ • pytest        │ • Claude CLI    │
│ • diffview          │ • npm run dev   │ • git commands  │
│ • editing           │ • logs          │ • build output  │
└─────────────────────┴─────────────────┴─────────────────┘
```

**Why this works**:
- **Concurrency**: Each window = isolated branch context
- **Persistence**: tmux sessions survive SSH disconnects
- **Context**: Claude sees all panes, provides intelligent help
- **Speed**: Never leave the terminal, everything is keyboard-driven

---

## Getting Started

### Installation Checklist

✅ **nvim 0.11.5+**
```bash
nvim --version  # Should show 0.11.5 or later
```

✅ **tmux with plugins**
```bash
tmux -V  # Should show 3.0+
ls ~/.tmux/plugins/tpm  # Plugin manager installed
```

✅ **Required scripts**
```bash
ls ~/.local/bin/choiros-*  # Should show 3 scripts
```

✅ **nvim plugins installed**
```bash
nvim --headless "+Lazy sync" +qa  # Installs/updates plugins
```

### Your First Session

Start a development session:

```bash
# Option 1: Create new session manually
tmux new-session -s my-feature -n my-feature
~/.local/bin/choiros-3pane  # Apply 3-pane layout

# Option 2: Run the demo (creates 'choiros-demo' session)
~/.local/bin/choiros-demo
tmux attach-session -t choiros-demo

# Option 3: Use worktree script (creates worktree + window)
~/.local/bin/choiros-worktree feature/new-stuff origin/main
```

---

## Core Workflows

### 1. **"Ctrl+P" File Navigation** (Telescope)

The VS Code "Ctrl+P" experience, but faster:

```vim
" In nvim normal mode:
<leader>ff    " Find files (fuzzy search)
<leader>fg    " Live grep (search content)
<leader>fb    " Find buffers (open files)
<leader>gs    " Git status (changed files) ⭐
<leader>gf    " Git files (tracked files only)
```

**Example workflow**:
1. Press `<Space>gs` (leader + g + s)
2. Telescope opens with list of changed files
3. Type to filter (e.g., "api")
4. Press `jj` to navigate, `Enter` to open
5. File opens in nvim

**Why `git_status` vs `find_files`?**
- `git_status`: Only shows changed files (faster for active work)
- `git_files`: Only tracked files (ignores node_modules, build artifacts)
- `find_files`: All files (including untracked)

### 2. **Diff Navigation** (Diffview)

Review changes before committing:

```vim
<leader>dv    " Open diff view (tab-based)
<leader>dc    " Close diff view
```

**In Diffview**:
- `jj` / `kk`: Navigate between files
- `Enter`: Open file diff
- `[c` / `]c`: Next/previous change hunk
- `:DiffviewOpen main...HEAD`: Compare against main

### 3. **Git Worktrees**

Work on multiple branches simultaneously:

```bash
# Create new worktree + tmux window
~/.local/bin/choiros-worktree feature/my-feature origin/main

# Inside nvim: switch worktrees
<leader>ws    " Switch worktree (prompts for branch)

# Inside nvim: create worktree
:GitWorktree create feature/new-feature origin/main
```

**This creates**:
- New git worktree at `/conductor/workspaces/choirOS/feature/new-feature`
- New tmux window named `new-feature`
- 3-pane layout ready for development

**Switch between branches**:
```bash
# In tmux: Ctrl+b then window number
Ctrl+b 0    " Window 0 (main)
Ctrl+b 1    " Window 1 (first worktree)
Ctrl+b w    " List windows, choose by name

# In nvim: use Telescope
<leader>wt    " Telescope worktrees
```

---

## Keybindings Reference

### nvim (leader = Space)

| Keybinding | Mode | Action |
|------------|------|--------|
| `<Space>` | - | Leader key |
| `<leader>ff` | Normal | Find files |
| `<leader>fg` | Normal | Live grep |
| `<leader>fb` | Normal | Find buffers |
| `<leader>gs` | Normal | Git status (changed files) |
| `<leader>gf` | Normal | Git files |
| `<leader>gc` | Normal | Git commits |
| `<leader>gb` | Normal | Git branches |
| `<leader>ws` | Normal | Switch worktree |
| `<leader>dv` | Normal | Diffview open |
| `<leader>dc` | Normal | Diffview close |
| `<leader>ac` | Normal | Toggle Claude Code |
| `<leader>as` | Visual | Send selection to Claude |

### tmux (prefix = Ctrl+b)

| Keybinding | Action |
|------------|--------|
| `Ctrl+b c` | Create new window |
| `Ctrl+b 0-9` | Switch to window 0-9 |
| `Ctrl+b n` | Next window |
| `Ctrl+b p` | Previous window |
| `Ctrl+b ,` | Rename window |
| `Ctrl+b w` | List windows |
| `Ctrl+b 0` | Select pane 0 |
| `Ctrl+b 1` | Select pane 1 |
| `Ctrl+b 2` | Select pane 2 |
| `Ctrl+b o` | Rotate panes |
| `Ctrl+b [` | Enter scroll mode |
| `Ctrl+b ]` | Paste buffer |

### Telescope (inside fuzzy finder)

| Keybinding | Action |
|------------|--------|
| `jj` / `kk` | Navigate down/up |
| `Enter` | Open selected |
| `C-c` | Close Telescope |
| `C-f` | Scroll preview down |
| `C-b` | Scroll preview up |
| `Tab` | Multi-select |
| `Esc` | Close |

---

## The Bidirectional Control Flow

### **Claude → tmux → nvim** ✅

I (Claude) can control your editor through tmux:

```bash
# I run these commands:
tmux send-keys -t choiros:main.0 ':Telescope git_status' Enter
tmux send-keys -t choiros:main.1 'pytest -v' Enter
tmux send-keys -t choiros:main.2 'git status' Enter
```

**Use cases**:
- "Claude, open the API router file"
- "Claude, run tests for the supervisor"
- "Claude, show me the git diff for feature/auth"

### **nvim → Claude** ✅

Send code context from nvim to Claude:

1. **Select text in nvim** (visual mode: `v`, then navigate)
2. **Press `<leader>as`** (send to Claude)
3. **Claude receives your selection** as context

**Example**:
```vim
" In nvim:
1. Move cursor to function start
2. Press v (visual mode)
3. Navigate to function end
4. Press <leader>as
5. Claude now sees your function
```

### **nvim → tmux → Claude** (Future)

Send commands from nvim to adjacent tmux panes:

```vim
" Select text in nvim
" Press <localleader>s (to be configured)
" Text sent to pane 1 (test runner)
```

---

## Worktree Workflow

### **Scenario: Working on 3 branches simultaneously**

```bash
# Start with main branch
cd ~/choirOS
git checkout main

# Create worktree for feature A
~/.local/bin/choiros-worktree feature/add-auth origin/main
# → Creates window "add-auth" in tmux session "choiros"

# Create worktree for feature B
~/.local/bin/choiros-worktree feature/refactor-api origin/main
# → Creates window "refactor-api" in tmux session "choiros"

# Create worktree for bugfix
~/.local/bin/choiros-worktree bugfix/login-crash origin/main
# → Creates window "login-crash" in tmux session "choiros"
```

**Your tmux session now has 4 windows**:
- `0: main` - Production code
- `1: add-auth` - Feature A development
- `2: refactor-api` - Feature B development
- `3: login-crash` - Bugfix

**Switch between branches**:
```bash
# In tmux:
Ctrl+b 0    " Switch to main
Ctrl+b 1    " Switch to add-auth
Ctrl+b 2    " Switch to refactor-api
Ctrl+b 3    " Switch to login-crash

# Each window has its own:
# - nvim instance (different files open)
# - test pane (running tests for that branch)
# - command pane (git/logs for that branch)
```

**Parallel development example**:
1. **Window 0 (main)**: Run production tests in pane 1
2. **Window 1 (add-auth)**: Code auth flow in pane 0
3. **Window 2 (refactor-api)**: Run API server in pane 1
4. **Window 3 (login-crash)**: Debug crash with Claude in pane 2

**No more stashing changes, no more context switching!**

---

## Daily Development Patterns

### **Pattern 1: Feature Development**

```bash
# 1. Create worktree
~/.local/bin/choiros-worktree feature/new-auth origin/main

# 2. Tmux creates window "new-auth" with 3 panes
# Pane 0: nvim (your editor)
# Pane 1: tests (run pytest/npm test)
# Pane 2: commands (Claude, git, build)

# 3. Start development
# In pane 0:
cd api  # nvim terminal mode: :terminal
pytest tests/test_auth.py -v

# In pane 2:
git status
git log --oneline -5

# 4. Code changes in pane 0
<leader>gs    " See changed files
<leader>dv    " Review diffs

# 5. Run tests in pane 1
pytest -k test_login

# 6. Ask Claude for help (in pane 2)
claude
> How do I fix this test failure?

# 7. Claude's response appears in pane 2
# Claude can also send commands to pane 0:
tmux send-keys -t choiros:new-auth.0 ':e auth/router.py' Enter
```

### **Pattern 2: Bug Investigation**

```bash
# 1. Create bugfix worktree
~/.local/bin/choiros-worktree bugfix/crash-on-login origin/main

# 2. Open nvim in pane 0
nvim supervisor/machine.py

# 3. Navigate to error location
# In nvim: /TypeError<Enter>  (search for TypeError)

# 4. Open Telescope git status
<leader>gs

# 5. Send context to Claude
# Visual select function (v, navigate)
<leader>as

# 6. Claude sees your code, helps debug
# Claude can run commands:
tmux send-keys -t choiros:bugfix/crash-on-login.1 'pytest tests/test_machine.py::test_startup -xvs' Enter

# 7. Test output appears in pane 1
# Claude analyzes output, suggests fix
```

### **Pattern 3: Code Review**

```bash
# 1. Switch to PR branch
~/.local/bin/choiros-worktree pr/123-feature origin/main

# 2. Open diffview
<leader>dv

# 3. Navigate changes
jj    " Next file
Enter    " Open file diff
]c    " Next change

# 4. Ask Claude for review
# Visual select diff
<leader>as

# Claude:
> "This function has a potential race condition.
>  Line 45: missing error handling.
>  Suggest adding try/except block."

# 5. Apply suggestions
# Claude can send edits:
tmux send-keys -t choiros:pr/123-feature.0 'i    try:' Enter
```

### **Pattern 4: Testing Multiple Scenarios**

```bash
# Window 0: main (production)
# Pane 1: npm run test (integration tests)

# Window 1: feature/fast-api (performance work)
# Pane 1: pytest benchmarks/ -v

# Window 2: bugfix/memory-leak (debugging)
# Pane 1: pytest -xvs tests/test_memory.py
# Pane 2: watch -n 1 'ps aux | grep python'

# Switch between windows to monitor progress:
Ctrl+b 0    " Check main tests
Ctrl+b 1    " Check benchmarks
Ctrl+b 2    " Check memory tests
```

---

## Troubleshooting

### **nvim won't start / plugins missing**

```bash
# Reinstall plugins
nvim --headless "+Lazy sync" +qa

# Check plugin directory
ls ~/.local/share/nvim/lazy/

# Should see: telescope.nvim, git-worktree.nvim, etc.
```

### **tmux layout not applying**

```bash
# Manual layout:
~/.local/bin/choiros-3pane

# Check pane count:
tmux list-panes -F "#{pane_index}: #{pane_current_command}"

# Should show 3 panes
```

### **git-worktree not working**

```bash
# Check worktree list
git worktree list

# Remove stale worktree
git worktree remove /path/to/worktree

# Recreate
~/.local/bin/choiros-worktree feature/fix origin/main
```

### **Claude can't control nvim**

```bash
# Check tmux session
tmux list-sessions

# Verify pane numbers
tmux list-panes -t choiros:main -F "#{pane_index}: #{pane_current_command}"

# Test send-keys
tmux send-keys -t choiros:main.0 'echo test' Enter
```

### **Telescope not finding files**

```bash
# In nvim, check Telescope:
:checkhealth telescope

# Restart nvim and try again
:q
nvim
<leader>ff
```

---

## Next Steps (After Tutorial)

### **Phase 4: Container Orchestration** (Paused)

This is where we add:
- Per-worktree Docker containers
- Automatic port allocation
- Isolated databases per branch
- Hot-reload development servers

**Coming soon**:
- `~/.local/bin/choiros-containerize` - Spin up container for current worktree
- `~/.local/bin/choiros-env` - Show all running containers and ports
- Integration with docker-compose for local development

---

## Summary

You now have:

✅ **nvim 0.11.5** with Telescope, git-worktree, diffview, Claude integration
✅ **tmux** with standardized 3-pane layout
✅ **Scripts** for worktree management and session setup
✅ **Bidirectional control**: Claude → tmux → nvim, nvim → Claude
✅ **Parallel development**: Multiple branches, multiple windows, zero context switching

**Key workflows**:
1. `<leader>gs` - See changed files (Telescope git status)
2. `<leader>dv` - Review changes (Diffview)
3. `~/.local/bin/choiros-worktree branch-name` - Create worktree + window
4. `tmux send-keys -t session:window.pane 'command' Enter` - Control panes

**Practice this**:
1. Run `~/.local/bin/choiros-demo`
2. Open Telescope with `<Space>gs`
3. Navigate files with `jj`, open with `Enter`
4. Try diffview with `<Space>dv`
5. Create a test worktree

**Questions?**
- Ask me: "How do I [task]?"
- I can send commands to your tmux panes
- I can help debug nvim configurations
- I can guide you through any workflow

---

**Version**: 1.0
**Last Updated**: 2025-01-25
**Maintained by**: Claude Code + Human Collaboration

---

## Step 4: Container Orchestration (Per-Worktree Isolation)

### Overview

Each worktree can have its own isolated Docker container with:
- Automatic port allocation (5173, 5174, 5175...)
- Independent databases/services
- No port conflicts between branches
- Easy spin-up/spin-down

### Commands

**Check environment status:**
```bash
~/.local/bin/choiros-env
```

**Start container for worktree:**
```bash
~/.local/bin/choiros-containerize spokane start
```

**Stop container:**
```bash
~/.local/bin/choiros-containerize spokane stop
```

**View logs:**
```bash
~/.local/bin/choiros-containerize spokane logs
```

**Open shell in container:**
```bash
~/.local/bin/choiros-containerize spokane shell
```

**Create worktree + container:**
```bash
~/.local/bin/choiros-worktree feature/new origin/main --container
```

### Port Allocation

Ports are automatically allocated based on worktree name:
- `main`: 5173, 8000, 8001
- `spokane`: 5174, 8001, 8002 (example)
- `albuquerque`: 5175, 8002, 8003 (example)

Each container gets:
- Frontend port (base)
- Backend port (base + 1)
- Supervisor port (base + 2)

### Daily Workflow

```bash
# 1. Check what's running
~/.local/bin/choiros-env

# 2. Start container for worktree
~/.local/bin/choiros-containerize spokane start

# 3. Attach to tmux session
tmux attach-session -t choiros

# 4. Switch to worktree window
Ctrl+b w (select "spokane")

# 5. Code in nvim (pane 0), tests run in container

# 6. Check logs
~/.local/bin/choiros-containerize spokane logs

# 7. Stop when done
~/.local/bin/choiros-containerize spokane stop
```

### Container Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Host System                                                  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Container:   │  │ Container:   │  │ Container:   │      │
│  │ choiros-main │  │choiros-spokane│ │choiros-osaka │      │
│  │              │  │              │  │              │      │
│  │ Ports:       │  │ Ports:       │  │ Ports:       │      │
│  │ 5173 (fe)    │  │ 5174 (fe)    │  │ 5175 (fe)    │      │
│  │ 8000 (be)    │  │ 8001 (be)    │  │ 8002 (be)    │      │
│  │ 8001 (sup)   │  │ 8002 (sup)   │  │ 8003 (sup)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                           │                                 │
│                    ┌────────▼────────┐                      │
│                    │   NATS (Docker) │                      │
│                    │   Port 4222     │                      │
│                    └─────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### Troubleshooting

**Container won't start:**
```bash
# Check logs
~/.local/bin/choiros-containerize <name> logs

# Rebuild
~/.local/bin/choiros-containerize <name> stop
docker image rm choirOS:latest
~/.local/bin/choiros-containerize <name> start
```

**Port conflicts:**
```bash
# Check what's using ports
lsof -i :5173-5180

# Stop conflicting containers
~/.local/bin/choiros-env
~/.local/bin/choiros-containerize <name> stop
```

**Need to access database in container:**
```bash
~/.local/bin/choiros-containerize <name> shell
# Inside container:
psql postgresql://user:pass@localhost:5432/db
```


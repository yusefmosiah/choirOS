# ChoirOS Development Notes

## 2024 - Agentic Desktop Genesis

### What We've Built
The **Agentic Desktop** - a novel UX pattern where:
- The AI agent IS the operating system interface
- HMR enables real-time UI mutation through conversation
- Natural language → immediate spatial reality
- Self-modifying substrate (agent can read/edit its own components)

### Next: Logging & Retrieval

#### Requirements to Define:
1. **What to log?**
   - Conversation history (user ↔ agent)
   - File mutations (what changed, when, why)
   - Window state changes
   - Agent actions/tool calls

2. **Where to store?**
   - Local file system (`logs/`)
   - IndexedDB (browser-side persistence)
   - SQLite (if we want queries)
   - Simple JSON append-log

3. **Retrieval patterns needed:**
   - "What did we discuss yesterday?"
   - "Show me all changes to theme.css"
   - "Undo the last 3 things"
   - "What windows were open when we were working on X?"
   - Semantic search over conversation history?

4. **Architecture questions:**
   - Should logs be reactive (subscribable)?
   - Event sourcing pattern? (rebuild state from log)
   - Separate log viewer window?
   - Agent memory integration?

### Ideas
- The log itself could be a window component
- "Rewind" feature - scrub through desktop states
- Git-like commits for UI states
- Agent can query its own history for context

---

*This file is the beginning of persistent memory.*

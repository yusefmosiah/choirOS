"""
Agent Harness - Main agent loop with Claude via AWS Bedrock.

Receives prompts via WebSocket, calls Claude with tools, executes tool calls.
Logs all events to the SQLite event store.

REFACTORED: Now uses RalphLoop abstraction.
"""

from typing import AsyncGenerator, Any, Optional

from .tools import AgentTools
from .ralph import RalphLoop
from ..db import get_store, EventStore


# Model to use - Cross-region inference profile required for newer models
# MODEL_ID = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
# MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
MODEL_ID = "us.anthropic.claude-opus-4-5-20251101-v1:0"


# System prompt for the agent
SYSTEM_PROMPT = """You are the ChoirOS agent, operating inside a web desktop environment.

Your capabilities:
- Read, write, and edit files in the /app/choiros directory
- Execute shell commands
- Modify the UI by editing React components, CSS, and configuration files

The desktop shell is served by Vite with Hot Module Replacement (HMR). When you edit files, the changes will appear immediately in the user's browser.

Key directories:
- /app/choiros/src/components - React components
- /app/choiros/src/styles - CSS files (theme.css, global.css)
- /app/choiros/public - Static assets

When the user asks you to change the UI (colors, layout, etc.), you should:
1. Read the relevant file to understand current state
2. Edit the file with your changes
3. The user will see the update via HMR

Be concise in your responses. Focus on taking action."""


class AgentHarness:
    """Main agent harness that processes prompts and executes tools."""

    def __init__(self, file_history=None, event_store: Optional[EventStore] = None):
        """
        Initialize the agent harness.

        Args:
            file_history: Optional FileHistory instance for undo support
            event_store: Optional EventStore for persistence (uses global if not provided)
        """
        self.store = event_store or get_store()
        self.tools = AgentTools(file_history=file_history)

        # Instantiate the generic Ralph loop with specific configuration
        self.ralph = RalphLoop(
            model=MODEL_ID,
            system_prompt=SYSTEM_PROMPT,
            tools=AgentTools.TOOL_DEFINITIONS,
            tool_handler=self.tools.execute_tool,
            event_store=self.store
        )

    async def process(self, prompt: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process a user prompt and yield responses.
        Delegates to the internal RalphLoop instance.
        """
        async for event in self.ralph.process(prompt):
            yield event

"""
Agent Harness - Main agent loop with Claude via AWS Bedrock.

Receives prompts via WebSocket, calls Claude with tools, executes tool calls.
"""

import json
import uuid
from typing import AsyncGenerator, Any

from supervisor.llm import LLMSettings, Message, build_llm_client
from .tools import AgentTools


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

    def __init__(self, file_history=None):
        """
        Initialize the agent harness.

        Args:
            file_history: Optional FileHistory instance for undo support
        """
        self.tools = AgentTools(file_history=file_history)

        # Initialize provider-agnostic LLM client
        self.llm_settings = LLMSettings.from_env()
        self.client = build_llm_client(self.llm_settings)
        self.model = self.llm_settings.model

    async def process(self, prompt: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process a user prompt and yield responses.

        Yields dict with keys:
        - type: "thinking", "tool_use", "tool_result", "text", "error", "done"
        - content: The actual content
        """
        try:
            messages: list[Message] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]

            yield {"type": "thinking", "content": "Processing your request..."}

            while True:
                response = self.client.chat(
                    messages=messages,
                    model=self.model,
                    max_tokens=4096,
                    tools=AgentTools.TOOL_DEFINITIONS,
                )

                assistant_content = []

                text_content = response.get("content", "")
                if text_content:
                    yield {"type": "text", "content": text_content}
                    assistant_content.append({"type": "text", "text": text_content})

                tool_calls = response.get("tool_calls", []) or []
                if not tool_calls:
                    if assistant_content:
                        messages.append({"role": "assistant", "content": assistant_content})
                    break

                for tool_call in tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_input = tool_call.get("arguments", {})
                    tool_use_id = tool_call.get("id") or str(uuid.uuid4())

                    yield {
                        "type": "tool_use",
                        "content": {
                            "tool": tool_name,
                            "input": tool_input,
                        }
                    }

                    assistant_content.append({
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": tool_input,
                    })

                    # Execute the tool
                    result = await self.tools.execute_tool(tool_name, tool_input)

                    yield {
                        "type": "tool_result",
                        "content": {
                            "tool": tool_name,
                            "result": result,
                        }
                    }

                    # Add assistant message and tool result for next turn
                    messages.append({"role": "assistant", "content": assistant_content})
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(result),
                        }]
                    })

                    assistant_content = []

            yield {"type": "done", "content": None}

        except Exception as e:
            yield {"type": "error", "content": str(e)}

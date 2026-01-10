"""
Agent Harness - Main agent loop with Claude via AWS Bedrock.

Receives prompts via WebSocket, calls Claude with tools, executes tool calls.
Logs all events to the SQLite event store.
"""

import json
import os
from typing import AsyncGenerator, Any, Optional

import anthropic

from .tools import AgentTools
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
        self.tools = AgentTools(file_history=file_history)
        self.store = event_store or get_store()
        self.conversation_id: Optional[int] = None

        # Initialize Anthropic client for AWS Bedrock
        self.client = anthropic.AnthropicBedrock(
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        )

    async def process(self, prompt: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process a user prompt and yield responses.

        Yields dict with keys:
        - type: "thinking", "tool_use", "tool_result", "text", "error", "done"
        - content: The actual content
        """
        try:
            # Ensure we have a conversation
            if self.conversation_id is None:
                self.conversation_id = self.store.get_or_create_conversation()
            
            # Log user message
            self.store.add_message(self.conversation_id, "user", prompt)
            
            messages = [{"role": "user", "content": prompt}]

            yield {"type": "thinking", "content": "Processing your request..."}

            while True:
                # Call Claude
                response = self.client.messages.create(
                    model=MODEL_ID,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=AgentTools.TOOL_DEFINITIONS,
                    messages=messages,
                )

                # Process response content blocks
                assistant_content = []
                has_tool_use = False

                assistant_text_parts = []  # Collect text for logging
                
                for block in response.content:
                    if block.type == "text":
                        yield {"type": "text", "content": block.text}
                        assistant_content.append({"type": "text", "text": block.text})
                        assistant_text_parts.append(block.text)

                    elif block.type == "tool_use":
                        has_tool_use = True
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id

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
                        
                        # Log tool call to event store
                        self.store.log_tool_call(
                            self.conversation_id,
                            tool_name,
                            tool_input,
                            result
                        )

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

                        # Reset for potential next tool call
                        assistant_content = []

                # If no tool use, we're done - log the final assistant response
                if not has_tool_use:
                    if assistant_text_parts:
                        full_response = "\n".join(assistant_text_parts)
                        self.store.add_message(
                            self.conversation_id, 
                            "assistant", 
                            full_response
                        )
                    break

                # Check stop reason
                if response.stop_reason == "end_turn":
                    if assistant_text_parts:
                        full_response = "\n".join(assistant_text_parts)
                        self.store.add_message(
                            self.conversation_id,
                            "assistant",
                            full_response
                        )
                    break

            yield {"type": "done", "content": None}

        except Exception as e:
            yield {"type": "error", "content": str(e)}

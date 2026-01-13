import json
import os
from typing import AsyncGenerator, Any, Optional, List, Dict, Callable, Awaitable

import anthropic

from ..db import get_store, EventStore


class RalphLoop:
    """
    A generic agent loop (Simple Ralph) that processes prompts using an LLM and tools.

    This class handles the core loop:
    1. User Input -> LLM
    2. LLM -> Text (streamed) OR Tool Use
    3. Tool Use -> Execute Tool -> Tool Result
    4. Tool Result -> LLM -> ...
    """

    def __init__(
        self,
        model: str,
        system_prompt: str,
        tools: List[Dict[str, Any]],
        tool_handler: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]],
        event_store: Optional[EventStore] = None,
    ):
        """
        Initialize the Ralph loop.

        Args:
            model: The ID of the model to use (e.g., Claude 3.5 Sonnet).
            system_prompt: The system prompt for the agent.
            tools: List of tool definitions (JSON schema).
            tool_handler: Async function to execute tools. Takes (name, args) returns result dict.
            event_store: Optional EventStore for persistence.
        """
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_handler = tool_handler
        self.store = event_store or get_store()

        # Initialize Anthropic client
        # Note: In a more advanced version, we might inject the client or support other providers.
        self.client = anthropic.AnthropicBedrock(
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        )

        self.conversation_id: Optional[int] = None

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
                # Call LLM
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=self.system_prompt,
                    tools=self.tools,
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

                        # Execute the tool via the handler
                        try:
                            result = await self.tool_handler(tool_name, tool_input)
                        except Exception as e:
                            result = {"error": str(e)}

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

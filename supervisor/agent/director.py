"""
Director Agent - Plans and delegates tasks to the Associate.
"""

import json
import os
import uuid
from typing import AsyncGenerator, Any, Optional

import anthropic

from ..db import get_store, EventStore
from .schemas import DirectorTask, AssociateResult
from .associate import AssociateAgent

MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

DIRECTOR_SYSTEM_PROMPT = """You are the Director, the planning and supervision agent in the ChoirOS system.
Your role is to receive user requests, plan the work, and delegate tasks to the Associate.

You operate in a "Director Sandbox" and do NOT have direct access to the file system or shell.
To affect change or inspect the system, you MUST delegate tasks to the Associate.

Your capabilities:
- Analyze user requests.
- Create detailed plans.
- Issue `DirectorTask`s to the Associate using the `delegate_task` tool.
- Review `AssociateResult`s.
- Communicate with the user.

When a user asks for something:
1. Break it down into clear, deterministic tasks.
2. Delegate one task at a time to the Associate.
3. Wait for the result.
4. Verify the result satisfies the plan.
5. If more work is needed, delegate the next task.
6. Once the goal is met, inform the user.

Do not try to read files or run commands yourself. You must use the Associate for everything.
"""

class DirectorAgent:
    """
    Director agent that orchestrates the Associate.
    """

    def __init__(self, file_history=None, event_store: Optional[EventStore] = None):
        self.store = event_store or get_store()
        self.associate = AssociateAgent(file_history=file_history, event_store=self.store)

        self.client = anthropic.AnthropicBedrock(
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        )

        # Tools available to the Director
        self.tools = [
            {
                "name": "delegate_task",
                "description": "Delegate a task to the Associate agent.",
                "input_schema": DirectorTask.model_json_schema()
            }
        ]

    async def run(self, prompt: str, conversation_id: int) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process the user prompt, delegate tasks, and yield responses.
        """
        # Load conversation history or start new
        # For simplicity in this v0 implementation, we just use the current prompt
        # In a real impl, we'd fetch history from store using conversation_id

        messages = [{"role": "user", "content": prompt}]

        max_turns = 20
        current_turn = 0

        # This loop continues until the Director decides to stop (no tool use)
        while current_turn < max_turns:
            current_turn += 1

            response = self.client.messages.create(
                model=MODEL_ID,
                max_tokens=4096,
                system=DIRECTOR_SYSTEM_PROMPT,
                tools=self.tools,
                messages=messages,
            )

            assistant_content = []
            has_tool_use = False

            assistant_text_parts = []

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

                    tool_result_content = ""

                    if tool_name == "delegate_task":
                        # Validate input against schema
                        try:
                            # Ensure task_id is present or generate one
                            if "task_id" not in tool_input:
                                tool_input["task_id"] = str(uuid.uuid4())

                            task = DirectorTask(**tool_input)

                            # Log task delegation
                            yield {"type": "thinking", "content": f"Delegating task: {task.instruction}"}

                            # Execute via Associate
                            # Note: The associate logs its own tool calls to the store
                            result: AssociateResult = await self.associate.run(task)

                            tool_result_content = result.model_dump_json()

                            yield {
                                "type": "tool_result",
                                "content": {
                                    "tool": tool_name,
                                    "result": json.loads(tool_result_content)
                                }
                            }

                            # Log tool call to event store
                            self.store.log_tool_call(
                                conversation_id,
                                tool_name,
                                tool_input,
                                json.loads(tool_result_content)
                            )

                        except Exception as e:
                            tool_result_content = json.dumps({"error": str(e)})
                            yield {"type": "error", "content": f"Task delegation failed: {e}"}

                            # Log failed tool call
                            self.store.log_tool_call(
                                conversation_id,
                                tool_name,
                                tool_input,
                                {"error": str(e)}
                            )

                    messages.append({"role": "assistant", "content": assistant_content})
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": tool_result_content,
                        }]
                    })
                    assistant_content = []

            # If the Director didn't use a tool, it's replying to the user
            if not has_tool_use:
                if assistant_text_parts:
                    full_response = "\n".join(assistant_text_parts)
                    self.store.add_message(
                        conversation_id,
                        "assistant",
                        full_response
                    )
                break

            # If we processed tool uses, we loop again to see what the Director wants to do next
            # (e.g., delegate another task or answer user)

        if current_turn >= max_turns:
             yield {"type": "error", "content": "Director reached maximum turn limit."}

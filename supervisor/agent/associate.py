"""
Associate Agent - Executes tasks defined by the Director.
"""

import json
import os
from typing import Optional, Any
import anthropic

from .tools import AgentTools
from .schemas import DirectorTask, AssociateResult
from ..db import get_store, EventStore

MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

ASSOCIATE_SYSTEM_PROMPT = """You are the Associate, an agentic Ralph loop in the ChoirOS system.
Your goal is to execute deterministic tasks assigned by the Director.

You have access to tools to:
- Read, write, and edit files in the /app/choiros directory
- Execute shell commands
- Manage git checkpoints
- Inspect the environment

When you receive a task:
1. Understand the goal and acceptance criteria.
2. Use tools to achieve the goal.
3. Verify your work using provided verification commands or by inspecting the state.
4. Submit the result using the `submit_result` tool.

You must submit a result to complete the task.
Do not ask the user for input directly; if you need input, report it in the `needs_input` status in your result.
"""

class AssociateAgent:
    """Executes DirectorTasks using tools."""

    def __init__(self, file_history=None, event_store: Optional[EventStore] = None):
        self.tools = AgentTools(file_history=file_history)
        self.store = event_store or get_store()
        self.client = anthropic.AnthropicBedrock(
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        )
        self.task: Optional[DirectorTask] = None

    async def run(self, task: DirectorTask) -> AssociateResult:
        """
        Run the Associate loop to complete the task.
        """
        self.task = task

        # Prepare tools: Standard tools + submit_result
        tools = list(AgentTools.TOOL_DEFINITIONS)
        tools.append({
            "name": "submit_result",
            "description": "Submit the final result of the task execution.",
            "input_schema": AssociateResult.model_json_schema()
        })

        # Construct initial message
        prompt = f"""Task ID: {task.task_id}
Kind: {task.kind}
Instruction: {task.instruction}
Acceptance Criteria:
{json.dumps(task.acceptance_criteria, indent=2)}

Base Ref: {task.base_ref}
Allowed Tools: {task.allowed_tools}
Commands: {task.commands}
Verify Profile: {json.dumps(task.verify_profile.model_dump(), indent=2)}
Egress Profile: {json.dumps(task.egress_profile.model_dump(), indent=2)}
"""
        messages = [{"role": "user", "content": prompt}]

        max_turns = 20
        current_turn = 0

        while current_turn < max_turns:
            current_turn += 1

            # Call Claude
            response = self.client.messages.create(
                model=MODEL_ID,
                max_tokens=4096,
                system=ASSOCIATE_SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

            assistant_content = []

            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})

                elif block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_use_id = block.id

                    assistant_content.append({
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": tool_input,
                    })

                    # Handle submit_result specially
                    if tool_name == "submit_result":
                        try:
                            result = AssociateResult(**tool_input)
                            return result
                        except Exception as e:
                            # If validation fails, feed it back to the agent
                            error_msg = f"Invalid result format: {str(e)}"
                            messages.append({"role": "assistant", "content": assistant_content})
                            messages.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": error_msg,
                                    "is_error": True
                                }]
                            })
                            assistant_content = [] # Reset for next iteration (which comes from the continue)
                            continue

                    # Execute standard tools
                    # Enforce allowed_tools
                    # If allowed_tools is explicitly set (even empty), enforce it.
                    # If None, allow all (though schema says List[str] so it might be empty list)
                    # Based on contract: "allowlist: empty unless explicitly set" in Egress.
                    # For allowed_tools, the example shows a list.
                    # I will interpret any list (even empty) as "restrict to these tools".
                    # submit_result is always allowed.

                    is_allowed = True
                    if task.allowed_tools is not None:
                        if tool_name not in task.allowed_tools and tool_name != "submit_result":
                            is_allowed = False

                    if not is_allowed:
                         result = {"error": f"Tool {tool_name} is not allowed for this task. Allowed: {task.allowed_tools}"}
                    else:
                        result = await self.tools.execute_tool(tool_name, tool_input)

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

            # If we didn't return from submit_result and loop finished, we continue

        # If we run out of turns
        return AssociateResult(
            task_id=task.task_id,
            status="failed",
            summary="Associate ran out of turns.",
            questions=["Task timed out."]
        )

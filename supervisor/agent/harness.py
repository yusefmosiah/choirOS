
"""
Agent Harness - Main agent loop using BAML and AWS Bedrock.

Receives prompts via WebSocket, plans actions using BAML, and executes tools.
Logs all events to the SQLite event store.
Streaming is handled via BAML's stream feature.
"""

import json
import logging
import uuid
from typing import AsyncGenerator, Any, Optional, List

from .tools import AgentTools
from ..db import ProjectionStore, get_store
from ..event_publisher import EventPublisher, get_publisher
from ..mode_config import ModeConfig, get_mode_config
from ..prompt_builder import ModePromptBuilder
from supervisor.baml_client import b
from supervisor.baml_client.types import Message, AgentPlan, AgentToolCall
from supervisor.replay import ReplayToolCache

logger = logging.getLogger("agent-harness")

class AgentHarness:
    """Main agent harness that processes prompts and executes tools using BAML."""

    def __init__(
        self,
        file_history=None,
        projection: Optional[ProjectionStore] = None,
        publisher: Optional[EventPublisher] = None,
        mode_config: Optional[ModeConfig] = None,
        prompt_builder: Optional[ModePromptBuilder] = None,
        replay: bool = False,
        replay_read_only: bool = True,
        replay_conversation_id: Optional[int] = None,
    ):
        self.projection = projection or get_store()
        self.publisher = publisher or get_publisher(self.projection.user_id)
        self.mode_config = mode_config or get_mode_config("CALM")
        self.prompt_builder = prompt_builder or ModePromptBuilder()
        self.tools = AgentTools(
            file_history=file_history,
            event_publisher=self.publisher,
            mode_config=self.mode_config,
        )
        self.conversation_id: Optional[int] = None
        self.message_history: List[Message] = []
        self.current_run_id: Optional[str] = None
        self.replay = replay
        self.replay_read_only = replay_read_only
        self.replay_conversation_id = replay_conversation_id
        self._replay_tools: Optional[ReplayToolCache] = None

    def set_mode(self, mode_config: ModeConfig) -> None:
        if self.mode_config.mode_id != mode_config.mode_id:
            self.message_history = []
            self.conversation_id = None
        self.mode_config = mode_config
        self.tools.mode_config = mode_config

    def load_replay_context(self, conversation_id: int) -> None:
        self.conversation_id = conversation_id
        messages = self.projection.get_conversation_messages(conversation_id, limit=1000)
        self.message_history = [Message(role=m["role"], content=m["content"]) for m in messages]
        self._replay_tools = ReplayToolCache.from_store(self.projection, conversation_id)

    def _get_replay_tool_result(self, tool_name: str, tool_input: dict) -> Optional[Any]:
        if not self.replay:
            return None
        if self._replay_tools is None and self.conversation_id is not None:
            self._replay_tools = ReplayToolCache.from_store(self.projection, self.conversation_id)
        if not self._replay_tools:
            return None
        return self._replay_tools.get(tool_name, tool_input)

    async def process(self, prompt: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process a user prompt and yield responses.
        Uses BAML streaming to send updates.
        """
        try:
            # Ensure we have a conversation
            if self.conversation_id is None:
                if self.replay and self.replay_conversation_id is not None:
                    self.load_replay_context(self.replay_conversation_id)
                else:
                    self.conversation_id = int(uuid.uuid4().int >> 64)

            if self.tools:
                self.tools.current_run_id = self.current_run_id

            ahdb_state = self.projection.get_ahdb_state()
            system_context = self.prompt_builder.build(
                mode=self.mode_config,
                ahdb_state=ahdb_state,
                context={"receipts": [], "artifacts": []},
            )
            if not self.replay_read_only:
                await self.publisher.publish(
                    "receipt.context.footprint",
                    {
                        "conversation_id": self.conversation_id,
                        "mode": self.mode_config.mode_id,
                        "ahdb_keys": sorted(ahdb_state.keys()),
                        "run_id": self.current_run_id,
                    },
                    source="system",
                )

            # Log user message
            if not self.replay_read_only:
                await self.publisher.add_message_async(
                    self.conversation_id,
                    "user",
                    prompt,
                    run_id=self.current_run_id,
                )
            self.message_history.append(Message(role="user", content=prompt))

            # Initial "thinking" state
            yield {"type": "thinking", "content": "Planning..."}

            while True:
                # 1. Call BAML to Plan Action (Streaming)
                # We collect the partial 'thinking' to yield it
                current_thinking = ""
                final_plan: Optional[AgentPlan] = None

                # We need to construct the prompt with available tools listing
                # Since BAML calls the LLM, we pass tool defs as a string for the prompt context
                allowed = self.mode_config.tool_allowlist
                tool_defs_str = json.dumps(
                    [t["name"] for t in AgentTools.TOOL_DEFINITIONS if t["name"] in allowed],
                    indent=2,
                )

                # Get the current provider's BAML client
                from ..provider_factory import get_provider_factory
                factory = get_provider_factory(self.projection)
                client = factory.get_baml_client()

                stream = b.with_options(client=client).stream.PlanAction(
                    messages=self.message_history,
                    system_context=system_context,
                    available_tools=tool_defs_str,
                )

                async for chunk in stream:
                    if chunk.thinking and len(chunk.thinking) > len(current_thinking):
                        delta = chunk.thinking[len(current_thinking):]
                        current_thinking = chunk.thinking
                        # Emit thinking delta
                        yield {"type": "thinking", "content": delta}

                    # We can also track if confidence or tool_calls appear roughly?
                    # BAML stream yields partial objects.

                # Get final result
                final_plan = await stream.get_final_response()

                # If we have a final response (no tools), we are done
                if final_plan.final_response:
                     yield {"type": "text", "content": final_plan.final_response}
                     if not self.replay_read_only:
                        await self.publisher.add_message_async(
                            self.conversation_id,
                            "assistant",
                            final_plan.final_response,
                            run_id=self.current_run_id,
                        )
                     self.message_history.append(Message(role="assistant", content=final_plan.final_response))
                     break

                # If no tool calls and no final response, something is wrong, but let's break to avoid loop
                if not final_plan.tool_calls:
                     logger.warning("No tool calls and no final response from agent.")
                     break

                # 2. Execute Tools
                # We treat the plan as the assistant's "thought" + "tool request"
                # In strict chat logic, we might need to record the assistant's turn.
                # Here we'll simplify: The "Thinking" is the reasoning.

                # We add the "thinking" as an assistant message?
                # Or we just add the tool results.
                # BAML doesn't manage the `messages` list automatically, we must do it.
                # Standard practice: User -> Assistant (with tool_calls) -> User (with tool_results)

                # Construct assistant message for history
                # Note: Our simple Message schema (role, content) doesn't strictly support `tool_calls` field
                # compatible with Anthropic API directly if we were passing it raw.
                # But since we use BAML to format the prompt, we just need to represent it effectively.

                # Let's format the assistant's turn as:
                # "Thinking: <reasoning>\nCalling: <tools>"
                assistant_content = f"Thinking: {final_plan.thinking}\n"
                for tc in final_plan.tool_calls:
                     assistant_content += f"Tool Call: {tc.tool_name}({tc.tool_args})\n"

                self.message_history.append(Message(role="assistant", content=assistant_content))
                await self.publisher.add_message_async(
                    self.conversation_id,
                    "assistant",
                    assistant_content,
                    run_id=self.current_run_id,
                )

                # Execute each tool
                # Wait, PlanAction returns ALL tool calls for this turn concurrently?
                # BAML returns a list.

                for tc in final_plan.tool_calls:
                    yield {
                        "type": "tool_use",
                        "content": {
                            "tool": tc.tool_name,
                            "input": tc.tool_args # It's a string, frontend might expect dict
                        }
                    }

                    # Parse args
                    try:
                        args = json.loads(tc.tool_args)
                    except:
                        args = {} # Should act as empty dict if parsing fails? or error

                    replay_result = self._get_replay_tool_result(tc.tool_name, args)
                    if replay_result is None and self.replay:
                        raise RuntimeError(f"Replay missing tool result for {tc.tool_name}")
                    tool_call_id = str(uuid.uuid4())
                    if not self.replay_read_only:
                        await self.publisher.log_tool_call_async(
                            self.conversation_id,
                            tc.tool_name,
                            args,
                            tool_call_id,
                            run_id=self.current_run_id,
                        )

                    result = replay_result if replay_result is not None else await self.tools.execute_tool(
                        tc.tool_name,
                        args,
                    )
                    if not self.replay_read_only:
                        await self.publisher.log_tool_result_async(
                            self.conversation_id,
                            tc.tool_name,
                            result,
                            tool_call_id,
                            run_id=self.current_run_id,
                        )

                    yield {
                        "type": "tool_result",
                        "content": {
                            "tool": tc.tool_name,
                            "result": result
                        }
                    }

                    # Append result to history
                    # We attribute tool results to 'user' role usually in simple chat formats,
                    # or 'system' or specific tool role if supported.
                    # Our BAML Loop uses just User/Assistant/System usually.
                    tool_result_str = f"Tool '{tc.tool_name}' Result: {json.dumps(result)}"
                    self.message_history.append(Message(role="user", content=tool_result_str))

                # Loop continues to next PlanAction

            yield {"type": "done", "content": None}

        except Exception as e:
            logger.error(f"Agent process error: {e}")
            yield {"type": "error", "content": str(e)}

"""
Agent Harness - Entry point for the Ralph-in-Ralph agent system.
Orchestrates the Director and Associate agents.
"""

import json
from typing import AsyncGenerator, Any, Optional

from .director import DirectorAgent
from ..db import get_store, EventStore


class AgentHarness:
    """
    Main harness that initializes the Director and routes user prompts to it.
    """

    def __init__(self, file_history=None, event_store: Optional[EventStore] = None):
        """
        Initialize the agent harness.
        """
        self.store = event_store or get_store()
        self.conversation_id: Optional[int] = None

        # Initialize the Director
        self.director = DirectorAgent(file_history=file_history, event_store=self.store)

    async def process(self, prompt: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process a user prompt by sending it to the Director.
        """
        try:
            # Ensure we have a conversation
            if self.conversation_id is None:
                self.conversation_id = self.store.get_or_create_conversation()
            
            # Log user message
            self.store.add_message(self.conversation_id, "user", prompt)
            
            yield {"type": "thinking", "content": "Director is planning..."}

            # Run Director
            async for event in self.director.run(prompt, self.conversation_id):
                yield event

            yield {"type": "done", "content": None}

        except Exception as e:
            yield {"type": "error", "content": str(e)}

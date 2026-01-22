
import asyncio
import json
from typing import Optional, List, Dict
from supervisor.baml_client import b
from supervisor.baml_client.types import AuditorContext, AuditResult
from .tools import AgentTools

class UnilateralAuditor:
    """
    The Unilateral Auditor agent.

    Critiques context using BAML-defined persona and specialized tools.
    """

    def __init__(self, tools: Optional[AgentTools] = None):
        self.tools = tools or AgentTools()

    async def audit(self,
                   task_description: str,
                   recent_events: List[str],
                   file_content: Optional[str] = None) -> AuditResult:
        """
        Run the audit loop.

        Args:
            task_description: What the user is doing.
            recent_events: List of recent actions/events.
            file_content: Optional content of the file being worked on.

        Returns:
            AuditResult containing the critique.
        """

        # 1. Gather context object
        context = AuditorContext(
            task_description=task_description,
            recent_events=recent_events,
            file_content=file_content
        )

        # 2. Call BAML function
        # BAML handles the LLM call and structured parsing
        result = await b.Audit(context)

        # 3. (Optional) If result contains search queries, execute them and re-audit?
        # For Phase 1, we just return the first pass critique.

        return result

    async def audit_file(self, file_path: str) -> AuditResult:
        """Helper to audit a specific file."""
        read_result = await self.tools.read_file(file_path)
        if "error" in read_result:
            raise ValueError(f"Could not read file {file_path}: {read_result['error']}")

        content = read_result.get("content", "")

        return await self.audit(
            task_description=f"Auditing file {file_path}",
            recent_events=[f"User edited {file_path}"],
            file_content=content
        )

"""Mode configuration for the agent harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ModeBudgets:
    time_seconds: int = 600
    tool_calls: int = 50
    diff_bytes: int = 50_000
    files_touched: int = 10


@dataclass(frozen=True)
class ModeConfig:
    mode_id: str
    tool_allowlist: list[str]
    allow_write: bool = False
    allow_network: bool = False
    budgets: ModeBudgets = field(default_factory=ModeBudgets)
    description: Optional[str] = None

    def allows_tool(self, tool_name: str) -> bool:
        return tool_name in self.tool_allowlist


def get_mode_config(mode_id: str) -> ModeConfig:
    key = (mode_id or "").upper()
    if key == "CURIOUS":
        return ModeConfig(
            mode_id="CURIOUS",
            description="Read-only inquiry and retrieval.",
            tool_allowlist=["read_file", "read_artifact", "web_search", "git_status"],
            allow_write=False,
            allow_network=True,
            budgets=ModeBudgets(time_seconds=300, tool_calls=25, diff_bytes=0, files_touched=0),
        )
    if key == "SKEPTICAL":
        return ModeConfig(
            mode_id="SKEPTICAL",
            description="Verification and adjudication only.",
            tool_allowlist=["read_file", "read_artifact", "bash", "git_status"],
            allow_write=False,
            allow_network=False,
            budgets=ModeBudgets(time_seconds=600, tool_calls=40, diff_bytes=0, files_touched=0),
        )
    if key == "PARANOID":
        return ModeConfig(
            mode_id="PARANOID",
            description="Hardening and safety checks.",
            tool_allowlist=["read_file", "read_artifact", "bash", "git_status"],
            allow_write=False,
            allow_network=False,
            budgets=ModeBudgets(time_seconds=600, tool_calls=30, diff_bytes=0, files_touched=0),
        )
    if key == "DEFERENTIAL":
        return ModeConfig(
            mode_id="DEFERENTIAL",
            description="Preference elicitation and approvals.",
            tool_allowlist=["read_file", "read_artifact"],
            allow_write=False,
            allow_network=False,
            budgets=ModeBudgets(time_seconds=300, tool_calls=10, diff_bytes=0, files_touched=0),
        )
    if key == "CONTRITE":
        return ModeConfig(
            mode_id="CONTRITE",
            description="Recovery and state consistency checks.",
            tool_allowlist=["read_file", "read_artifact", "git_status"],
            allow_write=False,
            allow_network=False,
            budgets=ModeBudgets(time_seconds=300, tool_calls=20, diff_bytes=0, files_touched=0),
        )
    if key == "BOLD":
        return ModeConfig(
            mode_id="BOLD",
            description="High-velocity execution with verification.",
            tool_allowlist=["read_file", "read_artifact", "write_file", "edit_file", "bash", "git_checkpoint", "git_status"],
            allow_write=True,
            allow_network=False,
            budgets=ModeBudgets(time_seconds=600, tool_calls=60, diff_bytes=100_000, files_touched=20),
        )
    if key == "PETTY":
        return ModeConfig(
            mode_id="PETTY",
            description="Adversarial or exploit detection lane.",
            tool_allowlist=["read_file", "read_artifact", "bash", "git_status"],
            allow_write=False,
            allow_network=False,
            budgets=ModeBudgets(time_seconds=600, tool_calls=20, diff_bytes=0, files_touched=0),
        )
    return ModeConfig(
        mode_id="CALM",
        description="Default execution mode.",
        tool_allowlist=["read_file", "read_artifact", "write_file", "edit_file", "bash", "git_checkpoint", "git_status"],
        allow_write=True,
        allow_network=False,
        budgets=ModeBudgets(time_seconds=600, tool_calls=50, diff_bytes=50_000, files_touched=10),
    )

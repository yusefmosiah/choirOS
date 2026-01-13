from typing import List, Optional, Any, Literal
from pydantic import BaseModel, Field

class EgressProfile(BaseModel):
    mode: Literal["git+pkg"] = "git+pkg"
    allowlist: List[str] = Field(default_factory=list)

class VerifyProfile(BaseModel):
    mode: Literal["smoke"] = "smoke"
    commands: List[str] = Field(default_factory=list)

class DirectorTask(BaseModel):
    task_id: str
    kind: Literal["edit_repo", "run", "git", "inspect"]
    instruction: str
    acceptance_criteria: List[str]
    base_ref: Optional[str] = None
    allowed_tools: List[str]
    egress_profile: EgressProfile = Field(default_factory=EgressProfile)
    verify_profile: VerifyProfile = Field(default_factory=VerifyProfile)
    commands: List[str] = Field(default_factory=list)
    time_budget_s: int = 300
    return_config: dict = Field(default_factory=dict, alias="return")

class CommandRun(BaseModel):
    command: str
    exit_code: int
    stdout_path: Optional[str] = None
    stderr_path: Optional[str] = None

class DiffContent(BaseModel):
    format: Literal["unified"] = "unified"
    content: str

class VerificationResult(BaseModel):
    mode: Literal["smoke"] = "smoke"
    status: Literal["pass", "fail", "unknown"]
    commands: List[str] = Field(default_factory=list)
    logs_path: Optional[str] = None

class AssociateResult(BaseModel):
    task_id: str
    status: Literal["ok", "needs_input", "failed"]
    summary: str
    diff: Optional[DiffContent] = None
    files_changed: List[str] = Field(default_factory=list)
    commands_run: List[CommandRun] = Field(default_factory=list)
    verify: Optional[VerificationResult] = None
    questions: List[str] = Field(default_factory=list)
    suggested_next: Optional[str] = None

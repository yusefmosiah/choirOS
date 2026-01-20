// ─────────────────────────────────────────────────────────────────────────────
// ChoirOS Agent Functions - BAML LLM Functions
// ─────────────────────────────────────────────────────────────────────────────
//
// These functions define structured LLM calls for the agent loop.
// Uses ClaudeBedrock client from verifier.baml.

// ─────────────────────────────────────────────────────────────────────────────
// Agent Planning
// ─────────────────────────────────────────────────────────────────────────────

class AgentPlan {
  thinking string @description("Step-by-step reasoning about the task")
  tool_calls ToolCall[] @description("Ordered list of tools to invoke")
  confidence float @description("0.0 to 1.0 confidence in this plan")
}

function PlanAction(
  user_prompt: string,
  system_context: string,
  available_tools: string
) -> AgentPlan {
  client ClaudeBedrock
  prompt #"
    You are the ChoirOS agent. Given the user's request and system context,
    plan the sequence of tool calls needed to complete the task.

    {{ system_context }}

    Available tools:
    {{ available_tools }}

    User request: {{ user_prompt }}

    Think step-by-step, then output your plan.

    {{ ctx.output_format }}
  "#
}

// ─────────────────────────────────────────────────────────────────────────────
// Agent Synthesis
// ─────────────────────────────────────────────────────────────────────────────

class AgentResponse {
  summary string @description("Concise summary of what was done")
  details string[] @description("Key observations or results")
  next_steps string? @description("Suggested follow-up actions, if any")
}

function SynthesizeResponse(
  user_prompt: string,
  tool_results: string
) -> AgentResponse {
  client ClaudeBedrock
  prompt #"
    You are the ChoirOS agent. The user made a request, and you executed tools.
    Synthesize the results into a helpful response.

    User request: {{ user_prompt }}

    Tool execution results:
    {{ tool_results }}

    Summarize what happened and any relevant details.

    {{ ctx.output_format }}
  "#
}

// ─────────────────────────────────────────────────────────────────────────────
// Task Analysis (for Director)
// ─────────────────────────────────────────────────────────────────────────────

class TaskAssessment {
  complexity string @description("One of: TRIVIAL, MODERATE, COMPLEX")
  requires_verification bool @description("Should this task go through verification?")
  risk_factors string[] @description("Potential issues to watch for")
  estimated_steps int @description("Approximate number of tool calls needed")
}

function AssessTask(prompt: string) -> TaskAssessment {
  client ClaudeBedrock
  prompt #"
    Analyze this user request and assess its complexity, risk, and scope.

    User request: {{ prompt }}

    Consider:
    - Does this modify files? (higher risk)
    - Does this require multiple steps? (higher complexity)
    - Could this break the system? (needs verification)

    {{ ctx.output_format }}
  "#
}

generator PythonClient {
  output_type python/pydantic
  output_dir "../supervisor"
  version "0.217.0"
}

// ─────────────────────────────────────────────────────────────────────────────
// Clients: ChoirOS "Moods" implemented as BAML client strategies
// ─────────────────────────────────────────────────────────────────────────────

// SKEPTICAL mood: Low temp, reasoning-heavy. Used for verification.
client<llm> ClaudeBedrock {
  provider aws-bedrock
  options {
    model "us.anthropic.claude-opus-4-5-20251101-v1:0"
    region "us-east-1"
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Types: Structured outputs for verification
// ─────────────────────────────────────────────────────────────────────────────

class VerifierOutcome {
  status string @description("One of: PASS, FAIL, BLOCKER")
  summary string @description("Concise summary of what happened")
  details string[] @description("Key observations or errors found in the logs")
  confidence float @description("0.0 to 1.0 confidence in this assessment")
}

// ─────────────────────────────────────────────────────────────────────────────
// Functions: LLM-powered analysis
// ─────────────────────────────────────────────────────────────────────────────

function AnalyzeVerifierOutput(command: string, exit_code: int, stdout: string, stderr: string) -> VerifierOutcome {
  client ClaudeBedrock
  prompt #"
    Analyze the execution of the following command:
    Command: {{ command }}
    Exit Code: {{ exit_code }}

    --- STDOUT ---
    {{ stdout }}

    --- STDERR ---
    {{ stderr }}

    Determine if this was a success or failure.
    Even if exit_code is 0, look for error messages in the logs.
    If exit_code is non-zero, it is likely a failure, but explain why.

    {{ ctx.output_format }}
  "#
}

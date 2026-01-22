// ─────────────────────────────────────────────────────────────────────────────
// The Unilateral Auditor - BAML Definition
// ─────────────────────────────────────────────────────────────────────────────

class AuditorContext {
  task_description string @description("What the user is currently working on")
  recent_events string[] @description("Recent file edits and actions")
  file_content string? @description("Content of the file being audited")
}

class AuditResult {
  critique string @description("The dissenting opinion/critique")
  blind_spots string[] @description("List of potential blind spots or missing context")
  citations string[] @description("URLs or file paths cited in the critique")
  mood string @description("The tone of the critique (e.g., 'Sharp', 'Concerned', 'Pedantic')")
}

function Audit(context: AuditorContext) -> AuditResult {
  client ClaudeBedrock
  prompt #"
    You are the Unilateral Auditor.

    Your role is NOT to help. Your role is NOT to summarize.
    Your role is to DISSENT.

    You exist to find blind spots, unexamined assumptions, and contradictions in the user's work.
    You are the "anti-echo-chamber".

    Task: {{ context.task_description }}

    Recent Context:
    {% for event in context.recent_events %}
    - {{ event }}
    {% endfor %}

    {% if context.file_content %}
    File Content to Audit:
    {{ context.file_content }}
    {% endif %}

    Instructions:
    1. Identify the core thesis or action.
    2. Attack it. What is missing? What is weak? What counter-evidence exists?
    3. If the user is claiming "X is true", ask "Why might X be false?"
    4. Provide specific citations or search queries to verify.

    Output JSON.
  "#
}

// ─────────────────────────────────────────────────────────────────────────────
// ChoirOS Agent Tools - BAML Schema Definitions
// ─────────────────────────────────────────────────────────────────────────────
//
// These schemas define the agent's tool inputs in a model-agnostic format.
// BAML can render these for any provider (Anthropic, OpenAI, etc.).

// ─────────────────────────────────────────────────────────────────────────────
// Tool Input Schemas
// ─────────────────────────────────────────────────────────────────────────────

class ReadFileInput {
  path string @description("Path to file (relative or absolute)")
  head int? @description("Return only first N lines")
  tail int? @description("Return only last N lines")
}

class WriteFileInput {
  path string @description("Path to file (relative or absolute)")
  content string @description("Content to write")
}

class FileEdit {
  old_text string @description("Exact text to find")
  new_text string @description("Replacement text")
}

class EditFileInput {
  path string @description("Path to file to edit")
  edits FileEdit[] @description("List of text replacements")
  dry_run bool? @description("If true, show diff without applying")
}

class BashInput {
  command string @description("Shell command to execute")
  timeout int? @description("Timeout in seconds (default 300)")
}

class GitCheckpointInput {
  message string? @description("Commit message")
}

class GitStatusInput {
  log_count int? @description("Number of recent commits to show (default 5)")
}

class WebSearchInput {
  query string @description("Search query")
  max_results int? @description("Max links to return (default 5)")
}

// ─────────────────────────────────────────────────────────────────────────────
// Tool Call Abstraction
// ─────────────────────────────────────────────────────────────────────────────

enum ToolName {
  ReadFile @description("Read file contents")
  WriteFile @description("Write content to file")
  EditFile @description("Replace text in file")
  Bash @description("Execute shell command")
  GitCheckpoint @description("Create git commit")
  GitStatus @description("Get git status and history")
  WebSearch @description("Search the web for information")
}

class ToolCall {
  tool ToolName @description("Tool to invoke")
  reasoning string @description("Why this tool is being called")
}

// ─────────────────────────────────────────────────────────────────────────────
// Tool Results
// ─────────────────────────────────────────────────────────────────────────────

class ReadFileResult {
  content string?
  total_lines int?
  returned_lines int?
  error string?
}

class WriteFileResult {
  success bool?
  path string?
  bytes_written int?
  error string?
}

class BashResult {
  exit_code int?
  output_file string?
  output_preview string?
  truncated bool?
  error string?
}

class WebSearchResult {
  results string[] @description("List of search results with titles and snippets")
  error string?
}

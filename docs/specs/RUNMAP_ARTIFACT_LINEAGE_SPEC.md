# RunMap And Artifact Lineage Spec

This spec replaces "conversation/chat/thread" language with a run-first model.

## Canonical Vocabulary

- Conversation -> Run
- Message -> Run Trace Event (or Run Input)
- Thread/History -> Artifact Lineage
- Context Heatmap -> RunMap

## Core Entities

### Run

Every command prompt submission creates exactly one run.

Suggested shape:

- run_id: string
- work_item_id: string
- prompt: string
- status: queued | running | completed | failed | cancelled
- created_at: string
- started_at: string | null
- finished_at: string | null
- parent_artifact_id: string | null
- parent_artifact_version: number | null
- output_artifact_id: string | null
- output_artifact_version: number | null

### Run Input

Run inputs capture the initial prompt and any follow-ups issued inside the RunMap while a run
is processing.

Suggested shape:

- input_id: string
- run_id: string
- prompt: string
- kind: initial | followup | comment
- created_at: string

### Artifact And Artifact Version

Artifacts are run outputs. Each run should produce a primary artifact version.

Suggested shapes:

Artifact:
- artifact_id: string
- path: string
- latest_version: number
- created_at: string
- updated_at: string

Artifact Version:
- artifact_id: string
- version: number
- run_id: string
- parent_version: number | null
- content_pointer: string
- created_at: string

### Comment

Comments attach to an artifact version. Creating a comment spawns a new run that targets the
artifact version.

Suggested shape:

- comment_id: string
- artifact_id: string
- artifact_version: number
- body: string
- created_at: string
- spawned_run_id: string | null

### Run Trace Event

Run trace events are replayable observability records tied to a run.

Suggested shape:

- event_seq: number
- run_id: string
- timestamp: string
- type: string
- payload: object

Examples:

- context.footprint
- tool.use
- tool.result
- file.read
- file.write
- web.search
- artifact.write
- mode.start
- mode.update
- mode.stop

## UX Rules

1. Command bar submission creates a new run.
2. The RunMap window opens automatically for the run.
3. Follow-ups issued inside the RunMap apply to the same run.
4. The RunMap sidebar lists past runs and enables replay.
5. The Files app should expose artifact lineage and allow "attach to run".

## Migration Strategy (Incremental)

1. Make run_id a first-class field across work items, run traces, and tool/message logs.
2. Ensure the scheduler executes run-scoped work without cross-session mixing.
3. Add run listing and run trace endpoints for the RunMap sidebar and replay.
4. Introduce run inputs to capture follow-ups in the RunMap UI.
5. Implement artifact lineage and comment -> run spawning.


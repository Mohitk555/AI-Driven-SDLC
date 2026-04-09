# CLI Interaction Instruction Contract

## Purpose
Standardize terminal-based interaction with the instruction-driven SDLC system.

## Session Rules
- Every request must include a `session_id`.
- Maintain context by reusing the same `session_id` for related actions.
- Display phase, active agent, and tool summary in each response.

## Request Envelope
1. `message`
2. `session_id`
3. `mode` (optional: `chat` or `pipeline`)

## Response Envelope
1. `status`
2. `intent`
3. `agent_id`
4. `message`
5. `data`

## Behavioral Constraints
- Keep responses deterministic and concise.
- Do not present unverified tool results as completed work.
- Show blocked state clearly with next required action.
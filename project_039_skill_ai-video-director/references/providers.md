# Provider adapter contract

This file describes responsibilities, not an SDK. Discover callable tools and their current schemas on every new session. Never invent a model name, generation option, endpoint or account balance. Preserve valid ongoing jobs when capabilities change.

## Native Codex image generation

Use the built-in image generation tool for visual bibles and clean shot frames. It works inside a supported Codex host; the local Python helper cannot invoke it. No separate OpenAI API key is required for this path. Follow the installed tool's exact parameters and image-reference limit. For a local reference, inspect it first. Label each reference's role (face, clothing, setting, object, style); maintain the canonical reference rather than editing an increasingly drifted derivative forever.

Native output may first be saved in a host-controlled cache. Copy selected assets to the user's project and record their source; do not promise the tool can write to an arbitrary output directory. Preserve the default original unless specifically authorized to remove it. Do not switch to an API script or a different image model to evade this path behavior. If native generation is unavailable, tell the user and ask about an explicitly chosen alternative.

## Kling: capability → upload → generate → query → download

1. Discover `who_am_i`, confirm connection and read the relevant `availableModels.image_to_video` entry. If the server reports that the host tool list is stale, follow its refresh instructions. Query membership/credits only through the connected tools. Ignore another project's old balance.
2. Choose a suitable available model using its current description, input roles, duration/resolution and audio constraints. A model with multi-reference/Elements is useful for consistency only when those features are declared. Single-frame versus tail-frame versus motion-control is a creative choice, not an automatic escalation ladder. Do not change an existing user-bound Element into its cover image.
3. Confirm existing authority covers sending the needed images/video/text to Kling and the planned paid jobs. Bundle only genuinely missing questions. A plan estimate is not a promised server quote. Record authorized limits in the manifest; don't manufacture authorization to satisfy the script.
4. Prepare each compatible local upload using current limits; preserve the high-quality original. Request `file_upload` using the actual byte length and MIME type. Use the returned one-time upload ticket exactly as documented, then persist the final resource URL. Reuse an unchanged uploaded resource where valid; an expired ticket is not the final resource URL. Keep tickets and signed URLs private.
5. Save the exact intended request and reserve its estimated charge locally. A currently observed MCP shape is `{model, arguments:[{name,value}], inputs:[{name,inputType:"URL",url}], rationale, taskTraceId}`. This is an example, not a frozen schema: argument values were strings, and `who_am_i` provided the valid names. Prefer explicit single-result generation. Create/reuse a task trace identifier according to the live schema; don't fill placeholders into a real call.
6. Call generation once. Immediately save the raw response before parsing, inspect `isError`/error fields, then record the real generation ID and any actual fee. If a filesystem write fails after submission, recover the returned ID from the conversation/tool output and write it locally; do NOT generate again. In concurrent host cells, wait for upload completion before consuming its URL; an in-flight global store may not be visible elsewhere.
7. Poll `query_tasks` for the existing ID at a moderate interval (e.g. 15/30/60 seconds, adjust to the service). A polling network error is not a failed generation or permission to submit a replacement. Announce long waits and retain resumable state. Respect tool rules on timeout/failure and any required user choice before retry. Do not busy-poll finished jobs. Download real output media before URLs expire and verify its container/duration.
8. Prefer a provider-supplied legitimately available watermark-free download when present. Do not describe upscaled output as native 4K or assume a server `COMPLETED` means artistic acceptance. A refund requires evidence; don't attribute an account balance delta across concurrent projects to one job. No unsolicited feedback messages to third parties; follow host authorization rules.

If only the official Kling CLI is available, inspect its installed skill/help and use the equivalent authenticated operations. For a missing CLI, account region and installation are setup decisions; do not guess the region, scrape cookies, request pasted tokens, or build a private API client. This bundle does not install or update provider tools automatically.

## Voices, music and sound

Decide exact speech before timing final shots. Prefer an already connected speech/audio tool with a stable supported voice. Discover its schema, confirm necessary external text transmission is within scope, then save every utterance and its actual duration. Keep a display transcript separate from a pronunciation-adjusted TTS transcript; protect factual meaning and exact names. A voice model's marketing label is not evidence of accurate pronunciation. Native Kling speech is an alternative only when deliberately selected, checked and budgeted; do not create extra video jobs merely to discover a voice without authorization.

Use music supplied with appropriate permission, a licensed local library, or an authorized generator. Record source and allowed use. Do not invent license claims or silently fetch arbitrary commercial tracks. For quick mode, one coherent music/FX bed is usually enough. If an essential soundtrack cannot be produced, mark BLOCKED_SOUND and ask one actionable question; do not call a silent export the requested narrated film. A user-approved silent sample is valid and must be labelled as such.

## Decision boundaries after an imperfect generation

| Evidence | Allowed next step |
|---|---|
| Usable interval already exists; full intended action remains | Select that interval, update edit timing and review its boundaries |
| Only a harmless visual detail needs local correction | Perform a truthful deterministic fix; record what changed |
| Required action absent, wrong identity, extra limb, object teleportation | Reject the interval; prepare a targeted correction, follow provider retry authorization |
| Same first/end frame made the hands motionless | Simplify to a single start frame if authorized; don't declare camera motion to be hand action |
| Service outcome uncertain or receipt missing | Recover/query the original job; never assume no charge |
| All requested shots accepted | Proceed to finishing; no need to regenerate for a new arbitrary style preference |

Generated clips, photographs, scripts and music are not covered by this repository's software license merely because this skill used them.
